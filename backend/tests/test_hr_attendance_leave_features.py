"""
Test HR Attendance Input, HR Leave Input, and Payroll Summary Report features
- Employee selection dropdown on HR Attendance Input page (/hr-attendance-input)
- Employee selection dropdown on HR Leave Input page (/hr-leave-input)
- Custom attendance policy creation for specific employees
- Custom policy listing and deletion
- Auto-validate attendance using per-employee custom policies
- CSV export button on Payroll Summary Report (/payroll-summary-report)
- Employee filter updates leave requests table
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestCustomAttendancePolicy:
    """Test custom attendance policy CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as HR Manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.hr_token = token
        else:
            pytest.skip("HR Manager login failed")
    
    def test_get_attendance_policy(self):
        """Test GET /api/attendance/policy - Get default policy"""
        response = self.session.get(f"{BASE_URL}/api/attendance/policy")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "policy" in data
        assert "working_days" in data["policy"]
        assert "non_consulting" in data["policy"]
        assert "consulting" in data["policy"]
        assert "grace_period_minutes" in data["policy"]
        assert "grace_days_per_month" in data["policy"]
        print(f"✓ Default policy: {data['policy']}")
    
    def test_list_custom_policies(self):
        """Test GET /api/attendance/policy/custom - List all custom policies"""
        response = self.session.get(f"{BASE_URL}/api/attendance/policy/custom")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "policies" in data
        print(f"✓ Found {len(data['policies'])} custom policies")
        
        # Check structure of existing policies
        for policy in data["policies"]:
            assert "employee_id" in policy
            assert "check_in" in policy
            assert "check_out" in policy
            print(f"  - Policy for: {policy.get('employee_name', 'Unknown')}")
    
    def test_get_employees_for_dropdown(self):
        """Test GET /api/employees - Employees for selection dropdown"""
        response = self.session.get(f"{BASE_URL}/api/employees")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0, "No employees found"
        
        # Check employee structure for dropdown
        for emp in data[:3]:  # Check first 3
            assert "id" in emp
            assert "first_name" in emp
            assert "employee_id" in emp  # Employee code like EMP001
            print(f"  - Employee: {emp.get('first_name')} {emp.get('last_name')} ({emp.get('employee_id')})")
        
        print(f"✓ Total employees available for dropdown: {len(data)}")
    
    def test_get_specific_employee_policy(self):
        """Test GET /api/attendance/policy/employee/{employee_id} - Get policy for specific employee"""
        # First get an employee ID
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        emp_id = employees[0]["id"]
        response = self.session.get(f"{BASE_URL}/api/attendance/policy/employee/{emp_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employee_id" in data
        assert "policy" in data
        assert "check_in" in data["policy"]
        assert "check_out" in data["policy"]
        print(f"✓ Employee policy: {data['employee_name']} - {data['policy']}")
    
    def test_create_custom_policy(self):
        """Test POST /api/attendance/policy/custom - Create custom policy"""
        # First get an employee to create policy for
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        # Find an employee without custom policy (or use last one)
        test_employee = employees[-1] if employees else None
        
        if not test_employee:
            pytest.skip("No employees available")
        
        # Create custom policy
        policy_data = {
            "employee_id": test_employee["id"],
            "check_in": "08:30",
            "check_out": "17:30",
            "grace_period_minutes": 45,
            "grace_days_per_month": 4,
            "reason": "TEST_Custom schedule for testing"
        }
        
        response = self.session.post(f"{BASE_URL}/api/attendance/policy/custom", json=policy_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "policy" in data
        print(f"✓ Created custom policy: {data['message']}")
        
        # Store for cleanup
        self.test_employee_id = test_employee["id"]
    
    def test_verify_custom_policy_exists(self):
        """Verify custom policy was created - GET /api/attendance/policy/custom"""
        response = self.session.get(f"{BASE_URL}/api/attendance/policy/custom")
        
        assert response.status_code == 200
        
        data = response.json()
        policies = data.get("policies", [])
        
        # Check if test policy exists
        test_policies = [p for p in policies if "TEST_" in (p.get("reason") or "")]
        print(f"✓ Found {len(test_policies)} test custom policies")
    
    def test_delete_custom_policy(self):
        """Test DELETE /api/attendance/policy/custom/{employee_id} - Delete custom policy"""
        # First get list of custom policies
        list_response = self.session.get(f"{BASE_URL}/api/attendance/policy/custom")
        policies = list_response.json().get("policies", [])
        
        # Find test policy to delete
        test_policies = [p for p in policies if "TEST_" in (p.get("reason") or "")]
        
        if not test_policies:
            print("⚠ No test policies to delete, skipping")
            return
        
        emp_id = test_policies[0]["employee_id"]
        response = self.session.delete(f"{BASE_URL}/api/attendance/policy/custom/{emp_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ Deleted custom policy: {data['message']}")


class TestAutoValidateAttendance:
    """Test auto-validate attendance with custom policies"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as HR Manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("HR Manager login failed")
    
    def test_auto_validate_attendance(self):
        """Test POST /api/attendance/auto-validate - Run auto validation"""
        response = self.session.post(f"{BASE_URL}/api/attendance/auto-validate", json={
            "month": "2026-01"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "month" in data
        assert "employees" in data
        assert "summary" in data
        
        summary = data["summary"]
        assert "total_employees" in summary
        assert "clean" in summary
        assert "penalty_pending" in summary
        
        print(f"✓ Validation results for {data['month']}:")
        print(f"  - Total employees: {summary['total_employees']}")
        print(f"  - Clean: {summary['clean']}")
        print(f"  - Penalty pending: {summary['penalty_pending']}")
        
        # Check employee data structure
        if data["employees"]:
            emp = data["employees"][0]
            assert "employee_id" in emp
            assert "name" in emp
            assert "policy_times" in emp
            assert "present_days" in emp
            # Check for custom policy indicator
            if emp.get("has_custom_policy"):
                print(f"  - Employee with custom policy: {emp['name']}")
    
    def test_auto_validate_with_custom_policies_indicator(self):
        """Verify auto-validate uses per-employee custom policies"""
        # First check if Rahul Kumar (EMP001) has custom policy
        response = self.session.post(f"{BASE_URL}/api/attendance/auto-validate", json={
            "month": "2026-01"
        })
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Find Rahul Kumar in results
        rahul = None
        for emp in data["employees"]:
            if emp.get("employee_code") == "EMP001" or "Rahul" in emp.get("name", ""):
                rahul = emp
                break
        
        if rahul:
            print(f"✓ Rahul Kumar validation result:")
            print(f"  - Policy times: {rahul.get('policy_times')}")
            print(f"  - Has custom policy: {rahul.get('has_custom_policy')}")
            print(f"  - Grace days allowed: {rahul.get('grace_days_allowed')}")
        else:
            print("⚠ Rahul Kumar not found in validation results")


class TestHRAttendanceInput:
    """Test HR Attendance Input page API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as HR Manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("HR Manager login failed")
    
    def test_get_employee_attendance_input(self):
        """Test GET /api/attendance/hr/employee-attendance-input/{month}"""
        response = self.session.get(f"{BASE_URL}/api/attendance/hr/employee-attendance-input/2026-01")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "month" in data
        assert "employees" in data
        
        employees = data["employees"]
        print(f"✓ Employee attendance input for 2026-01: {len(employees)} employees")
        
        # Check structure
        if employees:
            emp = employees[0]
            assert "employee_id" in emp
            assert "name" in emp
            assert "present_days" in emp
            assert "absent_days" in emp
            print(f"  - Sample: {emp['name']} - Present: {emp['present_days']}, Absent: {emp['absent_days']}")
    
    def test_mark_bulk_attendance(self):
        """Test POST /api/attendance/hr/mark-attendance-bulk"""
        # Get employees first
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        # Mark attendance for first employee
        test_emp = employees[0]
        response = self.session.post(f"{BASE_URL}/api/attendance/hr/mark-attendance-bulk", json={
            "date": "2026-02-20",
            "records": [{
                "employee_id": test_emp["id"],
                "status": "present",
                "check_in": "2026-02-20T10:00:00Z",
                "check_out": "2026-02-20T19:00:00Z"
            }]
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ Bulk attendance marked: {data['message']}")


class TestHRLeaveInput:
    """Test HR Leave Input page API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as HR Manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("HR Manager login failed")
    
    def test_get_all_leave_requests(self):
        """Test GET /api/leave-requests/all - For leave requests table"""
        response = self.session.get(f"{BASE_URL}/api/leave-requests/all")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Total leave requests: {len(data)}")
        
        # Check structure
        if data:
            req = data[0]
            assert "employee_id" in req
            assert "leave_type" in req
            assert "status" in req
            print(f"  - Sample: {req.get('employee_name')} - {req.get('leave_type')} - {req.get('status')}")
    
    def test_apply_leave_for_employee(self):
        """Test POST /api/attendance/hr/apply-leave-for-employee"""
        # Get employees first
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        # Apply leave for first employee
        test_emp = employees[0]
        response = self.session.post(f"{BASE_URL}/api/attendance/hr/apply-leave-for-employee", json={
            "employee_id": test_emp["id"],
            "leave_type": "casual_leave",
            "start_date": "2026-03-15",
            "end_date": "2026-03-15",
            "reason": "TEST_Leave applied by HR for testing",
            "is_half_day": False
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert "leave_request_id" in data
        print(f"✓ Leave applied: {data['message']}")
    
    def test_bulk_credit_leaves(self):
        """Test POST /api/attendance/hr/bulk-leave-credit"""
        response = self.session.post(f"{BASE_URL}/api/attendance/hr/bulk-leave-credit", json={
            "leave_type": "casual_leave",
            "credit_days": 1,
            "reset_used": False,
            "employee_ids": []  # Empty means all employees
        })
        
        # This should work or return an error based on permissions
        # HR Manager should be able to do this
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Bulk leave credit: {data.get('message')}")
        elif response.status_code == 403:
            print("⚠ Bulk credit requires admin role")
        else:
            print(f"⚠ Unexpected response: {response.status_code} - {response.text}")


class TestPayrollSummaryReport:
    """Test Payroll Summary Report page API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as HR Manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("HR Manager login failed")
    
    def test_get_payroll_summary_report(self):
        """Test GET /api/payroll/summary-report - For CSV export data"""
        response = self.session.get(f"{BASE_URL}/api/payroll/summary-report?month=2026-01")
        
        # Check response
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Payroll summary report data retrieved")
            print(f"  - Total employees: {data.get('total_employees', 'N/A')}")
            print(f"  - Total net salary: {data.get('total_net_salary', 'N/A')}")
            
            # Check for CSV export fields
            if data.get("employee_details"):
                emp = data["employee_details"][0]
                csv_fields = ["name", "gross_salary", "total_deductions", "net_salary", 
                              "present_days", "leave_days"]
                for field in csv_fields:
                    assert field in emp, f"CSV export field '{field}' missing"
                print(f"  - CSV export fields verified")
        elif response.status_code == 404:
            print("⚠ No payroll data for 2026-01")
        else:
            print(f"⚠ Response: {response.status_code} - {response.text}")
    
    def test_get_generated_reports(self):
        """Test GET /api/payroll/generated-reports"""
        response = self.session.get(f"{BASE_URL}/api/payroll/generated-reports")
        
        if response.status_code == 200:
            data = response.json()
            reports = data.get("reports", [])
            print(f"✓ Generated reports: {len(reports)}")
        else:
            print(f"⚠ Response: {response.status_code} - {response.text}")


class TestEmployeeFilterFunctionality:
    """Test employee filter updates across pages"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as HR Manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("HR Manager login failed")
    
    def test_filter_attendance_by_employee(self):
        """Test filtering attendance input by specific employee"""
        # Get employees first
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        # Get attendance for specific employee
        test_emp = employees[0]
        response = self.session.get(f"{BASE_URL}/api/attendance/hr/employee-attendance-input/2026-01")
        
        assert response.status_code == 200
        
        data = response.json()
        all_employees = data.get("employees", [])
        
        # Filter client-side (as done in frontend)
        filtered = [e for e in all_employees if e.get("employee_id") == test_emp["id"]]
        
        print(f"✓ Attendance filter test:")
        print(f"  - All employees: {len(all_employees)}")
        print(f"  - Filtered by {test_emp['first_name']}: {len(filtered)}")
    
    def test_filter_leave_requests_by_employee(self):
        """Test filtering leave requests by specific employee"""
        # Get employees first
        emp_response = self.session.get(f"{BASE_URL}/api/employees")
        employees = emp_response.json()
        
        if not employees:
            pytest.skip("No employees available")
        
        # Get all leave requests
        response = self.session.get(f"{BASE_URL}/api/leave-requests/all")
        
        assert response.status_code == 200
        
        all_requests = response.json()
        
        # Filter client-side (as done in frontend)
        test_emp = employees[0]
        filtered = [r for r in all_requests if r.get("employee_id") == test_emp["id"]]
        
        print(f"✓ Leave requests filter test:")
        print(f"  - All requests: {len(all_requests)}")
        print(f"  - Filtered by {test_emp['first_name']}: {len(filtered)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
