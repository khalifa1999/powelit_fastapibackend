import cloudinary
import cloudinary.uploader
import os
from fastapi import UploadFile
from typing import Optional, Dict, Any
from app.config import settings

class CloudinaryService:
    def __init__(self):
        # Configure Cloudinary with environment variables
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
    
    async def upload_blueprint(self, file: UploadFile, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload blueprint file to Cloudinary"""
        try:
            # Create folder structure based on user_id or anonymous
            folder = f"powerlit/{user_id}" if user_id else "powerlit/previews"
            
            # Upload file
            upload_result = cloudinary.uploader.upload(
                file.file,
                folder=folder,
                resource_type="auto",  # Auto-detect file type
                allowed_formats=["pdf", "png", "jpg", "jpeg"],
                max_file_size=50 * 1024 * 1024,  # 50MB limit
                overwrite=True,
                use_filename=True,
                unique_filename=True
            )
            
            return {
                "success": True,
                "url": upload_result["secure_url"],
                "public_id": upload_result["public_id"],
                "size": upload_result.get("bytes", 0),
                "format": upload_result.get("format", ""),
                "folder": upload_result.get("folder", "")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_file(self, public_id: str) -> bool:
        """Delete file from Cloudinary"""
        try:
            cloudinary.uploader.destroy(public_id)
            return True
        except Exception:
            return False
    
    async def get_file_info(self, public_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from Cloudinary"""
        try:
            result = cloudinary.api.resource(public_id)
            return {
                "public_id": result.get("public_id"),
                "url": result.get("secure_url"),
                "size": result.get("bytes", 0),
                "format": result.get("format", ""),
                "created_at": result.get("created_at")
            }
        except Exception:
            return None