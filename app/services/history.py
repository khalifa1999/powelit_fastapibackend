from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.database import AnalysisHistory, get_engine, init_db, get_session_maker
from app.config import settings
import json
from datetime import datetime

class HistoryService:
    """Service for managing analysis history"""
    
    def __init__(self):
        # Use SQLite by default, can be overridden with DATABASE_URL env var
        database_url = getattr(settings, 'DATABASE_URL', 'sqlite:///./powerlit.db')
        self.engine = get_engine(database_url)
        init_db(self.engine)
        self.SessionLocal = get_session_maker(self.engine)
    
    def get_db(self):
        """Get database session"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def save_analysis(
        self,
        user_id: str,
        project_name: Optional[str],
        building_type: str,
        analysis_data: dict,
        file_names: List[str]
    ) -> AnalysisHistory:
        """Save an analysis to history"""
        db = next(self.get_db())
        
        try:
            # Extract summary data
            calculations = analysis_data.get('calculations', {})
            inventory = analysis_data.get('inventory', [])
            
            history_entry = AnalysisHistory(
                user_id=user_id,
                project_name=project_name,
                building_type=building_type,
                total_connected_load=calculations.get('total_connected_load', 0),
                maximum_demand=calculations.get('maximum_demand', 0),
                diversity_factor=calculations.get('diversity_factor', 0),
                component_count=len(inventory),
                file_names=json.dumps(file_names),
                analysis_data=analysis_data
            )
            
            db.add(history_entry)
            db.commit()
            db.refresh(history_entry)
            return history_entry
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_user_history(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """Get analysis history for a user"""
        db = next(self.get_db())
        try:
            results = db.query(AnalysisHistory).filter(
                AnalysisHistory.user_id == user_id
            ).order_by(
                AnalysisHistory.created_at.desc()
            ).offset(skip).limit(limit).all()
            return results
        finally:
            db.close()
    
    def get_analysis_by_id(
        self,
        user_id: str,
        analysis_id: int
    ) -> Optional[AnalysisHistory]:
        """Get a specific analysis by ID"""
        db = next(self.get_db())
        try:
            result = db.query(AnalysisHistory).filter(
                AnalysisHistory.user_id == user_id,
                AnalysisHistory.id == analysis_id
            ).first()
            return result
        finally:
            db.close()
    
    def delete_analysis(
        self,
        user_id: str,
        analysis_id: int
    ) -> bool:
        """Delete an analysis from history"""
        db = next(self.get_db())
        try:
            result = db.query(AnalysisHistory).filter(
                AnalysisHistory.user_id == user_id,
                AnalysisHistory.id == analysis_id
            ).first()
            
            if result:
                db.delete(result)
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get statistics for a user"""
        db = next(self.get_db())
        try:
            total_analyses = db.query(AnalysisHistory).filter(
                AnalysisHistory.user_id == user_id
            ).count()
            
            latest = db.query(AnalysisHistory).filter(
                AnalysisHistory.user_id == user_id
            ).order_by(
                AnalysisHistory.created_at.desc()
            ).first()
            
            return {
                "total_analyses": total_analyses,
                "last_analysis_date": latest.created_at.isoformat() if latest else None,
                "last_project": latest.project_name if latest else None
            }
        finally:
            db.close()
