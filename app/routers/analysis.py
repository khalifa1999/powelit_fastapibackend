from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import List
import time
import os

from app.models.schemas import AnalysisRequest, AnalysisResponse, BuildingType
from app.services.vision import VisionService
from app.services.calculator import LoadCalculator
from app.services.rag import RAGService
from app.config import settings

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_blueprint(
    building_type: BuildingType = Form(...),
    project_name: str = Form(None),
    files: List[UploadFile] = File(...)
):
    """
    Analyze electrical blueprints and calculate load requirements.
    
    - **building_type**: Type of building (residential, commercial, industrial)
    - **project_name**: Optional project identifier
    - **files**: Blueprint files (PDF, PNG, JPG)
    """
    start_time = time.time()
    
    # Validate files
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
    
    try:
        # Initialize services
        vision_service = VisionService()
        calculator = LoadCalculator()
        rag_service = RAGService()
        
        # Process files (placeholder for actual implementation)
        inventory = await vision_service.extract_components(files)
        
        # Calculate loads
        calculations = calculator.calculate_load(
            inventory=inventory,
            building_type=building_type
        )
        
        # Check compliance
        compliance = await rag_service.check_compliance(calculations)
        
        # Get recommendations
        recommendations = calculator.get_power_recommendations(calculations)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AnalysisResponse(
            inventory=inventory,
            calculations=calculations,
            compliance_audit=compliance,
            recommendations=recommendations,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest-standards")
async def ingest_standards():
    """
    Ingest GS1009 standards into the vector database.
    Run this when new standards are added.
    """
    try:
        rag_service = RAGService()
        result = await rag_service.ingest_standards()
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/diversity-factors")
async def get_diversity_factors():
    """Get standard diversity factors for different building types"""
    return {
        "residential": 0.6,
        "commercial": 0.8,
        "industrial": 0.9,
        "description": "Diversity factors per Ghana Energy Commission standards"
    }
