from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from enum import Enum
from datetime import datetime

class BuildingType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"

class ElectricalComponent(BaseModel):
    name: str
    quantity: int
    rating_watts: float
    total_watts: float

class LoadCalculation(BaseModel):
    total_connected_load: float = Field(..., description="Total Connected Load in Watts")
    diversity_factor: float = Field(..., description="Diversity factor applied")
    maximum_demand: float = Field(..., description="Maximum Demand in Watts")
    building_type: BuildingType

class ComplianceAudit(BaseModel):
    standard_clause: str
    description: str
    compliance_status: Literal["compliant", "non_compliant", "review_required"]

class PowerSourceRecommendation(BaseModel):
    source: Literal["grid", "solar", "generator", "hybrid"]
    percentage: float
    capacity_kw: float
    reasoning: str

class AnalysisResponse(BaseModel):
    inventory: List[ElectricalComponent]
    calculations: LoadCalculation
    compliance_audit: List[ComplianceAudit]
    recommendations: List[PowerSourceRecommendation]
    processing_time_ms: int

class AnalysisRequest(BaseModel):
    building_type: BuildingType
    project_name: Optional[str] = None
    voltage_standard: float = 230.0  # Ghana standard

# Authentication Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    subscription_tier: str
    analyses_limit: int
    analyses_used: int
    subscription_expires: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefresh(BaseModel):
    refresh_token: str

# Payment Schemas
class SubscriptionPackage(BaseModel):
    tier: str
    usd: float
    ghs: float
    description: str

class SubscriptionResponse(BaseModel):
    authorization_url: str
    reference: str
    access_code: str

class WebhookEvent(BaseModel):
    event: str
    data: dict
