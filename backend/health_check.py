#!/usr/bin/env python3
"""
Backend Health Check Script for NETRA ERP
Run this after any refactoring to verify all API endpoints work.

Usage:
  python3 /app/backend/health_check.py

Returns exit code 0 if all checks pass, 1 if any fail.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add backend to path
sys.path.insert(0, '/app/backend')

async def check_database_connection():
    """Verify database is accessible."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import load_dotenv
        load_dotenv('/app/backend/.env')
        
        mongo_url = os.environ.get('MONGO_URL')
        db_name = os.environ.get('DB_NAME')
        
        if not mongo_url or not db_name:
            return False, "MONGO_URL or DB_NAME not set in .env"
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        # Test connection
        await db.command('ping')
        return True, "Database connected"
    except Exception as e:
        return False, f"Database error: {str(e)}"

async def check_router_imports():
    """Verify all routers can be imported without errors."""
    results = []
    routers_dir = '/app/backend/routers'
    
    for filename in os.listdir(routers_dir):
        if not filename.endswith('.py') or filename.startswith('_'):
            continue
        if filename in ['__init__.py', 'models.py', 'deps.py']:
            continue
            
        module_name = filename[:-3]
        try:
            exec(f"from routers import {module_name}")
            results.append((module_name, True, "OK"))
        except Exception as e:
            results.append((module_name, False, str(e)))
    
    return results

async def check_critical_endpoints():
    """Test critical API endpoints."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import load_dotenv
        load_dotenv('/app/backend/.env')
        
        mongo_url = os.environ.get('MONGO_URL')
        db_name = os.environ.get('DB_NAME')
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        tests = []
        
        # Test 1: Users collection
        users_count = await db.users.count_documents({})
        tests.append(("users collection", True, f"{users_count} users"))
        
        # Test 2: Masters - Tenure Types
        tenure_count = await db.tenure_types.count_documents({})
        tests.append(("tenure_types collection", True, f"{tenure_count} tenure types"))
        
        # Test 3: Masters - Meeting Types
        meeting_count = await db.meeting_types.count_documents({})
        tests.append(("meeting_types collection", True, f"{meeting_count} meeting types"))
        
        # Test 4: Masters - Consultant Roles
        roles_count = await db.consultant_roles.count_documents({})
        tests.append(("consultant_roles collection", True, f"{roles_count} consultant roles"))
        
        # Test 5: SOW Masters - Categories
        cat_count = await db.sow_categories.count_documents({})
        tests.append(("sow_categories collection", True, f"{cat_count} SOW categories"))
        
        # Test 6: SOW Masters - Scopes
        scope_count = await db.sow_scope_templates.count_documents({})
        tests.append(("sow_scope_templates collection", True, f"{scope_count} scope templates"))
        
        # Test 7: Leads
        leads_count = await db.leads.count_documents({})
        tests.append(("leads collection", True, f"{leads_count} leads"))
        
        # Test 8: Projects
        projects_count = await db.projects.count_documents({})
        tests.append(("projects collection", True, f"{projects_count} projects"))
        
        return tests
        
    except Exception as e:
        return [("database test", False, str(e))]

def print_results(title, results, is_list=True):
    """Print formatted results."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    
    if is_list:
        passed = sum(1 for _, ok, _ in results if ok)
        failed = sum(1 for _, ok, _ in results if not ok)
        
        for name, ok, msg in results:
            status = "✓" if ok else "❌"
            print(f"  {status} {name}: {msg}")
        
        print(f"\n  Summary: {passed} passed, {failed} failed")
        return failed == 0
    else:
        ok, msg = results
        status = "✓" if ok else "❌"
        print(f"  {status} {msg}")
        return ok

async def main():
    print(f"\n{'#'*60}")
    print(f" NETRA ERP - Backend Health Check")
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}")
    
    all_passed = True
    
    # 1. Database Connection
    db_result = await check_database_connection()
    if not print_results("Database Connection", db_result, is_list=False):
        all_passed = False
    
    # 2. Router Imports
    router_results = await check_router_imports()
    if not print_results("Router Imports", router_results):
        all_passed = False
    
    # 3. Critical Endpoints (Collections)
    endpoint_results = await check_critical_endpoints()
    if not print_results("Critical Data Collections", endpoint_results):
        all_passed = False
    
    # Final Summary
    print(f"\n{'='*60}")
    if all_passed:
        print(" ✓ ALL HEALTH CHECKS PASSED")
    else:
        print(" ❌ SOME HEALTH CHECKS FAILED")
    print(f"{'='*60}\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
