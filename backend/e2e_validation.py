#!/usr/bin/env python3
"""
NETRA ERP - Full E2E Validation Script
Runs comprehensive tests across all roles and returns stability score.

Usage: python3 /app/backend/e2e_validation.py
Required: Backend server must be running
"""

import asyncio
import aiohttp
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

# Configuration
API_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leads-fix-validation.preview.emergentagent.com')
if not API_URL.startswith('http'):
    API_URL = f"https://{API_URL}"

# Test Users
TEST_USERS = {
    'admin': {'email': 'admin@dvbc.com', 'password': 'admin123', 'expected_role': 'admin'},
    'sales_executive': {'email': 'sales@dvbc.com', 'password': 'sales123', 'expected_role': 'executive'},
}

# Role-based route access matrix
ROUTE_ACCESS = {
    'admin': [
        '/api/auth/me',
        '/api/stats/sales-dashboard-enhanced',
        '/api/masters/tenure-types',
        '/api/masters/consultant-roles',
        '/api/masters/meeting-types',
        '/api/sow-masters/categories',
        '/api/sow-masters/scopes',
        '/api/leads',
        '/api/projects',
        '/api/employees',
        '/api/drafts',
        '/api/approvals/pending',
    ],
    'sales_executive': [
        '/api/auth/me',
        '/api/leads',
        '/api/drafts',
        '/api/my/check-status',
    ],
}

# Expected unauthorized routes per role
UNAUTHORIZED_ROUTES = {
    'sales_executive': [
        '/api/employees',           # HR only - FIXED
        '/api/payroll/salary-components',  # HR only - FIXED
        '/api/users',               # Admin only
    ],
}

class ValidationResult:
    def __init__(self):
        self.total_points = 0
        self.max_points = 100
        self.results = []
        self.failures = []
    
    def add(self, category, test_name, passed, points, max_points, message=""):
        self.results.append({
            'category': category,
            'test': test_name,
            'passed': passed,
            'points': points if passed else 0,
            'max_points': max_points,
            'message': message
        })
        if passed:
            self.total_points += points
        else:
            self.failures.append(f"{category}/{test_name}: {message}")
    
    def score(self):
        return self.total_points
    
    def print_report(self):
        print(f"\n{'='*70}")
        print(f" NETRA ERP - E2E VALIDATION REPORT")
        print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        current_category = None
        for r in self.results:
            if r['category'] != current_category:
                current_category = r['category']
                print(f"\n[{current_category}]")
            
            status = "✓" if r['passed'] else "❌"
            points = f"{r['points']}/{r['max_points']}"
            print(f"  {status} {r['test']}: {points} {r['message']}")
        
        print(f"\n{'='*70}")
        print(f" STABILITY SCORE: {self.total_points}/{self.max_points}")
        print(f"{'='*70}")
        
        if self.failures:
            print(f"\n FAILURES ({len(self.failures)}):")
            for f in self.failures:
                print(f"  - {f}")
        
        status = "PASSED ✓" if self.total_points >= 95 else "FAILED ❌"
        print(f"\n OVERALL: {status}")
        print(f"{'='*70}\n")


async def get_token(session, user_key):
    """Get auth token for user."""
    user = TEST_USERS.get(user_key)
    if not user:
        return None, f"User {user_key} not configured"
    
    try:
        async with session.post(
            f"{API_URL}/api/auth/login",
            json={'email': user['email'], 'password': user['password']}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('access_token'), None
            else:
                text = await resp.text()
                return None, f"Login failed: {resp.status} - {text[:100]}"
    except Exception as e:
        return None, f"Login error: {str(e)}"


async def test_endpoint(session, token, endpoint, expected_status=200):
    """Test an API endpoint."""
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        async with session.get(f"{API_URL}{endpoint}", headers=headers) as resp:
            return resp.status, await resp.text()
    except Exception as e:
        return 0, str(e)


async def run_validation():
    result = ValidationResult()
    
    async with aiohttp.ClientSession() as session:
        
        # ==================== 1. DATABASE CONNECTIVITY (10 points) ====================
        try:
            async with session.get(f"{API_URL}/api/health") as resp:
                if resp.status == 200:
                    result.add("Database", "Health endpoint", True, 10, 10)
                else:
                    result.add("Database", "Health endpoint", False, 0, 10, f"Status: {resp.status}")
        except Exception as e:
            result.add("Database", "Health endpoint", False, 0, 10, str(e))
        
        # ==================== 2. AUTH SYSTEM (15 points) ====================
        tokens = {}
        for user_key, user_data in TEST_USERS.items():
            token, error = await get_token(session, user_key)
            if token:
                tokens[user_key] = token
                result.add("Auth", f"Login {user_key}", True, 5, 5)
                
                # Verify role
                status, body = await test_endpoint(session, token, '/api/auth/me')
                if status == 200:
                    import json
                    data = json.loads(body)
                    if data.get('role') == user_data['expected_role']:
                        result.add("Auth", f"Role verify {user_key}", True, 2.5, 2.5)
                    else:
                        result.add("Auth", f"Role verify {user_key}", False, 0, 2.5, 
                                   f"Expected {user_data['expected_role']}, got {data.get('role')}")
                else:
                    result.add("Auth", f"Role verify {user_key}", False, 0, 2.5, f"Status: {status}")
            else:
                tokens[user_key] = None
                result.add("Auth", f"Login {user_key}", False, 0, 5, error)
                result.add("Auth", f"Role verify {user_key}", False, 0, 2.5, "No token")
        
        # ==================== 3. ROUTE ACCESSIBILITY (20 points) ====================
        admin_token = tokens.get('admin')
        if admin_token:
            routes_tested = 0
            routes_passed = 0
            for endpoint in ROUTE_ACCESS['admin']:
                status, body = await test_endpoint(session, admin_token, endpoint)
                routes_tested += 1
                if status == 200:
                    routes_passed += 1
                else:
                    result.add("Routes", f"Admin: {endpoint}", False, 0, 0, f"Status: {status}")
            
            points = (routes_passed / routes_tested) * 20 if routes_tested > 0 else 0
            result.add("Routes", f"Admin route access ({routes_passed}/{routes_tested})", 
                       routes_passed == routes_tested, points, 20)
        else:
            result.add("Routes", "Admin route access", False, 0, 20, "No admin token")
        
        # ==================== 4. ROLE GUARDS (10 points) ====================
        # Test that sales_executive cannot access admin-only routes
        sales_token = tokens.get('sales_executive')
        if sales_token:
            guards_tested = 0
            guards_passed = 0
            for endpoint in UNAUTHORIZED_ROUTES.get('sales_executive', []):
                status, _ = await test_endpoint(session, sales_token, endpoint)
                guards_tested += 1
                if status in [401, 403]:
                    guards_passed += 1
                else:
                    result.add("Guards", f"Block {endpoint} for sales", False, 0, 0, 
                               f"Expected 401/403, got {status}")
            
            if guards_tested > 0:
                points = (guards_passed / guards_tested) * 10
                result.add("Guards", f"Role guards ({guards_passed}/{guards_tested})", 
                           guards_passed == guards_tested, points, 10)
            else:
                result.add("Guards", "Role guards", True, 10, 10, "No unauthorized routes to test")
        else:
            result.add("Guards", "Role guards", False, 0, 10, "No sales token")
        
        # ==================== 5. MASTERS DATA (15 points) ====================
        if admin_token:
            masters_tests = [
                ('/api/masters/tenure-types', 'tenure types', 5),
                ('/api/masters/consultant-roles', 'consultant roles', 5),
                ('/api/masters/meeting-types', 'meeting types', 5),
            ]
            for endpoint, name, points in masters_tests:
                status, body = await test_endpoint(session, admin_token, endpoint)
                if status == 200:
                    import json
                    data = json.loads(body)
                    if isinstance(data, list) and len(data) > 0:
                        result.add("Masters", f"Load {name}", True, points, points, f"{len(data)} items")
                    else:
                        result.add("Masters", f"Load {name}", False, 0, points, "Empty response")
                else:
                    result.add("Masters", f"Load {name}", False, 0, points, f"Status: {status}")
        else:
            result.add("Masters", "Masters data", False, 0, 15, "No admin token")
        
        # ==================== 6. SOW MASTERS DATA (10 points) ====================
        if admin_token:
            sow_tests = [
                ('/api/sow-masters/categories', 'SOW categories', 5),
                ('/api/sow-masters/scopes', 'SOW scopes', 5),
            ]
            for endpoint, name, points in sow_tests:
                status, body = await test_endpoint(session, admin_token, endpoint)
                if status == 200:
                    import json
                    data = json.loads(body)
                    if isinstance(data, list) and len(data) > 0:
                        result.add("SOW Masters", f"Load {name}", True, points, points, f"{len(data)} items")
                    else:
                        result.add("SOW Masters", f"Load {name}", False, 0, points, "Empty response")
                else:
                    result.add("SOW Masters", f"Load {name}", False, 0, points, f"Status: {status}")
        else:
            result.add("SOW Masters", "SOW masters data", False, 0, 10, "No admin token")
        
        # ==================== 7. DRAFTS API (10 points) ====================
        if admin_token:
            # Test GET drafts
            status, body = await test_endpoint(session, admin_token, '/api/drafts')
            if status == 200:
                result.add("Drafts", "GET /api/drafts", True, 5, 5)
            else:
                result.add("Drafts", "GET /api/drafts", False, 0, 5, f"Status: {status}")
            
            # Test POST drafts
            try:
                async with session.post(
                    f"{API_URL}/api/drafts",
                    headers={'Authorization': f'Bearer {admin_token}'},
                    json={'draft_type': 'test', 'title': 'E2E Test', 'data': {}}
                ) as resp:
                    if resp.status in [200, 201]:
                        result.add("Drafts", "POST /api/drafts", True, 5, 5)
                    else:
                        result.add("Drafts", "POST /api/drafts", False, 0, 5, f"Status: {resp.status}")
            except Exception as e:
                result.add("Drafts", "POST /api/drafts", False, 0, 5, str(e))
        else:
            result.add("Drafts", "Drafts API", False, 0, 10, "No admin token")
        
        # ==================== 8. CORE DATA (10 points) ====================
        if admin_token:
            core_tests = [
                ('/api/leads', 'Leads', 5),
                ('/api/projects', 'Projects', 5),
            ]
            for endpoint, name, points in core_tests:
                status, body = await test_endpoint(session, admin_token, endpoint)
                if status == 200:
                    import json
                    data = json.loads(body)
                    count = len(data) if isinstance(data, list) else data.get('total', 0)
                    result.add("Core Data", f"Load {name}", True, points, points, f"{count} items")
                else:
                    result.add("Core Data", f"Load {name}", False, 0, points, f"Status: {status}")
        else:
            result.add("Core Data", "Core data", False, 0, 10, "No admin token")
    
    return result


async def main():
    print(f"\n{'#'*70}")
    print(f" NETRA ERP - FULL E2E VALIDATION")
    print(f" API: {API_URL}")
    print(f"{'#'*70}")
    
    result = await run_validation()
    result.print_report()
    
    # Return appropriate exit code
    if result.score() >= 95:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
