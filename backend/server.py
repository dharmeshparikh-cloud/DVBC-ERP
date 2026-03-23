"""
NETRA ERP - Clean Server Entry Point
=====================================
This file contains ONLY:
- App initialization
- Middleware setup
- Router inclusion
- Startup/shutdown events
- Exception handlers

All endpoints are defined in their respective routers under /routers/
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database configuration
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

# Initialize FastAPI app
app = FastAPI(
    title="NETRA - Business Management ERP",
    description="Comprehensive ERP system for DVBC Consulting",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Database client (initialized on startup)
client = None
db = None


# ==================== STARTUP/SHUTDOWN EVENTS ====================

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection and set up routers."""
    global client, db
    
    logger.info("Starting NETRA ERP...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Set database reference for all routers
    from routers import deps as router_deps
    router_deps.set_db(db)
    
    # Initialize RBAC system
    logger.info("Initializing RBAC system...")
    try:
        from routers.rbac_service import rbac
        from routers.rbac_migration import initialize_rbac_migration
        
        # Set database for RBAC service
        rbac.set_db(db)
        
        # Initialize RBAC (seeds defaults if needed, runs consistency checks)
        await rbac.initialize()
        
        # Run migration framework initialization
        consistency_report = await initialize_rbac_migration(db)
        logger.info(f"RBAC initialized: {consistency_report['status']}")
        
        if consistency_report['issues_found'] > 0:
            logger.warning(f"RBAC has {consistency_report['issues_found']} consistency issues")
            
    except Exception as e:
        logger.error(f"RBAC initialization error: {e}")
        # Don't fail startup - RBAC will use defaults with logging
    
    # Initialize database indexes for performance
    logger.info("Ensuring database indexes...")
    try:
        from routers.db_indexes import ensure_indexes
        index_stats = await ensure_indexes(db)
        logger.info(f"Database indexes: {index_stats['created']} ensured, {len(index_stats['errors'])} errors")
    except Exception as e:
        logger.error(f"Index initialization error: {e}")
    
    # Initialize Redis cache (optional - falls back to in-memory)
    logger.info("Initializing Redis cache...")
    try:
        from services.redis_cache import redis_cache
        redis_connected = await redis_cache.connect()
        if redis_connected:
            logger.info("Redis cache connected")
        else:
            logger.info("Redis not available - using in-memory cache")
    except Exception as e:
        logger.warning(f"Redis initialization error: {e} - using in-memory cache")
    
    # Start WebSocket ping task
    try:
        from routers.websocket_router import start_ping_task
        start_ping_task()
        logger.info("WebSocket manager initialized")
    except Exception as e:
        logger.warning(f"WebSocket ping task error: {e}")
    
    # Initialize and start the Integrity Audit Scheduler
    try:
        from services.integrity_scheduler import get_integrity_scheduler
        scheduler = get_integrity_scheduler(db)
        await scheduler.start()
        logger.info("Integrity audit scheduler started (daily at 02:00 UTC)")
    except Exception as e:
        logger.warning(f"Integrity scheduler initialization error: {e}")

    # Initialize and start the Meeting Auto-Accept Scheduler
    try:
        from services.meeting_auto_accept_scheduler import start_meeting_auto_accept_scheduler
        auto_accept_scheduler = await start_meeting_auto_accept_scheduler(db)
        logger.info("Meeting auto-accept scheduler started (hourly)")
    except Exception as e:
        logger.warning(f"Meeting auto-accept scheduler initialization error: {e}")

    # Initialize CEO Daily Report Scheduler (23:59 IST = Asia/Kolkata)
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz
        from services.ceo_report import CEOReportGenerator

        ceo_scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        ceo_report = CEOReportGenerator(db)

        ceo_scheduler.add_job(
            ceo_report.send_report,
            CronTrigger(hour=23, minute=59, timezone=pytz.timezone('Asia/Kolkata')),
            id='ceo_daily_report',
            name='CEO Daily Intelligence Report (23:59 IST)',
            replace_existing=True,
        )
        ceo_scheduler.start()

        # Store reference for manual trigger
        app.state.ceo_report = ceo_report

        next_run = ceo_scheduler.get_job('ceo_daily_report').next_run_time
        logger.info(f"CEO Daily Report scheduler started — next run: {next_run}")
    except Exception as e:
        logger.warning(f"CEO Report scheduler initialization error: {e}")
    
    logger.info(f"Connected to MongoDB: {db_name}")
    logger.info("NETRA ERP started successfully")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection and cleanup."""
    global client
    
    # Stop integrity scheduler
    try:
        from services.integrity_scheduler import get_integrity_scheduler
        scheduler = get_integrity_scheduler()
        if scheduler:
            await scheduler.stop()
    except Exception as e:
        logger.warning(f"Integrity scheduler stop error: {e}")
    
    # Stop meeting auto-accept scheduler
    try:
        from services.meeting_auto_accept_scheduler import stop_meeting_auto_accept_scheduler
        await stop_meeting_auto_accept_scheduler()
    except Exception as e:
        logger.warning(f"Meeting auto-accept scheduler stop error: {e}")
    
    # Close Redis connection
    try:
        from services.redis_cache import redis_cache
        await redis_cache.disconnect()
    except Exception as e:
        logger.warning(f"Redis disconnect error: {e}")
    
    if client:
        client.close()
        logger.info("Database connection closed")


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "NETRA ERP"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint."""
    return {"status": "healthy", "service": "NETRA ERP API", "version": "2.0.0"}


@app.get("/api/system-status")
async def system_status():
    """
    Real-time system status check for dashboard.
    Checks: Database connectivity, API responsiveness, core collections.
    """
    from datetime import datetime, timezone
    status = {
        "overall": "operational",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    try:
        # Check database connectivity
        await db.command("ping")
        status["checks"]["database"] = "operational"
    except Exception as e:
        status["checks"]["database"] = "degraded"
        status["overall"] = "degraded"
    
    try:
        # Check core collections exist
        collections = await db.list_collection_names()
        core_collections = ["users", "employees", "rbac_roles"]
        missing = [c for c in core_collections if c not in collections]
        if missing:
            status["checks"]["collections"] = "degraded"
            status["overall"] = "degraded"
        else:
            status["checks"]["collections"] = "operational"
    except Exception:
        status["checks"]["collections"] = "error"
        status["overall"] = "degraded"
    
    status["checks"]["api"] = "operational"
    
    return status

from routers.deps import get_current_user_from_token
from fastapi import Depends as _Dep, HTTPException as _HTTPExc
from fastapi.responses import HTMLResponse as _HTMLResponse


@app.post("/api/ceo-report/trigger")
async def trigger_ceo_report(current_user=_Dep(get_current_user_from_token)):
    """Manually trigger the CEO Daily Report. Admin only."""
    if current_user.role != "admin":
        raise _HTTPExc(status_code=403, detail="Admin only")
    try:
        ceo_report = app.state.ceo_report
        result = await ceo_report.send_report()
        return {"status": result.get("delivery_status"), "message": "CEO Report triggered", "details": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ceo-report/preview")
async def preview_ceo_report(current_user=_Dep(get_current_user_from_token)):
    """Preview the CEO report without sending email. Admin only."""
    if current_user.role != "admin":
        raise _HTTPExc(status_code=403, detail="Admin only")
    try:
        ceo_report = app.state.ceo_report
        report_data = await ceo_report.generate_report()
        html = ceo_report._render_html(report_data)
        return _HTMLResponse(content=html)
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/ceo-report/logs")
async def get_ceo_report_logs(current_user=_Dep(get_current_user_from_token)):
    """Get CEO report email delivery logs. Admin only."""
    if current_user.role != "admin":
        raise _HTTPExc(status_code=403, detail="Admin only")
    logs = await db.system_email_logs.find(
        {"email_type": "ceo_daily_report"},
        {"_id": 0}
    ).sort("date", -1).to_list(30)
    for log in logs:
        if hasattr(log.get("date"), "isoformat"):
            log["date"] = log["date"].isoformat()
    return {"logs": logs}

@app.get("/api/ceo-report/config")
async def get_ceo_report_config(current_user=_Dep(get_current_user_from_token)):
    """Get CEO report configuration. Admin only."""
    if current_user.role != "admin":
        raise _HTTPExc(status_code=403, detail="Admin only")
    config = await db.system_settings.find_one({"key": "ceo_report_config"}, {"_id": 0})
    import os
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_configured = bool(smtp_user and os.environ.get("SMTP_PASSWORD", ""))
    default = {
        "recipient": app.state.ceo_report.recipient if hasattr(app.state, "ceo_report") else "dharmesh.parikh@dvconsulting.co.in",
        "schedule_time": "23:59",
        "timezone": "Asia/Kolkata",
        "enabled": True,
        "smtp_status": "configured" if smtp_configured else "not_configured",
        "smtp_user": smtp_user,
    }
    if config:
        default.update({k: v for k, v in config.items() if k != "key"})
    return default

@app.put("/api/ceo-report/config")
async def update_ceo_report_config(request: Request, current_user=_Dep(get_current_user_from_token)):
    """Update CEO report config (recipient, enabled). Admin only."""
    if current_user.role != "admin":
        raise _HTTPExc(status_code=403, detail="Admin only")
    body = await request.json()
    allowed = {"recipient", "enabled"}
    updates = {k: v for k, v in body.items() if k in allowed}
    if "recipient" in updates:
        app.state.ceo_report.recipient = updates["recipient"]
    await db.system_settings.update_one(
        {"key": "ceo_report_config"},
        {"$set": {**updates, "key": "ceo_report_config"}},
        upsert=True
    )
    return {"status": "ok", "updated": updates}

@app.get("/api/ceo-report/data")
async def get_ceo_report_data(current_user=_Dep(get_current_user_from_token)):
    """Get raw CEO report data (JSON) for dashboard display. Admin only."""
    if current_user.role != "admin":
        raise _HTTPExc(status_code=403, detail="Admin only")
    try:
        ceo_report = app.state.ceo_report
        report_data = await ceo_report.generate_report()
        return report_data
    except Exception as e:
        return {"status": "error", "message": str(e)}



# ==================== ROUTER IMPORTS AND INCLUSION ====================

from fastapi import APIRouter, Depends
api_router = APIRouter(prefix="/api")

# Import get_current_user for alias endpoints
from routers.auth import get_current_user

# Core routers
from routers import auth as auth_router
from routers import users as users_router
from routers import leads as leads_router
from routers import projects as projects_router
from routers import meetings as meetings_router
from routers import meeting_workflow as meeting_workflow_router

# HR Module routers
from routers import employees as employees_router
from routers import attendance as attendance_router
from routers import hr as hr_router
from routers import ctc as ctc_router
from routers import letters as letters_router
from routers import expenses as expenses_router

# Sales Module routers
from routers import sales as sales_router
from routers import enhanced_sow as enhanced_sow_router
from routers import sow_masters as sow_masters_router
from routers import masters as masters_router
from routers import kickoff as kickoff_router

# Finance Module routers
from routers import payments as payments_router
from routers import project_payments as project_payments_router
from routers import payroll as payroll_router

# Analytics & Reports routers
from routers import analytics as analytics_router
from routers import stats as stats_router
from routers import project_pnl as project_pnl_router

# Administration routers
from routers import role_management as role_management_router
from routers import permission_config as permission_config_router
from routers import department_access as department_access_router
from routers import security as security_router
from routers import rbac_router

# Communication routers
from routers import chat as chat_router
from routers import ai_assistant as ai_assistant_router
from routers import email_actions as email_actions_router
from routers import documentation as documentation_router
from routers import audio_samples as audio_samples_router

# New modular routers (Phase 2)
from routers import travel as travel_router
from routers import sow_legacy as sow_legacy_router
from routers import agreements as agreements_router
from routers import tasks as tasks_router
from routers import notifications as notifications_router
from routers import approvals as approvals_router
from routers import quotations as quotations_router
from routers import consultants as consultants_router
from routers import reports as reports_router
from routers import settings as settings_router
from routers import roles as roles_router
from routers import my as my_router
from routers import leave_requests as leave_requests_router

# Leave Policies (new - comprehensive leave management)
from routers import leave_policies as leave_policies_router

# Project Completion (new)
from routers import project_completion as project_completion_router

# Pricing Plans (new)
from routers import pricing_plans as pricing_plans_router

# Stage Guard (new - guided workflow)
from routers import stage_guard as stage_guard_router

# Drafts (new - auto-save functionality)
from routers import drafts as drafts_router

# Enhanced Permission System (new)
from routers import permissions as permissions_router

# Consolidated My Router (new)
from routers import my_consolidated as my_consolidated_router

# Manager Router (new - team data)
from routers import manager as manager_router

# Sales Funnel Business Logic (new - stage resume, dual approval, consent)
from routers import sales_funnel_logic as sales_funnel_logic_router

# Expanded Audit Logging (new)
from routers import audit_logging as audit_logging_router

# Test Email Preview (new)
from routers import test_email_preview as test_email_preview_router

# Client Portal Authentication
from routers import client_auth as client_auth_router

# Self-Service Candidate Onboarding
from routers import onboarding as onboarding_router

# Help Content Management
from routers import help as help_router

# Employee Governance & Consent (new - audit trail, field-level RBAC, consent workflow)
from routers import employee_governance as employee_governance_router
from routers import employee_consent as employee_consent_router

# Data Integrity (P1 architectural fixes - client lookup, team consolidation, CTC versioning)
from routers import data_integrity as data_integrity_router

# Client Master (read-only for Sales/Consulting, auto-created from kickoff)
from routers import clients as clients_router

# Meeting Schedules (Recurring meetings, Calendar, Conflict detection)
from routers import meeting_schedules as meeting_schedules_router

# Excel Upload (Bulk Import - employees, attendance, leave, salary)
from routers import excel_upload as excel_upload_router

# ==================== INCLUDE ALL ROUTERS ====================

# Core
api_router.include_router(auth_router.router)
api_router.include_router(client_auth_router.router)  # Client Portal Auth
api_router.include_router(users_router.router)
api_router.include_router(leads_router.router)
api_router.include_router(projects_router.router)
api_router.include_router(meetings_router.router)

# Meeting Workflow (Notifications, Client Response, State Machine)
api_router.include_router(meeting_workflow_router.router)

# Meeting Schedules (Recurring, Calendar)
api_router.include_router(meeting_schedules_router.router)

# Consulting Meetings Tracking Endpoint
@api_router.get("/consulting-meetings/tracking")
async def get_consulting_tracking(current_user = Depends(get_current_user)):
    """Get committed vs actual meetings per project for consulting meetings"""
    projects = await db.projects.find({}, {"_id": 0}).to_list(1000)
    tracking = []
    for project in projects:
        committed = project.get('total_meetings_committed', 0)
        delivered = project.get('total_meetings_delivered', 0)
        # Count consulting meetings for this project
        actual_count = await db.meetings.count_documents({
            "project_id": project['id'],
            "type": "consulting"
        })
        tracking.append({
            "project_id": project['id'],
            "project_name": project.get('name', ''),
            "client_name": project.get('client_name', ''),
            "committed": committed,
            "delivered": delivered,
            "actual_meetings": actual_count,
            "status": project.get('status', 'active'),
            "variance": actual_count - committed if committed > 0 else 0,
            "completion_pct": round((actual_count / committed * 100), 1) if committed > 0 else 0
        })
    return tracking

# HR Module
api_router.include_router(employees_router.router)
api_router.include_router(attendance_router.router)
api_router.include_router(hr_router.router)
api_router.include_router(ctc_router.router)
api_router.include_router(letters_router.router)
api_router.include_router(expenses_router.router)

# Self-Service Candidate Onboarding
api_router.include_router(onboarding_router.router)

# Help Content Management
api_router.include_router(help_router.router)

# Go-Live Approval Workflow
from routers import go_live as go_live_router
api_router.include_router(go_live_router.router)

# Bank verification alias (for frontend compatibility)
@api_router.post("/bank-verify/{employee_id}")
async def bank_verify_alias(employee_id: str, current_user = Depends(get_current_user)):
    """Alias for /go-live/bank-verify/{employee_id}"""
    return await go_live_router.verify_bank_details(employee_id, current_user)

# Sales Module
api_router.include_router(sales_router.router)
api_router.include_router(enhanced_sow_router.router)
api_router.include_router(sow_masters_router.router)
api_router.include_router(masters_router.router)
api_router.include_router(kickoff_router.router)
api_router.include_router(pricing_plans_router.router)
api_router.include_router(stage_guard_router.router)

# Finance Module
api_router.include_router(payments_router.router)
api_router.include_router(project_payments_router.router)
api_router.include_router(payroll_router.router)

# Analytics & Reports
api_router.include_router(analytics_router.router)
api_router.include_router(stats_router.router)
api_router.include_router(project_pnl_router.router)

# Administration
api_router.include_router(role_management_router.router)
api_router.include_router(permission_config_router.router)
api_router.include_router(department_access_router.router)
api_router.include_router(security_router.router)
api_router.include_router(rbac_router.router)  # New RBAC Admin API

# Communication
api_router.include_router(chat_router.router)
api_router.include_router(ai_assistant_router.router)
api_router.include_router(email_actions_router.router)
api_router.include_router(documentation_router.router)
api_router.include_router(audio_samples_router.router)

# New Phase 2 Routers
api_router.include_router(travel_router.router)
api_router.include_router(sow_legacy_router.router)
api_router.include_router(agreements_router.router)
api_router.include_router(tasks_router.router)
api_router.include_router(notifications_router.router)
api_router.include_router(approvals_router.router)
api_router.include_router(quotations_router.router)
api_router.include_router(consultants_router.router)
api_router.include_router(reports_router.router)
api_router.include_router(settings_router.router)
api_router.include_router(roles_router.router)
api_router.include_router(my_router.router)
api_router.include_router(leave_requests_router.router)

# Exit Organisation / Resignation
from routers import exit_organisation as exit_organisation_router
api_router.include_router(exit_organisation_router.router)

# Leave Policies
api_router.include_router(leave_policies_router.router)

# Project Completion
api_router.include_router(project_completion_router.router)

# Drafts
api_router.include_router(drafts_router.router)

# Enhanced Permission System
api_router.include_router(permissions_router.router)

# Consolidated My Router (aggregates all /my/* endpoints)
api_router.include_router(my_consolidated_router.router)

# Manager Router (team data for managers)
api_router.include_router(manager_router.router)

# Sales Funnel Business Logic (stage resume, dual approval, client consent)
api_router.include_router(sales_funnel_logic_router.router)

# Expanded Audit Logging
api_router.include_router(audit_logging_router.router)

# Test Email Preview
api_router.include_router(test_email_preview_router.router)

# Employee Governance & Consent
api_router.include_router(employee_governance_router.router)
api_router.include_router(employee_consent_router.router)

# Data Integrity (P1 architectural fixes)
api_router.include_router(data_integrity_router.router)

# Client Master (read-only for Sales/Consulting, auto-created from kickoff)
api_router.include_router(clients_router.router)

# Excel Upload (Bulk Import)
api_router.include_router(excel_upload_router.router)

# Upload endpoint alias for meeting attachments
from fastapi import UploadFile, File
from typing import List as TypeList
import os
import uuid
from datetime import datetime, timezone as tz

MOM_UPLOAD_DIR = "/app/uploads/mom_documents"
os.makedirs(MOM_UPLOAD_DIR, exist_ok=True)

@api_router.post("/upload/meeting-attachments")
async def upload_meeting_attachments_alias(
    files: TypeList[UploadFile] = File(...)
):
    """Generic endpoint for uploading meeting attachments (MOM documents)."""
    uploaded_files = []
    ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "application/pdf",
                     "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     "text/plain", "text/csv"]
    
    for file in files:
        content_type = file.content_type
        if content_type not in ALLOWED_TYPES:
            continue
        
        content = await file.read()
        if len(content) > 20 * 1024 * 1024:  # 20MB limit
            continue
        
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        file_id = str(uuid.uuid4())
        filename = f"mom_{file_id}.{file_ext}"
        filepath = os.path.join(MOM_UPLOAD_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        uploaded_files.append({
            "id": file_id,
            "filename": file.filename,
            "name": file.filename,
            "path": f"/uploads/mom_documents/{filename}",
            "url": f"/api/meetings/documents/{file_id}/download",
            "content_type": content_type,
            "size": len(content)
        })
    
    return {"files": uploaded_files, "count": len(uploaded_files)}

from routers import follow_ups as follow_ups_router
api_router.include_router(follow_ups_router.router)

# WebSocket for real-time updates (under /api prefix for proper routing through ingress)
from routers import websocket_router
api_router.include_router(websocket_router.router)

# Include all API routes under /api prefix
app.include_router(api_router)

# ==================== ROOT ENDPOINT ====================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "NETRA ERP",
        "version": "2.0.0",
        "status": "running",
        "docs": "/api/docs"
    }
