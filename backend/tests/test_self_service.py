"""
Test Self-Service (My Workspace) APIs:
- GET /api/my/attendance
- GET /api/my/leave-balance
- GET /api/my/salary-slips
- GET /api/my/expenses
- POST /api/leave-requests (from My Leaves)
- POST /api/expenses (from My Expenses)
- POST /api/expenses/{id}/submit
- Payroll expense reimbursement integration
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSelfServiceAPIs:
    """Self-Service /api/my/* endpoints tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token for admin user"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.admin_token = login_response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Get admin user details
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.admin_headers)
        assert me_response.status_code == 200
        self.admin_user = me_response.json()
        
    def test_my_attendance_returns_data(self):
        """GET /api/my/attendance should return current user's attendance with summary"""
        response = requests.get(f"{BASE_URL}/api/my/attendance", headers=self.admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "records" in data, "Response should have 'records' field"
        assert "summary" in data, "Response should have 'summary' field"
        assert "employee" in data, "Response should have 'employee' field"
        
        # Verify summary structure
        summary = data["summary"]
        assert "present" in summary
        assert "absent" in summary
        assert "half_day" in summary
        assert "wfh" in summary
        assert "on_leave" in summary
        
        print(f"My Attendance: {len(data['records'])} records, summary: {summary}")
        
    def test_my_attendance_with_month_filter(self):
        """GET /api/my/attendance?month=YYYY-MM should filter by month"""
        current_month = datetime.now().strftime("%Y-%m")
        response = requests.get(f"{BASE_URL}/api/my/attendance?month={current_month}", headers=self.admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "records" in data
        assert "summary" in data
        print(f"My Attendance for {current_month}: {len(data['records'])} records")
        
    def test_my_leave_balance_returns_data(self):
        """GET /api/my/leave-balance should return leave balance with casual/sick/earned"""
        response = requests.get(f"{BASE_URL}/api/my/leave-balance", headers=self.admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "casual" in data, "Response should have 'casual' leave balance"
        assert "sick" in data, "Response should have 'sick' leave balance"
        assert "earned" in data, "Response should have 'earned' leave balance"
        
        # Verify balance structure
        for leave_type in ["casual", "sick", "earned"]:
            balance = data[leave_type]
            assert "total" in balance, f"{leave_type} should have 'total'"
            assert "used" in balance, f"{leave_type} should have 'used'"
            assert "available" in balance, f"{leave_type} should have 'available'"
            
        print(f"Leave Balance: casual={data['casual']['available']}, sick={data['sick']['available']}, earned={data['earned']['available']}")
        
    def test_my_salary_slips_returns_list(self):
        """GET /api/my/salary-slips should return all historical salary slips"""
        response = requests.get(f"{BASE_URL}/api/my/salary-slips", headers=self.admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if len(data) > 0:
            slip = data[0]
            assert "month" in slip, "Slip should have 'month'"
            assert "net_salary" in slip, "Slip should have 'net_salary'"
            print(f"My Salary Slips: {len(data)} slips found. Latest: {slip.get('month')}")
        else:
            print("My Salary Slips: 0 slips (none generated yet)")
            
    def test_my_expenses_returns_data(self):
        """GET /api/my/expenses should return user's expenses with summary"""
        response = requests.get(f"{BASE_URL}/api/my/expenses", headers=self.admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "expenses" in data, "Response should have 'expenses' field"
        assert "summary" in data, "Response should have 'summary' field"
        
        # Verify summary structure
        summary = data["summary"]
        assert "pending" in summary
        assert "approved" in summary
        assert "reimbursed" in summary
        assert "total_amount" in summary
        
        print(f"My Expenses: {len(data['expenses'])} expenses, pending={summary.get('pending', 0)}")
        

class TestLeaveRequestCreation:
    """Test POST /api/leave-requests from My Leaves page"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_create_leave_request(self):
        """POST /api/leave-requests should create a leave request"""
        start_date = (datetime.now() + timedelta(days=7)).isoformat()
        end_date = (datetime.now() + timedelta(days=8)).isoformat()
        
        payload = {
            "leave_type": "casual_leave",
            "start_date": start_date,
            "end_date": end_date,
            "reason": "TEST_Self service leave request for testing"
        }
        
        response = requests.post(f"{BASE_URL}/api/leave-requests", json=payload, headers=self.headers)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id'"
        assert data.get("leave_type") == "casual_leave"
        assert "status" in data, "Response should have 'status'"
        print(f"Leave request created: {data['id']}, status: {data['status']}")
        
        # Verify request appears in my leave requests
        list_response = requests.get(f"{BASE_URL}/api/leave-requests", headers=self.headers)
        assert list_response.status_code == 200
        requests_list = list_response.json()
        assert any(r["id"] == data["id"] for r in requests_list), "Created request should appear in list"
        

class TestExpenseCreationAndSubmission:
    """Test expense creation and submission from My Expenses page"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_create_expense_as_draft(self):
        """POST /api/expenses should create expense as draft"""
        payload = {
            "is_office_expense": True,
            "notes": "TEST_Self service expense",
            "line_items": [
                {
                    "category": "Travel",
                    "description": "TEST Travel expense",
                    "amount": 500,
                    "date": datetime.now().isoformat()
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/expenses", json=payload, headers=self.headers)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should have 'id'"
        assert data.get("status") == "draft", f"New expense should be draft, got: {data.get('status')}"
        assert data.get("total_amount") == 500
        
        self.created_expense_id = data["id"]
        print(f"Expense created: {data['id']}, status: {data['status']}, amount: {data['total_amount']}")
        
        return data["id"]
        
    def test_submit_expense_for_approval(self):
        """POST /api/expenses/{id}/submit should change status to pending"""
        # First create an expense
        payload = {
            "is_office_expense": True,
            "notes": "TEST_Expense to submit",
            "line_items": [
                {
                    "category": "Local Conveyance",
                    "description": "TEST Local travel",
                    "amount": 300,
                    "date": datetime.now().isoformat()
                }
            ]
        }
        
        create_response = requests.post(f"{BASE_URL}/api/expenses", json=payload, headers=self.headers)
        assert create_response.status_code in [200, 201]
        expense_id = create_response.json()["id"]
        
        # Submit for approval
        submit_response = requests.post(f"{BASE_URL}/api/expenses/{expense_id}/submit", headers=self.headers)
        assert submit_response.status_code == 200, f"Expected 200, got {submit_response.status_code}: {submit_response.text}"
        
        # Verify status changed to pending
        data = submit_response.json()
        assert data.get("status") == "pending", f"Status should be pending after submit, got: {data.get('status')}"
        print(f"Expense submitted: {expense_id}, new status: {data['status']}")
        

class TestPayrollExpenseReimbursement:
    """Test that approved expenses appear as Conveyance Reimbursement in salary slip"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get employee ID for admin
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        self.user = me_response.json()
        
        # Get employee record
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        if emp_response.status_code == 200:
            employees = emp_response.json()
            for emp in employees:
                if emp.get("user_id") == self.user["id"]:
                    self.employee_id = emp["id"]
                    break
                    
    def test_generate_slip_includes_expense_logic(self):
        """POST /api/payroll/generate-slip should include expense lookup for Conveyance Reimbursement"""
        if not hasattr(self, 'employee_id'):
            pytest.skip("Admin employee record not found")
            
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/generate-slip",
            json={"employee_id": self.employee_id, "month": current_month},
            headers=self.headers
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        
        slip = response.json()
        assert "earnings" in slip, "Slip should have earnings"
        assert "net_salary" in slip, "Slip should have net_salary"
        
        # Check if Conveyance Reimbursement is in earnings (if there are approved expenses)
        earnings = slip.get("earnings", [])
        expense_reimb = next((e for e in earnings if e.get("key") == "expense_reimbursement"), None)
        
        if expense_reimb:
            print(f"Conveyance Reimbursement found: ₹{expense_reimb['amount']}")
        else:
            print(f"No Conveyance Reimbursement (no approved expenses for {current_month})")
            
        print(f"Salary slip generated: net_salary=₹{slip.get('net_salary')}")
        

class TestRouteAccess:
    """Test that all 4 self-service routes work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_my_attendance_route(self):
        """GET /api/my/attendance should be accessible"""
        response = requests.get(f"{BASE_URL}/api/my/attendance", headers=self.headers)
        assert response.status_code == 200, f"My Attendance route failed: {response.status_code}"
        print("Route /api/my/attendance: PASSED")
        
    def test_my_leave_balance_route(self):
        """GET /api/my/leave-balance should be accessible"""
        response = requests.get(f"{BASE_URL}/api/my/leave-balance", headers=self.headers)
        assert response.status_code == 200, f"My Leave Balance route failed: {response.status_code}"
        print("Route /api/my/leave-balance: PASSED")
        
    def test_my_salary_slips_route(self):
        """GET /api/my/salary-slips should be accessible"""
        response = requests.get(f"{BASE_URL}/api/my/salary-slips", headers=self.headers)
        assert response.status_code == 200, f"My Salary Slips route failed: {response.status_code}"
        print("Route /api/my/salary-slips: PASSED")
        
    def test_my_expenses_route(self):
        """GET /api/my/expenses should be accessible"""
        response = requests.get(f"{BASE_URL}/api/my/expenses", headers=self.headers)
        assert response.status_code == 200, f"My Expenses route failed: {response.status_code}"
        print("Route /api/my/expenses: PASSED")


class TestMultiRoleAccess:
    """Test that My Workspace is accessible to different user roles"""
    
    def test_admin_access(self):
        """Admin should access all self-service APIs"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        for endpoint in ["/api/my/attendance", "/api/my/leave-balance", "/api/my/salary-slips", "/api/my/expenses"]:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code in [200, 400], f"Admin failed on {endpoint}: {response.status_code}"
        print("Admin access: All self-service APIs accessible")
        
    def test_manager_access(self):
        """Manager should access all self-service APIs"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        if login_response.status_code != 200:
            pytest.skip("Manager user not found")
            
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        for endpoint in ["/api/my/attendance", "/api/my/leave-balance", "/api/my/salary-slips", "/api/my/expenses"]:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            # 400 is acceptable if no employee record linked
            assert response.status_code in [200, 400], f"Manager failed on {endpoint}: {response.status_code}"
        print("Manager access: Self-service APIs accessible (or requires employee linking)")
        
    def test_executive_access(self):
        """Executive should access all self-service APIs"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        if login_response.status_code != 200:
            pytest.skip("Executive user not found")
            
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        for endpoint in ["/api/my/attendance", "/api/my/leave-balance", "/api/my/salary-slips", "/api/my/expenses"]:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code in [200, 400], f"Executive failed on {endpoint}: {response.status_code}"
        print("Executive access: Self-service APIs accessible (or requires employee linking)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
