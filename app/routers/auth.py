from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.models.user import User, UserSession, SubscriptionTier
from app.models.schemas import UserCreate, UserResponse, Token, TokenRefresh
from app.utils.security import verify_password, create_access_token, create_refresh_token, verify_token, get_password_hash
from app.dependencies import get_active_user, create_user_response
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register new user with free solo tier"""
    
    # Check if user already exists
    existing_user = await User.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        password_hash=get_password_hash(user_data.password),
        subscription_tier=SubscriptionTier.SOLO,
        analyses_limit=10  # Free tier allows 10 analyses per month
    )
    
    await user.save()
    
    return create_user_response(user)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return JWT tokens"""
    
    # Find user by email (form_data.username is email in our case)
    user = await User.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Create tokens
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Store refresh token
    session = UserSession(
        user_id=str(user.id),
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    await session.save()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh):
    """Refresh JWT access token using refresh token"""
    
    # Verify refresh token
    payload = verify_token(token_data.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Check if refresh token exists in database and hasn't expired
    session = await UserSession.find_one({"refresh_token": token_data.refresh_token})
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid"
        )
    
    # Get user
    user = await User.get(payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    new_access_token = create_access_token({"sub": str(user.id)})
    new_refresh_token = create_refresh_token({"sub": str(user.id)})
    
    # Update session with new refresh token
    session.refresh_token = new_refresh_token
    session.expires_at = datetime.utcnow() + timedelta(days=7)
    await session.save()
    
    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )

@router.post("/logout")
async def logout(current_user: User = Depends(get_active_user)):
    """Logout user by deleting refresh tokens"""
    
    # Delete all user sessions
    await UserSession.find({"user_id": str(current_user.id)}).delete()
    
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_active_user)):
    """Get current user profile"""
    return create_user_response(current_user)

@router.get("/verify-email")
async def verify_email():
    """Placeholder for email verification (to be implemented)"""
    return {"message": "Email verification not implemented yet"}