from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from app.core.auth_dependency import get_current_user
from app.services.firebase_service import firebase_service
from datetime import datetime, timezone
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/team", tags=["Team"])
logger = logging.getLogger(__name__)

class InviteRequest(BaseModel):
    email: str
    role: str

@router.get("/", response_model=Dict[str, Any])
async def list_team_members(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List team members for the current workspace"""
    try:
        # Get user's workspace
        uid = current_user.get("uid")
        doc_ref = firebase_service.db.collection("users").document(uid).get()
        if not doc_ref.exists:
            # Fallback to just returning the current user
            return {
                "success": True,
                "members": [{
                    "id": uid,
                    "name": current_user.get("displayName") or current_user.get("email"),
                    "email": current_user.get("email"),
                    "role": "Owner",
                    "status": "Active",
                    "joinedAt": datetime.now(timezone.utc).isoformat()
                }]
            }
        
        user_data = doc_ref.to_dict()
        workspace = user_data.get("workspace", {})
        members = workspace.get("members", [])
        
        # Build member list (always include owner)
        team_members = [{
            "id": uid,
            "name": user_data.get("displayName") or user_data.get("email"),
            "email": user_data.get("email"),
            "role": "Owner",
            "status": "Active",
            "joinedAt": user_data.get("createdAt") or datetime.now(timezone.utc).isoformat()
        }]
        
        # Add other members
        for member in members:
            team_members.append({
                "id": member.get("id"),
                "name": member.get("name") or member.get("email"),
                "email": member.get("email"),
                "role": member.get("role", "Viewer"),
                "status": member.get("status", "Pending"),
                "joinedAt": member.get("joinedAt")
            })
            
        return {"success": True, "members": team_members}

    except Exception as e:
        logger.error(f"Error listing team members: {e}")
        raise HTTPException(status_code=500, detail="Failed to load team members")

@router.post("/invite", response_model=Dict[str, Any])
async def invite_team_member(
    body: InviteRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Invite a new team member to the workspace"""
    try:
        uid = current_user.get("uid")
        doc_ref = firebase_service.db.collection("users").document(uid)
        
        # Check if user document exists
        doc = doc_ref.get()
        if not doc.exists:
            # Create a minimal document with workspace
            doc_ref.set({
                "workspace": {
                    "members": []
                }
            }, merge=True)
            doc = doc_ref.get()
            
        user_data = doc.to_dict()
        workspace = user_data.get("workspace", {})
        members = workspace.get("members", [])
        
        # Check if already invited
        if any(m.get("email") == body.email for m in members):
            raise HTTPException(status_code=400, detail="User already invited")
            
        # Add to members array
        new_member = {
            "id": f"inv_{int(datetime.now().timestamp())}",
            "email": body.email,
            "role": body.role,
            "status": "Pending",
            "joinedAt": datetime.now(timezone.utc).isoformat()
        }
        
        members.append(new_member)
        
        # Update Firestore
        doc_ref.set({
            "workspace": {
                "members": members
            }
        }, merge=True)
        
        # Send actual invitation email via SMTP
        from app.core.config import settings
        import aiosmtplib
        from email.message import EmailMessage

        if settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            try:
                msg = EmailMessage()
                msg.set_content(
                    f"Hello,\n\n"
                    f"You have been invited to join the FlowMind AI workspace of {user_data.get('email')} "
                    f"with the role of {body.role}.\n\n"
                    f"Please log in or sign up at {settings.CORS_ORIGINS[0]} to accept the invitation.\n\n"
                    f"Best regards,\nFlowMind AI Team"
                )
                msg["Subject"] = "Invitation to join FlowMind AI Workspace"
                msg["From"] = settings.EMAIL_FROM
                msg["To"] = body.email

                await aiosmtplib.send(
                    msg,
                    hostname=settings.SMTP_HOST,
                    port=settings.SMTP_PORT,
                    username=settings.SMTP_USERNAME,
                    password=settings.SMTP_PASSWORD,
                    use_tls=(settings.SMTP_PORT == 465),
                    start_tls=(settings.SMTP_PORT == 587),
                )
                logger.info(f"Invitation email sent successfully to {body.email}")
            except Exception as email_err:
                logger.error(f"Failed to send invitation email: {email_err}")
                # We still return success but maybe warn that email failed
        else:
            logger.warning("SMTP not fully configured in .env. Invitation recorded but email not sent.")
        
        return {
            "success": True, 
            "message": "Invitation sent successfully",
            "member": new_member
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inviting team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to invite team member")
