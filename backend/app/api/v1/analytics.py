"""
Analytics & Monitoring API.

All numbers are computed from real execution records (see app/db/analytics_db.py).
- /workflows/* and /dashboard/*: scoped to the caller; admins see the whole platform.
- /system/* and /users/*: platform-wide, admins and managers (analytics:platform).
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.core.auth_dependency import get_current_user, has_permission, require_permission
from app.core.security import rate_limit
from app.models.analytics_models import *
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics & Monitoring"])

PLATFORM = require_permission("analytics:platform")


def scope(user: dict) -> Optional[str]:
    """None = platform-wide for admins/managers, otherwise the caller's uid."""
    return None if has_permission(user, "analytics:platform") else user["uid"]


def _ok(result: dict, status_code: int = 500) -> dict:
    if not result.get('success'):
        raise HTTPException(status_code=status_code, detail=result.get('error', 'Analytics query failed'))
    return result


# ==================== Workflow Analytics ====================

@router.get("/workflows/overview")
@rate_limit(requests_per_minute=50)
async def get_workflow_overview(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None)
):
    """Execution totals, success rate, average duration and token usage"""
    return _ok(await analytics_service.get_workflow_overview(timeRange, startDate, endDate, scope(user)))


@router.get("/workflows/performance", response_model=WorkflowPerformanceResponse)
@rate_limit(requests_per_minute=30)
async def get_workflow_performance_comparison(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None)
):
    """Each workflow's current period vs the previous period of equal length"""
    result = _ok(await analytics_service.get_workflow_performance_comparison(timeRange, startDate, endDate, scope(user)))
    return WorkflowPerformanceResponse(
        success=True,
        comparisons=[WorkflowPerformanceComparison(**c) for c in result['comparisons']],
        period=result['period'],
    )


@router.get("/workflows/success-rate")
@rate_limit(requests_per_minute=50)
async def get_workflow_success_rates(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS)
):
    """Success rate per workflow"""
    return _ok(await analytics_service.get_workflow_success_rates(timeRange, scope(user)))


@router.get("/workflows/top-performers")
@rate_limit(requests_per_minute=50)
async def get_top_performing_workflows(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS),
    limit: int = Query(10, ge=1, le=50)
):
    """Best performing workflows"""
    result = _ok(await analytics_service.get_workflow_success_rates(timeRange, scope(user)))
    return {'success': True, 'topPerformers': result['successRates'][:limit], 'period': result['period']}


@router.get("/workflows/node-metrics")
@rate_limit(requests_per_minute=50)
async def get_node_metrics(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS)
):
    """Call volume, latency and failure rate per node type on the caller's own runs —
    e.g. compares how fast OpenAI, Gemini, Groq and a local model answered"""
    return await analytics_service.get_api_metrics(timeRange, scope(user))


@router.get("/workflows/bottlenecks")
@rate_limit(requests_per_minute=30)
async def identify_workflow_bottlenecks(
    request: Request,
    user: dict = Depends(get_current_user),
    workflowId: Optional[str] = Query(None),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS)
):
    """Slowest and most failure-prone workflow steps, from per-node execution logs"""
    bottlenecks = await analytics_service.get_bottlenecks(timeRange, workflowId, scope(user))
    return {
        'success': True,
        'bottlenecks': [WorkflowBottleneck(**b) for b in bottlenecks],
        'timeRange': timeRange.value,
    }


@router.get("/workflows/{workflow_id}/metrics", response_model=WorkflowAnalyticsResponse)
@rate_limit(requests_per_minute=50)
async def get_workflow_metrics(
    request: Request,
    workflow_id: str,
    user: dict = Depends(get_current_user),
    workflowName: str = Query(""),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None)
):
    """Detailed metrics and execution time series for one workflow"""
    result = _ok(await analytics_service.get_workflow_metrics(
        workflow_id, workflowName, timeRange, startDate, endDate, scope(user)
    ), status_code=404)
    return WorkflowAnalyticsResponse(
        success=True,
        metrics=WorkflowMetrics(**result['metrics']),
        timeSeries=[TimeSeriesDataPoint(timestamp=t['timestamp'], value=t['count']) for t in result['timeSeries']],
        period=result['period'],
    )


@router.get("/workflows/{workflow_id}/executions", response_model=WorkflowExecutionsResponse)
@rate_limit(requests_per_minute=50)
async def get_workflow_executions(
    request: Request,
    workflow_id: str,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_7_DAYS),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100)
):
    """Execution history of one workflow"""
    result = _ok(await analytics_service.get_workflow_executions(
        workflow_id, timeRange, startDate, endDate, status, page, pageSize, scope(user)
    ))
    return WorkflowExecutionsResponse(
        success=True,
        executions=[WorkflowExecution(**e) for e in result['executions']],
        total=result['total'],
        page=page,
        pageSize=pageSize,
    )


# ==================== System Metrics (admin / manager) ====================

@router.get("/system/health", response_model=SystemHealthResponse)
@rate_limit(requests_per_minute=100)
async def get_system_health(request: Request, user: dict = Depends(PLATFORM)):
    """Platform health over the last 24 hours"""
    return SystemHealthResponse(**_ok(await analytics_service.get_system_health()))


@router.get("/system/resource-usage", response_model=ResourceUsageMetrics)
@rate_limit(requests_per_minute=100)
async def get_resource_usage(request: Request, user: dict = Depends(PLATFORM)):
    """CPU, memory and disk of the backend host"""
    return ResourceUsageMetrics(**_ok(await analytics_service.get_resource_usage())['metrics'])


@router.get("/system/api-metrics")
@rate_limit(requests_per_minute=50)
async def get_api_metrics(
    request: Request,
    user: dict = Depends(PLATFORM),
    timeRange: TimeRange = Query(TimeRange.LAST_24_HOURS)
):
    """Call volume and latency per node type (AI providers, HTTP, integrations)"""
    return await analytics_service.get_api_metrics(timeRange)


@router.get("/system/error-rate", response_model=ErrorRateMetrics)
@rate_limit(requests_per_minute=50)
async def get_error_rate_metrics(
    request: Request,
    user: dict = Depends(PLATFORM),
    timeRange: TimeRange = Query(TimeRange.LAST_24_HOURS)
):
    """Failed executions grouped by failing node type and workflow"""
    return ErrorRateMetrics(**await analytics_service.get_error_rate_metrics(timeRange))


@router.get("/system/uptime")
@rate_limit(requests_per_minute=50)
async def get_system_uptime(
    request: Request,
    user: dict = Depends(PLATFORM),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS)
):
    """Reliability: hours where most executions failed count as incidents"""
    return await analytics_service.get_uptime(timeRange)


# ==================== User Activity (admin / manager) ====================

@router.get("/users/activity", response_model=UserActivityResponse)
@rate_limit(requests_per_minute=50)
async def get_user_activity(
    request: Request,
    user: dict = Depends(PLATFORM),
    userId: Optional[str] = Query(None),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=100)
):
    """Per-user activity derived from executions"""
    result = _ok(await analytics_service.get_user_activity_metrics(userId, timeRange, page, pageSize))
    return UserActivityResponse(
        success=True,
        metrics=[UserActivityMetrics(**m) for m in result['metrics']],
        total=result['total'],
        page=page,
        pageSize=pageSize,
    )


@router.get("/users/engagement", response_model=UserEngagementMetrics)
@rate_limit(requests_per_minute=50)
async def get_user_engagement(
    request: Request,
    user: dict = Depends(PLATFORM),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS)
):
    """Active / new / returning users"""
    return UserEngagementMetrics(**await analytics_service.get_user_engagement_metrics(timeRange))


@router.get("/users/retention", response_model=UserRetentionMetrics)
@rate_limit(requests_per_minute=30)
async def get_user_retention(
    request: Request,
    user: dict = Depends(PLATFORM),
    cohort: Optional[str] = Query(None, pattern=r'^\d{4}-\d{2}$', description="YYYY-MM, defaults to this month")
):
    """Weekly retention of users whose first run was in the cohort month"""
    return UserRetentionMetrics(**await analytics_service.get_user_retention(cohort))


@router.get("/users/{user_id}/metrics")
@rate_limit(requests_per_minute=50)
async def get_user_metrics(
    request: Request,
    user_id: str,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS)
):
    """Metrics for one user (that user or an admin)"""
    if user_id != user["uid"] and not has_permission(user, "analytics:platform"):
        raise HTTPException(status_code=403, detail="Admin access required")
    result = _ok(await analytics_service.get_user_activity_metrics(user_id, timeRange, 1, 1))
    if not result['metrics']:
        raise HTTPException(status_code=404, detail="No activity for this user in the period")
    return {'success': True, 'metrics': result['metrics'][0]}


# ==================== Dashboard ====================

@router.get("/dashboard/overview", response_model=DashboardOverview)
@rate_limit(requests_per_minute=100)
async def get_dashboard_overview(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_24_HOURS)
):
    """Main dashboard data"""
    return DashboardOverview(**_ok(await analytics_service.get_dashboard_overview(timeRange, scope(user))))


@router.get("/dashboard/real-time", response_model=RealTimeMetrics)
@rate_limit(requests_per_minute=100)
async def get_real_time_metrics(request: Request, user: dict = Depends(get_current_user)):
    """Live metrics over the last hour"""
    return RealTimeMetrics(**await analytics_service.get_real_time_metrics(scope(user)))


@router.get("/dashboard/trends", response_model=TrendAnalysis)
@rate_limit(requests_per_minute=50)
async def get_trend_analysis(
    request: Request,
    user: dict = Depends(get_current_user),
    metric: str = Query("executions", description="executions | success_rate | error_rate | duration | tokens"),
    timeRange: TimeRange = Query(TimeRange.LAST_7_DAYS)
):
    """Trend of a metric over time"""
    return TrendAnalysis(**await analytics_service.get_trends(metric, timeRange, scope(user)))


@router.get("/dashboard/alerts", response_model=AlertsResponse)
@rate_limit(requests_per_minute=100)
async def get_alerts(
    request: Request,
    user: dict = Depends(get_current_user),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    """Alerts (e.g. failed workflow runs)"""
    result = await analytics_service.get_alerts(severity, category, acknowledged, limit, scope(user))
    return AlertsResponse(
        success=True,
        alerts=[Alert(**a) for a in result.get('alerts', [])],
        total=result.get('total', 0),
        criticalCount=result.get('criticalCount', 0),
        warningCount=result.get('warningCount', 0),
    )


@router.post("/dashboard/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: dict = Depends(get_current_user)):
    """Dismiss an alert"""
    if not await analytics_service.acknowledge_alert(alert_id, user["uid"], has_permission(user, "analytics:platform")):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {'success': True}


@router.get("/dashboard/widgets")
@rate_limit(requests_per_minute=50)
async def get_dashboard_widgets(
    request: Request,
    user: dict = Depends(get_current_user),
    widgetType: str = Query(..., description="execution_chart | success_rate")
):
    """Data for small dashboard widgets (last 7 days)"""
    data = await analytics_service.get_widget(widgetType, scope(user))
    if data is None:
        raise HTTPException(status_code=400, detail="Unknown widget type")
    return {'success': True, 'widgetType': widgetType, 'data': data}


# ==================== Events & Export ====================

@router.post("/events", status_code=201)
@rate_limit(requests_per_minute=100)
async def track_event(request: Request, event: AnalyticsEventCreate, user: dict = Depends(get_current_user)):
    """Track a custom analytics event (always attributed to the caller)"""
    event_data = event.dict()
    event_data['userId'] = user['uid']
    result = _ok(await analytics_service.track_event(event_data))
    return {'success': True, 'eventId': result['eventId'], 'message': 'Event tracked successfully'}


@router.get("/events", response_model=EventsResponse)
@rate_limit(requests_per_minute=50)
async def query_events(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_24_HOURS),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None),
    userId: Optional[str] = Query(None),
    workflowId: Optional[str] = Query(None),
    eventType: Optional[EventType] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(100, ge=1, le=1000)
):
    """Query custom events (non-admins only see their own)"""
    owner = userId if has_permission(user, "analytics:platform") else user["uid"]
    result = _ok(await analytics_service.get_events(
        timeRange, startDate, endDate, owner, workflowId,
        eventType.value if eventType else None, pageSize, (page - 1) * pageSize
    ))
    return EventsResponse(
        success=True,
        events=[AnalyticsEventResponse(**e) for e in result['events']],
        total=result['total'],
        page=page,
        pageSize=pageSize,
    )


@router.get("/events/timeline", response_model=EventTimelineResponse)
@rate_limit(requests_per_minute=50)
async def get_event_timeline(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_24_HOURS),
    startDate: Optional[datetime] = Query(None),
    endDate: Optional[datetime] = Query(None),
    interval: str = Query('hour', pattern='^(hour|day|week)$')
):
    """Workflow executions over time"""
    result = _ok(await analytics_service.get_event_timeline(timeRange, startDate, endDate, interval, scope(user)))
    return EventTimelineResponse(success=True, timeline=result['timeline'], period=result['period'])


@router.get("/events/export")
@rate_limit(requests_per_minute=10)
async def export_events(
    request: Request,
    user: dict = Depends(get_current_user),
    timeRange: TimeRange = Query(TimeRange.LAST_30_DAYS),
    format: str = Query('csv', pattern='^(csv|json)$')
):
    """Download execution history as CSV or JSON"""
    rows = analytics_service.export_rows(timeRange, scope(user))
    stamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    if format == 'json':
        content, media_type = json.dumps(rows, indent=2, default=str), 'application/json'
    else:
        buf = io.StringIO()
        fields = list(rows[0].keys()) if rows else ['executionId']
        writer = csv.DictWriter(buf, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        content, media_type = buf.getvalue(), 'text/csv'
    return Response(
        content=content,
        media_type=media_type,
        headers={'Content-Disposition': f'attachment; filename="flowmind-executions-{stamp}.{format}"'},
    )
