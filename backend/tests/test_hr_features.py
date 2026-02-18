"""
Test HR Features: Org Chart, Leave Management, Attendance, Payroll
Tests for iteration 13 - New HR modules
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://enterprise-ops-10.preview.emergentagent.com')

class TestHRFeatures:
    """Tests for new HR features: OrgChart, Leave, Attendance, Payroll"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test credentials and token"""
        self.admin_credentials = {"email": "admin@company.com", "password": "admin123"}
        self.manager_credentials = {"email": "manager@company.com", "password": "manager123"}
        self.admin_token = None
        self.manager_token = None
        self.test_employee_id = None
        
    def get_admin_token(self):
        """Get admin auth token"""
        if not self.admin_token:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=self.admin_credentials
            )
            if response.status_code == 200:
                self.admin_token = response.json().get("access_token")
        return self.admin_token
    
    def get_manager_token(self):
        """Get manager auth token"""
        if not self.manager_token:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=self.manager_credentials
            )
            if response.status_code == 200:
                self.manager_token = response.json().get("access_token")
        return self.manager_token

    def get_headers(self, token=None):
        """Get request headers with auth"""
        if not token:
            token = self.get_admin_token()
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # ==================== AUTH TESTS ====================
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=self.admin_credentials
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "admin@company.com"
        print(f"✓ Admin login successful - role: {data['user']['role']}")
    
    def test_manager_login(self):
        """Test manager login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=self.manager_credentials
        )
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✓ Manager login successful - role: {data['user']['role']}")
    
    # ==================== ORG CHART TESTS ====================
    
    def test_org_chart_hierarchy_endpoint(self):
        """Test GET /api/employees/org-chart/hierarchy"""
        response = requests.get(
            f"{BASE_URL}/api/employees/org-chart/hierarchy",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Org chart endpoint failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Org chart hierarchy returned {len(data)} root nodes")
        
        # If there are nodes, verify structure
        if len(data) > 0:
            node = data[0]
            assert "id" in node, "Node should have id"
            assert "name" in node, "Node should have name"
            assert "children" in node, "Node should have children array"
            print(f"  - First root node: {node.get('name')} - {node.get('designation', 'N/A')}")
    
    # ==================== LEAVE MANAGEMENT TESTS ====================
    
    def test_get_leave_requests_my(self):
        """Test GET /api/leave-requests - user's own requests"""
        response = requests.get(
            f"{BASE_URL}/api/leave-requests",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get leave requests failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ My leave requests: {len(data)} requests found")
    
    def test_get_all_leave_requests_hr(self):
        """Test GET /api/leave-requests/all - all requests for HR"""
        response = requests.get(
            f"{BASE_URL}/api/leave-requests/all",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get all leave requests failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ All leave requests (HR view): {len(data)} requests found")
    
    # ==================== ATTENDANCE TESTS ====================
    
    def test_get_employees_for_attendance(self):
        """Get employees to use for attendance tests"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get employees failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Found {len(data)} employees")
        if len(data) > 0:
            self.test_employee_id = data[0].get('id')
            print(f"  - Using employee: {data[0].get('first_name')} {data[0].get('last_name')}")
        return data
    
    def test_post_attendance(self):
        """Test POST /api/attendance - create attendance record"""
        employees = self.test_get_employees_for_attendance()
        if not employees:
            pytest.skip("No employees found for attendance test")
        
        employee_id = employees[0].get('id')
        today = datetime.now().strftime('%Y-%m-%d')
        
        response = requests.post(
            f"{BASE_URL}/api/attendance",
            headers=self.get_headers(),
            json={
                "employee_id": employee_id,
                "date": today,
                "status": "present",
                "remarks": "Test attendance record"
            }
        )
        assert response.status_code == 200, f"Create attendance failed: {response.text}"
        data = response.json()
        assert "message" in data
        print(f"✓ Attendance created/updated: {data.get('message')}")
    
    def test_post_attendance_bulk(self):
        """Test POST /api/attendance/bulk - bulk upload attendance"""
        employees = self.test_get_employees_for_attendance()
        if not employees or len(employees) < 1:
            pytest.skip("No employees found for bulk attendance test")
        
        today = datetime.now().strftime('%Y-%m-%d')
        records = []
        for emp in employees[:3]:  # Use first 3 employees
            records.append({
                "employee_id": emp.get('id'),
                "date": today,
                "status": "present",
                "remarks": "Bulk test"
            })
        
        response = requests.post(
            f"{BASE_URL}/api/attendance/bulk",
            headers=self.get_headers(),
            json=records
        )
        assert response.status_code == 200, f"Bulk attendance upload failed: {response.text}"
        data = response.json()
        assert "created" in data or "updated" in data
        print(f"✓ Bulk attendance: {data.get('created', 0)} created, {data.get('updated', 0)} updated")
    
    def test_get_attendance(self):
        """Test GET /api/attendance - get attendance records"""
        current_month = datetime.now().strftime('%Y-%m')
        response = requests.get(
            f"{BASE_URL}/api/attendance?month={current_month}",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get attendance failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Attendance records for {current_month}: {len(data)} records")
    
    def test_get_attendance_summary(self):
        """Test GET /api/attendance/summary - per-employee summary"""
        current_month = datetime.now().strftime('%Y-%m')
        response = requests.get(
            f"{BASE_URL}/api/attendance/summary?month={current_month}",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get attendance summary failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Attendance summary for {current_month}: {len(data)} employees")
        
        # Verify summary structure if we have data
        if len(data) > 0:
            summary = data[0]
            expected_keys = ["employee_id", "present", "absent", "half_day", "wfh", "on_leave", "total"]
            for key in expected_keys:
                assert key in summary, f"Summary missing key: {key}"
            print(f"  - Sample: {summary.get('name')} - Present:{summary.get('present')} Absent:{summary.get('absent')}")
    
    # ==================== PAYROLL TESTS ====================
    
    def test_get_salary_components(self):
        """Test GET /api/payroll/salary-components"""
        response = requests.get(
            f"{BASE_URL}/api/payroll/salary-components",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get salary components failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "earnings" in data, "Should have earnings array"
        assert "deductions" in data, "Should have deductions array"
        assert isinstance(data["earnings"], list)
        assert isinstance(data["deductions"], list)
        
        print(f"✓ Salary components: {len(data['earnings'])} earnings, {len(data['deductions'])} deductions")
        
        # Verify sample earning
        if len(data["earnings"]) > 0:
            earning = data["earnings"][0]
            assert "name" in earning
            print(f"  - Sample earning: {earning.get('name')}")
    
    def test_get_salary_slips(self):
        """Test GET /api/payroll/salary-slips"""
        current_month = datetime.now().strftime('%Y-%m')
        response = requests.get(
            f"{BASE_URL}/api/payroll/salary-slips?month={current_month}",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Get salary slips failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Salary slips for {current_month}: {len(data)} slips")
    
    def test_generate_salary_slip(self):
        """Test POST /api/payroll/generate-slip"""
        # First get employees with salary configured
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.get_headers()
        )
        employees = response.json()
        emp_with_salary = [e for e in employees if (e.get('salary') or 0) > 0]
        
        if not emp_with_salary:
            print("⚠ No employees with salary configured - attempting to set salary")
            # Try to set salary for first employee
            if employees:
                emp_id = employees[0].get('id')
                patch_resp = requests.patch(
                    f"{BASE_URL}/api/employees/{emp_id}",
                    headers=self.get_headers(),
                    json={"salary": 50000}
                )
                if patch_resp.status_code == 200:
                    emp_with_salary = [employees[0]]
                    print(f"  - Set salary for employee {emp_id}")
                else:
                    pytest.skip(f"Cannot set salary: {patch_resp.text}")
        
        if not emp_with_salary:
            pytest.skip("No employees with salary to generate slip")
        
        employee_id = emp_with_salary[0].get('id')
        current_month = datetime.now().strftime('%Y-%m')
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/generate-slip",
            headers=self.get_headers(),
            json={
                "employee_id": employee_id,
                "month": current_month
            }
        )
        assert response.status_code == 200, f"Generate salary slip failed: {response.text}"
        data = response.json()
        
        # Verify slip structure
        assert "employee_id" in data
        assert "earnings" in data
        assert "deductions" in data
        assert "net_salary" in data
        
        print(f"✓ Generated salary slip: {data.get('employee_name')}")
        print(f"  - Gross: {data.get('gross_salary')}, Net: {data.get('net_salary')}")
    
    def test_generate_bulk_salary_slips(self):
        """Test POST /api/payroll/generate-bulk"""
        current_month = datetime.now().strftime('%Y-%m')
        
        response = requests.post(
            f"{BASE_URL}/api/payroll/generate-bulk",
            headers=self.get_headers(),
            json={"month": current_month}
        )
        assert response.status_code == 200, f"Bulk generate slips failed: {response.text}"
        data = response.json()
        
        assert "count" in data
        print(f"✓ Bulk generated: {data.get('count')} salary slips for {current_month}")


class TestNavigation:
    """Test that HR navigation items are present"""
    
    def test_hr_nav_items_accessible(self):
        """Verify HR routes are accessible"""
        # Login first
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@company.com", "password": "admin123"}
        )
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoints that power navigation pages
        endpoints_to_test = [
            "/api/employees",  # Employees page
            "/api/employees/org-chart/hierarchy",  # Org Chart page
            "/api/leave-requests",  # Leave Management page
            "/api/attendance",  # Attendance page
            "/api/payroll/salary-components",  # Payroll page
        ]
        
        for endpoint in endpoints_to_test:
            resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert resp.status_code == 200, f"Endpoint {endpoint} failed: {resp.status_code}"
            print(f"✓ {endpoint} - OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
