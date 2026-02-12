from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class AnalysisHistory(Base):
    """Database model for storing analysis history"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # API key or user identifier
    project_name = Column(String, nullable=True)
    building_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Store the full analysis response as JSON
    analysis_data = Column(JSON)
    
    # Summary fields for quick access
    total_connected_load = Column(Float)
    maximum_demand = Column(Float)
    diversity_factor = Column(Float)
    component_count = Column(Integer)
    
    # Store file names (not the actual files)
    file_names = Column(Text)  # JSON array of file names
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "building_type": self.building_type,
            "created_at": self.created_at.isoformat(),
            "total_connected_load": self.total_connected_load,
            "maximum_demand": self.maximum_demand,
            "diversity_factor": self.diversity_factor,
            "component_count": self.component_count,
            "file_names": json.loads(self.file_names) if self.file_names else [],
            "analysis_data": self.analysis_data
        }

# Database setup
def get_engine(database_url: str = "sqlite:///./powerlit.db"):
    """Create database engine"""
    return create_engine(database_url, connect_args={"check_same_thread": False} if "sqlite" in database_url else {})

def init_db(engine):
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_session_maker(engine):
    """Get session maker bound to engine"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
