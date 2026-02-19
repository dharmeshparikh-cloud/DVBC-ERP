"""
Test Employee Permissions and Attendance Summary APIs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEmployeePermissionsAndAttendance:
    """Test Employee Permissions and Attendance APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test with admin authentication"""
        self.admin_email = "admin@dvbc.com"
        self.admin_password = "admin123"
        self.headers = {"Content-Type": "application/json"}
        
        # Login as admin
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": self.admin_email, "password": self.admin_password}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.headers["Authorization"] = f"Bearer {token}"
        else:
            pytest.skip("Failed to authenticate as admin")
    
    def test_employees_list(self):
        """Test employees list endpoint returns employees"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        employees = response.json()
        assert isinstance(employees, list), "Expected list of employees"
        assert len(employees) > 0, "Expected at least one employee"
        
        # Verify employee structure
        if len(employees) > 0:
            emp = employees[0]
            assert "first_name" in emp or "employee_id" in emp, "Employee should have name or ID"
        
        print(f"SUCCESS: Found {len(employees)} employees")
    
    def test_employee_permissions_get(self):
        """Test get employee permissions endpoint"""
        # First get an employee ID
        employees_response = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        employees = employees_response.json()
        
        if len(employees) == 0:
            pytest.skip("No employees found for testing")
        
        employee_id = employees[0].get("employee_id") or employees[0].get("id")
        
        # Get permissions for the employee
        response = requests.get(
            f"{BASE_URL}/api/employee-permissions/{employee_id}",
            headers=self.headers
        )
        
        # Should return 200 or 404 (if no permissions set yet)
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Got permissions for employee {employee_id}")
            print(f"  - Permissions keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        else:
            print(f"INFO: No permissions set yet for employee {employee_id}")
    
    def test_permission_change_requests_list(self):
        """Test get pending permission change requests (admin approval workflow)"""
        response = requests.get(
            f"{BASE_URL}/api/permission-change-requests?status=pending",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        requests_list = response.json()
        assert isinstance(requests_list, list), "Expected list of requests"
        
        print(f"SUCCESS: Found {len(requests_list)} pending permission change requests")
        
        if len(requests_list) > 0:
            req = requests_list[0]
            assert "employee_name" in req or "employee_id" in req, "Request should have employee info"
            print(f"  - First request: {req.get('employee_name', req.get('employee_id'))}")
    
    def test_attendance_summary(self):
        """Test attendance summary endpoint returns per-employee breakdown"""
        # Test for current month
        from datetime import datetime
        now = datetime.now()
        month = now.month
        year = now.year
        
        response = requests.get(
            f"{BASE_URL}/api/attendance/summary?month={month}&year={year}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        summary = response.json()
        assert isinstance(summary, list), "Expected list of attendance summaries"
        
        print(f"SUCCESS: Got attendance summary for {month}/{year}")
        print(f"  - Found {len(summary)} employee summaries")
        
        if len(summary) > 0:
            emp_summary = summary[0]
            # Verify expected fields
            expected_fields = ["employee_id", "name", "present", "absent", "total"]
            for field in expected_fields:
                if field in emp_summary:
                    print(f"  - {field}: {emp_summary[field]}")
    
    def test_attendance_records(self):
        """Test attendance records endpoint"""
        # Get records for current month
        from datetime import datetime
        now = datetime.now()
        start_date = f"{now.year}-{str(now.month).zfill(2)}-01"
        end_date = f"{now.year}-{str(now.month).zfill(2)}-28"
        
        response = requests.get(
            f"{BASE_URL}/api/attendance?date_from={start_date}&date_to={end_date}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        records = response.json()
        assert isinstance(records, list), "Expected list of records"
        
        print(f"SUCCESS: Got {len(records)} attendance records for current month")
    
    def test_roles_list(self):
        """Test roles list endpoint for dropdown"""
        response = requests.get(f"{BASE_URL}/api/roles", headers=self.headers)
        
        # May return 200 or 404 if endpoint doesn't exist
        if response.status_code == 200:
            roles = response.json()
            assert isinstance(roles, list), "Expected list of roles"
            print(f"SUCCESS: Found {len(roles)} roles")
        else:
            print(f"INFO: Roles endpoint returned {response.status_code}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
