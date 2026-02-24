"""
Help Content Management System - Backend Router
Provides APIs for help content, context-aware guidance, and feature onboarding.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel
from bson import ObjectId
import re

router = APIRouter(prefix="/help", tags=["Help Center"])

# ============== MODELS ==============

class HelpStep(BaseModel):
    title: str
    description: str
    imageUrl: Optional[str] = None
    tip: Optional[str] = None

class TroubleshootItem(BaseModel):
    problem: str
    solution: str

class RelatedTopic(BaseModel):
    id: str
    title: str

class HelpTopic(BaseModel):
    title: str
    slug: str
    type: str  # guide, troubleshoot, video, faq, whatsnew
    category: str
    routes: List[str] = []  # Routes where this topic is contextually relevant
    roles: List[str] = []  # Empty means all roles can see
    introduction: Optional[str] = None
    steps: Optional[List[HelpStep]] = []
    troubleshooting: Optional[List[TroubleshootItem]] = []
    videoUrl: Optional[str] = None
    notes: Optional[str] = None
    relatedTopicIds: List[str] = []
    keywords: List[str] = []
    featureVersion: Optional[str] = None  # e.g., "2.5.0" for version tagging
    isNew: bool = False
    newUntil: Optional[datetime] = None
    requiresOnboarding: bool = False  # Show guided tour for first-time users
    onboardingSteps: Optional[List[dict]] = []
    priority: int = 0  # Higher = shown first
    isActive: bool = True

class HelpCategory(BaseModel):
    name: str
    slug: str
    icon: str
    description: Optional[str] = None
    order: int = 0
    roles: List[str] = []  # Role-based visibility

class UserFeatureProgress(BaseModel):
    userId: str
    featureId: str
    completedOnboarding: bool = False
    firstAccessAt: datetime
    onboardingCompletedAt: Optional[datetime] = None
    viewCount: int = 0

# ============== DATABASE ACCESS ==============

from .deps import get_db

# ============== HELPER FUNCTIONS ==============

def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    doc['id'] = str(doc.pop('_id', ''))
    return doc

def check_role_access(topic_roles: List[str], user_role: str) -> bool:
    """Check if user role has access to topic."""
    if not topic_roles:  # Empty means all roles
        return True
    return user_role in topic_roles or user_role == 'admin'

# ============== PUBLIC ENDPOINTS ==============

@router.get("/context")
async def get_context_topics(
    route: str = Query(..., description="Current page route"),
    role: Optional[str] = Query(None, description="User role")
):
    """Get context-aware help topics for the current route."""
    db = get_db()
    
    # Build query for matching routes
    query = {
        "isActive": True,
        "$or": [
            {"routes": {"$regex": f"^{re.escape(route)}", "$options": "i"}},
            {"routes": route},
            {"routes": {"$regex": route.split('/')[1] if '/' in route else route, "$options": "i"}}
        ]
    }
    
    topics = await db.help_topics.find(query).sort("priority", -1).limit(10).to_list(10)
    
    # Filter by role
    filtered = []
    for topic in topics:
        if check_role_access(topic.get('roles', []), role):
            filtered.append({
                "id": str(topic['_id']),
                "title": topic['title'],
                "type": topic['type'],
                "excerpt": topic.get('introduction', '')[:100] + '...' if topic.get('introduction') else '',
                "isNew": topic.get('isNew', False) and (
                    not topic.get('newUntil') or topic['newUntil'] > datetime.now(timezone.utc)
                ),
                "requiresOnboarding": topic.get('requiresOnboarding', False)
            })
    
    return {"topics": filtered, "route": route}


@router.get("/categories")
async def get_categories(role: Optional[str] = Query(None)):
    """Get all help categories visible to user's role."""
    db = get_db()
    
    categories = await db.help_categories.find({"isActive": {"$ne": False}}).sort("order", 1).to_list(50)
    
    result = []
    for cat in categories:
        if check_role_access(cat.get('roles', []), role):
            # Count topics in category
            topic_count = await db.help_topics.count_documents({
                "category": cat['slug'],
                "isActive": True
            })
            result.append({
                "id": cat['slug'],
                "name": cat['name'],
                "icon": cat.get('icon', '📖'),
                "description": cat.get('description'),
                "topicCount": topic_count
            })
    
    return result


@router.get("/categories/{category_id}/topics")
async def get_category_topics(
    category_id: str,
    role: Optional[str] = Query(None)
):
    """Get all topics in a category."""
    db = get_db()
    
    query = {"isActive": True}
    
    if category_id == 'all':
        pass  # No category filter
    elif category_id == 'troubleshooting':
        query["type"] = "troubleshoot"
    elif category_id == 'videos':
        query["type"] = "video"
    else:
        query["category"] = category_id
    
    topics = await db.help_topics.find(query).sort("priority", -1).to_list(100)
    
    result = []
    for topic in topics:
        if check_role_access(topic.get('roles', []), role):
            result.append({
                "id": str(topic['_id']),
                "title": topic['title'],
                "type": topic['type'],
                "category": topic['category'],
                "excerpt": topic.get('introduction', '')[:100] + '...' if topic.get('introduction') else '',
                "isNew": topic.get('isNew', False)
            })
    
    return result


@router.get("/search")
async def search_topics(
    q: str = Query(..., min_length=2),
    role: Optional[str] = Query(None)
):
    """Search help topics by keyword."""
    db = get_db()
    
    # Build text search query
    search_regex = {"$regex": q, "$options": "i"}
    
    query = {
        "isActive": True,
        "$or": [
            {"title": search_regex},
            {"introduction": search_regex},
            {"keywords": search_regex},
            {"steps.title": search_regex},
            {"steps.description": search_regex}
        ]
    }
    
    topics = await db.help_topics.find(query).limit(20).to_list(20)
    
    results = []
    for topic in topics:
        if check_role_access(topic.get('roles', []), role):
            results.append({
                "id": str(topic['_id']),
                "title": topic['title'],
                "category": topic['category'],
                "type": topic['type'],
                "excerpt": topic.get('introduction', '')[:150] + '...' if topic.get('introduction') else ''
            })
    
    return {"results": results, "query": q}


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: str, role: Optional[str] = Query(None)):
    """Get a single help topic by ID."""
    db = get_db()
    
    try:
        topic = await db.help_topics.find_one({"_id": ObjectId(topic_id)})
    except Exception:
        # Try by slug
        topic = await db.help_topics.find_one({"slug": topic_id})
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    if not check_role_access(topic.get('roles', []), role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get related topics
    related = []
    if topic.get('relatedTopicIds'):
        for rid in topic['relatedTopicIds'][:5]:
            try:
                rel = await db.help_topics.find_one({"_id": ObjectId(rid)}, {"title": 1})
                if rel:
                    related.append({"id": str(rel['_id']), "title": rel['title']})
            except Exception:
                pass
    
    return {
        "id": str(topic['_id']),
        "title": topic['title'],
        "type": topic['type'],
        "category": topic['category'],
        "introduction": topic.get('introduction'),
        "steps": topic.get('steps', []),
        "troubleshooting": topic.get('troubleshooting', []),
        "videoUrl": topic.get('videoUrl'),
        "notes": topic.get('notes'),
        "relatedTopics": related,
        "isNew": topic.get('isNew', False),
        "featureVersion": topic.get('featureVersion'),
        "requiresOnboarding": topic.get('requiresOnboarding', False),
        "onboardingSteps": topic.get('onboardingSteps', [])
    }


@router.post("/topics/{topic_id}/view")
async def track_topic_view(topic_id: str):
    """Track a topic view for analytics."""
    db = get_db()
    
    try:
        await db.help_topics.update_one(
            {"_id": ObjectId(topic_id)},
            {"$inc": {"viewCount": 1}, "$set": {"lastViewedAt": datetime.now(timezone.utc)}}
        )
    except Exception:
        pass
    
    return {"success": True}


@router.post("/topics/{topic_id}/feedback")
async def submit_feedback(topic_id: str, helpful: bool = Body(..., embed=True)):
    """Submit feedback for a help topic."""
    db = get_db()
    
    field = "helpfulCount" if helpful else "notHelpfulCount"
    try:
        await db.help_topics.update_one(
            {"_id": ObjectId(topic_id)},
            {"$inc": {field: 1}}
        )
    except Exception:
        pass
    
    return {"success": True}


# ============== WHAT'S NEW ==============

@router.get("/whats-new")
async def get_whats_new(
    role: Optional[str] = Query(None),
    limit: int = Query(10, le=50)
):
    """Get recently added features and updates."""
    db = get_db()
    
    query = {
        "isActive": True,
        "isNew": True,
        "$or": [
            {"newUntil": {"$gt": datetime.now(timezone.utc)}},
            {"newUntil": None}
        ]
    }
    
    topics = await db.help_topics.find(query).sort("createdAt", -1).limit(limit).to_list(limit)
    
    result = []
    for topic in topics:
        if check_role_access(topic.get('roles', []), role):
            result.append({
                "id": str(topic['_id']),
                "title": topic['title'],
                "type": topic['type'],
                "category": topic['category'],
                "introduction": topic.get('introduction', '')[:200],
                "featureVersion": topic.get('featureVersion'),
                "createdAt": topic.get('createdAt', datetime.now(timezone.utc)).isoformat()
            })
    
    return {"items": result, "total": len(result)}


# ============== ONBOARDING / FIRST-TIME USE ==============

@router.get("/onboarding/check/{feature_id}")
async def check_onboarding_status(
    feature_id: str,
    user_id: str = Query(...)
):
    """Check if user has completed onboarding for a feature."""
    db = get_db()
    
    progress = await db.help_user_progress.find_one({
        "userId": user_id,
        "featureId": feature_id
    })
    
    if not progress:
        # First time accessing this feature
        await db.help_user_progress.insert_one({
            "userId": user_id,
            "featureId": feature_id,
            "completedOnboarding": False,
            "firstAccessAt": datetime.now(timezone.utc),
            "viewCount": 1
        })
        return {"needsOnboarding": True, "firstTime": True}
    
    # Increment view count
    await db.help_user_progress.update_one(
        {"_id": progress['_id']},
        {"$inc": {"viewCount": 1}}
    )
    
    return {
        "needsOnboarding": not progress.get('completedOnboarding', False),
        "firstTime": False,
        "viewCount": progress.get('viewCount', 0) + 1
    }


@router.post("/onboarding/complete/{feature_id}")
async def complete_onboarding(
    feature_id: str,
    user_id: str = Body(..., embed=True)
):
    """Mark onboarding as complete for a feature."""
    db = get_db()
    
    await db.help_user_progress.update_one(
        {"userId": user_id, "featureId": feature_id},
        {
            "$set": {
                "completedOnboarding": True,
                "onboardingCompletedAt": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    
    return {"success": True}


@router.get("/onboarding/steps/{feature_id}")
async def get_onboarding_steps(feature_id: str, role: Optional[str] = Query(None)):
    """Get onboarding steps for a feature."""
    db = get_db()
    
    try:
        topic = await db.help_topics.find_one({
            "$or": [
                {"_id": ObjectId(feature_id)},
                {"slug": feature_id}
            ],
            "requiresOnboarding": True
        })
    except Exception:
        topic = await db.help_topics.find_one({
            "slug": feature_id,
            "requiresOnboarding": True
        })
    
    if not topic:
        return {"steps": [], "found": False}
    
    if not check_role_access(topic.get('roles', []), role):
        return {"steps": [], "found": False}
    
    return {
        "steps": topic.get('onboardingSteps', []),
        "title": topic['title'],
        "found": True
    }


# ============== ADMIN ENDPOINTS ==============

@router.get("/admin/topics")
async def admin_list_topics(
    category: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    isActive: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0)
):
    """Admin: List all help topics."""
    db = get_db()
    
    query = {}
    if category:
        query["category"] = category
    if type:
        query["type"] = type
    if isActive is not None:
        query["isActive"] = isActive
    
    total = await db.help_topics.count_documents(query)
    topics = await db.help_topics.find(query).skip(skip).limit(limit).sort("updatedAt", -1).to_list(limit)
    
    return {
        "topics": [serialize_doc(t) for t in topics],
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.post("/admin/topics")
async def admin_create_topic(topic: HelpTopic):
    """Admin: Create a new help topic."""
    db = get_db()
    
    doc = topic.dict()
    doc['createdAt'] = datetime.now(timezone.utc)
    doc['updatedAt'] = datetime.now(timezone.utc)
    doc['viewCount'] = 0
    doc['helpfulCount'] = 0
    doc['notHelpfulCount'] = 0
    
    result = await db.help_topics.insert_one(doc)
    
    return {"id": str(result.inserted_id), "message": "Topic created"}


@router.put("/admin/topics/{topic_id}")
async def admin_update_topic(topic_id: str, topic: HelpTopic):
    """Admin: Update an existing help topic."""
    db = get_db()
    
    doc = topic.dict()
    doc['updatedAt'] = datetime.now(timezone.utc)
    
    result = await db.help_topics.update_one(
        {"_id": ObjectId(topic_id)},
        {"$set": doc}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"message": "Topic updated"}


@router.delete("/admin/topics/{topic_id}")
async def admin_delete_topic(topic_id: str):
    """Admin: Delete a help topic (soft delete)."""
    db = get_db()
    
    result = await db.help_topics.update_one(
        {"_id": ObjectId(topic_id)},
        {"$set": {"isActive": False, "deletedAt": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    return {"message": "Topic deleted"}


@router.get("/admin/categories")
async def admin_list_categories():
    """Admin: List all categories."""
    db = get_db()
    categories = await db.help_categories.find().sort("order", 1).to_list(100)
    return [serialize_doc(c) for c in categories]


@router.post("/admin/categories")
async def admin_create_category(category: HelpCategory):
    """Admin: Create a new category."""
    db = get_db()
    
    doc = category.dict()
    doc['createdAt'] = datetime.now(timezone.utc)
    doc['isActive'] = True
    
    result = await db.help_categories.insert_one(doc)
    return {"id": str(result.inserted_id), "message": "Category created"}


@router.put("/admin/categories/{category_id}")
async def admin_update_category(category_id: str, category: HelpCategory):
    """Admin: Update a category."""
    db = get_db()
    
    result = await db.help_categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": category.dict()}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {"message": "Category updated"}


@router.get("/admin/analytics")
async def admin_get_analytics():
    """Admin: Get help center analytics."""
    db = get_db()
    
    total_topics = await db.help_topics.count_documents({"isActive": True})
    total_views = await db.help_topics.aggregate([
        {"$match": {"isActive": True}},
        {"$group": {"_id": None, "total": {"$sum": "$viewCount"}}}
    ]).to_list(1)
    
    # Top viewed topics
    top_viewed = await db.help_topics.find(
        {"isActive": True}
    ).sort("viewCount", -1).limit(10).to_list(10)
    
    # Most helpful topics
    most_helpful = await db.help_topics.find(
        {"isActive": True, "helpfulCount": {"$gt": 0}}
    ).sort("helpfulCount", -1).limit(10).to_list(10)
    
    # Least helpful (may need improvement)
    needs_improvement = await db.help_topics.find(
        {"isActive": True, "notHelpfulCount": {"$gt": 0}}
    ).sort("notHelpfulCount", -1).limit(10).to_list(10)
    
    return {
        "totalTopics": total_topics,
        "totalViews": total_views[0]['total'] if total_views else 0,
        "topViewed": [{"id": str(t['_id']), "title": t['title'], "views": t.get('viewCount', 0)} for t in top_viewed],
        "mostHelpful": [{"id": str(t['_id']), "title": t['title'], "helpful": t.get('helpfulCount', 0)} for t in most_helpful],
        "needsImprovement": [{"id": str(t['_id']), "title": t['title'], "notHelpful": t.get('notHelpfulCount', 0)} for t in needs_improvement]
    }


# ============== SEED DATA ENDPOINT ==============

@router.post("/admin/seed")
async def seed_help_content():
    """Admin: Seed initial help content."""
    db = get_db()
    
    # Check if already seeded
    existing = await db.help_categories.count_documents({})
    if existing > 0:
        return {"message": "Already seeded", "skipped": True}
    
    # Seed categories
    categories = [
        {"name": "Getting Started", "slug": "getting-started", "icon": "🚀", "order": 1, "description": "New to NETRA? Start here."},
        {"name": "Onboarding", "slug": "onboarding", "icon": "👋", "order": 2, "description": "Employee onboarding guides"},
        {"name": "Leave & Attendance", "slug": "leave-attendance", "icon": "📅", "order": 3, "description": "Managing leaves and attendance"},
        {"name": "Payroll & CTC", "slug": "payroll", "icon": "💰", "order": 4, "description": "Salary and compensation"},
        {"name": "Documents", "slug": "documents", "icon": "📄", "order": 5, "description": "Letters, policies, and forms"},
        {"name": "HR Administration", "slug": "hr-admin", "icon": "⚙️", "order": 6, "description": "HR tools and settings", "roles": ["hr_manager", "admin"]},
        {"name": "Troubleshooting", "slug": "troubleshooting", "icon": "🔧", "order": 7, "description": "Common issues and solutions"},
    ]
    
    for cat in categories:
        cat['createdAt'] = datetime.now(timezone.utc)
        cat['isActive'] = True
    
    await db.help_categories.insert_many(categories)
    
    # Seed sample topics
    topics = [
        {
            "title": "Welcome to NETRA ERP",
            "slug": "getting-started",
            "type": "guide",
            "category": "getting-started",
            "routes": ["/dashboard", "/"],
            "roles": [],
            "introduction": "NETRA is D&V Business Consulting's comprehensive ERP system. This guide will help you get started.",
            "steps": [
                {"title": "Access Your Dashboard", "description": "After logging in, you'll see your personalized dashboard with quick stats and pending tasks."},
                {"title": "Update Your Profile", "description": "Go to 'My Details' to ensure your personal information is up to date."},
                {"title": "Explore Modules", "description": "Use the sidebar to navigate different modules like Leave, Attendance, and Documents."},
                {"title": "Get Help Anytime", "description": "Click the orange help button (bottom-right) on any page for context-aware assistance."}
            ],
            "isNew": True,
            "newUntil": datetime(2026, 3, 31, tzinfo=timezone.utc),
            "priority": 100,
            "keywords": ["start", "begin", "new", "welcome", "first"]
        },
        {
            "title": "How to Send Onboarding Invite",
            "slug": "send-onboarding-invite",
            "type": "guide",
            "category": "onboarding",
            "routes": ["/onboarding-hub", "/onboarding"],
            "roles": ["hr_manager", "admin", "principal_consultant"],
            "introduction": "Learn how to invite new candidates to complete their onboarding form.",
            "steps": [
                {"title": "Navigate to Onboarding Hub", "description": "Go to HR → Onboarding Hub in the sidebar."},
                {"title": "Click 'Send Invite' Tab", "description": "Select the 'Send Invite' tab at the top."},
                {"title": "Enter Candidate Details", "description": "Fill in the candidate's name, email, and offered position."},
                {"title": "Send the Invite", "description": "Click 'Send Invite'. The candidate will receive an email with a secure link to complete their onboarding form."}
            ],
            "troubleshooting": [
                {"problem": "Candidate didn't receive email", "solution": "Check spam folder. If not there, resend the invite or verify the email address."},
                {"problem": "Link expired error", "solution": "Links expire after 24 hours. Send a new invite from the Onboarding Hub."}
            ],
            "isNew": True,
            "newUntil": datetime(2026, 3, 31, tzinfo=timezone.utc),
            "priority": 90,
            "requiresOnboarding": True,
            "onboardingSteps": [
                {"target": "[data-testid='send-invite-tab']", "title": "Send Invite Tab", "description": "Click here to send new onboarding invites"},
                {"target": "[data-testid='candidate-name-input']", "title": "Enter Details", "description": "Fill in the candidate's information"},
                {"target": "[data-testid='send-invite-btn']", "title": "Send Invite", "description": "Click to send the onboarding invite email"}
            ],
            "keywords": ["onboarding", "invite", "candidate", "new hire", "email"]
        },
        {
            "title": "Completing Onboarding as a Candidate",
            "slug": "candidate-onboarding-form",
            "type": "guide",
            "category": "onboarding",
            "routes": ["/onboarding/candidate"],
            "roles": [],
            "introduction": "Step-by-step guide to complete your onboarding form.",
            "steps": [
                {"title": "Access the Form", "description": "Click the link in your invitation email. No login required."},
                {"title": "Fill Personal Details", "description": "Enter your name, DOB, phone (10 digits), PAN, Aadhaar, and addresses."},
                {"title": "Add Education", "description": "Add at least one education qualification with degree, institution, year, and percentage."},
                {"title": "Add Work Experience", "description": "Add your previous work experience with company, role, dates, and reason for leaving."},
                {"title": "Enter Bank Details", "description": "Provide your bank account details for salary processing."},
                {"title": "Add References", "description": "Add one professional and one personal reference."},
                {"title": "Emergency Contact", "description": "Provide an emergency contact person's details."},
                {"title": "Upload Documents", "description": "Upload your PAN card and Aadhaar (required). Other documents are optional."},
                {"title": "Review & Submit", "description": "Review all information, check the declaration box, and submit."}
            ],
            "troubleshooting": [
                {"problem": "Can't proceed to next step", "solution": "Ensure all fields marked with * are filled correctly. Check for validation errors."},
                {"problem": "Invalid phone number error", "solution": "Enter 10 digits starting with 6, 7, 8, or 9."},
                {"problem": "Invalid PAN format", "solution": "PAN must be 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)."}
            ],
            "priority": 85,
            "keywords": ["form", "fill", "submit", "candidate", "join"]
        },
        {
            "title": "HR Review & Completing Onboarding",
            "slug": "hr-review-onboarding",
            "type": "guide",
            "category": "onboarding",
            "routes": ["/onboarding/review", "/onboarding-hub"],
            "roles": ["hr_manager", "admin"],
            "introduction": "How to review submissions and complete employee onboarding.",
            "steps": [
                {"title": "View Pending Submissions", "description": "In Onboarding Hub, click 'Pending' to see submissions awaiting review."},
                {"title": "Click 'Review'", "description": "Select a submission to review all candidate data."},
                {"title": "Verify Documents", "description": "Check uploaded documents and mark as verified."},
                {"title": "Verify Bank Details", "description": "Confirm bank account information is correct."},
                {"title": "Assign HR Details", "description": "Set department, reporting manager, joining date, and official email."},
                {"title": "Complete Onboarding", "description": "Once checklist is complete, click 'Complete Onboarding' to create employee record."}
            ],
            "notes": "The 'Complete Onboarding' button only enables when all checklist items are complete.",
            "priority": 80,
            "keywords": ["review", "approve", "complete", "verify", "hr"]
        },
        {
            "title": "Go-Live Process",
            "slug": "golive-process",
            "type": "guide",
            "category": "onboarding",
            "routes": ["/go-live"],
            "roles": ["hr_manager", "admin"],
            "introduction": "The final step to activate an employee in the system.",
            "steps": [
                {"title": "Access Go-Live Dashboard", "description": "Navigate to HR → Go-Live Dashboard."},
                {"title": "Review Checklist", "description": "Ensure all Go-Live checklist items are complete for the employee."},
                {"title": "Submit for Go-Live", "description": "Click 'Submit for Go-Live' when ready."},
                {"title": "Admin Approval", "description": "An admin will review and approve the Go-Live request."},
                {"title": "Employee Active", "description": "Once approved, the employee can log in and access all features."}
            ],
            "priority": 75,
            "keywords": ["golive", "activate", "approve", "final", "active"]
        },
        {
            "title": "Applying for Leave",
            "slug": "apply-leave",
            "type": "guide",
            "category": "leave-attendance",
            "routes": ["/leave", "/my-leaves"],
            "roles": [],
            "introduction": "How to apply for leave in NETRA.",
            "steps": [
                {"title": "Go to Leave Module", "description": "Click 'Leave & Attendance' → 'My Leaves' in sidebar."},
                {"title": "Click 'Apply Leave'", "description": "Click the 'Apply Leave' button."},
                {"title": "Select Leave Type", "description": "Choose Casual Leave, Sick Leave, etc."},
                {"title": "Select Dates", "description": "Pick start and end dates. Half-day option available."},
                {"title": "Add Reason", "description": "Provide a reason for your leave."},
                {"title": "Submit", "description": "Click 'Submit'. Your manager will be notified."}
            ],
            "priority": 70,
            "keywords": ["leave", "apply", "vacation", "off", "absent"]
        },
        {
            "title": "Cannot Login to System",
            "slug": "cannot-login",
            "type": "troubleshoot",
            "category": "troubleshooting",
            "routes": ["/login"],
            "roles": [],
            "introduction": "Troubleshooting login issues.",
            "troubleshooting": [
                {"problem": "Incorrect password", "solution": "Click 'Forgot Password' or contact HR to reset your password."},
                {"problem": "Employee ID not found", "solution": "Ensure you're using your correct Employee ID (e.g., DVC001). Contact HR if unsure."},
                {"problem": "Account locked", "solution": "After 5 failed attempts, accounts are locked for 30 minutes. Wait or contact admin."},
                {"problem": "Go-Live not completed", "solution": "New employees need Go-Live approval before they can log in. Check with HR."}
            ],
            "priority": 95,
            "keywords": ["login", "password", "access", "locked", "cant", "cannot"]
        }
    ]
    
    for topic in topics:
        topic['createdAt'] = datetime.now(timezone.utc)
        topic['updatedAt'] = datetime.now(timezone.utc)
        topic['viewCount'] = 0
        topic['helpfulCount'] = 0
        topic['notHelpfulCount'] = 0
        topic['isActive'] = True
    
    await db.help_topics.insert_many(topics)
    
    # Create text index for search
    try:
        await db.help_topics.create_index([
            ("title", "text"),
            ("introduction", "text"),
            ("keywords", "text")
        ])
    except Exception:
        pass
    
    return {"message": "Help content seeded successfully", "categories": len(categories), "topics": len(topics)}
