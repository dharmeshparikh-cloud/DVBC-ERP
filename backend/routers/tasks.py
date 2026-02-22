"""
Tasks Router - Task management, delegation, and tracking.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field
from .deps import get_db, PROJECT_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    project_id: Optional[str] = None
    sow_item_id: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: str = "medium"  # low, medium, high, urgent
    due_date: Optional[str] = None
    category: Optional[str] = None
    estimated_hours: Optional[float] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    actual_hours: Optional[float] = None


@router.post("")
async def create_task(data: TaskCreate, current_user: User = Depends(get_current_user)):
    """Create a new task"""
    db = get_db()
    
    task_id = str(uuid.uuid4())
    task_doc = {
        "id": task_id,
        "title": data.title,
        "description": data.description,
        "project_id": data.project_id,
        "sow_item_id": data.sow_item_id,
        "assigned_to": data.assigned_to,
        "priority": data.priority,
        "due_date": data.due_date,
        "category": data.category,
        "estimated_hours": data.estimated_hours,
        "actual_hours": 0,
        "status": TaskStatus.PENDING,
        "order": 0,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.tasks.insert_one(task_doc)
    task_doc.pop("_id", None)
    return task_doc


@router.get("")
async def get_tasks(
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks with filters"""
    db = get_db()
    
    query = {}
    if project_id:
        query["project_id"] = project_id
    if assigned_to:
        query["assigned_to"] = assigned_to
    if status:
        query["status"] = status
    
    # If not manager, only show own tasks or tasks created by user
    if current_user.role not in PROJECT_ROLES:
        query["$or"] = [
            {"assigned_to": current_user.id},
            {"created_by": current_user.id}
        ]
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort([("priority", -1), ("due_date", 1)]).to_list(500)
    return tasks


@router.get("/{task_id}")
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Get task by ID"""
    db = get_db()
    
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.patch("/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, current_user: User = Depends(get_current_user)):
    """Update a task"""
    db = get_db()
    
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check permission
    can_edit = (
        current_user.role in PROJECT_ROLES or
        task.get("assigned_to") == current_user.id or
        task.get("created_by") == current_user.id
    )
    if not can_edit:
        raise HTTPException(status_code=403, detail="Not authorized to edit this task")
    
    update_data = data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user.id
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    return {"message": "Task updated", "task_id": task_id}


@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Delete a task"""
    db = get_db()
    
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    can_delete = (
        current_user.role in PROJECT_ROLES or
        task.get("created_by") == current_user.id
    )
    if not can_delete:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    
    await db.tasks.delete_one({"id": task_id})
    
    return {"message": "Task deleted"}


@router.patch("/{task_id}/delegate")
async def delegate_task(task_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Delegate task to another user"""
    db = get_db()
    
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    new_assignee = data.get("assigned_to")
    if not new_assignee:
        raise HTTPException(status_code=400, detail="assigned_to is required")
    
    await db.tasks.update_one(
        {"id": task_id},
        {
            "$set": {
                "assigned_to": new_assignee,
                "delegated_by": current_user.id,
                "delegated_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Task delegated", "new_assignee": new_assignee}


@router.patch("/reorder")
async def reorder_tasks(data: dict, current_user: User = Depends(get_current_user)):
    """Reorder tasks"""
    db = get_db()
    
    task_orders = data.get("tasks", [])  # [{id: "xxx", order: 1}, ...]
    
    for task_order in task_orders:
        await db.tasks.update_one(
            {"id": task_order["id"]},
            {"$set": {"order": task_order["order"]}}
        )
    
    return {"message": f"Reordered {len(task_orders)} tasks"}


@router.patch("/{task_id}/dates")
async def update_task_dates(task_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update task dates (for Gantt chart)"""
    db = get_db()
    
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_fields = {}
    if "start_date" in data:
        update_fields["start_date"] = data["start_date"]
    if "due_date" in data:
        update_fields["due_date"] = data["due_date"]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_fields})
    
    return {"message": "Task dates updated"}
