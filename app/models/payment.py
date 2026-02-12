from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional

class Subscription(Document):
    user_id: str
    tier: str  # solo, business, enterprise
    amount_usd: float
    amount_ghs: float
    reference: Indexed(str, unique=True)  # Paystack reference
    status: str = "pending"  # pending, success, failed
    paystack_data: Optional[dict] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "subscriptions"