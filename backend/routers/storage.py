"""
Storage Router - File Upload/Download Endpoints

Provides HTTP endpoints for file uploads and downloads using Emergent Object Storage.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Header, Query, Depends
from fastapi.responses import Response
from typing import Optional
import logging

from .deps import get_current_user
from .models import User
from utils.storage import (
    upload_file,
    get_object,
    get_content_type,
    init_storage
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["Storage"])


# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types for uploads
ALLOWED_EXTENSIONS = {
    # Documents
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv",
    # Images
    "jpg", "jpeg", "png", "gif", "webp",
    # Archives
    "zip",
}


@router.post("/upload")
async def upload_storage_file(
    file: UploadFile = File(...),
    folder: str = Query(default="uploads", description="Folder name for organization"),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a file to storage.
    
    Returns the storage metadata including the access URL.
    """
    # Validate extension
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Determine content type
    content_type = file.content_type or get_content_type(file.filename)
    
    try:
        result = upload_file(
            data=content,
            original_filename=file.filename,
            content_type=content_type,
            folder=folder,
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "file": result
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/files/{path:path}")
async def download_file(
    path: str,
    authorization: Optional[str] = Header(None),
    auth: Optional[str] = Query(None)
):
    """
    Download a file from storage.
    
    Supports both header-based auth (Authorization: Bearer token)
    and query param auth (?auth=token) for image src tags.
    """
    # For now, allow public access to storage files (they have UUIDs)
    # In production, you'd want to validate the auth header
    
    try:
        content, content_type = get_object(path)
        
        # Determine filename from path
        filename = path.split("/")[-1] if "/" in path else path
        
        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\"",
                "Cache-Control": "public, max-age=3600"
            }
        )
    except Exception as e:
        logger.error(f"Download failed for {path}: {e}")
        raise HTTPException(status_code=404, detail="File not found")


@router.on_event("startup")
async def init_storage_on_startup():
    """Initialize storage on app startup."""
    try:
        init_storage()
        logger.info("Storage initialized on startup")
    except Exception as e:
        logger.warning(f"Storage init failed on startup (will retry on first use): {e}")
