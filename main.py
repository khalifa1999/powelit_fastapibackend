from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.routers import analysis, auth, payments
from app.config import settings
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    os.makedirs("data/knowledge_base", exist_ok=True)
    os.makedirs("chromadb_store", exist_ok=True)
    
    # Initialize MongoDB and Beanie ODM
    await init_db()
    
    yield
    # Shutdown
    pass

app = FastAPI(
    title="PowerLit API",
    description="Electrical blueprint analysis and load calculation API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(auth.router)
app.include_router(payments.router)

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
