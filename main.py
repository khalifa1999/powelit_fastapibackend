from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os
import traceback

from app.routers import analysis
from app.config import settings
from app.utils.error_handler import ErrorCode, create_error_response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    os.makedirs("data/knowledge_base", exist_ok=True)
    os.makedirs("chromadb_store", exist_ok=True)
    
    # Test services
    print("🔧 Testing services...")
    try:
        from app.services.calculator import LoadCalculator
        calc = LoadCalculator()
        print("✅ LoadCalculator initialized")
    except Exception as e:
        print(f"⚠️ LoadCalculator failed: {e}")
    
    try:
        from app.services.rag import RAGService
        rag = RAGService()
        print("✅ RAGService initialized")
    except Exception as e:
        print(f"⚠️ RAGService failed: {e}")
    
    try:
        from app.services.gemini_service import GeminiBlueprintService
        gemini = GeminiBlueprintService()
        print("✅ GeminiBlueprintService initialized")
    except Exception as e:
        print(f"⚠️ GeminiBlueprintService failed: {e}")
    
    print("✅ PowerLit API started successfully")
    yield
    # Shutdown
    print("🛑 PowerLit API shutting down")

app = FastAPI(
    title="PowerLit API",
    description="Electrical blueprint analysis and load calculation API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])


# Global exception handlers for user-friendly error responses

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors (422 from Pydantic)"""
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        loc = " -> ".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "")
        error_messages.append(f"{loc}: {msg}")
    
    error_response = create_error_response(
        ErrorCode.VALIDATION_ERROR,
        technical_details="; ".join(error_messages),
        custom_message="The request data is invalid",
        custom_suggestion="Please check that all required fields are provided and all files are valid PDF, PNG, or JPG files."
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.to_dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with user-friendly messages"""
    print(f"🔴 HTTPException caught: {exc.status_code}, detail type: {type(exc.detail)}, detail: {exc.detail}")
    
    # Map HTTP status codes to error codes
    status_code_mapping = {
        400: ErrorCode.VALIDATION_ERROR,
        404: ErrorCode.INVALID_BLUEPRINT,
        422: ErrorCode.ANALYSIS_FAILED,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.REQUEST_TIMEOUT,
    }
    
    error_code = status_code_mapping.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    # Check if detail already contains structured error info
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        print(f"✅ Returning structured error response")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Create structured error response
    error_response = create_error_response(
        error_code=error_code,
        technical_details=str(exc.detail) if exc.detail else None
    )
    
    print(f"📝 Created new error response: {error_response.to_dict()}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.to_dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    # Log the full error immediately
    print(f"❌ CRITICAL ERROR: {exc}")
    print(traceback.format_exc())
    
    # Map common exception messages to error codes
    error_code = ErrorCode.INTERNAL_ERROR
    technical_details = str(exc)
    
    exc_str = str(exc).upper()
    if "RATE_LIMIT" in exc_str or "RATE LIMIT" in exc_str:
        error_code = ErrorCode.RATE_LIMIT_EXCEEDED
    elif "SERVICE_UNAVAILABLE" in exc_str or "UNAVAILABLE" in exc_str:
        error_code = ErrorCode.SERVICE_UNAVAILABLE
    elif "TIMEOUT" in exc_str or "DEADLINE" in exc_str:
        error_code = ErrorCode.REQUEST_TIMEOUT
    elif "FILE" in exc_str and ("READ" in exc_str or "OPEN" in exc_str):
        error_code = ErrorCode.FILE_READ_ERROR
    elif "API_KEY" in exc_str or "KEY" in exc_str:
        error_code = ErrorCode.SERVICE_UNAVAILABLE
        technical_details = "Service configuration issue"
    
    try:
        error_response = create_error_response(
            error_code=error_code,
            technical_details=technical_details
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.to_dict()
        )
    except Exception as handler_error:
        # If error handling fails, return a simple response
        print(f"❌ Error handler failed: {handler_error}")
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "user_message": "Something went wrong",
                "suggestion": "Please try again later",
                "retryable": True
            }
        )

@app.get("/")
async def root():
    return {
        "message": "PowerLit API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
