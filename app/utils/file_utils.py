import os
import shutil
from typing import Optional
from fastapi import UploadFile

async def save_upload_file(upload_file: UploadFile, destination: str) -> str:
    """Save an uploaded file to disk"""
    file_path = os.path.join(destination, upload_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """Check if file extension is allowed"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions

def ensure_dir(directory: str):
    """Ensure directory exists"""
    os.makedirs(directory, exist_ok=True)
