from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import time
import os

from app.models.schemas import BuildingType, AnalysisResponse
from app.models.user import User
from app.models.analysis import Analysis
from app.services.vision import VisionService
from app.services.calculator import LoadCalculator
from app.services.rag import RAGService
from app.services.cloudinary_service import CloudinaryService
from app.services.currency_service import CurrencyService
from app.dependencies import get_active_user
from app.config import settings

router = APIRouter()

@router.post("/preview")
async def create_preview(
    full_name: str = Form(...),
    email: str = Form(...),
    building_type: BuildingType = Form(...),
    files: List[UploadFile] = File(...)
):
    """Create free preview (no authentication required)"""
    
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    
    start_time = time.time()
    
    # Validate files
    for file in files:
        if not file.filename:
            continue
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
    
    try:
        # Upload first file to Cloudinary (preview)
        cloudinary_service = CloudinaryService()
        upload_result = await cloudinary_service.upload_blueprint(files[0])
        
        if not upload_result["success"]:
            raise HTTPException(status_code=500, detail="File upload failed")
        
        # Extract basic preview data using vision service
        vision_service = VisionService()
        try:
            preview_components = await vision_service.extract_components([files[0]])
        except:
            preview_components = []
        
        # Calculate basic preview data
        total_load_watts = sum(comp.total_watts for comp in preview_components)
        estimated_load_kw = total_load_watts / 1000
        
        # Create preview data
        preview_data = {
            "components_count": len(preview_components),
            "estimated_load_kw": round(estimated_load_kw, 2),
            "file_size_mb": round(upload_result["size"] / (1024 * 1024), 2),
            "user_info": {
                "full_name": full_name,
                "email": email
            }
        }
        
        # Create preview analysis record
        analysis = Analysis(
            file_url=upload_result["url"],
            file_name=files[0].filename,
            building_type=building_type,
            status="preview",
            preview_data=preview_data
        )
        
        await analysis.save()
        
        # Get pricing info
        pricing = CurrencyService.get_ghs_pricing()
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "analysis_id": str(analysis.id),
            "preview": preview_data,
            "pricing": pricing,
            "next_steps": {
                "signup_url": "/api/v1/auth/register",
                "login_url": "/api/v1/auth/login",
                "payment_url": "/api/v1/payments/subscribe"
            },
            "processing_time_ms": processing_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze")
async def create_full_analysis(
    building_type: BuildingType = Form(...),
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_active_user)
):
    """Create full analysis (authentication and credits required)"""
    
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")
    
    # Check user's analysis limit
    if current_user.analyses_used >= current_user.analyses_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Analysis limit reached ({current_user.analyses_used}/{current_user.analyses_limit}). Please upgrade your subscription."
        )
    
    start_time = time.time()
    
    # Validate files
    for file in files:
        if not file.filename:
            continue
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
    
    try:
        # Upload file to Cloudinary (user's folder)
        cloudinary_service = CloudinaryService()
        upload_result = await cloudinary_service.upload_blueprint(files[0], str(current_user.id))
        
        if not upload_result["success"]:
            raise HTTPException(status_code=500, detail="File upload failed")
        
        # Run full analysis
        vision_service = VisionService()
        calculator = LoadCalculator()
        rag_service = RAGService()
        
        inventory = await vision_service.extract_components([files[0]])
        calculations = calculator.calculate_load(inventory, building_type)
        compliance = await rag_service.check_compliance(calculations)
        recommendations = calculator.get_power_recommendations(calculations)
        
        # Create full analysis
        analysis = Analysis(
            user_id=str(current_user.id),
            file_url=upload_result["url"],
            file_name=files[0].filename,
            building_type=building_type,
            status="completed",
            inventory=[comp.dict() for comp in inventory],
            calculations=calculations.dict(),
            compliance_audit=[audit.dict() for audit in compliance],
            recommendations=[rec.dict() for rec in recommendations],
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        
        await analysis.save()
        
        # Update user's analysis count
        current_user.analyses_used += 1
        await current_user.save()
        
        return {
            "analysis_id": str(analysis.id),
            "inventory": [comp.dict() for comp in inventory],
            "calculations": calculations.dict(),
            "compliance_audit": [audit.dict() for audit in compliance],
            "recommendations": [rec.dict() for rec in recommendations],
            "credits_remaining": current_user.analyses_limit - current_user.analyses_used,
            "processing_time_ms": analysis.processing_time_ms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_analysis_history(current_user: User = Depends(get_active_user)):
    """Get user's analysis history"""
    analyses = await Analysis.find({"user_id": str(current_user.id)}).sort("-created_at").to_list()
    
    return {
        "analyses": [
            {
                "id": str(analysis.id),
                "file_name": analysis.file_name,
                "building_type": analysis.building_type,
                "status": analysis.status,
                "created_at": analysis.created_at,
                "processing_time_ms": analysis.processing_time_ms
            }
            for analysis in analyses
        ],
        "total": len(analyses)
    }

@router.get("/{analysis_id}")
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_active_user)
):
    """Get specific analysis by ID"""
    
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Check if user owns this analysis
    if analysis.user_id and analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "analysis": {
            "id": str(analysis.id),
            "file_name": analysis.file_name,
            "building_type": analysis.building_type,
            "status": analysis.status,
            "file_url": analysis.file_url,
            "created_at": analysis.created_at,
            "preview_data": analysis.preview_data,
            "inventory": analysis.inventory,
            "calculations": analysis.calculations,
            "compliance_audit": analysis.compliance_audit,
            "recommendations": analysis.recommendations,
            "processing_time_ms": analysis.processing_time_ms
        }
    }

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
