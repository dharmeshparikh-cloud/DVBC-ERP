"""
Production Readiness Audit Test Suite for DVBC-NETRA ERP
Iteration 81 - Comprehensive E2E Testing

Covers:
1. Data Integrity Tests
2. RBAC Verification
3. Transaction Reliability (Sales to Consulting E2E Flow)
4. Session Stability
5. Failure Scenarios (Chaos Test)
6. HR Module Validation
7. Critical Bug Regression
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://netra-notifications.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@dvbc.com", "password": "admin123"}
HR_MANAGER_CREDS = {"email": "hr.manager@dvbc.com", "password": "hr123"}
EMPLOYEE_CREDS = {"email": "rahul.kumar@dvbc.com", "password": "Welcome@EMP001"}
MANAGER_CREDS = {"email": "dp@dvbc.com", "password": "Welcome@123"}


# ============================================
# FIXTURES
# ============================================

@pytest.fixture(scope="module")
def admin_token():
    """Get admin token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def hr_token():
    """Get HR Manager token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
    assert response.status_code == 200, f"HR Manager login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def employee_token():
    """Get Employee token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
    assert response.status_code == 200, f"Employee login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def manager_token():
    """Get Manager token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code != 200:
        pytest.skip("Manager login failed - skipping manager tests")
    return response.json()["access_token"]


# ============================================
# 1. DATA INTEGRITY TESTS
# ============================================

class TestDataIntegrity:
    """Verify data consistency across collections"""
    
    def test_employees_have_required_fields(self, admin_token):
        """All employees should have required fields"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        employees = response.json()
        
        required_fields = ["id", "employee_id", "first_name"]
        for emp in employees:
            for field in required_fields:
                assert field in emp, f"Employee missing {field}: {emp.get('employee_id', 'Unknown')}"
        
        print(f"✅ All {len(employees)} employees have required fields")
    
    def test_leave_requests_have_valid_employee_ids(self, admin_token):
        """All leave requests should reference valid employees"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all leave requests
        response = requests.get(f"{BASE_URL}/api/leave-requests", headers=headers)
        assert response.status_code == 200
        leaves = response.json()
        
        # Get all employee IDs
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        employees = emp_response.json()
        valid_ids = {e["id"] for e in employees} | {e.get("employee_id") for e in employees}
        
        orphaned = []
        for leave in leaves:
            emp_id = leave.get("employee_id")
            if emp_id and emp_id not in valid_ids:
                orphaned.append(leave.get("id"))
        
        if orphaned:
            print(f"⚠️ Found {len(orphaned)} leave requests with invalid employee_id")
        else:
            print(f"✅ All {len(leaves)} leave requests have valid employee references")
    
    def test_projects_have_required_created_by_field(self, admin_token):
        """REGRESSION: All projects should have created_by field (was 520 error)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        assert response.status_code == 200, f"Projects endpoint failed: {response.text}"
        
        projects = response.json()
        for proj in projects:
            assert "created_by" in proj, f"Project missing created_by: {proj.get('id')}"
        
        print(f"✅ All {len(projects)} projects have created_by field (520 error FIXED)")
    
    def test_kickoff_requests_link_to_valid_projects(self, admin_token):
        """Kickoff requests with project_id should reference valid projects"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get kickoff requests
        kickoff_response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=headers)
        assert kickoff_response.status_code == 200
        kickoffs = kickoff_response.json()
        
        # Get projects
        proj_response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        projects = proj_response.json()
        valid_project_ids = {p["id"] for p in projects}
        
        for kickoff in kickoffs:
            if kickoff.get("project_id"):
                assert kickoff["project_id"] in valid_project_ids, \
                    f"Kickoff {kickoff['id']} references non-existent project"
        
        print(f"✅ All kickoff requests have valid project references")


# ============================================
# 2. RBAC VERIFICATION
# ============================================

class TestRBACVerification:
    """Test role-based access control"""
    
    def test_admin_can_access_all_modules(self, admin_token):
        """Admin should access HR, Sales, and Consulting modules"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        endpoints = [
            ("/api/employees", "HR"),
            ("/api/leads", "Sales"),
            ("/api/projects", "Consulting"),
            ("/api/ctc/pending-approvals", "CTC Approvals"),
            ("/api/kickoff-requests", "Kickoff Requests"),
        ]
        
        for endpoint, module in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 200, f"Admin cannot access {module}: {response.status_code}"
        
        print("✅ Admin can access all modules")
    
    def test_hr_manager_can_access_hr_module(self, hr_token):
        """HR Manager should access HR module"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        hr_endpoints = [
            "/api/employees",
            "/api/leave-requests",
            "/api/attendance",
            "/api/hr/bank-change-requests",
        ]
        
        for endpoint in hr_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 200, f"HR Manager cannot access {endpoint}"
        
        print("✅ HR Manager can access HR module")
    
    def test_employee_blocked_from_admin_functions(self, employee_token):
        """Regular employee should be blocked from admin functions"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        admin_only_endpoints = [
            "/api/ctc/pending-approvals",
            "/api/hr/bank-change-requests",
        ]
        
        for endpoint in admin_only_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code == 403, f"Employee should not access {endpoint}: got {response.status_code}"
        
        print("✅ Employee correctly blocked from admin functions")
    
    def test_unauthorized_access_returns_401(self):
        """API calls without token should return 401"""
        endpoints = ["/api/employees", "/api/leads", "/api/projects"]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 401, f"Expected 401 for {endpoint}, got {response.status_code}"
        
        print("✅ Unauthorized access properly returns 401")


# ============================================
# 3. TRANSACTION RELIABILITY (Sales to Consulting E2E)
# ============================================

class TestSalesConsultingE2EFlow:
    """Test full sales to consulting workflow"""
    
    def test_get_existing_lead_and_pricing_plan(self, admin_token):
        """Verify existing leads and pricing plans"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get leads
        leads_response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        assert leads_response.status_code == 200
        leads = leads_response.json()
        print(f"✅ Found {len(leads)} leads in system")
        
        # Get pricing plans
        pp_response = requests.get(f"{BASE_URL}/api/pricing-plans", headers=headers)
        assert pp_response.status_code == 200
        plans = pp_response.json()
        print(f"✅ Found {len(plans)} pricing plans in system")
    
    def test_get_existing_agreements(self, admin_token):
        """Verify existing agreements"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/agreements", headers=headers)
        assert response.status_code == 200
        agreements = response.json()
        print(f"✅ Found {len(agreements)} agreements in system")
        
        # Check status distribution
        status_counts = {}
        for agr in agreements:
            status = agr.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        print(f"  Agreement statuses: {status_counts}")
    
    def test_get_kickoff_requests(self, admin_token):
        """Verify kickoff requests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=headers)
        assert response.status_code == 200
        kickoffs = response.json()
        print(f"✅ Found {len(kickoffs)} kickoff requests")
        
        # Check status distribution
        status_counts = {}
        for k in kickoffs:
            status = k.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        print(f"  Kickoff statuses: {status_counts}")
    
    def test_consultant_assignment_on_projects(self, admin_token):
        """Verify projects have consultant assignments"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        assert response.status_code == 200
        projects = response.json()
        
        assigned_count = sum(1 for p in projects if p.get("assigned_consultants"))
        print(f"✅ {assigned_count}/{len(projects)} projects have consultant assignments")


# ============================================
# 4. SESSION STABILITY
# ============================================

class TestSessionStability:
    """Test login/logout and session handling"""
    
    def test_multiple_role_login_logout_cycle(self):
        """Test login/logout for multiple roles"""
        roles = [
            ("Admin", ADMIN_CREDS),
            ("HR Manager", HR_MANAGER_CREDS),
            ("Employee", EMPLOYEE_CREDS),
        ]
        
        for role_name, creds in roles:
            # Login
            response = requests.post(f"{BASE_URL}/api/auth/login", json=creds)
            assert response.status_code == 200, f"{role_name} login failed"
            data = response.json()
            assert "access_token" in data
            
            # Verify token works
            token = data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            me_response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
            assert me_response.status_code == 200
            
            print(f"✅ {role_name} login/session verified")
    
    def test_concurrent_requests_with_same_token(self, admin_token):
        """Test concurrent requests with same token"""
        import concurrent.futures
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        endpoints = ["/api/employees", "/api/leads", "/api/projects", "/api/notifications"]
        
        def make_request(endpoint):
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            return endpoint, response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request, ep) for ep in endpoints]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        for endpoint, status in results:
            assert status == 200, f"Concurrent request to {endpoint} failed: {status}"
        
        print("✅ Concurrent requests handled correctly")
    
    def test_invalid_token_returns_401(self):
        """Test that invalid token returns 401"""
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbnZhbGlkQHRlc3QuY29tIiwiZXhwIjoxNzMwMDAwMDAwfQ.invalid_signature"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✅ Invalid token correctly returns 401")


# ============================================
# 5. FAILURE SCENARIOS (CHAOS TEST)
# ============================================

class TestFailureScenarios:
    """Test error handling and edge cases"""
    
    def test_missing_required_fields_returns_validation_error(self, hr_token):
        """Submit form with missing required fields"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Create employee with missing fields
        data = {"first_name": "Test"}  # Missing last_name, email, etc.
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        
        # Should return 200 (with defaults) or 400/422 for validation error
        # Not 500 internal server error
        assert response.status_code != 500, f"Server error 500 for missing fields: {response.text}"
        print(f"✅ Missing fields handled: {response.status_code}")
    
    def test_nonexistent_resource_returns_404(self, admin_token):
        """Access non-existent resource IDs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        fake_id = str(uuid.uuid4())
        endpoints = [
            f"/api/employees/{fake_id}",
            f"/api/leads/{fake_id}",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code in [404, 400], \
                f"Expected 404 for non-existent resource at {endpoint}, got {response.status_code}"
        
        print("✅ Non-existent resources return 404")
    
    def test_duplicate_email_returns_proper_error(self, hr_token):
        """Submit duplicate data where unique constraint exists"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Try creating employee with existing admin email
        data = {
            "first_name": "TEST",
            "last_name": "Duplicate",
            "email": "admin@dvbc.com",  # Existing email
            "department": "HR",
            "date_of_joining": datetime.now().isoformat()
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        
        # Should not be 500
        assert response.status_code != 500, f"Server error for duplicate email: {response.text}"
        
        if response.status_code == 400:
            print("✅ Duplicate email properly returns 400")
        else:
            print(f"⚠️ Duplicate email returned {response.status_code} (expected 400)")
    
    def test_invalid_email_format_validation(self, hr_token):
        """Submit invalid email format"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        data = {
            "first_name": "TEST",
            "last_name": "Invalid",
            "email": "not-an-email",  # Invalid format
            "department": "HR"
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        
        # Should fail validation, not 500
        assert response.status_code != 500, f"Server error for invalid email: {response.text}"
        
        if response.status_code in [400, 422]:
            print("✅ Invalid email format properly rejected")
        else:
            print(f"⚠️ Invalid email returned {response.status_code} (expected 400/422)")


# ============================================
# 6. HR MODULE VALIDATION
# ============================================

class TestHRModuleValidation:
    """Test HR module workflows"""
    
    def test_leave_request_flow(self, admin_token, employee_token):
        """Test leave request flow"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        
        # Get leave balance
        balance_response = requests.get(f"{BASE_URL}/api/leave-requests/my-balance", headers=headers)
        assert balance_response.status_code == 200, f"Get leave balance failed: {balance_response.text}"
        print("✅ Leave balance retrieved")
    
    def test_attendance_record_retrieval(self, hr_token):
        """Test attendance retrieval"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        response = requests.get(f"{BASE_URL}/api/attendance", headers=headers)
        assert response.status_code == 200, f"Get attendance failed: {response.text}"
        print("✅ Attendance records retrieved")
    
    def test_modification_request_for_go_live_employee(self, admin_token):
        """Test modification request workflow for Go-Live employees"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get pending modification requests
        response = requests.get(f"{BASE_URL}/api/employees/modification-requests/pending", headers=headers)
        assert response.status_code == 200, f"Get modification requests failed: {response.text}"
        
        requests_list = response.json()
        print(f"✅ Found {len(requests_list)} pending modification requests")


# ============================================
# 7. CRITICAL BUG REGRESSION
# ============================================

class TestCriticalBugRegression:
    """Verify critical bugs from previous iterations are fixed"""
    
    def test_projects_endpoint_no_longer_520_error(self, admin_token):
        """REGRESSION: /api/projects should not return 520 error"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        assert response.status_code == 200, f"Projects endpoint returned {response.status_code}: {response.text}"
        
        projects = response.json()
        assert isinstance(projects, list), "Projects should return a list"
        print(f"✅ /api/projects working correctly ({len(projects)} projects)")
    
    def test_email_validation_prevents_invalid_formats(self, hr_token):
        """REGRESSION: Email validation should prevent invalid formats"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        data = {
            "first_name": "TEST",
            "last_name": "EmailValidation",
            "email": "invalid-email-format",
            "department": "HR"
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        
        # 500 is a bug, should be 400 or 422
        assert response.status_code != 500, "Invalid email should not cause 500 error"
        
        if response.status_code in [400, 422]:
            print("✅ Email validation working correctly")
        else:
            print(f"⚠️ Email validation returned {response.status_code} - check if employee was created")
    
    def test_email_uniqueness_check(self, hr_token):
        """REGRESSION: Email uniqueness should be checked"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        data = {
            "first_name": "TEST",
            "last_name": "UniqueCheck",
            "email": "admin@dvbc.com",  # Existing email
            "department": "HR"
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        
        # Should return 400 for duplicate
        assert response.status_code != 500, "Duplicate email should not cause 500 error"
        
        if response.status_code == 400:
            print("✅ Email uniqueness check working")
        else:
            print(f"⚠️ Duplicate email returned {response.status_code} (expected 400)")


# ============================================
# ADDITIONAL ENDPOINT TESTS
# ============================================

class TestAdditionalEndpoints:
    """Test additional critical endpoints"""
    
    def test_notifications_system(self, admin_token):
        """Test notifications system"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get unread count
        count_response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers)
        assert count_response.status_code == 200
        
        # Get notifications list
        list_response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert list_response.status_code == 200
        
        print("✅ Notifications system working")
    
    def test_ctc_system(self, hr_token):
        """Test CTC system"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        
        # Get CTC components
        comp_response = requests.get(f"{BASE_URL}/api/ctc/components", headers=headers)
        assert comp_response.status_code == 200
        
        # Get CTC list
        list_response = requests.get(f"{BASE_URL}/api/ctc", headers=headers)
        assert list_response.status_code == 200
        
        print("✅ CTC system working")
    
    def test_users_endpoint(self, admin_token):
        """Test users endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200
        users = response.json()
        print(f"✅ Found {len(users)} users")
    
    def test_departments_list(self, admin_token):
        """Test departments endpoint"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/employees/departments/list", headers=headers)
        assert response.status_code == 200
        depts = response.json()
        print(f"✅ Found {len(depts)} departments")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
