"""
Analytics & monitoring data access.

Every workflow metric is derived from the `executions` collection written by
`run_and_record` (manual, scheduled and webhook runs), so the dashboards show
exactly what the engine did — no separate event stream to keep in sync.

`user_id=None` means platform-wide (admin); otherwise data is scoped to that user.
"""

import logging
import os
import statistics
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from firebase_admin import firestore

logger = logging.getLogger(__name__)

EXECUTIONS = "executions"
PROCESS_STARTED = time.time()
STALE_RUNNING_MS = 60 * 60 * 1000  # a "running" record older than 1h was cut off by a restart


# ---------------------------------------------------------------------------
# Pure helpers (no Firestore) — covered by tests/test_analytics_helpers.py
# ---------------------------------------------------------------------------

def to_ms(dt: datetime) -> int:
    """Naive datetimes are treated as UTC (the codebase uses datetime.utcnow())."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def from_ms(ms: float) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = round(p / 100 * (len(ordered) - 1))
    return float(ordered[max(0, min(len(ordered) - 1, k))])


def is_running(row: Dict[str, Any], now_ms: Optional[int] = None) -> bool:
    now_ms = now_ms or int(time.time() * 1000)
    return row.get("status") == "running" and now_ms - (row.get("startTime") or 0) < STALE_RUNNING_MS


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts, success rate, duration stats (ms) and token totals for a set of executions."""
    finished = [r for r in rows if r.get("status") in ("completed", "failed")]
    successful = sum(1 for r in finished if r.get("status") == "completed")
    durations = [float(r.get("duration") or 0) for r in finished]
    return {
        "total": len(finished),
        "successful": successful,
        "failed": len(finished) - successful,
        "running": sum(1 for r in rows if is_running(r)),
        "successRate": successful / len(finished) * 100 if finished else 0.0,
        "errorRate": (len(finished) - successful) / len(finished) * 100 if finished else 0.0,
        "avgDuration": statistics.mean(durations) if durations else 0.0,
        "minDuration": min(durations, default=0.0),
        "maxDuration": max(durations, default=0.0),
        "p95Duration": percentile(durations, 95),
        "tokens": sum(int((r.get("metadata") or {}).get("tokensUsed") or 0) for r in rows),
        "lastExecutedAt": from_ms(max(r.get("startTime") or 0 for r in rows)) if rows else None,
    }


def _bucket_start(dt: datetime, interval: str) -> datetime:
    dt = dt.replace(minute=0, second=0, microsecond=0)
    if interval in ("day", "week"):
        dt = dt.replace(hour=0)
    if interval == "week":
        dt -= timedelta(days=dt.weekday())
    return dt


def timeline(rows: List[Dict[str, Any]], start: datetime, end: datetime, interval: str = "hour",
             value=len) -> List[Dict[str, Any]]:
    """Bucket executions by hour/day/week, filling empty buckets so charts have no gaps.

    `value` maps the executions in a bucket to a number (default: count).
    """
    step = {"hour": timedelta(hours=1), "day": timedelta(days=1), "week": timedelta(weeks=1)}[interval]
    grouped: Dict[datetime, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        grouped[_bucket_start(from_ms(r.get("startTime") or 0), interval)].append(r)
    points, cursor, last = [], _bucket_start(start, interval), _bucket_start(end, interval)
    while cursor <= last:
        bucket = grouped.get(cursor, [])
        points.append({"timestamp": cursor.isoformat(), "count": value(bucket) if bucket else 0})
        cursor += step
    return points


def node_stats(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Per node-type call counts and latencies from execution node logs."""
    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"calls": 0, "failed": 0, "latencies": []})
    for r in rows:
        for log in r.get("nodeLogs") or []:
            s = stats[log.get("nodeType") or "unknown"]
            s["calls"] += 1
            s["failed"] += log.get("status") == "failed"
            s["latencies"].append(float(log.get("executionTimeMs") or 0))
    return stats


def bottlenecks(rows: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """Slowest / most failure-prone steps, per workflow node."""
    per_step: Dict[tuple, Dict[str, Any]] = {}
    wf_time: Dict[str, float] = defaultdict(float)
    for r in rows:
        wf_id = r.get("workflowId", "")
        for idx, log in enumerate(r.get("nodeLogs") or []):
            key = (wf_id, log.get("nodeId"))
            s = per_step.setdefault(key, {
                "workflowId": wf_id, "workflowName": r.get("workflowName") or wf_id,
                "stepName": log.get("nodeName") or log.get("nodeType") or "step",
                "nodeType": log.get("nodeType") or "", "stepIndex": idx,
                "durations": [], "failed": 0,
            })
            ms = float(log.get("executionTimeMs") or 0)
            s["durations"].append(ms)
            s["failed"] += log.get("status") == "failed"
            wf_time[wf_id] += ms

    result = []
    for s in per_step.values():
        total = sum(s["durations"])
        failure_rate = s["failed"] / len(s["durations"]) * 100
        result.append({
            "workflowId": s["workflowId"], "workflowName": s["workflowName"],
            "stepName": s["stepName"], "stepIndex": s["stepIndex"],
            "avgStepDuration": total / len(s["durations"]),
            "percentageOfTotalTime": total / wf_time[s["workflowId"]] * 100 if wf_time[s["workflowId"]] else 0.0,
            "failureRate": failure_rate,
            "recommendedAction": _recommendation(s["nodeType"], failure_rate),
        })
    result.sort(key=lambda b: (b["failureRate"] > 20, b["avgStepDuration"]), reverse=True)
    return result[:limit]


def _recommendation(node_type: str, failure_rate: float) -> str:
    if failure_rate > 20:
        return "Fails often — check its credentials and configuration in the node settings."
    if node_type in {"OpenAI", "ClaudeAI", "Gemini", "Groq", "LocalLLM"}:
        return "AI call dominates runtime — try a smaller/faster model or lower Max Tokens."
    if node_type in {"HTTPRequest", "HttpRequest"}:
        return "Slow external API — check the endpoint latency or cache its response."
    if node_type == "Delay":
        return "Intentional wait — reduce the delay if it is not required."
    return "No action needed."


# ---------------------------------------------------------------------------
# Firestore access
# ---------------------------------------------------------------------------

class AnalyticsDB:
    """Database operations for analytics and monitoring"""

    def __init__(self):
        self.db = firestore.client()
        self.events_collection = 'analytics_events'
        self.alerts_collection = 'analytics_alerts'

    # ==================== Executions (source of truth) ====================

    def executions(self, start: datetime, end: datetime, user_id: Optional[str] = None,
                   workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Executions in [start, end], newest first.

        One equality/range filter per query and the rest filtered in Python, so
        no composite Firestore indexes are needed.
        """
        # ponytail: reads every run of the user/workflow; add composite indexes + range queries at scale
        query = self.db.collection(EXECUTIONS)
        if workflow_id:
            query = query.where('workflowId', '==', workflow_id)
        elif user_id:
            query = query.where('userId', '==', user_id)
        else:
            query = query.where('startTime', '>=', to_ms(start))
        lo, hi = to_ms(start), to_ms(end)
        rows = [
            r for r in (d.to_dict() for d in query.stream())
            if lo <= (r.get('startTime') or 0) <= hi and (not user_id or r.get('userId') == user_id)
        ]
        rows.sort(key=lambda r: r.get('startTime') or 0, reverse=True)
        return rows

    def workflows(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.collection('workflows')
        if user_id:
            query = query.where('userId', '==', user_id)
        return [{**d.to_dict(), 'id': d.id} for d in query.stream()]

    # ==================== Event Tracking (custom events) ====================

    async def track_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track analytics event"""
        try:
            event_ref = self.db.collection(self.events_collection).document()
            event_data['id'] = event_ref.id
            event_data['createdAt'] = firestore.SERVER_TIMESTAMP
            if not event_data.get('timestamp'):
                event_data['timestamp'] = datetime.utcnow()
            event_ref.set(event_data)
            return {'success': True, 'eventId': event_ref.id, 'data': event_data}
        except Exception as e:
            logger.error(f"❌ Failed to track event: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Query custom analytics events"""
        try:
            query = self.db.collection(self.events_collection)
            if user_id:
                query = query.where('userId', '==', user_id)
            events = [d.to_dict() for d in query.stream()]

            def keep(e):
                ts = e.get('timestamp')
                ts = ts.replace(tzinfo=None) if isinstance(ts, datetime) else None
                return (
                    (not start_date or (ts and ts >= start_date))
                    and (not end_date or (ts and ts <= end_date))
                    and (not workflow_id or e.get('workflowId') == workflow_id)
                    and (not event_type or e.get('eventType') == event_type)
                )

            events = sorted(filter(keep, events), key=lambda e: e.get('timestamp'), reverse=True)
            return {'success': True, 'events': events[offset:offset + limit], 'total': len(events)}
        except Exception as e:
            logger.error(f"❌ Failed to get events: {str(e)}")
            return {'success': False, 'error': str(e), 'events': [], 'total': 0}

    async def get_event_timeline(self, start_date: datetime, end_date: datetime, interval: str = 'hour',
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """Execution activity over time"""
        try:
            rows = self.executions(start_date, end_date, user_id)
            return {
                'success': True,
                'timeline': timeline(rows, start_date, end_date, interval),
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            }
        except Exception as e:
            logger.error(f"❌ Failed to get event timeline: {str(e)}")
            return {'success': False, 'error': str(e), 'timeline': []}

    # ==================== Workflow Analytics ====================

    async def get_workflow_metrics(self, workflow_id: str, start_date: datetime, end_date: datetime,
                                   user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            rows = self.executions(start_date, end_date, user_id, workflow_id)
            s = summarize(rows)
            return {
                'success': True,
                'rows': rows,
                'metrics': {
                    'workflowId': workflow_id,
                    'totalExecutions': s['total'],
                    'successfulExecutions': s['successful'],
                    'failedExecutions': s['failed'],
                    'successRate': s['successRate'],
                    'avgExecutionTime': s['avgDuration'],
                    'minExecutionTime': s['minDuration'],
                    'maxExecutionTime': s['maxDuration'],
                    'p95ExecutionTime': s['p95Duration'],
                    'totalTokens': s['tokens'],
                    'lastExecutedAt': s['lastExecutedAt'],
                },
            }
        except Exception as e:
            logger.error(f"❌ Failed to get workflow metrics: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_workflow_executions(
        self,
        workflow_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            rows = self.executions(start_date or datetime(1970, 1, 1), end_date or datetime.utcnow(),
                                   user_id, workflow_id)
            if status:
                rows = [r for r in rows if r.get('status') == status]
            executions = [{
                'id': r.get('id', ''),
                'workflowId': r.get('workflowId', ''),
                'workflowName': r.get('workflowName') or '',
                'status': r.get('status', ''),
                'startTime': from_ms(r.get('startTime') or 0),
                'endTime': from_ms(r['endTime']) if r.get('endTime') else None,
                'duration': r.get('duration'),
                'errorMessage': r.get('error'),
                'stepsCompleted': r.get('stepsCompleted') or 0,
                'totalSteps': r.get('totalSteps') or len(r.get('nodeLogs') or []),
                'triggeredBy': r.get('trigger') or 'manual',
            } for r in rows[offset:offset + limit]]
            return {'success': True, 'executions': executions, 'total': len(rows)}
        except Exception as e:
            logger.error(f"❌ Failed to get workflow executions: {str(e)}")
            return {'success': False, 'error': str(e), 'executions': [], 'total': 0}

    async def get_all_workflows_performance(self, start_date: datetime, end_date: datetime,
                                            user_id: Optional[str] = None) -> Dict[str, Any]:
        """Current vs previous period, per workflow"""
        try:
            span = end_date - start_date
            current = self.executions(start_date, end_date, user_id)
            previous = self.executions(start_date - span, start_date, user_id)
            names = {w['id']: w.get('name', 'Untitled') for w in self.workflows(user_id)}

            by_wf_now, by_wf_prev = defaultdict(list), defaultdict(list)
            for r in current:
                by_wf_now[r.get('workflowId')].append(r)
            for r in previous:
                by_wf_prev[r.get('workflowId')].append(r)

            def change(now, before):
                return (now - before) / before * 100 if before else 0.0

            comparisons = []
            for wf_id in set(by_wf_now) | set(by_wf_prev):
                now, before = summarize(by_wf_now[wf_id]), summarize(by_wf_prev[wf_id])
                comparisons.append({
                    'workflowId': wf_id,
                    'workflowName': names.get(wf_id) or (by_wf_now[wf_id] or by_wf_prev[wf_id])[0].get('workflowName') or wf_id,
                    'currentPeriodExecutions': now['total'],
                    'previousPeriodExecutions': before['total'],
                    'executionChange': change(now['total'], before['total']),
                    'currentSuccessRate': now['successRate'],
                    'previousSuccessRate': before['successRate'],
                    'successRateChange': now['successRate'] - before['successRate'],
                    'avgExecutionTime': now['avgDuration'],
                    'executionTimeChange': change(now['avgDuration'], before['avgDuration']),
                })
            comparisons.sort(key=lambda c: c['currentPeriodExecutions'], reverse=True)
            return {'success': True, 'comparisons': comparisons,
                    'period': f"{start_date.isoformat()} to {end_date.isoformat()}"}
        except Exception as e:
            logger.error(f"❌ Failed to get workflows performance: {str(e)}")
            return {'success': False, 'error': str(e), 'comparisons': []}

    async def get_bottlenecks(self, start_date: datetime, end_date: datetime, user_id: Optional[str] = None,
                              workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return bottlenecks(self.executions(start_date, end_date, user_id, workflow_id))

    async def get_node_metrics(self, start_date: datetime, end_date: datetime,
                               user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Latency / failure stats per node type — every AI provider and integration call."""
        metrics = []
        for node_type, s in node_stats(self.executions(start_date, end_date, user_id)).items():
            lat = s['latencies']
            metrics.append({
                'endpoint': node_type,
                'method': 'NODE',
                'totalCalls': s['calls'],
                'successfulCalls': s['calls'] - s['failed'],
                'failedCalls': s['failed'],
                'avgLatency': statistics.mean(lat) if lat else 0.0,
                'p50Latency': percentile(lat, 50),
                'p95Latency': percentile(lat, 95),
                'p99Latency': percentile(lat, 99),
                'minLatency': min(lat, default=0.0),
                'maxLatency': max(lat, default=0.0),
                'errorRate': s['failed'] / s['calls'] * 100 if s['calls'] else 0.0,
            })
        metrics.sort(key=lambda m: m['totalCalls'], reverse=True)
        return metrics

    # ==================== System Metrics ====================

    async def get_system_health(self) -> Dict[str, Any]:
        """Platform health over the last 24 hours of executions"""
        try:
            now = datetime.utcnow()
            s = summarize(self.executions(now - timedelta(hours=24), now))
            status = 'down' if s['errorRate'] > 25 else 'degraded' if s['errorRate'] > 10 else 'healthy'
            return {
                'success': True,
                'status': status,
                'uptime': time.time() - PROCESS_STARTED,
                'uptimePercentage': 100.0 - s['errorRate'],
                'totalRequests': s['total'],
                'successfulRequests': s['successful'],
                'failedRequests': s['failed'],
                'avgResponseTime': s['avgDuration'],
                'errorRate': s['errorRate'],
                'activeConnections': s['running'],
                'timestamp': now,
            }
        except Exception as e:
            logger.error(f"❌ Failed to get system health: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_resource_usage(self) -> Dict[str, Any]:
        """CPU / memory / disk of the backend host"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            return {
                'success': True,
                'metrics': {
                    'cpuUsage': psutil.cpu_percent(interval=0.2),
                    'memoryUsage': mem.percent,
                    'memoryUsedMB': (mem.total - mem.available) / 2**20,
                    'memoryTotalMB': mem.total / 2**20,
                    'diskUsage': disk.percent,
                    'diskUsedGB': disk.used / 2**30,
                    'diskTotalGB': disk.total / 2**30,
                    'activeThreads': threading.active_count(),
                    'timestamp': datetime.utcnow(),
                },
            }
        except Exception as e:
            logger.error(f"❌ Failed to get resource usage: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== User Activity ====================

    async def get_user_activity_metrics(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Per-user activity: a session is a day with activity, its length the first→last run span"""
        try:
            end_date = end_date or datetime.utcnow()
            start_date = start_date or end_date - timedelta(days=30)
            lo, hi = to_ms(start_date), to_ms(end_date)
            rows = self.executions(start_date, end_date, user_id)

            created = defaultdict(int)
            for w in self.workflows(user_id):
                ts = w.get('createdAt')
                if isinstance(ts, datetime) and lo <= to_ms(ts) <= hi:
                    created[w.get('userId')] += 1

            connections = defaultdict(int)
            for doc in self.db.collection_group('credentials').stream():
                owner = doc.reference.parent.parent
                if owner is not None:
                    connections[owner.id] += 1

            by_user: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for r in rows:
                by_user[r.get('userId')].append(r)

            metrics = []
            for uid, user_rows in by_user.items():
                days: Dict[str, List[int]] = defaultdict(list)
                for r in user_rows:
                    days[from_ms(r['startTime']).date().isoformat()].append(r['startTime'])
                spans = [(max(t) - min(t)) / 60000 for t in days.values()]
                metrics.append({
                    'userId': uid,
                    'totalSessions': len(days),
                    'totalActions': len(user_rows),
                    'avgSessionDuration': statistics.mean(spans) if spans else 0.0,
                    'lastActive': from_ms(max(r['startTime'] for r in user_rows)),
                    'workflowsCreated': created[uid],
                    'workflowsExecuted': len({r.get('workflowId') for r in user_rows}),
                    'integrationsConnected': connections[uid],
                    'apiCallsMade': sum(len(r.get('nodeLogs') or []) for r in user_rows),
                })
            metrics.sort(key=lambda m: m['lastActive'], reverse=True)
            return {'success': True, 'metrics': metrics[offset:offset + limit], 'total': len(metrics)}
        except Exception as e:
            logger.error(f"❌ Failed to get user activity metrics: {str(e)}")
            return {'success': False, 'error': str(e), 'metrics': [], 'total': 0}

    def count_users(self) -> int:
        return sum(1 for _ in self.db.collection('users').select([]).stream())

    # ==================== Dashboard ====================

    async def get_dashboard_overview(self, start_date: datetime, end_date: datetime,
                                     user_id: Optional[str] = None) -> Dict[str, Any]:
        try:
            rows = self.executions(start_date, end_date, user_id)
            s = summarize(rows)
            workflows = self.workflows(user_id)
            executed = {r.get('workflowId') for r in rows}
            active = [w for w in workflows if w['id'] in executed or (w.get('schedule') or {}).get('active')]

            from nodes.registry import get_registry
            used_types = {n.get('type') for w in workflows for n in w.get('nodes', [])}
            if user_id:
                connections = sum(1 for _ in self.db.collection('users').document(user_id)
                                  .collection('credentials').stream())
                users = {'total': 1, 'active': 1 if rows else 0, 'new': 0}
            else:
                connections = sum(1 for _ in self.db.collection_group('credentials').stream())
                users = {'total': self.count_users(), 'active': len({r.get('userId') for r in rows}), 'new': 0}

            health = await self.get_system_health()
            return {
                'success': True,
                'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
                'workflows': {'total': len(workflows), 'active': len(active), 'success_rate': s['successRate']},
                'executions': {'total': s['total'], 'successful': s['successful'], 'failed': s['failed'],
                               'running': s['running'], 'tokens': s['tokens'],
                               'avg_duration_ms': s['avgDuration']},
                'users': users,
                'integrations': {'total': len(get_registry()), 'active': len(used_types),
                                 'connections': connections},
                'system': {'health': health.get('status', 'unknown'),
                           'uptime': health.get('uptimePercentage', 0.0),
                           'error_rate': health.get('errorRate', 0.0)},
                'recentActivity': [{
                    'id': r.get('id'),
                    'type': 'execution',
                    'name': f"{r.get('workflowName') or 'Workflow'} — {r.get('status')}",
                    'timestamp': from_ms(r.get('startTime') or 0),
                    'user': r.get('userId'),
                    'trigger': r.get('trigger') or 'manual',
                } for r in rows[:10]],
                'timestamp': datetime.utcnow(),
            }
        except Exception as e:
            logger.error(f"❌ Failed to get dashboard overview: {str(e)}")
            return {'success': False, 'error': str(e)}

    # ==================== Alerts ====================

    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            alert_ref = self.db.collection(self.alerts_collection).document()
            alert_data.update(id=alert_ref.id, timestamp=firestore.SERVER_TIMESTAMP,
                              acknowledged=False, resolvedAt=None)
            alert_ref.set(alert_data)
            return {'success': True, 'alertId': alert_ref.id}
        except Exception as e:
            logger.error(f"❌ Failed to create alert: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_alerts(
        self,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            query = self.db.collection(self.alerts_collection)
            if user_id:
                query = query.where('userId', '==', user_id)
            alerts = [
                a for a in (d.to_dict() for d in query.stream())
                if (not severity or a.get('severity') == severity)
                and (not category or a.get('category') == category)
                and (acknowledged is None or a.get('acknowledged') == acknowledged)
                and a.get('timestamp') is not None
            ]
            alerts.sort(key=lambda a: a['timestamp'], reverse=True)
            alerts = alerts[:limit]
            return {
                'success': True,
                'alerts': alerts,
                'total': len(alerts),
                'criticalCount': sum(1 for a in alerts if a.get('severity') == 'critical'),
                'warningCount': sum(1 for a in alerts if a.get('severity') == 'warning'),
            }
        except Exception as e:
            logger.error(f"❌ Failed to get alerts: {str(e)}")
            return {'success': True, 'error': str(e), 'alerts': [], 'total': 0, 'criticalCount': 0, 'warningCount': 0}

    async def acknowledge_alert(self, alert_id: str, user_id: str, admin: bool) -> bool:
        ref = self.db.collection(self.alerts_collection).document(alert_id)
        doc = ref.get()
        if not doc.exists or (not admin and doc.to_dict().get('userId') != user_id):
            return False
        ref.update({'acknowledged': True, 'acknowledgedBy': user_id})
        return True


# Global instance
analytics_db = AnalyticsDB()
