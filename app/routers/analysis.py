from fastapi import APIRouter, File, UploadFile, HTTPException, Form, Header, Depends
from typing import List, Optional
import time
import os

from app.models.schemas import AnalysisRequest, AnalysisResponse, BuildingType
from app.services.gemini_service import GeminiBlueprintService, FileTypeDetector
from app.services.calculator import LoadCalculator
from app.services.rag import RAGService
from app.services.history import HistoryService
from app.config import settings

router = APIRouter()

# Initialize history service
history_service = HistoryService()

def get_user_id(x_api_key: Optional[str] = Header(None, description="User API key for history tracking")) -> str:
    """Get user ID from API key header or use default"""
    return x_api_key or "anonymous"

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_blueprint(
    building_type: BuildingType = Form(...),
    project_name: str = Form(None),
    blueprint_file: UploadFile = File(..., description="Blueprint file (PDF, PNG, JPG) - contains floor plan"),
    legend_file: Optional[UploadFile] = File(None, description="Optional: Legend file (PDF, PNG, JPG) - contains symbol definitions"),
    save_history: bool = Form(True, description="Save this analysis to history"),
    user_id: str = Depends(get_user_id)
):
    """
    Analyze electrical blueprints and calculate load requirements using Gemini AI.
    
    **Two modes supported:**
    
    **Mode 1: Separate Legend and Blueprint**
    - Upload blueprint_file (the floor plan)
    - Upload legend_file (the symbol legend/schedule)
    - System will use legend to interpret blueprint symbols
    
    **Mode 2: Combined File**
    - Upload only blueprint_file (contains both legend and floor plan)
    - System will auto-detect and parse both
    
    - **building_type**: Type of building (residential, commercial, industrial)
    - **project_name**: Optional project identifier
    - **blueprint_file**: Blueprint/floor plan file (required)
    - **legend_file**: Legend/schedule file (optional)
    - **save_history**: Whether to save this analysis to user's history (default: true)
    - **x-api-key**: Header for user identification (optional)
    """
    start_time = time.time()
    
    # Validate blueprint file
    blueprint_ext = os.path.splitext(blueprint_file.filename)[1].lower() if blueprint_file.filename else ""
    if blueprint_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid blueprint file type: {blueprint_ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Validate legend file if provided
    legend_content = None
    if legend_file:
        legend_ext = os.path.splitext(legend_file.filename)[1].lower() if legend_file.filename else ""
        if legend_ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid legend file type: {legend_ext}. Allowed: {settings.ALLOWED_EXTENSIONS}"
            )
        legend_content = await legend_file.read()
    
    try:
        # Read blueprint file
        blueprint_content = await blueprint_file.read()
        
        # Initialize Gemini service
        gemini_service = GeminiBlueprintService()
        
        # Analyze blueprint using Gemini
        inventory = await gemini_service.analyze_blueprint(
            blueprint_file=blueprint_content,
            legend_file=legend_content,
            filename=blueprint_file.filename or "blueprint"
        )
        
        if not inventory:
            raise HTTPException(
                status_code=422,
                detail="Could not analyze the blueprint. Please try again later."
            )
        
        # Initialize other services
        calculator = LoadCalculator()
        rag_service = RAGService()
        
        # Calculate loads
        calculations = calculator.calculate_load(
            inventory=inventory,
            building_type=building_type
        )
        
        # Check compliance using RAG system
        compliance = await rag_service.check_compliance(calculations)
        
        # Get recommendations
        recommendations = calculator.get_power_recommendations(calculations)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Build response data for history
        response_data = {
            "inventory": [item.model_dump() for item in inventory],
            "calculations": calculations.model_dump(),
            "compliance_audit": [audit.model_dump() for audit in compliance],
            "recommendations": [rec.model_dump() for rec in recommendations],
            "processing_time_ms": processing_time
        }
        
        # Save to history if requested
        if save_history:
            try:
                file_names = [blueprint_file.filename] if blueprint_file.filename else []
                if legend_file and legend_file.filename:
                    file_names.append(legend_file.filename)
                
                history_service.save_analysis(
                    user_id=user_id,
                    project_name=project_name,
                    building_type=building_type.value,
                    analysis_data=response_data,
                    file_names=file_names
                )
            except Exception as e:
                # Don't fail the request if history saving fails
                print(f"Warning: Failed to save history: {e}")
        
        return AnalysisResponse(
            inventory=inventory,
            calculations=calculations,
            compliance_audit=compliance,
            recommendations=recommendations,
            processing_time_ms=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        if str(e) == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(status_code=429, detail="You've sent too many requests. Please wait a moment and try again.")
        elif str(e) == "SERVICE_UNAVAILABLE":
            raise HTTPException(status_code=503, detail="The service is temporarily busy. Please try again in a few moments.")
        elif str(e) == "REQUEST_TIMEOUT":
            raise HTTPException(status_code=504, detail="The request took too long. Please try with fewer or smaller files.")
        else:
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-batch")
async def analyze_blueprint_batch(
    building_type: BuildingType = Form(..., description="Type of building: residential, commercial, or industrial"),
    project_name: Optional[str] = Form(None),
    files: List[UploadFile] = File(..., description="Multiple files - mix of blueprints and legends (auto-detected)"),
    save_history: bool = Form(True, description="Save this analysis to history"),
    user_id: str = Depends(get_user_id)
):
    """
    Analyze multiple blueprint files with automatic legend/blueprint detection.
    
    This endpoint accepts multiple files and automatically:
    - Detects which files are legends vs blueprints
    - Matches legends to appropriate blueprints
    - Performs analysis on each blueprint
    
    - **building_type**: Type of building (residential, commercial, industrial)
    - **project_name**: Optional project identifier
    - **files**: Multiple blueprint/legend files (PDF, PNG, JPG)
    - **save_history**: Whether to save this analysis to user's history (default: true)
    - **x-api-key**: Header for user identification (optional)
    
    Example curl:
    curl -X POST "http://localhost:8000/api/v1/analysis/analyze-batch" \
      -F "building_type=residential" \
      -F "files=@plan_a.png" \
      -F "files=@plan_b.png"
    """
    import traceback
    start_time = time.time()
    
    print(f"📥 Received analyze-batch request")
    print(f"   Building type: {building_type}")
    print(f"   Files count: {len(files) if files else 0}")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided. Please upload at least one file using the 'files' field.")
    
    try:
        # Validate file extensions
        for file in files:
            if file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in settings.ALLOWED_EXTENSIONS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid file type '{ext}' for file '{file.filename}'. Allowed: {settings.ALLOWED_EXTENSIONS}"
                    )
        
        # Read all files and categorize them
        file_contents = []
        for idx, file in enumerate(files):
            print(f"   Reading file {idx+1}: {file.filename}")
            content = await file.read()
            file_size = len(content)
            print(f"   File size: {file_size} bytes")
            if file_size == 0:
                raise HTTPException(status_code=400, detail=f"File '{file.filename}' is empty")
            file_contents.append((file.filename or "unknown", content))
        
        # Auto-detect file types
        detector = FileTypeDetector()
        categorized = detector.detect_file_types(file_contents)
        
        legends = categorized["legends"]
        blueprints = categorized["blueprints"]
        
        if not blueprints:
            raise HTTPException(
                status_code=400, 
                detail="No blueprint files detected. Please upload files with names containing: plan, layout, drawing, blueprint, floor, or elevation"
            )
        
        # Initialize services
        gemini_service = GeminiBlueprintService()
        calculator = LoadCalculator()
        rag_service = RAGService()
        
        # Use first legend if available, otherwise None
        legend_content = legends[0][1] if legends else None
        
        # Process all blueprints
        all_inventory = []
        blueprint_results = []
        
        for filename, content in blueprints:
            inventory = await gemini_service.analyze_blueprint(
                blueprint_file=content,
                legend_file=legend_content,
                filename=filename
            )
            
            if inventory:
                all_inventory.extend(inventory)
                blueprint_results.append({
                    "filename": filename,
                    "components_found": len(inventory),
                    "total_watts": sum(item.total_watts for item in inventory)
                })
        
        if not all_inventory:
            raise HTTPException(
                status_code=422,
                detail="Could not analyze any of the uploaded files. Please try uploading clearer blueprint images."
            )
        
        # Calculate loads (use aggregated inventory)
        calculations = calculator.calculate_load(
            inventory=all_inventory,
            building_type=building_type
        )
        
        # Check compliance
        compliance = await rag_service.check_compliance(calculations)
        
        # Get recommendations
        recommendations = calculator.get_power_recommendations(calculations)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "status": "success",
            "files_processed": len(blueprints),
            "legends_detected": len(legends),
            "blueprint_results": blueprint_results,
            "analysis": AnalysisResponse(
                inventory=all_inventory,
                calculations=calculations,
                compliance_audit=compliance,
                recommendations=recommendations,
                processing_time_ms=processing_time
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if str(e) == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(status_code=429, detail="You've sent too many requests. Please wait a moment and try again.")
        elif str(e) == "SERVICE_UNAVAILABLE":
            raise HTTPException(status_code=503, detail="The service is temporarily busy. Please try again in a few moments.")
        elif str(e) == "REQUEST_TIMEOUT":
            raise HTTPException(status_code=504, detail="The request took too long. Please try with fewer or smaller files.")
        else:
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
        if str(e) == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(status_code=429, detail="You've sent too many requests. Please wait a moment and try again.")
        elif str(e) == "SERVICE_UNAVAILABLE":
            raise HTTPException(status_code=503, detail="The service is temporarily busy. Please try again in a few moments.")
        elif str(e) == "REQUEST_TIMEOUT":
            raise HTTPException(status_code=504, detail="The request took too long. Please try with fewer or smaller files.")
        else:
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


@router.get("/history")
async def get_analysis_history(
    skip: int = 0,
    limit: int = 50,
    user_id: str = Depends(get_user_id)
):
    """
    Get analysis history for the user.
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return
    - **x-api-key**: Header for user identification (optional)
    """
    try:
        history = history_service.get_user_history(user_id, skip=skip, limit=limit)
        return {
            "history": [item.to_dict() for item in history],
            "total": len(history),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@router.get("/history/stats")
async def get_user_stats(user_id: str = Depends(get_user_id)):
    """
    Get statistics for the user's analysis history.
    
    - **x-api-key**: Header for user identification (optional)
    """
    try:
        stats = history_service.get_user_stats(user_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@router.get("/history/{analysis_id}")
async def get_analysis_detail(
    analysis_id: int,
    user_id: str = Depends(get_user_id)
):
    """
    Get detailed analysis by ID.
    
    - **analysis_id**: The ID of the analysis to retrieve
    - **x-api-key**: Header for user identification (optional)
    """
    try:
        analysis = history_service.get_analysis_by_id(user_id, analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return analysis.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


@router.delete("/history/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    user_id: str = Depends(get_user_id)
):
    """
    Delete an analysis from history.
    
    - **analysis_id**: The ID of the analysis to delete
    - **x-api-key**: Header for user identification (optional)
    """
    try:
        success = history_service.delete_analysis(user_id, analysis_id)
        if not success:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return {"status": "success", "message": "Analysis deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
