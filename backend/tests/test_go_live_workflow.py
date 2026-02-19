"""
Go-Live Workflow API Tests
Tests the Go-Live dashboard endpoints for HR Manager and Admin roles
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGoLiveWorkflow:
    """Go-Live workflow endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.hr_token = None
        self.admin_token = None
        self.hr_user = None
        self.admin_user = None
        
    def login_hr(self):
        """Login as HR Manager"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert response.status_code == 200, f"HR login failed: {response.text}"
        data = response.json()
        self.hr_token = data.get("access_token")
        self.hr_user = data.get("user")
        self.session.headers.update({"Authorization": f"Bearer {self.hr_token}"})
        return self.hr_token
        
    def login_admin(self):
        """Login as Admin"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.admin_token = data.get("access_token")
        self.admin_user = data.get("user")
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
        return self.admin_token

    def test_01_hr_login(self):
        """Test HR Manager can login"""
        token = self.login_hr()
        assert token is not None
        assert self.hr_user is not None
        assert self.hr_user.get("role") == "hr_manager"
        print(f"✓ HR Manager logged in: {self.hr_user.get('full_name')}")

    def test_02_admin_login(self):
        """Test Admin can login"""
        token = self.login_admin()
        assert token is not None
        assert self.admin_user is not None
        assert self.admin_user.get("role") == "admin"
        print(f"✓ Admin logged in: {self.admin_user.get('full_name')}")

    def test_03_get_employees_list(self):
        """Test fetching employees list for Go-Live dashboard"""
        self.login_hr()
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        employees = response.json()
        assert isinstance(employees, list)
        print(f"✓ Got {len(employees)} employees")
        
        # Store employee for further tests
        if employees:
            self.test_employee = employees[0]
            print(f"  Test employee: {self.test_employee.get('first_name')} {self.test_employee.get('last_name')} ({self.test_employee.get('employee_id')})")

    def test_04_get_go_live_checklist(self):
        """Test GET /api/go-live/checklist/{employee_id} endpoint"""
        self.login_hr()
        
        # First get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees found to test checklist")
            
        test_emp = employees[0]
        emp_id = test_emp.get("employee_id") or test_emp.get("id")
        
        # Get checklist
        response = self.session.get(f"{BASE_URL}/api/go-live/checklist/{emp_id}")
        assert response.status_code == 200, f"Failed to get checklist: {response.text}"
        
        data = response.json()
        assert "employee" in data
        assert "checklist" in data
        
        checklist = data["checklist"]
        print(f"✓ Got Go-Live checklist for {data['employee'].get('name')}")
        print(f"  - Onboarding Complete: {checklist.get('onboarding_complete')}")
        print(f"  - CTC Approved: {checklist.get('ctc_approved')}")
        print(f"  - Bank Details Added: {checklist.get('bank_details_added')}")
        print(f"  - Bank Verified: {checklist.get('bank_verified')}")
        print(f"  - Documents Generated: {checklist.get('documents_generated')}")
        print(f"  - Portal Access: {checklist.get('portal_access_granted')}")
        print(f"  - Go-Live Status: {checklist.get('go_live_status')}")

    def test_05_get_pending_go_live_admin(self):
        """Test GET /api/go-live/pending endpoint (Admin only)"""
        self.login_admin()
        
        response = self.session.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 200, f"Failed to get pending requests: {response.text}"
        
        requests_list = response.json()
        assert isinstance(requests_list, list)
        print(f"✓ Got {len(requests_list)} pending Go-Live requests")

    def test_06_hr_cannot_get_pending(self):
        """Test HR cannot access pending endpoint (should fail)"""
        self.login_hr()
        
        response = self.session.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 403, f"HR should not access pending: {response.status_code}"
        print(f"✓ HR correctly denied access to pending requests (403)")

    def test_07_go_live_checklist_structure(self):
        """Test Go-Live checklist response structure"""
        self.login_admin()
        
        # Get an employee
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees found")
            
        emp_id = employees[0].get("employee_id") or employees[0].get("id")
        
        response = self.session.get(f"{BASE_URL}/api/go-live/checklist/{emp_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate response structure
        assert "employee" in data
        assert "checklist" in data
        
        employee = data["employee"]
        assert "id" in employee
        assert "name" in employee
        
        checklist = data["checklist"]
        expected_keys = [
            "onboarding_complete", "ctc_approved", "bank_details_added",
            "bank_verified", "documents_generated", "portal_access_granted",
            "go_live_status"
        ]
        for key in expected_keys:
            assert key in checklist, f"Missing key: {key}"
            
        print(f"✓ Go-Live checklist structure validated")

    def test_08_submit_go_live_request_hr(self):
        """Test HR can submit Go-Live request"""
        self.login_hr()
        
        # Get employees
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees found")
        
        # Find an employee that's not already pending/active
        test_emp = None
        for emp in employees:
            emp_id = emp.get("employee_id") or emp.get("id")
            checklist_resp = self.session.get(f"{BASE_URL}/api/go-live/checklist/{emp_id}")
            if checklist_resp.status_code == 200:
                checklist_data = checklist_resp.json()
                status = checklist_data.get("checklist", {}).get("go_live_status")
                if status in ["not_submitted", "rejected"]:
                    test_emp = emp
                    break
        
        if not test_emp:
            print("  All employees already have pending/active Go-Live status - skipping submit test")
            pytest.skip("No eligible employee for submission")
            
        emp_id = test_emp.get("employee_id") or test_emp.get("id")
        
        response = self.session.post(f"{BASE_URL}/api/go-live/submit/{emp_id}", json={
            "checklist": {"all_items_complete": True},
            "notes": "Test Go-Live submission"
        })
        
        # Should succeed or fail with 400 if already pending
        assert response.status_code in [200, 400], f"Unexpected response: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "request_id" in data
            print(f"✓ Go-Live request submitted: {data.get('request_id')}")
        else:
            print(f"✓ Go-Live request already pending (expected behavior)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
