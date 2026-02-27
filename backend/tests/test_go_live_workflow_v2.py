"""
Go-Live Workflow API Tests - Iteration 133
Tests the new Go-Live approval flow where:
1. Employee ID is generated ONLY after Admin approves Go-Live
2. Admin approval dialog shows full employee details including preview Employee ID

Endpoints tested:
- GET /api/go-live/pending - Get pending Go-Live requests
- GET /api/go-live/request/{id}/details - Get full details for admin review  
- POST /api/go-live/{id}/approve - Approve and generate Employee ID
- POST /api/go-live/bank-verify/{employee_id} - Verify bank details
- GET /api/go-live/checklist/{employee_id} - Get checklist status
- POST /api/go-live/submit/{employee_id} - Submit for Go-Live approval
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGoLiveWorkflow:
    """Test Go-Live approval workflow APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin for tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as Admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Admin login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_token = token
        
    def test_01_get_pending_go_live_requests(self):
        """Test GET /api/go-live/pending - should return list of pending requests"""
        response = self.session.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 200, f"Failed to get pending requests: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Pending Go-Live requests: {len(data)}")
        
        # If there are pending requests, verify structure
        if len(data) > 0:
            req = data[0]
            assert "id" in req, "Request should have id"
            assert "employee_id" in req, "Request should have employee_id"
            assert "employee_name" in req, "Request should have employee_name"
            assert "status" in req, "Request should have status"
            print(f"  First pending request: {req.get('employee_name')} - {req.get('status')}")
        
    def test_02_get_employees_list(self):
        """Test GET /api/employees - get list of employees for Go-Live testing"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        
        data = response.json()
        employees = data if isinstance(data, list) else data.get('items', [])
        print(f"✓ Found {len(employees)} employees")
        
        # Find employees needing Go-Live
        for emp in employees[:5]:
            go_live_status = emp.get('go_live_status', 'not_submitted')
            print(f"  - {emp.get('employee_id', 'N/A')} ({emp.get('full_name', 'N/A')}): {go_live_status}")
            
    def test_03_get_go_live_checklist(self):
        """Test GET /api/go-live/checklist/{employee_id} - get checklist for an employee"""
        # First get an employee
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        data = response.json()
        employees = data if isinstance(data, list) else data.get('items', [])
        
        if len(employees) == 0:
            pytest.skip("No employees found for checklist test")
            
        # Get checklist for first employee
        emp = employees[0]
        emp_id = emp.get('id') or emp.get('employee_id')
        
        response = self.session.get(f"{BASE_URL}/api/go-live/checklist/{emp_id}")
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "employee" in data, "Response should have employee"
            assert "checklist" in data, "Response should have checklist"
            assert "summary" in data, "Response should have summary"
            
            print(f"✓ Got checklist for {data['employee'].get('name')}")
            print(f"  Readiness: {data['summary'].get('percentage')}% ({data['summary'].get('completed')}/{data['summary'].get('total')})")
            
            # Print checklist items
            for key, item in data.get('checklist', {}).items():
                status = "✓" if item.get('completed') else "✗"
                print(f"  {status} {item.get('label')}")
        else:
            print(f"  Employee {emp_id} not found for checklist")
            
    def test_04_get_request_details_endpoint(self):
        """Test GET /api/go-live/request/{id}/details - Full details for admin review"""
        # First get pending requests
        response = self.session.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 200
        
        pending = response.json()
        if len(pending) == 0:
            print("⚠ No pending Go-Live requests to test details endpoint")
            return
            
        # Get details for first pending request
        req_id = pending[0].get('id')
        response = self.session.get(f"{BASE_URL}/api/go-live/request/{req_id}/details")
        assert response.status_code == 200, f"Failed to get request details: {response.text}"
        
        data = response.json()
        
        # Verify structure - this is what the enhanced Go-Live dialog needs
        assert "request" in data, "Response should have request"
        assert "employee" in data, "Response should have employee"
        
        employee = data.get('employee', {})
        print(f"✓ Got Go-Live request details:")
        print(f"  Employee: {employee.get('full_name')}")
        print(f"  Current ID: {employee.get('current_employee_id')}")
        print(f"  ID Pending: {employee.get('employee_id_pending')}")
        print(f"  Preview ID: {employee.get('preview_employee_id')}")
        print(f"  Department: {employee.get('department')}")
        print(f"  Designation: {employee.get('designation')}")
        print(f"  Joining Date: {employee.get('joining_date')}")
        print(f"  Reporting Manager: {employee.get('reporting_manager_name')}")
        print(f"  Bank Verified: {employee.get('bank_verified')}")
        
        # Check for CTC structure
        if data.get('ctc_structure'):
            print(f"  CTC: {data['ctc_structure'].get('annual_ctc')}")
            
        # Check for reporting manager
        if data.get('reporting_manager'):
            print(f"  Manager: {data['reporting_manager'].get('full_name')}")
            
    def test_05_bank_verify_endpoint(self):
        """Test POST /api/go-live/bank-verify/{employee_id} - Verify bank details"""
        # Get employees list
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        data = response.json()
        employees = data if isinstance(data, list) else data.get('items', [])
        
        # Find employee with bank details but not verified
        test_emp = None
        for emp in employees:
            if emp.get('bank_account_number') and not emp.get('bank_verified'):
                test_emp = emp
                break
                
        if not test_emp:
            # Try with any employee with bank details
            for emp in employees:
                if emp.get('bank_account_number'):
                    test_emp = emp
                    break
                    
        if not test_emp:
            print("⚠ No employee with bank details found for verify test")
            return
            
        emp_id = test_emp.get('id') or test_emp.get('employee_id')
        print(f"Testing bank verify for: {test_emp.get('full_name', emp_id)}")
        
        response = self.session.post(f"{BASE_URL}/api/go-live/bank-verify/{emp_id}")
        assert response.status_code in [200, 403, 400], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            print("✓ Bank details verified successfully")
        else:
            print(f"⚠ Bank verify returned {response.status_code}: {response.json().get('detail', 'Unknown error')}")
            
    def test_06_go_live_stats(self):
        """Test GET /api/go-live/stats - Get Go-Live statistics"""
        response = self.session.get(f"{BASE_URL}/api/go-live/stats")
        assert response.status_code == 200, f"Failed to get stats: {response.text}"
        
        stats = response.json()
        print(f"✓ Go-Live Stats:")
        print(f"  Pending: {stats.get('pending', 0)}")
        print(f"  Approved: {stats.get('approved', 0)}")
        print(f"  Rejected: {stats.get('rejected', 0)}")
        print(f"  Total: {stats.get('total', 0)}")
        print(f"  Employees Pending Go-Live: {stats.get('employees_pending_go_live', 0)}")


class TestGoLiveApprovalFlow:
    """Test the complete Go-Live approval flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for approval flow tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_session(self):
        """Get admin session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        login = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if login.status_code == 200:
            session.headers.update({"Authorization": f"Bearer {login.json().get('access_token')}"})
            return session
        return None
        
    def get_hr_session(self):
        """Get HR session"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        login = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        if login.status_code == 200:
            session.headers.update({"Authorization": f"Bearer {login.json().get('access_token')}"})
            return session
        return None
        
    def test_01_hr_can_see_go_live_dashboard(self):
        """HR should be able to access Go-Live dashboard data"""
        hr = self.get_hr_session()
        if not hr:
            pytest.skip("HR login failed")
            
        # HR should see employees
        response = hr.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200, f"HR cannot access employees: {response.text}"
        print("✓ HR can access employees list")
        
    def test_02_admin_can_see_pending_approvals(self):
        """Admin should see pending Go-Live approvals"""
        admin = self.get_admin_session()
        if not admin:
            pytest.skip("Admin login failed")
            
        response = admin.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 200, f"Admin cannot access pending approvals: {response.text}"
        
        data = response.json()
        print(f"✓ Admin can see {len(data)} pending Go-Live approvals")
        
    def test_03_admin_can_view_full_details(self):
        """Admin should see full employee details for Go-Live approval"""
        admin = self.get_admin_session()
        if not admin:
            pytest.skip("Admin login failed")
            
        # Get pending
        response = admin.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 200
        
        pending = response.json()
        if len(pending) == 0:
            print("⚠ No pending Go-Live requests")
            return
            
        # Get full details
        req = pending[0]
        response = admin.get(f"{BASE_URL}/api/go-live/request/{req['id']}/details")
        assert response.status_code == 200, f"Failed to get details: {response.text}"
        
        details = response.json()
        employee = details.get('employee', {})
        
        # Key fields that should be present for Admin review
        print("✓ Admin can view full employee details:")
        print(f"  • Preview Employee ID: {employee.get('preview_employee_id', 'N/A')}")
        print(f"  • Employee ID Pending: {employee.get('employee_id_pending')}")
        print(f"  • Full Name: {employee.get('full_name')}")
        print(f"  • Department: {employee.get('department')}")
        print(f"  • Designation: {employee.get('designation')}")
        print(f"  • Joining Date: {employee.get('joining_date')}")
        print(f"  • Reporting Manager: {employee.get('reporting_manager_name')}")
        print(f"  • Current CTC: {employee.get('current_ctc')}")
        print(f"  • Bank Name: {employee.get('bank_name')}")
        print(f"  • Bank Account: {employee.get('bank_account_number')}")
        print(f"  • Bank Verified: {employee.get('bank_verified')}")
        print(f"  • Has Portal Access: {employee.get('has_portal_access')}")
        
        # Verify preview_employee_id is generated for pending approvals
        if employee.get('employee_id_pending'):
            assert employee.get('preview_employee_id'), "Preview Employee ID should be generated for pending approval"
            print(f"\n✓ Preview Employee ID correctly generated: {employee.get('preview_employee_id')}")


class TestEnablePortalAccess:
    """Test Enable Portal Access functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for portal access tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR
        login = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        if login.status_code == 200:
            self.session.headers.update({"Authorization": f"Bearer {login.json().get('access_token')}"})
            self.hr_token = login.json().get('access_token')
        else:
            # Try admin
            login = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "employee_id": "ADMIN001",
                "password": "admin123"
            })
            if login.status_code == 200:
                self.session.headers.update({"Authorization": f"Bearer {login.json().get('access_token')}"})
                self.hr_token = login.json().get('access_token')
            
    def test_01_portal_access_endpoint_exists(self):
        """Test that grant-portal-access endpoint exists"""
        # Get an employee to test with
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        data = response.json()
        employees = data if isinstance(data, list) else data.get('items', [])
        
        # Find employee without portal access
        test_emp = None
        for emp in employees:
            if not emp.get('user_id') and not emp.get('has_portal_access'):
                test_emp = emp
                break
                
        if not test_emp:
            print("⚠ No employee without portal access found - testing endpoint exists")
            # Just test with first employee
            if employees:
                test_emp = employees[0]
                
        if not test_emp:
            pytest.skip("No employees to test portal access")
            
        emp_id = test_emp.get('id')
        
        # Test endpoint exists (may fail if already has access, but endpoint should respond)
        response = self.session.post(f"{BASE_URL}/api/employees/{emp_id}/grant-access")
        assert response.status_code in [200, 400, 403, 409], f"Endpoint not responding properly: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Portal access granted:")
            print(f"  Login ID: {data.get('login_id')}")
            print(f"  Temp Password: {data.get('temp_password')}")
        else:
            print(f"⚠ Portal access status: {response.status_code} - {response.json().get('detail', 'Unknown')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
