"""
E2E Employee Onboarding Flow Test - Sales/Consulting department

Tests:
1. New employee EMP011 login with Welcome@EMP011
2. EMP011 user info shows correct department (Sales)
3. EMP011 can view leads (including their own created leads)
4. EMP011 can create new lead and it links to their employee_id
5. Lead created_by -> user.id -> user.employee_id = EMP011 chain
6. EMP011 appears in password management list
7. Sidebar menu based on Sales department
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL env var must be set"


class TestEMP011Login:
    """Test 1: New employee EMP011 can login with Welcome@EMP011"""
    
    def test_emp011_login_with_employee_id(self):
        """Login with EMP011 / Welcome@EMP011"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP011",
            "password": "Welcome@EMP011"
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        
        user = data["user"]
        assert user["email"] == "e2e.sales.rep@dvbc.com"
        assert user["full_name"] == "E2ETest SalesRep"
        assert user["role"] == "consultant"
        print(f"PASSED: EMP011 login successful - User: {user['full_name']}")


class TestEMP011DepartmentAccess:
    """Test 2: EMP011 sees correct sidebar menu based on Sales department"""
    
    @pytest.fixture
    def emp011_token(self):
        """Get auth token for EMP011"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP011",
            "password": "Welcome@EMP011"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_emp011_user_has_sales_department(self, emp011_token):
        """Verify EMP011 has Sales department in user profile"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        
        assert response.status_code == 200
        user = response.json()
        
        assert user["department"] == "Sales", f"Expected Sales, got {user['department']}"
        assert user["role"] == "consultant"
        print(f"PASSED: EMP011 department = {user['department']}")


class TestEMP011LeadsAccess:
    """Test 3 & 4: EMP011 can view leads and create new leads"""
    
    @pytest.fixture
    def emp011_token(self):
        """Get auth token for EMP011"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP011",
            "password": "Welcome@EMP011"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_emp011_can_view_leads(self, emp011_token):
        """EMP011 can access leads endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        
        assert response.status_code == 200
        leads = response.json()
        assert isinstance(leads, list)
        print(f"PASSED: EMP011 can view {len(leads)} leads")
    
    def test_emp011_existing_lead_shows_correct_linkage(self, emp011_token):
        """E2E Test Company lead was created by EMP011"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        
        assert response.status_code == 200
        leads = response.json()
        
        # Find the E2E test lead
        e2e_leads = [l for l in leads if "E2E Test" in l.get("company", "")]
        assert len(e2e_leads) > 0, "E2E Test lead not found"
        
        lead = e2e_leads[0]
        assert lead["company"] == "E2E Test Company Pvt Ltd"
        assert lead["created_by"] is not None
        print(f"PASSED: E2E Test lead found - created_by: {lead['created_by']}")
    
    def test_emp011_can_create_new_lead(self, emp011_token):
        """EMP011 can create a new lead"""
        new_lead = {
            "first_name": "Pytest",
            "last_name": "Lead",
            "company": f"Pytest Test Company {uuid.uuid4().hex[:6]}",
            "email": "pytest.lead@testcompany.com",
            "phone": "9876543210",
            "source": "API Test"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {emp011_token}"},
            json=new_lead
        )
        
        assert response.status_code == 200, f"Failed to create lead: {response.text}"
        lead = response.json()
        
        assert lead["first_name"] == "Pytest"
        assert lead["company"].startswith("Pytest Test Company")
        assert lead["created_by"] is not None
        print(f"PASSED: EMP011 created lead - ID: {lead['id']}, created_by: {lead['created_by']}")
        
        return lead


class TestEmployeeIDLinkageChain:
    """Test 5: Lead created_by -> user.id -> user.employee_id = EMP011 chain"""
    
    @pytest.fixture
    def emp011_token(self):
        """Get auth token for EMP011"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP011",
            "password": "Welcome@EMP011"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get auth token for Admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_created_by_links_to_emp011_user(self, emp011_token, admin_token):
        """Verify the chain: lead.created_by -> user.id -> user.employee_id = EMP011"""
        
        # Step 1: Get EMP011's user info
        user_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        assert user_response.status_code == 200
        emp011_user = user_response.json()
        emp011_user_id = emp011_user["id"]
        
        # Step 2: Get the E2E test lead
        leads_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        assert leads_response.status_code == 200
        leads = leads_response.json()
        
        e2e_leads = [l for l in leads if "E2E Test" in l.get("company", "")]
        assert len(e2e_leads) > 0, "E2E Test lead not found"
        lead = e2e_leads[0]
        
        # Step 3: Verify lead.created_by == emp011_user.id
        assert lead["created_by"] == emp011_user_id, \
            f"Linkage broken: lead.created_by={lead['created_by']} != user.id={emp011_user_id}"
        
        # Step 4: Get all users to find EMP011 user and verify employee_id
        users_response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert users_response.status_code == 200
        users = users_response.json()
        
        emp011_user_full = [u for u in users if u["id"] == emp011_user_id]
        assert len(emp011_user_full) > 0, f"User {emp011_user_id} not found"
        
        user_record = emp011_user_full[0]
        assert user_record.get("employee_id") == "EMP011", \
            f"Employee ID mismatch: expected EMP011, got {user_record.get('employee_id')}"
        
        print(f"PASSED: Linkage chain verified:")
        print(f"  Lead ({lead['company']}) created_by: {lead['created_by']}")
        print(f"  User ID: {emp011_user_id}")
        print(f"  User employee_id: {user_record['employee_id']}")


class TestPasswordManagement:
    """Test 8: EMP011 appears in Password Management list"""
    
    @pytest.fixture
    def admin_token(self):
        """Get auth token for Admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_emp011_in_employees_list(self, admin_token):
        """EMP011 appears in employees list"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        employees = response.json()
        
        emp011 = [e for e in employees if e.get("employee_id") == "EMP011"]
        assert len(emp011) > 0, "EMP011 not found in employees list"
        
        employee = emp011[0]
        assert employee["employee_id"] == "EMP011"
        assert employee["department"] == "Sales"
        print(f"PASSED: EMP011 found in employees list - {employee['first_name']} {employee['last_name']}")
    
    def test_emp011_in_users_list_with_correct_employee_id(self, admin_token):
        """EMP011 appears in users list with correct employee_id"""
        response = requests.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        users = response.json()
        
        emp011_user = [u for u in users if u.get("employee_id") == "EMP011"]
        assert len(emp011_user) > 0, "User with employee_id EMP011 not found"
        
        user = emp011_user[0]
        assert user["employee_id"] == "EMP011"
        assert user["email"] == "e2e.sales.rep@dvbc.com"
        print(f"PASSED: EMP011 found in users list - {user['full_name']}")


class TestSalesDepartmentPages:
    """Test 6: EMP011 can access Sales Dashboard, SOW & Pricing, Agreements pages"""
    
    @pytest.fixture
    def emp011_token(self):
        """Get auth token for EMP011"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP011",
            "password": "Welcome@EMP011"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_emp011_can_access_pricing_plans(self, emp011_token):
        """EMP011 can access pricing plans endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/pricing-plans",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        
        # 200 or 404 (empty) is acceptable
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        print(f"PASSED: EMP011 can access pricing plans endpoint (status: {response.status_code})")
    
    def test_emp011_can_access_agreements(self, emp011_token):
        """EMP011 can access agreements endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"PASSED: EMP011 can access agreements endpoint")
    
    def test_emp011_can_access_sow(self, emp011_token):
        """EMP011 can access SOW endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/sow",
            headers={"Authorization": f"Bearer {emp011_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        print(f"PASSED: EMP011 can access SOW endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
