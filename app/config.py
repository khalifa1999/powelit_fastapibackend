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

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
