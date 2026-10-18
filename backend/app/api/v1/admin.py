"""
Administration module — platform-wide moderation of workflows and templates.

Listing needs admin:read (admins and managers); every change needs an admin and is
written to the audit log. /admin/whoami is open to any signed-in user.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.auth_dependency import (
    ROLE_PERMISSIONS, get_admin_user, get_current_user, has_permission, is_admin, require_permission, role_of,
)
from app.services.audit_service import audit_service
from app.services.firebase_service import firebase_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administration"])

TRIGGER_TYPES = {"ManualTrigger", "Manual Trigger", "Webhook", "Schedule", "Scheduling", "ChatInput"}
TEMPLATES = "workflow_templates"


async def _audit(admin: Dict[str, Any], event_type: str, action: str, resource_type: str,
                 resource_id: str, resource_name: str, changes: Dict[str, Any], description: str) -> None:
    await audit_service.log_event({
        "eventType": event_type,
        "severity": "warning" if action.startswith("delete") else "info",
        "userId": admin["uid"],
        "userName": admin.get("email"),
        "resourceType": resource_type,
        "resourceId": resource_id,
        "resourceName": resource_name,
        "action": action,
        "description": description,
        "metadata": {"source": "admin_panel"},
        "changes": changes,
        "status": "success",
    })


def _stop_schedule(workflow_id: str) -> None:
    """Stop the in-memory cron job (the Firestore flag is cleared by the caller)."""
    try:
        from services.scheduler import SchedulerStatus, get_scheduler
        for job in get_scheduler().get_jobs_by_workflow_id(workflow_id):
            job.status = SchedulerStatus.STOPPED  # loop exits before its next run
    except Exception as exc:
        logger.warning("Could not stop schedule for %s: %s", workflow_id, exc)


# ==================== Session ====================

@router.get("/whoami")
async def whoami(user: dict = Depends(get_current_user)):
    """Role and permissions of the signed-in user — used by the frontend to gate UI."""
    role = role_of(user)
    return {"uid": user["uid"], "email": user.get("email"), "role": role,
            "permissions": sorted(ROLE_PERMISSIONS[role]), "isAdmin": is_admin(user),
            "canAccessAdmin": has_permission(user, "admin:read")}


# ==================== Workflows ====================

class WorkflowModeration(BaseModel):
    disabled: Optional[bool] = None   # blocks every trigger (manual, schedule, webhook)
    isPublic: Optional[bool] = None   # listed in the public gallery / marketplace
    reason: Optional[str] = None


@router.get("/workflows")
async def list_all_workflows(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, pattern="^(active|disabled|public|scheduled)$"),
    admin: dict = Depends(require_permission("admin:read")),
):
    """Every workflow on the platform with its owner and execution stats"""
    db = firebase_service.db
    owners = {d.id: (d.to_dict() or {}).get("email", "") for d in db.collection("users").stream()}
    rows = []
    for doc in db.collection("workflows").stream():
        w = doc.to_dict() or {}
        nodes = w.get("nodes") or []
        rows.append({
            "id": doc.id,
            "name": w.get("name") or "Untitled",
            "description": w.get("description") or "",
            "ownerId": w.get("userId"),
            "ownerEmail": owners.get(w.get("userId"), ""),
            "nodeCount": len(nodes),
            "triggers": sorted({n.get("type") for n in nodes if n.get("type") in TRIGGER_TYPES}),
            "executionCount": w.get("executionCount", 0),
            "lastExecutedAt": w.get("lastExecutedAt"),
            "createdAt": w.get("createdAt"),
            "updatedAt": w.get("updatedAt"),
            "isPublic": bool(w.get("canBeListed")),
            "disabled": bool(w.get("disabled")),
            "disabledReason": w.get("disabledReason"),
            "scheduled": bool((w.get("schedule") or {}).get("active")),
        })

    summary = {
        "total": len(rows),
        "disabled": sum(r["disabled"] for r in rows),
        "public": sum(r["isPublic"] for r in rows),
        "scheduled": sum(r["scheduled"] for r in rows),
    }
    if search:
        q = search.lower()
        rows = [r for r in rows if q in r["name"].lower() or q in r["ownerEmail"].lower() or q == r["id"]]
    if status:
        rows = [r for r in rows if {
            "active": not r["disabled"], "disabled": r["disabled"],
            "public": r["isPublic"], "scheduled": r["scheduled"],
        }[status]]
    rows.sort(key=lambda r: str(r["updatedAt"] or r["createdAt"] or ""), reverse=True)
    return {"workflows": rows, "total": len(rows), "summary": summary}


@router.patch("/workflows/{workflow_id}")
async def moderate_workflow(workflow_id: str, body: WorkflowModeration, admin: dict = Depends(get_admin_user)):
    """Disable/enable a workflow or change its public listing"""
    ref = firebase_service.db.collection("workflows").document(workflow_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Workflow not found")

    updates: Dict[str, Any] = {}
    if body.isPublic is not None:
        updates["canBeListed"] = body.isPublic
    if body.disabled is not None:
        updates["disabled"] = body.disabled
        updates["disabledReason"] = (body.reason or "Disabled by an administrator") if body.disabled else None
        if body.disabled and (doc.to_dict().get("schedule") or {}).get("active"):
            updates["schedule.active"] = False
            _stop_schedule(workflow_id)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    ref.update(updates)
    name = doc.to_dict().get("name", workflow_id)
    await _audit(admin, "workflow_updated", "moderate_workflow", "workflow", workflow_id, name, updates,
                 f"Admin updated workflow '{name}': {', '.join(f'{k}={v}' for k, v in updates.items())}")
    return {"success": True, "workflowId": workflow_id, "updates": updates}


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str, admin: dict = Depends(get_admin_user)):
    """Permanently delete a workflow (execution history is kept for analytics)"""
    ref = firebase_service.db.collection("workflows").document(workflow_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Workflow not found")
    _stop_schedule(workflow_id)
    ref.delete()
    data = doc.to_dict()
    await _audit(admin, "workflow_deleted", "delete_workflow", "workflow", workflow_id, data.get("name", ""),
                 {"ownerId": data.get("userId")}, f"Admin deleted workflow '{data.get('name', workflow_id)}'")
    return {"success": True}


# ==================== Templates ====================

class TemplateModeration(BaseModel):
    isActive: Optional[bool] = None
    isFeatured: Optional[bool] = None


@router.get("/templates")
async def list_all_templates(search: Optional[str] = Query(None), admin: dict = Depends(require_permission("admin:read"))):
    """Every template, including deactivated ones"""
    rows = []
    for doc in firebase_service.db.collection(TEMPLATES).stream():
        t = doc.to_dict() or {}
        rows.append({
            "id": doc.id,
            "name": t.get("name", "Untitled"),
            "description": t.get("description", ""),
            "category": t.get("category", ""),
            "difficulty": t.get("difficulty", ""),
            "authorId": t.get("authorId"),
            "authorName": t.get("authorName"),
            "nodeCount": len(t.get("nodes") or []),
            "usageCount": t.get("usageCount", 0),
            "rating": t.get("rating", 0.0),
            "reviewCount": t.get("reviewCount", 0),
            "isActive": t.get("isActive", True),
            "isFeatured": t.get("isFeatured", False),
            "createdAt": t.get("createdAt"),
        })
    summary = {
        "total": len(rows),
        "active": sum(1 for r in rows if r["isActive"]),
        "featured": sum(1 for r in rows if r["isFeatured"]),
    }
    if search:
        q = search.lower()
        rows = [r for r in rows if q in r["name"].lower() or q in (r["category"] or "").lower()
                or q in (r["authorName"] or "").lower()]
    rows.sort(key=lambda r: r["usageCount"], reverse=True)
    return {"templates": rows, "total": len(rows), "summary": summary}


@router.patch("/templates/{template_id}")
async def moderate_template(template_id: str, body: TemplateModeration, admin: dict = Depends(get_admin_user)):
    """Activate/deactivate or feature/unfeature a template"""
    ref = firebase_service.db.collection(TEMPLATES).document(template_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Template not found")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")
    ref.update(updates)
    name = doc.to_dict().get("name", template_id)
    await _audit(admin, "system_config_changed", "moderate_template", "template", template_id, name, updates,
                 f"Admin updated template '{name}': {', '.join(f'{k}={v}' for k, v in updates.items())}")
    return {"success": True, "templateId": template_id, "updates": updates}


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, admin: dict = Depends(get_admin_user)):
    ref = firebase_service.db.collection(TEMPLATES).document(template_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Template not found")
    ref.delete()
    name = doc.to_dict().get("name", template_id)
    await _audit(admin, "data_deleted", "delete_template", "template", template_id, name, {},
                 f"Admin deleted template '{name}'")
    return {"success": True}
