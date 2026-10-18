import logging
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.db.analytics_db import analytics_db, from_ms, is_running, summarize, timeline, to_ms
from app.models.analytics_models import TimeRange

logger = logging.getLogger(__name__)

# metric name → value of one time bucket of executions (for trend analysis)
TREND_METRICS = {
    "executions": len,
    "success_rate": lambda rows: summarize(rows)["successRate"],
    "error_rate": lambda rows: summarize(rows)["errorRate"],
    "duration": lambda rows: summarize(rows)["avgDuration"],
    "tokens": lambda rows: summarize(rows)["tokens"],
}


class AnalyticsService:
    """Service layer for analytics and monitoring.

    `user_id=None` → platform-wide (admins); otherwise scoped to that user.
    """

    def __init__(self):
        self.db = analytics_db

    # ==================== Helper Methods ====================

    def parse_time_range(self, time_range: TimeRange, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """Parse time range to start and end dates"""
        now = datetime.utcnow()
        if time_range == TimeRange.CUSTOM:
            return start_date or (now - timedelta(days=7)), end_date or now
        return now - {
            TimeRange.LAST_HOUR: timedelta(hours=1),
            TimeRange.LAST_24_HOURS: timedelta(hours=24),
            TimeRange.LAST_7_DAYS: timedelta(days=7),
            TimeRange.LAST_30_DAYS: timedelta(days=30),
            TimeRange.LAST_90_DAYS: timedelta(days=90),
        }.get(time_range, timedelta(days=7)), now

    @staticmethod
    def _interval(start: datetime, end: datetime) -> str:
        return "hour" if end - start <= timedelta(days=2) else "day"

    # ==================== Event Tracking ====================

    async def track_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.db.track_event(event_data)

    async def get_events(self, time_range: TimeRange = TimeRange.LAST_24_HOURS, start_date=None, end_date=None,
                         user_id=None, workflow_id=None, event_type=None, limit: int = 100, offset: int = 0):
        start, end = self.parse_time_range(time_range, start_date, end_date)
        return await self.db.get_events(start, end, user_id, workflow_id, event_type, limit, offset)

    async def get_event_timeline(self, time_range: TimeRange = TimeRange.LAST_24_HOURS, start_date=None,
                                 end_date=None, interval: str = 'hour', user_id: Optional[str] = None):
        start, end = self.parse_time_range(time_range, start_date, end_date)
        return await self.db.get_event_timeline(start, end, interval, user_id)

    # ==================== Workflow Analytics ====================

    async def get_workflow_overview(self, time_range: TimeRange = TimeRange.LAST_30_DAYS, start_date=None,
                                    end_date=None, user_id: Optional[str] = None) -> Dict[str, Any]:
        start, end = self.parse_time_range(time_range, start_date, end_date)
        s = summarize(self.db.executions(start, end, user_id))
        return {
            'success': True,
            'overview': {
                'totalExecutions': s['total'],
                'successfulExecutions': s['successful'],
                'failedExecutions': s['failed'],
                'runningExecutions': s['running'],
                'successRate': s['successRate'],
                'avgExecutionTimeMs': s['avgDuration'],
                'totalTokens': s['tokens'],
                'period': f"{start.isoformat()} to {end.isoformat()}",
            },
        }

    async def get_workflow_metrics(self, workflow_id: str, workflow_name: str,
                                   time_range: TimeRange = TimeRange.LAST_30_DAYS, start_date=None, end_date=None,
                                   user_id: Optional[str] = None) -> Dict[str, Any]:
        start, end = self.parse_time_range(time_range, start_date, end_date)
        result = await self.db.get_workflow_metrics(workflow_id, start, end, user_id)
        if not result['success']:
            return result
        metrics = {**result['metrics'], 'workflowName': workflow_name}
        return {
            'success': True,
            'metrics': metrics,
            'timeSeries': timeline(result['rows'], start, end, self._interval(start, end)),
            'period': f"{start.isoformat()} to {end.isoformat()}",
        }

    async def get_workflow_executions(self, workflow_id: str, time_range: TimeRange = TimeRange.LAST_7_DAYS,
                                      start_date=None, end_date=None, status=None, page: int = 1,
                                      page_size: int = 50, user_id: Optional[str] = None):
        start, end = self.parse_time_range(time_range, start_date, end_date)
        return await self.db.get_workflow_executions(workflow_id, start, end, status, page_size,
                                                     (page - 1) * page_size, user_id)

    async def get_workflow_performance_comparison(self, time_range: TimeRange = TimeRange.LAST_30_DAYS,
                                                  start_date=None, end_date=None, user_id: Optional[str] = None):
        start, end = self.parse_time_range(time_range, start_date, end_date)
        return await self.db.get_all_workflows_performance(start, end, user_id)

    async def get_workflow_success_rates(self, time_range: TimeRange = TimeRange.LAST_30_DAYS,
                                         user_id: Optional[str] = None) -> Dict[str, Any]:
        start, end = self.parse_time_range(time_range)
        performance = await self.db.get_all_workflows_performance(start, end, user_id)
        if not performance['success']:
            return performance
        success_rates = sorted(
            (
                {
                    'workflowId': p['workflowId'],
                    'workflowName': p['workflowName'],
                    'successRate': p['currentSuccessRate'],
                    'totalExecutions': p['currentPeriodExecutions'],
                    'avgExecutionTime': p['avgExecutionTime'],
                }
                for p in performance['comparisons'] if p['currentPeriodExecutions']
            ),
            key=lambda x: (x['successRate'], x['totalExecutions']),
            reverse=True,
        )
        return {'success': True, 'successRates': success_rates, 'period': performance['period']}

    async def get_bottlenecks(self, time_range: TimeRange, workflow_id: Optional[str] = None,
                              user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        start, end = self.parse_time_range(time_range)
        return await self.db.get_bottlenecks(start, end, user_id, workflow_id)

    # ==================== System Metrics ====================

    async def get_system_health(self) -> Dict[str, Any]:
        return await self.db.get_system_health()

    async def get_resource_usage(self) -> Dict[str, Any]:
        return await self.db.get_resource_usage()

    async def get_api_metrics(self, time_range: TimeRange = TimeRange.LAST_24_HOURS,
                              user_id: Optional[str] = None) -> Dict[str, Any]:
        """Per node-type call metrics — latency of every AI provider / integration used in workflows"""
        start, end = self.parse_time_range(time_range)
        return {'success': True, 'metrics': await self.db.get_node_metrics(start, end, user_id),
                'timestamp': datetime.utcnow()}

    async def get_error_rate_metrics(self, time_range: TimeRange = TimeRange.LAST_24_HOURS,
                                     user_id: Optional[str] = None) -> Dict[str, Any]:
        """Failed executions grouped by the node type and workflow that failed"""
        start, end = self.parse_time_range(time_range)
        rows = self.db.executions(start, end, user_id)
        failed = [r for r in rows if r.get('status') == 'failed']

        by_type, by_workflow, messages = Counter(), Counter(), Counter()
        critical = 0
        for r in failed:
            failing = next((log for log in r.get('nodeLogs') or [] if log.get('status') == 'failed'), {})
            by_type[failing.get('nodeType') or 'Engine'] += 1
            by_workflow[r.get('workflowName') or r.get('workflowId') or 'unknown'] += 1
            error = (r.get('error') or 'Unknown error')[:200]
            messages[error] += 1
            critical += error.startswith('Unexpected error') or not failing  # crash, not a handled failure

        finished = sum(1 for r in rows if r.get('status') in ('completed', 'failed'))
        return {
            'success': True,
            'totalErrors': len(failed),
            'errorRate': len(failed) / finished * 100 if finished else 0.0,
            'errorsByType': dict(by_type),
            'errorsByEndpoint': dict(by_workflow),
            'criticalErrors': critical,
            'warningErrors': len(failed) - critical,
            'topErrors': [{'type': msg, 'count': n} for msg, n in messages.most_common(10)],
            'timestamp': datetime.utcnow(),
        }

    async def get_uptime(self, time_range: TimeRange = TimeRange.LAST_30_DAYS) -> Dict[str, Any]:
        """Reliability over the period: an incident is an hour where most runs failed (≥3 runs)."""
        start, end = self.parse_time_range(time_range)
        hours = defaultdict(list)
        for r in self.db.executions(start, end):
            hours[from_ms(r.get('startTime') or 0).replace(minute=0, second=0, microsecond=0)].append(r)
        incident_hours = sorted(
            h for h, rows in hours.items()
            if len(rows) >= 3 and summarize(rows)['errorRate'] >= 50
        )
        downtime = len(incident_hours) * 3600
        period = max((end - start).total_seconds(), 1)
        return {
            'success': True,
            'uptime': 100 - downtime / period * 100,
            'totalDowntime': downtime,
            'incidents': len(incident_hours),
            'lastIncident': incident_hours[-1] if incident_hours else None,
            'timeRange': time_range.value,
        }

    # ==================== User Activity ====================

    async def get_user_activity_metrics(self, user_id: Optional[str] = None,
                                        time_range: TimeRange = TimeRange.LAST_30_DAYS,
                                        page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        start, end = self.parse_time_range(time_range)
        return await self.db.get_user_activity_metrics(user_id, start, end, page_size, (page - 1) * page_size)

    async def get_user_engagement_metrics(self, time_range: TimeRange = TimeRange.LAST_30_DAYS) -> Dict[str, Any]:
        """Active = ran at least one workflow; new = first run inside the period."""
        start, end = self.parse_time_range(time_range)
        total_users = self.db.count_users()
        history = self.db.executions(start - timedelta(days=365), end)
        first_seen: Dict[str, int] = {}
        for r in history:
            uid = r.get('userId')
            first_seen[uid] = min(first_seen.get(uid, r['startTime']), r['startTime'])

        period = [r for r in history if r['startTime'] >= to_ms(start)]
        now_ms = to_ms(end)
        active = {r.get('userId') for r in period}
        daily = {r.get('userId') for r in period if now_ms - r['startTime'] <= 86_400_000}
        weekly = {r.get('userId') for r in period if now_ms - r['startTime'] <= 7 * 86_400_000}
        sessions = {(r.get('userId'), from_ms(r['startTime']).date()) for r in period}
        new_users = sum(1 for uid in active if first_seen[uid] >= to_ms(start))

        return {
            'success': True,
            'totalUsers': total_users,
            'activeUsers': len(active),
            'dailyActiveUsers': len(daily),
            'weeklyActiveUsers': len(weekly),
            'monthlyActiveUsers': len(active),
            'newUsers': new_users,
            'returningUsers': len(active) - new_users,
            'avgSessionsPerUser': len(sessions) / len(active) if active else 0.0,
            'avgActionsPerUser': len(period) / len(active) if active else 0.0,
            'engagementRate': len(active) / total_users * 100 if total_users else 0.0,
        }

    async def get_user_retention(self, cohort: Optional[str] = None) -> Dict[str, Any]:
        """Users whose first run fell in `cohort` (YYYY-MM) and who ran again in weeks 1–4 after it."""
        now = datetime.utcnow()
        cohort = cohort or now.strftime('%Y-%m')
        cohort_start = datetime.strptime(cohort, '%Y-%m')
        cohort_end = (cohort_start + timedelta(days=32)).replace(day=1)

        runs: Dict[str, List[int]] = defaultdict(list)
        for r in self.db.executions(cohort_start - timedelta(days=365), now):
            runs[r.get('userId')].append(r['startTime'])
        members = {uid: min(ts) for uid, ts in runs.items() if to_ms(cohort_start) <= min(ts) < to_ms(cohort_end)}

        week_ms = 7 * 86_400_000
        retained = {
            f'week{w}': sum(
                1 for uid, first in members.items()
                if any(first + w * week_ms <= t < first + (w + 1) * week_ms for t in runs[uid])
            )
            for w in range(1, 5)
        }
        lifetimes = [(max(runs[uid]) - first) / 86_400_000 for uid, first in members.items()]
        total = len(members)
        return {
            'success': True,
            'cohort': cohort,
            'totalUsers': total,
            'retainedUsers': retained,
            'retentionRate': {k: v / total if total else 0.0 for k, v in retained.items()},
            'churnRate': 1 - retained['week4'] / total if total else 0.0,
            'avgLifetime': statistics.mean(lifetimes) if lifetimes else 0.0,
        }

    # ==================== Dashboard ====================

    async def get_dashboard_overview(self, time_range: TimeRange = TimeRange.LAST_24_HOURS,
                                     user_id: Optional[str] = None) -> Dict[str, Any]:
        start, end = self.parse_time_range(time_range)
        return await self.db.get_dashboard_overview(start, end, user_id)

    async def get_real_time_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Live view over the last hour of executions"""
        import psutil
        from services.scheduler import get_scheduler

        now = datetime.utcnow()
        hour = self.db.executions(now - timedelta(hours=1), now, user_id)
        s = summarize(hour)
        now_ms = to_ms(now)
        last_minute = sum(1 for r in hour if now_ms - r['startTime'] <= 60_000)

        own_workflows = None if user_id is None else {w['id'] for w in self.db.workflows(user_id)}
        scheduled = sum(
            1 for job in get_scheduler().get_all_jobs().values()
            if job.status.value == 'running' and (own_workflows is None or job.workflow_id in own_workflows)
        )
        platform = self.db.executions(now - timedelta(minutes=15), now)
        return {
            'success': True,
            'activeExecutions': sum(1 for r in hour if is_running(r, now_ms)),
            'executionsPerMinute': round(len(hour) / 60),
            'avgExecutionTime': s['avgDuration'],
            'currentErrorRate': s['errorRate'],
            'activeUsers': len({r.get('userId') for r in platform}),
            'requestsPerSecond': last_minute / 60,
            'queuedJobs': scheduled,
            'systemLoad': psutil.cpu_percent(interval=None),
            'timestamp': now,
        }

    async def get_trends(self, metric: str, time_range: TimeRange = TimeRange.LAST_7_DAYS,
                         user_id: Optional[str] = None) -> Dict[str, Any]:
        start, end = self.parse_time_range(time_range)
        value = TREND_METRICS.get(metric, len)
        points = timeline(self.db.executions(start, end, user_id), start, end, self._interval(start, end), value)
        data_points = [{'timestamp': p['timestamp'], 'value': p['count']} for p in points]

        # Compare the average of the first and second half — robust to empty edge buckets
        half = len(data_points) // 2
        first = statistics.mean(p['value'] for p in data_points[:half]) if half else 0
        second = statistics.mean(p['value'] for p in data_points[half:]) if data_points[half:] else 0
        change = (second - first) / first * 100 if first else (100.0 if second else 0.0)
        trend = 'increasing' if change > 5 else 'decreasing' if change < -5 else 'stable'
        insight = {
            'increasing': f"{metric} increased by {abs(change):.1f}% over the period",
            'decreasing': f"{metric} decreased by {abs(change):.1f}% over the period",
            'stable': f"{metric} remained stable over the period",
        }[trend]
        return {
            'success': True,
            'metric': metric,
            'timeRange': time_range.value,
            'dataPoints': data_points,
            'trend': trend,
            'changePercentage': change,
            'insights': [insight],
        }

    async def get_widget(self, widget_type: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        now = datetime.utcnow()
        week = self.db.executions(now - timedelta(days=7), now, user_id)
        if widget_type == 'execution_chart':
            points = timeline(week, now - timedelta(days=6), now, 'day')
            return {
                'labels': [datetime.fromisoformat(p['timestamp']).strftime('%a') for p in points],
                'values': [p['count'] for p in points],
            }
        if widget_type == 'success_rate':
            previous = summarize(self.db.executions(now - timedelta(days=14), now - timedelta(days=7), user_id))
            rate = summarize(week)['successRate']
            change = rate - previous['successRate']
            return {'rate': rate, 'change': change, 'trend': 'up' if change >= 0 else 'down'}
        return None

    def export_rows(self, time_range: TimeRange, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        start, end = self.parse_time_range(time_range)
        return [{
            'executionId': r.get('id'),
            'workflowId': r.get('workflowId'),
            'workflowName': r.get('workflowName'),
            'userId': r.get('userId'),
            'trigger': r.get('trigger') or 'manual',
            'status': r.get('status'),
            'startTime': from_ms(r.get('startTime') or 0).isoformat(),
            'durationMs': r.get('duration'),
            'tokensUsed': (r.get('metadata') or {}).get('tokensUsed', 0),
            'stepsCompleted': r.get('stepsCompleted'),
            'error': r.get('error') or '',
        } for r in self.db.executions(start, end, user_id)]

    # ==================== Alerts ====================

    async def get_alerts(self, severity=None, category=None, acknowledged=None, limit: int = 50,
                         user_id: Optional[str] = None) -> Dict[str, Any]:
        return await self.db.get_alerts(severity, category, acknowledged, limit, user_id)

    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.db.create_alert(alert_data)

    async def acknowledge_alert(self, alert_id: str, user_id: str, admin: bool) -> bool:
        return await self.db.acknowledge_alert(alert_id, user_id, admin)


# Global instance
analytics_service = AnalyticsService()
