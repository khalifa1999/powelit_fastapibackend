from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # API Keys
    GOOGLE_API_KEY: str = ""
    
    # Application settings
    APP_NAME: str = "PowerLit"
    DEBUG: bool = False
    
    # Vector DB settings
    CHROMA_DB_PATH: str = "./chromadb_store"
    COLLECTION_NAME: str = "gs1009_standards"
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # File upload settings
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".png", ".jpg", ".jpeg"}
    
    # NEW - MongoDB
    MONGODB_URL: str = ""
    
    # NEW - Authentication
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # NEW - Cloudinary
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    
    # NEW - Paystack
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    
    # NEW - Currency
    USD_TO_GHS_RATE: float = 11.01

#@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
