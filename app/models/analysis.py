from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import Optional, List
from app.models.schemas import BuildingType

class Analysis(Document):
    user_id: Optional[str] = None  # null for preview analyses
    file_url: str  # Cloudinary URL
    file_name: str
    building_type: BuildingType
    status: str = "preview"  # preview, completed, paid
    
    # Preview data (free)
    preview_data: Optional[dict] = {
        "components_count": 0,
        "estimated_load_kw": 0,
        "file_size_mb": 0,
        "user_info": {}
    }
    
    # Full analysis (paid)
    inventory: Optional[List[dict]] = None
    calculations: Optional[dict] = None
    compliance_audit: Optional[List[dict]] = None
    recommendations: Optional[List[dict]] = None
    
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "analyses"