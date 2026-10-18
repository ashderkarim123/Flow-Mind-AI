from typing import Dict, Any, Optional
import logging
import os
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.firebase_service import firebase_service

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user
    
    Returns:
        dict: User information including uid, email, isAdmin, etc.
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    try:
        token = credentials.credentials
        
        # Verify token with Firebase
        decoded_token = await firebase_service.verify_token(token)
        
        if not decoded_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user document to include additional info
        user_doc = await _get_user_document(decoded_token.get('uid'))
        
        # Combine Firebase token data with user document
        user_data = {
            'uid': decoded_token.get('uid'),
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
            'firebase_claims': decoded_token,
            **user_doc  # Include additional user data from document
        }
        
        return user_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def is_admin(current_user: Dict[str, Any]) -> bool:
    """True for admins: role/isAdmin in Firestore, an `admin` custom claim, or an ADMIN_EMAILS address."""
    # ponytail: ADMIN_EMAILS mirrors the frontend's email gate on /admin321; drop it once roles are assigned
    admin_emails = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "admin@gmail.com").split(",") if e.strip()}
    return bool(
        current_user.get('isAdmin', False)
        or current_user.get('role') == 'admin'
        or current_user.get('firebase_claims', {}).get('admin', False)
        or (current_user.get('email') or '').lower() in admin_emails
    )


# ---------------------------------------------------------------------------
# RBAC — User Management module. Role is users/{uid}.role in Firestore.
# ---------------------------------------------------------------------------

_VIEWER = {"workflow:read", "execution:read", "analytics:own"}
_USER = _VIEWER | {"workflow:write", "workflow:execute", "ai:use"}
_MANAGER = _USER | {"analytics:platform", "admin:read"}   # read-only access to the admin panel

ROLE_PERMISSIONS: Dict[str, set] = {
    "viewer": _VIEWER,    # read-only: browse workflows, runs and own analytics
    "user": _USER,        # build, run and schedule own workflows; use AI models
    "manager": _MANAGER,  # + platform-wide monitoring and analytics
    "admin": {"*"},       # everything, including moderation and role changes
}
ROLES = tuple(ROLE_PERMISSIONS)


def role_of(current_user: Dict[str, Any]) -> str:
    if is_admin(current_user):
        return "admin"
    role = current_user.get("role")
    return role if role in ROLE_PERMISSIONS else "user"


def has_permission(current_user: Dict[str, Any], permission: str) -> bool:
    perms = ROLE_PERMISSIONS[role_of(current_user)]
    return "*" in perms or permission in perms


def require_permission(permission: str):
    """FastAPI dependency: 403 unless the caller's role grants `permission`."""
    async def dependency(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ({role_of(current_user)}) is not allowed to do this ({permission}).",
            )
        return current_user
    return dependency


async def get_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency to get current user and ensure they have admin privileges

    Returns:
        dict: Admin user information

    Raises:
        HTTPException: 403 if user is not an admin
    """
    try:
        if not is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_admin_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin verification failed"
        )


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[Dict[str, Any]]:
    """
    Dependency to get current user if authenticated, otherwise None
    
    Useful for endpoints that work for both authenticated and anonymous users
    
    Returns:
        Optional[dict]: User information if authenticated, None otherwise
    """
    try:
        if not credentials:
            return None
            
        return await get_current_user(credentials)
        
    except HTTPException:
        # Return None instead of raising exception for optional auth
        return None
    except Exception as e:
        logger.debug(f"Optional auth failed: {str(e)}")
        return None


async def verify_user_access(target_user_id: str, current_user: Dict[str, Any]) -> bool:
    """
    Verify if current user can access target user's data
    
    Args:
        target_user_id: The user ID being accessed
        current_user: Current authenticated user
        
    Returns:
        bool: True if access is allowed
        
    Raises:
        HTTPException: 403 if access is denied
    """
    try:
        # Users can access their own data
        if current_user['uid'] == target_user_id:
            return True
        
        # Admins can access any user's data
        is_admin = (
            current_user.get('isAdmin', False) or 
            current_user.get('role') == 'admin' or
            current_user.get('firebase_claims', {}).get('admin', False)
        )
        
        if is_admin:
            return True
        
        # Check if users are in the same organization/team
        current_user_org = current_user.get('organizationId')
        if current_user_org:
            target_user_doc = await _get_user_document(target_user_id)
            target_user_org = target_user_doc.get('organizationId')
            
            if current_user_org == target_user_org:
                # Additional checks for organization role could go here
                return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to user data"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying user access: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access verification failed"
        )


async def require_subscription(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that requires user to have an active subscription
    
    Returns:
        dict: User information with subscription
        
    Raises:
        HTTPException: 402 if no active subscription
    """
    try:
        # Check user's subscription status
        subscription_status = current_user.get('subscription', {}).get('status')
        
        if subscription_status not in ['active', 'trialing']:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Active subscription required"
            )
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription verification failed"
        )


async def require_plan_level(min_plan_level: str):
    """
    Dependency factory that requires a minimum plan level
    
    Args:
        min_plan_level: Minimum required plan (e.g., 'basic', 'pro', 'enterprise')
        
    Returns:
        Dependency function
    """
    plan_hierarchy = {
        'free': 0,
        'basic': 1,
        'pro': 2,
        'enterprise': 3
    }
    
    async def check_plan_level(current_user: Dict[str, Any] = Depends(require_subscription)) -> Dict[str, Any]:
        try:
            user_plan = current_user.get('subscription', {}).get('plan', 'free')
            user_plan_level = plan_hierarchy.get(user_plan.replace('plan_', ''), 0)
            required_level = plan_hierarchy.get(min_plan_level, 0)
            
            if user_plan_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Plan upgrade required. Minimum plan: {min_plan_level}"
                )
            
            return current_user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking plan level: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Plan verification failed"
            )
    
    return check_plan_level


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _get_user_document(user_id: str) -> Dict[str, Any]:
    """
    Get user document from Firestore
    
    Args:
        user_id: Firebase user ID
        
    Returns:
        dict: User document data
    """
    try:
        from app.services.firebase_service import FirebaseService
        
        firebase_service = FirebaseService()
        user_doc = firebase_service.db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            logger.warning(f"User document not found for uid: {user_id}")
            return {}
        
        return user_doc.to_dict()
        
    except Exception as e:
        logger.error(f"Error getting user document for {user_id}: {str(e)}")
        return {}


def create_user_access_dependency(target_user_id_param: str = "user_id"):
    """
    Factory to create a dependency that verifies user access to target user
    
    Args:
        target_user_id_param: Parameter name containing the target user ID
        
    Returns:
        Dependency function
    """
    async def verify_access(
        current_user: Dict[str, Any] = Depends(get_current_user),
        **kwargs
    ) -> Dict[str, Any]:
        target_user_id = kwargs.get(target_user_id_param)
        
        if not target_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {target_user_id_param} parameter"
            )
        
        await verify_user_access(target_user_id, current_user)
        return current_user
    
    return verify_access