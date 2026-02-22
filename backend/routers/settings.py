"""
Settings Router - System settings and configurations.
"""

from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from .deps import get_db, ADMIN_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get system settings"""
    db = get_db()
    
    settings = await db.settings.find({}, {"_id": 0}).to_list(100)
    
    # Convert to dict
    settings_dict = {}
    for s in settings:
        settings_dict[s.get("key")] = s.get("value")
    
    return settings_dict


@router.get("/{key}")
async def get_setting(key: str, current_user: User = Depends(get_current_user)):
    """Get a specific setting"""
    db = get_db()
    
    setting = await db.settings.find_one({"key": key}, {"_id": 0})
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return setting


@router.put("/{key}")
async def update_setting(key: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a setting (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can update settings")
    
    value = data.get("value")
    if value is None:
        raise HTTPException(status_code=400, detail="value is required")
    
    await db.settings.update_one(
        {"key": key},
        {
            "$set": {
                "key": key,
                "value": value,
                "updated_by": current_user.id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Setting updated", "key": key}


@router.post("")
async def create_setting(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new setting (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can create settings")
    
    key = data.get("key")
    value = data.get("value")
    
    if not key:
        raise HTTPException(status_code=400, detail="key is required")
    
    existing = await db.settings.find_one({"key": key}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Setting with this key already exists")
    
    setting_doc = {
        "key": key,
        "value": value,
        "description": data.get("description", ""),
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.settings.insert_one(setting_doc)
    setting_doc.pop("_id", None)
    return setting_doc


@router.delete("/{key}")
async def delete_setting(key: str, current_user: User = Depends(get_current_user)):
    """Delete a setting (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can delete settings")
    
    result = await db.settings.delete_one({"key": key})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    return {"message": "Setting deleted", "key": key}
