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
    
    logger.info(f"Connected to MongoDB: {db_name}")
    logger.info("NETRA ERP started successfully")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection."""
    global client
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


# ==================== ROUTER IMPORTS AND INCLUSION ====================

from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# Core routers
from routers import auth as auth_router
from routers import users as users_router
from routers import leads as leads_router
from routers import projects as projects_router
from routers import meetings as meetings_router

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
from routers import timesheets as timesheets_router
from routers import consultants as consultants_router
from routers import reports as reports_router
from routers import settings as settings_router
from routers import roles as roles_router
from routers import my as my_router
from routers import leave_requests as leave_requests_router

# Project Completion (new)
from routers import project_completion as project_completion_router

# Pricing Plans (new)
from routers import pricing_plans as pricing_plans_router

# ==================== INCLUDE ALL ROUTERS ====================

# Core
api_router.include_router(auth_router.router)
api_router.include_router(users_router.router)
api_router.include_router(leads_router.router)
api_router.include_router(projects_router.router)
api_router.include_router(meetings_router.router)

# HR Module
api_router.include_router(employees_router.router)
api_router.include_router(attendance_router.router)
api_router.include_router(hr_router.router)
api_router.include_router(ctc_router.router)
api_router.include_router(letters_router.router)
api_router.include_router(expenses_router.router)

# Sales Module
api_router.include_router(sales_router.router)
api_router.include_router(enhanced_sow_router.router)
api_router.include_router(sow_masters_router.router)
api_router.include_router(masters_router.router)
api_router.include_router(kickoff_router.router)

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
api_router.include_router(timesheets_router.router)
api_router.include_router(consultants_router.router)
api_router.include_router(reports_router.router)
api_router.include_router(settings_router.router)
api_router.include_router(roles_router.router)
api_router.include_router(my_router.router)
api_router.include_router(leave_requests_router.router)

# Project Completion
api_router.include_router(project_completion_router.router)

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
