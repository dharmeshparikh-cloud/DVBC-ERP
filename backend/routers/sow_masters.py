"""
SOW Masters Router - Manage SOW Categories and Scope Items from Admin

This module provides:
1. SOW Categories (Sales, HR, Operations, etc.) - Admin configurable
2. SOW Scope Templates (Pre-defined scopes under each category)
3. Used by Sales team to select scopes, Consulting team to execute
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from .deps import get_db

router = APIRouter(prefix="/sow-masters", tags=["SOW Masters"])


# ============== Models ==============

class SOWCategory(BaseModel):
    """SOW Category (e.g., Sales, HR, Operations)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Sales", "HR", "Operations"
    code: str  # e.g., "sales", "hr", "operations"
    description: Optional[str] = None
    color: Optional[str] = "#6B7280"  # For UI display
    icon: Optional[str] = None  # Icon name for UI
    order: int = 0
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SOWCategoryCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    color: Optional[str] = "#6B7280"
    icon: Optional[str] = None
    order: Optional[int] = 0


class SOWCategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class SOWScopeTemplate(BaseModel):
    """Pre-defined scope item template for selection"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str  # Reference to SOWCategory
    category_code: str  # Denormalized for easy filtering
    name: str  # Scope name/title
    description: Optional[str] = None
    default_timeline_weeks: Optional[int] = None
    is_custom: bool = False  # True if added by sales (not from master)
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SOWScopeTemplateCreate(BaseModel):
    category_id: str
    name: str
    description: Optional[str] = None
    default_timeline_weeks: Optional[int] = None
    is_custom: Optional[bool] = False


class SOWScopeTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_timeline_weeks: Optional[int] = None
    is_active: Optional[bool] = None


# ============== Default Data ==============

DEFAULT_SOW_CATEGORIES = [
    {"name": "Sales", "code": "sales", "description": "Sales process improvement, CRM, pipeline management", "color": "#3B82F6", "order": 1},
    {"name": "HR", "code": "hr", "description": "Human resources, recruitment, employee engagement", "color": "#8B5CF6", "order": 2},
    {"name": "Operations", "code": "operations", "description": "Process optimization, efficiency improvement", "color": "#10B981", "order": 3},
    {"name": "Training", "code": "training", "description": "Employee training, skill development programs", "color": "#F59E0B", "order": 4},
    {"name": "Analytics", "code": "analytics", "description": "Data analysis, reporting, business intelligence", "color": "#EF4444", "order": 5},
    {"name": "Digital Marketing", "code": "digital_marketing", "description": "Online marketing, SEO, social media", "color": "#EC4899", "order": 6},
    {"name": "Finance", "code": "finance", "description": "Financial planning, budgeting, cost optimization", "color": "#14B8A6", "order": 7},
    {"name": "Strategy", "code": "strategy", "description": "Business strategy, market analysis, growth planning", "color": "#6366F1", "order": 8},
]

DEFAULT_SCOPE_TEMPLATES = [
    # Sales
    {"category_code": "sales", "name": "Sales Process Audit", "description": "Comprehensive audit of current sales processes"},
    {"category_code": "sales", "name": "CRM Implementation", "description": "Setup and configure CRM system"},
    {"category_code": "sales", "name": "Sales Team Training", "description": "Training sessions for sales team"},
    {"category_code": "sales", "name": "Pipeline Management Setup", "description": "Define and implement sales pipeline stages"},
    {"category_code": "sales", "name": "Sales KPI Dashboard", "description": "Create sales performance tracking dashboard"},
    {"category_code": "sales", "name": "Lead Scoring Model", "description": "Develop and implement lead scoring criteria"},
    
    # HR
    {"category_code": "hr", "name": "Recruitment Process Design", "description": "Design efficient recruitment workflow"},
    {"category_code": "hr", "name": "Employee Onboarding Program", "description": "Create structured onboarding process"},
    {"category_code": "hr", "name": "Performance Management System", "description": "Design KRA/KPI based performance system"},
    {"category_code": "hr", "name": "Employee Engagement Survey", "description": "Conduct and analyze engagement surveys"},
    {"category_code": "hr", "name": "Compensation Benchmarking", "description": "Market salary benchmarking study"},
    {"category_code": "hr", "name": "HR Policy Documentation", "description": "Document and standardize HR policies"},
    
    # Operations
    {"category_code": "operations", "name": "Process Mapping", "description": "Map and document existing processes"},
    {"category_code": "operations", "name": "Lean Implementation", "description": "Implement lean management principles"},
    {"category_code": "operations", "name": "Quality Management System", "description": "Setup QMS framework"},
    {"category_code": "operations", "name": "Vendor Management", "description": "Vendor evaluation and management system"},
    {"category_code": "operations", "name": "Inventory Optimization", "description": "Optimize inventory management"},
    {"category_code": "operations", "name": "SOP Development", "description": "Create standard operating procedures"},
    
    # Training
    {"category_code": "training", "name": "Training Needs Analysis", "description": "Assess training requirements"},
    {"category_code": "training", "name": "Leadership Development Program", "description": "Design leadership training curriculum"},
    {"category_code": "training", "name": "Soft Skills Training", "description": "Communication and interpersonal skills"},
    {"category_code": "training", "name": "Technical Skills Training", "description": "Job-specific technical training"},
    {"category_code": "training", "name": "Train the Trainer", "description": "Develop internal trainers"},
    
    # Analytics
    {"category_code": "analytics", "name": "Data Audit", "description": "Audit current data systems and quality"},
    {"category_code": "analytics", "name": "BI Dashboard Setup", "description": "Setup business intelligence dashboards"},
    {"category_code": "analytics", "name": "Predictive Analytics Model", "description": "Build predictive models"},
    {"category_code": "analytics", "name": "Customer Segmentation", "description": "Analyze and segment customer base"},
    {"category_code": "analytics", "name": "Market Research Analysis", "description": "Conduct market research"},
    
    # Digital Marketing
    {"category_code": "digital_marketing", "name": "Digital Marketing Audit", "description": "Audit current digital presence"},
    {"category_code": "digital_marketing", "name": "SEO Optimization", "description": "Search engine optimization"},
    {"category_code": "digital_marketing", "name": "Social Media Strategy", "description": "Social media marketing plan"},
    {"category_code": "digital_marketing", "name": "Content Marketing Plan", "description": "Content strategy and calendar"},
    {"category_code": "digital_marketing", "name": "PPC Campaign Setup", "description": "Paid advertising campaigns"},
    
    # Finance
    {"category_code": "finance", "name": "Financial Health Assessment", "description": "Assess financial status"},
    {"category_code": "finance", "name": "Budgeting Framework", "description": "Setup budgeting process"},
    {"category_code": "finance", "name": "Cost Optimization Study", "description": "Identify cost reduction opportunities"},
    {"category_code": "finance", "name": "Cash Flow Management", "description": "Cash flow forecasting and management"},
    
    # Strategy
    {"category_code": "strategy", "name": "Strategic Planning Workshop", "description": "Facilitate strategy sessions"},
    {"category_code": "strategy", "name": "Competitive Analysis", "description": "Analyze competitive landscape"},
    {"category_code": "strategy", "name": "Business Model Review", "description": "Review and optimize business model"},
    {"category_code": "strategy", "name": "Growth Strategy Development", "description": "Develop growth roadmap"},
]


# ============== Categories Endpoints ==============

@router.get("/categories", response_model=List[SOWCategory])
async def get_sow_categories(include_inactive: bool = False):
    """Get all SOW categories"""
    query = {} if include_inactive else {"is_active": True}
    categories = await get_db().sow_categories.find(query, {"_id": 0}).sort("order", 1).to_list(100)
    
    for cat in categories:
        if isinstance(cat.get('created_at'), str):
            cat['created_at'] = datetime.fromisoformat(cat['created_at'])
        if isinstance(cat.get('updated_at'), str):
            cat['updated_at'] = datetime.fromisoformat(cat['updated_at'])
    
    return categories


@router.post("/categories", response_model=SOWCategory)
async def create_sow_category(category: SOWCategoryCreate, current_user_id: str = None):
    """Create a new SOW category (Admin only)"""
    existing = await get_db().sow_categories.find_one({"code": category.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Category with code '{category.code}' already exists")
    
    new_category = SOWCategory(**category.model_dump(), created_by=current_user_id)
    doc = new_category.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await get_db().sow_categories.insert_one(doc)
    return new_category


@router.put("/categories/{category_id}", response_model=SOWCategory)
async def update_sow_category(category_id: str, update: SOWCategoryUpdate):
    """Update SOW category"""
    existing = await get_db().sow_categories.find_one({"id": category_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await get_db().sow_categories.update_one({"id": category_id}, {"$set": update_data})
    
    updated = await get_db().sow_categories.find_one({"id": category_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    
    return SOWCategory(**updated)


@router.delete("/categories/{category_id}")
async def delete_sow_category(category_id: str):
    """Soft delete SOW category"""
    existing = await get_db().sow_categories.find_one({"id": category_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    await get_db().sow_categories.update_one(
        {"id": category_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Category deactivated successfully"}


# ============== Scope Templates Endpoints ==============

@router.get("/scopes", response_model=List[SOWScopeTemplate])
async def get_sow_scope_templates(
    category_code: Optional[str] = None,
    include_inactive: bool = False,
    include_custom: bool = True
):
    """Get all SOW scope templates, optionally filtered by category"""
    query = {}
    if not include_inactive:
        query["is_active"] = True
    if category_code:
        query["category_code"] = category_code
    if not include_custom:
        query["is_custom"] = False
    
    scopes = await get_db().sow_scope_templates.find(query, {"_id": 0}).sort("name", 1).to_list(500)
    
    for scope in scopes:
        if isinstance(scope.get('created_at'), str):
            scope['created_at'] = datetime.fromisoformat(scope['created_at'])
        if isinstance(scope.get('updated_at'), str):
            scope['updated_at'] = datetime.fromisoformat(scope['updated_at'])
    
    return scopes


@router.get("/scopes/grouped")
async def get_sow_scopes_grouped(include_inactive: bool = False):
    """Get all scopes grouped by category for checkbox selection UI"""
    # Get active categories
    cat_query = {} if include_inactive else {"is_active": True}
    categories = await get_db().sow_categories.find(cat_query, {"_id": 0}).sort("order", 1).to_list(100)
    
    # Get scopes
    scope_query = {} if include_inactive else {"is_active": True}
    scopes = await get_db().sow_scope_templates.find(scope_query, {"_id": 0}).sort("name", 1).to_list(500)
    
    # Group scopes by category
    result = []
    for cat in categories:
        cat_scopes = [s for s in scopes if s.get('category_code') == cat.get('code')]
        result.append({
            "category": {
                "id": cat.get('id'),
                "name": cat.get('name'),
                "code": cat.get('code'),
                "color": cat.get('color'),
                "description": cat.get('description')
            },
            "scopes": cat_scopes
        })
    
    return result


@router.post("/scopes", response_model=SOWScopeTemplate)
async def create_sow_scope_template(scope: SOWScopeTemplateCreate, current_user_id: str = None):
    """Create a new SOW scope template"""
    # Validate category exists
    category = await get_db().sow_categories.find_one({"id": scope.category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    new_scope = SOWScopeTemplate(
        **scope.model_dump(),
        category_code=category['code'],
        created_by=current_user_id
    )
    
    doc = new_scope.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await get_db().sow_scope_templates.insert_one(doc)
    return new_scope


@router.put("/scopes/{scope_id}", response_model=SOWScopeTemplate)
async def update_sow_scope_template(scope_id: str, update: SOWScopeTemplateUpdate):
    """Update SOW scope template"""
    existing = await get_db().sow_scope_templates.find_one({"id": scope_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Scope template not found")
    
    update_data = update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await get_db().sow_scope_templates.update_one({"id": scope_id}, {"$set": update_data})
    
    updated = await get_db().sow_scope_templates.find_one({"id": scope_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    
    return SOWScopeTemplate(**updated)


@router.delete("/scopes/{scope_id}")
async def delete_sow_scope_template(scope_id: str):
    """Soft delete SOW scope template"""
    existing = await get_db().sow_scope_templates.find_one({"id": scope_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Scope template not found")
    
    await get_db().sow_scope_templates.update_one(
        {"id": scope_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Scope template deactivated successfully"}


# ============== Seed Default Data ==============

@router.post("/seed-defaults")
async def seed_sow_masters():
    """Seed default SOW categories and scope templates"""
    results = {"categories": 0, "scopes": 0}
    
    # Seed categories
    for cat_data in DEFAULT_SOW_CATEGORIES:
        existing = await get_db().sow_categories.find_one({"code": cat_data["code"]})
        if not existing:
            category = SOWCategory(**cat_data)
            doc = category.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await get_db().sow_categories.insert_one(doc)
            results["categories"] += 1
    
    # Get category mapping for scopes
    categories = await get_db().sow_categories.find({}, {"_id": 0}).to_list(100)
    cat_map = {c['code']: c['id'] for c in categories}
    
    # Seed scope templates
    for scope_data in DEFAULT_SCOPE_TEMPLATES:
        category_code = scope_data["category_code"]
        if category_code not in cat_map:
            continue
        
        existing = await get_db().sow_scope_templates.find_one({
            "category_code": category_code,
            "name": scope_data["name"]
        })
        if not existing:
            scope = SOWScopeTemplate(
                category_id=cat_map[category_code],
                category_code=category_code,
                name=scope_data["name"],
                description=scope_data.get("description"),
                default_timeline_weeks=scope_data.get("default_timeline_weeks")
            )
            doc = scope.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await get_db().sow_scope_templates.insert_one(doc)
            results["scopes"] += 1
    
    return {"message": "SOW masters seeded successfully", "created": results}
