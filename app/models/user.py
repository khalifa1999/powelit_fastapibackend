from beanie import Document, Indexed
from pydantic import Field, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum

class SubscriptionTier(str, Enum):
    SOLO = "solo"
    BUSINESS = "business" 
    ENTERPRISE = "enterprise"

class User(Document):
    email: Indexed(EmailStr, unique=True)  # Fast lookup
    password_hash: str
    full_name: str
    subscription_tier: SubscriptionTier = SubscriptionTier.SOLO
    is_active: bool = True
    analyses_used: int = 0
    analyses_limit: int = 10  # Based on subscription
    subscription_expires: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "users"

class UserSession(Document):
    user_id: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "sessions"