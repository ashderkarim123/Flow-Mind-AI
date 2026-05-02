"""
FlowMind AI — User Management API (Module 2: RBAC)
Provides admin endpoints for listing, managing, and assigning roles to users.
All endpoints require admin privileges.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Dict, Any, Optional, List
from app.core.auth_dependency import get_current_user, get_admin_user
from app.models.user_models import (
    UserProfile,
    UserListResponse,
    UpdateRoleRequest,
    UpdateStatusRequest,
    UserStatsResponse,
    UserWorkflowsResponse,
    CreateUserRequest,
)
from app.services.firebase_service import firebase_service
import logging
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/users", tags=["User Management"])
logger = logging.getLogger(__name__)

ALLOWED_ROLES = {"user", "admin", "manager"}


# ─── Helpers ───────────────────────────────────────────────────────────────

def _build_user_profile(fb_user: dict, user_doc: dict = None) -> UserProfile:
    """Build a UserProfile from Firebase Auth data + Firestore document."""
    doc = user_doc or {}
    role = doc.get("role", "user")

    # Check admins collection as fallback
    if role == "user" and doc.get("isAdmin"):
        role = "admin"

    created = None
    if fb_user.get("creationTime"):
        try:
            created = datetime.strptime(fb_user["creationTime"], "%a, %d %b %Y %H:%M:%S %Z")
        except Exception:
            pass

    last_sign_in = None
    if fb_user.get("lastSignInTime"):
        try:
            last_sign_in = datetime.strptime(fb_user["lastSignInTime"], "%a, %d %b %Y %H:%M:%S %Z")
        except Exception:
            pass

    return UserProfile(
        uid=fb_user.get("uid", ""),
        email=fb_user.get("email", ""),
        display_name=fb_user.get("displayName") or doc.get("displayName"),
        email_verified=fb_user.get("emailVerified", False),
        disabled=fb_user.get("disabled", False),
        role=role,
        created_at=created,
        last_sign_in=last_sign_in,
        photo_url=fb_user.get("photoURL"),
        workflow_count=doc.get("workflowCount", 0),
    )


# ─── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by email or display name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    disabled: Optional[bool] = Query(None, description="Filter by disabled status"),
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] List all users with optional filtering and pagination.
    """
    try:
        # List users from Firebase Auth
        raw_users = await firebase_service.list_all_users()

        profiles: List[UserProfile] = []
        for fb_user in raw_users:
            try:
                uid = fb_user.get("uid", "")
                # Fetch Firestore document for role / extra data
                try:
                    doc_ref = firebase_service.db.collection("users").document(uid).get()
                    user_doc = doc_ref.to_dict() if doc_ref.exists else {}
                except Exception:
                    user_doc = {}

                profile = _build_user_profile(fb_user, user_doc)

                # Apply filters
                if search:
                    q = search.lower()
                    if q not in (profile.email or "").lower() and q not in (profile.display_name or "").lower():
                        continue
                if role and profile.role != role:
                    continue
                if disabled is not None and profile.disabled != disabled:
                    continue

                profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to build profile for user {fb_user.get('uid')}: {e}")

        total = len(profiles)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated = profiles[start:end]

        return UserListResponse(
            success=True,
            users=paginated,
            total=total,
            page=page,
            page_size=page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] Get aggregate user statistics for the admin dashboard.
    """
    try:
        raw_users = await firebase_service.list_all_users()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        total = 0
        active = 0
        admins = 0
        disabled_count = 0
        new_today = 0
        new_week = 0

        for fb_user in raw_users:
            total += 1
            if fb_user.get("disabled"):
                disabled_count += 1
            else:
                active += 1

            try:
                doc_ref = firebase_service.db.collection("users").document(fb_user["uid"]).get()
                user_doc = doc_ref.to_dict() if doc_ref.exists else {}
                if user_doc.get("role") == "admin" or user_doc.get("isAdmin"):
                    admins += 1
            except Exception:
                pass

            try:
                ct = fb_user.get("creationTime")
                if ct:
                    created = datetime.strptime(ct, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                    if created >= today_start:
                        new_today += 1
                    if created >= week_start:
                        new_week += 1
            except Exception:
                pass

        return UserStatsResponse(
            success=True,
            total_users=total,
            active_users=active,
            admin_users=admins,
            disabled_users=disabled_count,
            new_users_today=new_today,
            new_users_this_week=new_week,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user statistics")


@router.get("/{uid}", response_model=UserProfile)
async def get_user(
    uid: str,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] Get a specific user by UID.
    """
    try:
        fb_user = await firebase_service.get_user_by_uid(uid)
        if not fb_user:
            raise HTTPException(status_code=404, detail="User not found")

        try:
            doc_ref = firebase_service.db.collection("users").document(uid).get()
            user_doc = doc_ref.to_dict() if doc_ref.exists else {}
        except Exception:
            user_doc = {}

        return _build_user_profile(fb_user, user_doc)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user")


@router.patch("/{uid}/role")
async def update_user_role(
    uid: str,
    body: UpdateRoleRequest,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] Assign a role to a user.
    Allowed roles: user, admin, manager.
    """
    if body.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Allowed roles: {', '.join(ALLOWED_ROLES)}",
        )

    try:
        # Prevent self-demotion
        if uid == current_user.get("uid") and body.role != "admin":
            raise HTTPException(
                status_code=400,
                detail="Admins cannot remove their own admin privileges",
            )

        # Update Firestore user document
        firebase_service.db.collection("users").document(uid).set(
            {"role": body.role, "updatedAt": datetime.now(timezone.utc)},
            merge=True,
        )

        # Also sync admins collection
        admin_ref = firebase_service.db.collection("admins").document(uid)
        if body.role == "admin":
            admin_ref.set({"role": "admin", "permissions": ["*"], "grantedAt": datetime.now(timezone.utc)}, merge=True)
        else:
            try:
                admin_ref.delete()
            except Exception:
                pass

        return {"success": True, "message": f"User role updated to '{body.role}'", "uid": uid, "role": body.role}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update role error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user role")


@router.patch("/{uid}/status")
async def update_user_status(
    uid: str,
    body: UpdateStatusRequest,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] Enable or disable a user account.
    """
    try:
        if uid == current_user.get("uid"):
            raise HTTPException(status_code=400, detail="You cannot disable your own account")

        result = await firebase_service.update_user(uid, {"disabled": body.disabled})
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to update user status")

        action = "disabled" if body.disabled else "enabled"
        return {"success": True, "message": f"User account {action}", "uid": uid, "disabled": body.disabled}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user status")


@router.get("/{uid}/workflows", response_model=UserWorkflowsResponse)
async def get_user_workflows(
    uid: str,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] Get all workflows belonging to a user.
    """
    try:
        workflows_ref = (
            firebase_service.db.collection("workflows").where("userId", "==", uid).stream()
        )
        workflows = []
        for doc in workflows_ref:
            wf = doc.to_dict()
            wf["id"] = doc.id
            workflows.append(wf)

        return UserWorkflowsResponse(success=True, uid=uid, workflows=workflows, total=len(workflows))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user workflows error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user workflows")

@router.post("/", response_model=Dict[str, Any])
async def create_user(
    body: CreateUserRequest,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """
    [ADMIN] Create a new user (Add Member).
    """
    try:
        if body.role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Allowed: {ALLOWED_ROLES}")

        # Create user in Firebase Auth
        result = await firebase_service.create_user(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to create user in Auth"))

        user_info = result.get("user", {})
        uid = user_info.get("uid")
        
        if not uid:
            raise HTTPException(status_code=500, detail="Failed to create user in Auth")

        # Set role and initial data in Firestore
        doc_ref = firebase_service.db.collection("users").document(uid)
        doc_ref.set({
            "uid": uid,
            "email": body.email,
            "displayName": body.display_name,
            "role": body.role,
            "isAdmin": body.role == "admin",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "workflowCount": 0
        }, merge=True)

        return {"success": True, "message": "User created successfully", "uid": uid, "role": body.role}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {e}")
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            raise HTTPException(status_code=400, detail="User with this email already exists")
        raise HTTPException(status_code=500, detail=f"Failed to create user: {error_msg}")
