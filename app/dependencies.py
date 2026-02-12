from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.models.user import User
from app.models.schemas import UserResponse
from app.utils.security import verify_token
from datetime import datetime

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await User.get(payload.get("sub"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user

async def get_active_user(current_user: User = Depends(get_current_user)):
    """Ensure current user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Check if subscription has expired
    if current_user.subscription_expires and current_user.subscription_expires < datetime.utcnow():
        current_user.subscription_tier = "solo"
        current_user.analyses_limit = 10  # Reset to free tier
        current_user.subscription_expires = None
        await current_user.save()
    
    return current_user

def create_user_response(user: User) -> UserResponse:
    """Create user response object from user model"""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        subscription_tier=user.subscription_tier,
        analyses_limit=user.analyses_limit,
        analyses_used=user.analyses_used,
        subscription_expires=user.subscription_expires
    )