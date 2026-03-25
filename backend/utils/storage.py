"""
Emergent Object Storage Utility

Provides a centralized interface for file uploads to Emergent Object Storage.
Used across the application for document uploads, proofs, receipts, etc.
"""

import os
import uuid
import requests
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "netra-erp"

# Module-level storage key - initialized once and reused
_storage_key: Optional[str] = None


def get_emergent_key() -> str:
    """Get the Emergent LLM key from environment."""
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise ValueError("EMERGENT_LLM_KEY not configured")
    return key


def init_storage() -> str:
    """
    Initialize storage and get a session-scoped storage key.
    Call ONCE at startup. Returns a reusable storage_key.
    """
    global _storage_key
    if _storage_key:
        return _storage_key
    
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": get_emergent_key()},
            timeout=30
        )
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Storage initialized successfully")
        return _storage_key
    except Exception as e:
        logger.error(f"Storage initialization failed: {e}")
        raise


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """
    Upload a file to storage.
    
    Args:
        path: Storage path (no leading slash)
        data: File content as bytes
        content_type: MIME type
        
    Returns:
        {"path": "...", "size": 123, "etag": "..."}
    """
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> Tuple[bytes, str]:
    """
    Download a file from storage.
    
    Args:
        path: Storage path
        
    Returns:
        Tuple of (content_bytes, content_type)
    """
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def upload_file(
    data: bytes,
    original_filename: str,
    content_type: str,
    folder: str,
    user_id: Optional[str] = None
) -> dict:
    """
    High-level file upload function.
    
    Args:
        data: File content
        original_filename: Original filename (for extension)
        content_type: MIME type
        folder: Logical folder (e.g., "proofs", "receipts", "documents")
        user_id: Optional user ID for path organization
        
    Returns:
        {
            "storage_path": str,
            "original_filename": str,
            "content_type": str,
            "size": int,
            "file_url": str  # Backend URL to access the file
        }
    """
    # Extract extension
    ext = original_filename.split(".")[-1] if "." in original_filename else "bin"
    
    # Build storage path
    unique_id = str(uuid.uuid4())
    if user_id:
        path = f"{APP_NAME}/{folder}/{user_id}/{unique_id}.{ext}"
    else:
        path = f"{APP_NAME}/{folder}/{unique_id}.{ext}"
    
    # Upload
    result = put_object(path, data, content_type)
    
    # Build backend URL for access
    backend_url = os.environ.get("REACT_APP_BACKEND_URL", "")
    file_url = f"{backend_url}/api/storage/files/{result['path']}"
    
    return {
        "storage_path": result["path"],
        "original_filename": original_filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "file_url": file_url
    }


# Common MIME types
MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "csv": "text/csv",
    "json": "application/json",
    "zip": "application/zip",
    "mp4": "video/mp4",
    "mp3": "audio/mpeg",
}


def get_content_type(filename: str, default: str = "application/octet-stream") -> str:
    """Get MIME type from filename extension."""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    return MIME_TYPES.get(ext, default)
