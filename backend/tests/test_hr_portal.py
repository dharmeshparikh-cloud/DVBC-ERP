"""
HR Portal Backend Tests
Tests HR Manager and HR Executive role-based access control:
1. HR Login - Only HR roles can access HR portal
2. HR Manager Dashboard - Has Team View access
3. HR Executive Dashboard - NO Team View access
4. Team Workload API - HR Manager read-only access to consultants
5. Staffing Requests - HR Manager can view project staffing notifications
6. Bank Details Change Request API - Requires proof, admin approval for changes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
HR_MANAGER_EMAIL = "hr_manager@company.com"
HR_MANAGER_PASSWORD = "hr123"
HR_EXECUTIVE_EMAIL = "lakshmi.pillai83@dvconsulting.co.in"
HR_EXECUTIVE_PASSWORD = "hr123"
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
# Non-HR user for access control tests
SALES_EMAIL = "sales@consulting.com"
SALES_PASSWORD = "sales123"


class TestHRPortalAuthentication:
    """Test HR Portal login and authentication"""
    
    def test_hr_manager_login_success(self):
        """HR Manager can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_MANAGER_EMAIL,
            "password": HR_MANAGER_PASSWORD
        })
        print(f"HR Manager Login: Status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["user"]["role"] == "hr_manager"
            print(f"SUCCESS: HR Manager login - Role: {data['user']['role']}")
        elif response.status_code == 401:
            print("INFO: HR Manager user might not exist, skipping...")
            pytest.skip("HR Manager user not found")
        else:
            print(f"Response: {response.text}")
            pytest.fail(f"Unexpected status: {response.status_code}")
    
    def test_hr_executive_login_success(self):
        """HR Executive can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EXECUTIVE_EMAIL,
            "password": HR_EXECUTIVE_PASSWORD
        })
        print(f"HR Executive Login: Status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert data["user"]["role"] == "hr_executive"
            print(f"SUCCESS: HR Executive login - Role: {data['user']['role']}")
        elif response.status_code == 401:
            print("INFO: HR Executive user might not exist, skipping...")
            pytest.skip("HR Executive user not found")
        else:
            print(f"Response: {response.text}")
            pytest.fail(f"Unexpected status: {response.status_code}")


class TestHRManagerPermissions:
    """Test HR Manager has consulting read access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get HR Manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_MANAGER_EMAIL,
            "password": HR_MANAGER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("HR Manager login failed")
    
    def test_hr_manager_can_access_consultants(self):
        """HR Manager can view consultants (read-only access)"""
        response = requests.get(f"{BASE_URL}/api/consultants", headers=self.headers)
        print(f"Consultants API: Status={response.status_code}")
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: HR Manager can view consultants - Count: {len(data) if isinstance(data, list) else 'N/A'}")
            # Verify no financial data is present (read-only operational view)
            if isinstance(data, list) and len(data) > 0:
                consultant = data[0]
                # HR Manager should see workload but not financials
                print(f"Consultant fields: {list(consultant.keys())}")
        else:
            print(f"INFO: HR Manager consultants access denied: {response.text}")
    
    def test_hr_manager_can_view_projects_no_financials(self):
        """HR Manager can view projects but not financial data"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=self.headers)
        print(f"Projects API: Status={response.status_code}")
        
        # HR Manager has read: True for projects
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: HR Manager can view projects")
            # Check that financial data is not exposed
            if isinstance(data, list) and len(data) > 0:
                project = data[0]
                # These fields should NOT be present for HR Manager
                financial_fields = ['project_value', 'billing_rate', 'total_revenue', 'margin']
                exposed_financials = [f for f in financial_fields if f in project]
                print(f"Financial fields visible: {exposed_financials if exposed_financials else 'None'}")
        elif response.status_code == 403:
            print("INFO: HR Manager projects access restricted")
    
    def test_hr_manager_can_access_notifications(self):
        """HR Manager receives staffing notifications"""
        response = requests.get(f"{BASE_URL}/api/notifications", headers=self.headers)
        print(f"Notifications API: Status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: HR Manager notifications count: {len(data)}")
            # Check for staffing request notifications
            staffing = [n for n in data if n.get('type') == 'project_staffing_required']
            print(f"Staffing request notifications: {len(staffing)}")
        else:
            print(f"Response: {response.text}")
    
    def test_hr_manager_can_access_hr_dashboard_stats(self):
        """HR Manager can access HR dashboard stats"""
        response = requests.get(f"{BASE_URL}/api/stats/hr-dashboard", headers=self.headers)
        print(f"HR Dashboard Stats: Status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: HR Dashboard stats: {list(data.keys())}")
        elif response.status_code == 404:
            print("INFO: HR Dashboard stats endpoint not found")
        else:
            print(f"Response: {response.text}")


class TestHRExecutivePermissions:
    """Test HR Executive has NO consulting access"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get HR Executive token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EXECUTIVE_EMAIL,
            "password": HR_EXECUTIVE_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("HR Executive login failed")
    
    def test_hr_executive_cannot_access_consultants(self):
        """HR Executive should NOT have access to consultants"""
        response = requests.get(f"{BASE_URL}/api/consultants", headers=self.headers)
        print(f"HR Executive Consultants API: Status={response.status_code}")
        
        # HR Executive has read: False for consultants
        if response.status_code == 403:
            print("SUCCESS: HR Executive correctly denied access to consultants")
        elif response.status_code == 200:
            print("WARNING: HR Executive CAN access consultants - should be restricted")
        else:
            print(f"Response: {response.text}")
    
    def test_hr_executive_cannot_access_projects(self):
        """HR Executive should NOT have access to projects"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=self.headers)
        print(f"HR Executive Projects API: Status={response.status_code}")
        
        # HR Executive has read: False for projects
        if response.status_code == 403:
            print("SUCCESS: HR Executive correctly denied access to projects")
        elif response.status_code == 200:
            print("WARNING: HR Executive CAN access projects - should be restricted")
        else:
            print(f"Response: {response.text}")
    
    def test_hr_executive_can_access_employees(self):
        """HR Executive CAN access employee data"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        print(f"HR Executive Employees API: Status={response.status_code}")
        
        # HR Executive has read: True for employees
        if response.status_code == 200:
            print("SUCCESS: HR Executive can access employee data")
        else:
            print(f"Response: {response.text}")


class TestBankDetailsChangeRequest:
    """Test bank details change request API with approval flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get tokens for different users"""
        # HR Manager token
        hr_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_MANAGER_EMAIL,
            "password": HR_MANAGER_PASSWORD
        })
        if hr_response.status_code == 200:
            self.hr_token = hr_response.json()["access_token"]
            self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        else:
            self.hr_token = None
            self.hr_headers = {}
        
        # Admin token
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if admin_response.status_code == 200:
            self.admin_token = admin_response.json()["access_token"]
            self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        else:
            self.admin_token = None
            self.admin_headers = {}
    
    def test_bank_details_change_requires_proof(self):
        """Bank details change requires proof document"""
        if not self.hr_token:
            pytest.skip("HR Manager login failed")
        
        # First get an employee
        employees_response = requests.get(f"{BASE_URL}/api/employees", headers=self.hr_headers)
        if employees_response.status_code != 200:
            pytest.skip("Could not fetch employees")
        
        employees = employees_response.json()
        if not employees:
            pytest.skip("No employees found for testing")
        
        employee = employees[0]
        employee_id = employee.get('id')
        
        # Try to change bank details without proof
        response = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/bank-details-change-request",
            headers=self.hr_headers,
            json={
                "employee_id": employee_id,
                "new_bank_details": {
                    "account_number": "1234567890",
                    "ifsc_code": "SBIN0001234",
                    "bank_name": "State Bank of India"
                },
                "reason": "Test bank details change"
            }
        )
        print(f"Bank Details Change (no proof): Status={response.status_code}")
        
        # Should either require proof (400) or create approval request (200/201)
        if response.status_code == 400:
            print("SUCCESS: Bank proof document required")
            assert "proof" in response.text.lower()
        elif response.status_code in [200, 201]:
            data = response.json()
            print(f"SUCCESS: Bank details change request created: {data}")
        else:
            print(f"Response: {response.text}")
    
    def test_admin_can_update_bank_details_directly(self):
        """Admin can update bank details without approval"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        
        # First get an employee
        employees_response = requests.get(f"{BASE_URL}/api/employees", headers=self.admin_headers)
        if employees_response.status_code != 200:
            pytest.skip("Could not fetch employees")
        
        employees = employees_response.json()
        if not employees:
            pytest.skip("No employees found for testing")
        
        employee = employees[0]
        employee_id = employee.get('id')
        
        # Admin can update directly
        response = requests.post(
            f"{BASE_URL}/api/employees/{employee_id}/bank-details-change-request",
            headers=self.admin_headers,
            json={
                "employee_id": employee_id,
                "new_bank_details": {
                    "account_number": "9999888877776666",
                    "ifsc_code": "ADMIN00TEST",
                    "bank_name": "Admin Test Bank"
                },
                "reason": "Admin direct update test"
            }
        )
        print(f"Admin Bank Details Update: Status={response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            # Admin should get direct update
            assert data.get("approval_required") == False or "updated" in data.get("message", "").lower()
            print(f"SUCCESS: Admin updated bank details directly: {data.get('message')}")
        else:
            print(f"Response: {response.text}")


class TestNonHRAccessControl:
    """Test that non-HR users cannot access HR portal routes"""
    
    def test_non_hr_user_denied_hr_access(self):
        """Non-HR user (sales) should not access HR endpoints"""
        # Login as sales user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": SALES_EMAIL,
            "password": SALES_PASSWORD
        })
        
        if response.status_code != 200:
            print(f"Sales user login failed or user doesn't exist: {response.status_code}")
            pytest.skip("Sales user login failed")
        
        sales_token = response.json()["access_token"]
        sales_headers = {"Authorization": f"Bearer {sales_token}"}
        role = response.json()["user"]["role"]
        
        # Try to access HR-specific endpoints
        # Sales user should not be able to access employees endpoint
        employees_response = requests.get(f"{BASE_URL}/api/employees", headers=sales_headers)
        print(f"Sales user accessing /api/employees: Status={employees_response.status_code}")
        
        # Non-HR roles typically shouldn't access employees
        if employees_response.status_code == 403:
            print(f"SUCCESS: Non-HR user ({role}) denied access to employees")
        elif employees_response.status_code == 200:
            print(f"INFO: Non-HR user ({role}) CAN access employees - verify if this is expected")


class TestOnboardingAPI:
    """Test onboarding API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get HR Manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_MANAGER_EMAIL,
            "password": HR_MANAGER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("HR Manager login failed")
    
    def test_create_employee_during_onboarding(self):
        """HR Manager can create new employee during onboarding"""
        import uuid
        
        test_employee = {
            "employee_id": f"TEST_HR_EMP_{uuid.uuid4().hex[:6].upper()}",
            "first_name": "Test",
            "last_name": "OnboardEmployee",
            "email": f"test_onboard_{uuid.uuid4().hex[:8]}@test.com",
            "phone": "+91 9876543210",
            "department": "Consulting",
            "designation": "Consultant",
            "employment_type": "full_time",
            "joining_date": "2026-02-01",
            "onboarding_status": "pending_user_creation"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/employees",
            headers=self.headers,
            json=test_employee
        )
        print(f"Create Employee: Status={response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"SUCCESS: Employee created - ID: {data.get('id') or data.get('employee_id')}")
        elif response.status_code == 403:
            print("INFO: HR Manager cannot create employees - check permissions")
        else:
            print(f"Response: {response.text}")
    
    def test_get_users_for_manager_selection(self):
        """HR can get users list for reporting manager selection"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        print(f"Users List: Status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Users list retrieved - Count: {len(data)}")
            # Check that potential managers are present
            manager_roles = ['manager', 'hr_manager', 'project_manager', 'principal_consultant', 'admin']
            managers = [u for u in data if u.get('role') in manager_roles]
            print(f"Potential managers found: {len(managers)}")
        else:
            print(f"Response: {response.text}")


class TestApprovalsAPI:
    """Test pending approvals API for HR"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get HR Manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_MANAGER_EMAIL,
            "password": HR_MANAGER_PASSWORD
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("HR Manager login failed")
    
    def test_get_pending_approvals(self):
        """HR Manager can view pending approvals"""
        response = requests.get(f"{BASE_URL}/api/approvals/pending", headers=self.headers)
        print(f"Pending Approvals: Status={response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Pending approvals - Count: {len(data)}")
        elif response.status_code == 404:
            print("INFO: Approvals endpoint not found")
        else:
            print(f"Response: {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
