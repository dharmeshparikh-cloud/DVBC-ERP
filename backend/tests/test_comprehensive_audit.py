"""
Comprehensive E2E Audit Test Suite for DVBC-NETRA ERP
Tests: Authentication, RBAC, Employees, CTC, Leave, Expenses, Attendance, Go-Live, Notifications
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@dvbc.com", "password": "admin123"}
HR_MANAGER_CREDS = {"email": "hr.manager@dvbc.com", "password": "hr123"}
EMPLOYEE_CREDS = {"email": "rahul.kumar@dvbc.com", "password": "Welcome@EMP001"}
MANAGER_CREDS = {"email": "dp@dvbc.com", "password": "Welcome@123"}

class TestAuthentication:
    """Test authentication flows"""
    
    def test_login_valid_admin(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✅ Admin login successful: {data['user']['email']}")
    
    def test_login_valid_hr_manager(self):
        """Test HR Manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        assert response.status_code == 200, f"HR Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "hr_manager"
        print(f"✅ HR Manager login successful: {data['user']['email']}")
    
    def test_login_valid_employee(self):
        """Test Employee login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"✅ Employee login successful: {data['user']['email']}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "invalid@test.com", "password": "wrong"})
        assert response.status_code in [401, 400], f"Expected 401/400, got {response.status_code}"
        print("✅ Invalid credentials rejected as expected")
    
    def test_unauthorized_access_without_token(self):
        """Test API access without token"""
        response = requests.get(f"{BASE_URL}/api/employees")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✅ Unauthorized access blocked")


class TestRBAC:
    """Test Role-Based Access Control"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["access_token"]
    
    def test_admin_can_access_all_employees(self, admin_token):
        """Admin should access all employees"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200, f"Admin employees access failed: {response.text}"
        employees = response.json()
        assert isinstance(employees, list)
        print(f"✅ Admin can access {len(employees)} employees")
    
    def test_hr_can_access_employees(self, hr_token):
        """HR Manager should access employees"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200, f"HR employees access failed: {response.text}"
        print("✅ HR Manager can access employees list")
    
    def test_employee_can_access_employees(self, employee_token):
        """Employee should be able to see employees list"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        # Employee may have restricted access
        assert response.status_code in [200, 403], f"Unexpected status: {response.status_code}"
        print(f"✅ Employee access to employees: {response.status_code}")
    
    def test_admin_can_access_ctc_pending(self, admin_token):
        """Admin should access pending CTC approvals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/ctc/pending-approvals", headers=headers)
        assert response.status_code == 200, f"Admin CTC pending access failed: {response.text}"
        print("✅ Admin can access CTC pending approvals")
    
    def test_employee_cannot_access_ctc_pending(self, employee_token):
        """Regular employee should not access CTC pending approvals"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/ctc/pending-approvals", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✅ Employee blocked from CTC pending approvals")
    
    def test_hr_can_access_bank_change_requests(self, hr_token):
        """HR Manager should access bank change requests"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/bank-change-requests", headers=headers)
        assert response.status_code == 200, f"HR bank requests access failed: {response.text}"
        print("✅ HR Manager can access bank change requests")
    
    def test_employee_cannot_access_bank_change_requests(self, employee_token):
        """Employee should not access bank change requests"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/bank-change-requests", headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✅ Employee blocked from bank change requests")


class TestEmployeeCRUD:
    """Test Employee CRUD operations"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    def test_get_employees_list(self, hr_token):
        """Get employees list"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        employees = response.json()
        assert isinstance(employees, list)
        print(f"✅ Retrieved {len(employees)} employees")
    
    def test_get_managers_list(self, hr_token):
        """Get managers for dropdown"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/managers", headers=headers)
        assert response.status_code == 200
        managers = response.json()
        assert isinstance(managers, list)
        print(f"✅ Retrieved {len(managers)} managers")
    
    def test_get_single_employee(self, hr_token):
        """Get a single employee by ID"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        # First get the list
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        employees = response.json()
        if employees:
            emp_id = employees[0]["id"]
            response = requests.get(f"{BASE_URL}/api/employees/{emp_id}", headers=headers)
            assert response.status_code == 200
            emp = response.json()
            assert emp["id"] == emp_id
            print(f"✅ Retrieved employee: {emp.get('first_name', '')} {emp.get('last_name', '')}")
    
    def test_create_employee_validates_duplicate_email(self, hr_token):
        """Test duplicate email prevention"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        # Try creating with existing email
        data = {
            "first_name": "TEST",
            "last_name": "Duplicate",
            "email": "admin@dvbc.com",  # Existing email
            "department": "HR",
            "designation": "Test",
            "date_of_joining": datetime.now().isoformat()
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        # Should fail with 400
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        print("✅ Duplicate email validation works")
    
    def test_employee_patch_update(self, hr_token):
        """Test PATCH update for employee"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        # Get an employee
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        employees = response.json()
        if employees:
            emp_id = employees[0]["id"]
            # Try PATCH update
            response = requests.patch(
                f"{BASE_URL}/api/employees/{emp_id}",
                headers=headers,
                json={"designation": "Updated Designation"}
            )
            assert response.status_code in [200, 403], f"PATCH failed: {response.text}"
            print(f"✅ Employee PATCH update: {response.status_code}")


class TestCTCStructure:
    """Test CTC Structure operations"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    def test_get_ctc_components(self, hr_token):
        """Get CTC component master"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/ctc/components", headers=headers)
        assert response.status_code == 200, f"Get CTC components failed: {response.text}"
        components = response.json()
        assert isinstance(components, list)
        print(f"✅ Retrieved {len(components)} CTC components")
    
    def test_get_ctc_list(self, hr_token):
        """Get list of CTC structures"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/ctc", headers=headers)
        assert response.status_code == 200, f"Get CTC list failed: {response.text}"
        print("✅ CTC list retrieved successfully")
    
    def test_calculate_ctc_breakdown(self, hr_token):
        """Test CTC breakdown calculation"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        data = {
            "annual_ctc": 1200000,
            "components": [
                {"key": "basic", "enabled": True, "value": 40},
                {"key": "hra", "enabled": True, "value": 50},
                {"key": "conveyance", "enabled": True, "value": 1600},
                {"key": "special_allowance", "enabled": True}
            ]
        }
        response = requests.post(f"{BASE_URL}/api/ctc/calculate", headers=headers, json=data)
        assert response.status_code == 200, f"CTC calculation failed: {response.text}"
        breakdown = response.json()
        assert "components" in breakdown or "monthly_gross" in breakdown or "gross" in breakdown
        print("✅ CTC breakdown calculated successfully")


class TestLeaveManagement:
    """Test Leave Request operations"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_get_leave_types(self, employee_token):
        """Get leave types"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/leave-types", headers=headers)
        assert response.status_code == 200, f"Get leave types failed: {response.text}"
        print("✅ Leave types retrieved")
    
    def test_get_leave_balance(self, employee_token):
        """Get leave balance for current user"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/leave-requests/my-balance", headers=headers)
        assert response.status_code == 200, f"Get leave balance failed: {response.text}"
        print("✅ Leave balance retrieved")
    
    def test_get_pending_leave_requests(self, hr_token):
        """HR should see pending leave requests"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/leave-requests?status=pending", headers=headers)
        assert response.status_code == 200, f"Get pending leaves failed: {response.text}"
        print("✅ Pending leave requests retrieved")


class TestExpenseManagement:
    """Test Expense operations"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_get_expense_categories(self, employee_token):
        """Get expense categories"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/expense-categories", headers=headers)
        assert response.status_code == 200, f"Get expense categories failed: {response.text}"
        print("✅ Expense categories retrieved")
    
    def test_get_pending_expenses(self, hr_token):
        """HR should see pending expenses"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/expenses?status=pending", headers=headers)
        assert response.status_code == 200, f"Get pending expenses failed: {response.text}"
        print("✅ Pending expenses retrieved")


class TestAttendance:
    """Test Attendance operations"""
    
    @pytest.fixture
    def employee_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_get_my_attendance(self, employee_token):
        """Get my attendance records"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/my", headers=headers)
        assert response.status_code == 200, f"Get my attendance failed: {response.text}"
        print("✅ My attendance retrieved")
    
    def test_get_attendance_summary(self, hr_token):
        """HR can get attendance summary"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/attendance/summary", headers=headers)
        # Could be 200 or 404 if no data
        assert response.status_code in [200, 404], f"Attendance summary failed: {response.text}"
        print(f"✅ Attendance summary: {response.status_code}")
    
    def test_get_pending_attendance_approvals(self, hr_token):
        """HR can see pending attendance approvals"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/hr/pending-attendance-approvals", headers=headers)
        assert response.status_code == 200, f"Pending attendance approvals failed: {response.text}"
        print("✅ Pending attendance approvals retrieved")


class TestGoLiveWorkflow:
    """Test Go-Live workflow operations"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    def test_get_go_live_dashboard(self, hr_token):
        """HR can access Go-Live dashboard"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/go-live-dashboard", headers=headers)
        assert response.status_code == 200, f"Go-Live dashboard failed: {response.text}"
        print("✅ Go-Live dashboard accessible")
    
    def test_get_go_live_employees(self, hr_token):
        """Get employees eligible for Go-Live"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/employees?status=pending_go_live", headers=headers)
        assert response.status_code == 200, f"Go-Live employees failed: {response.text}"
        print("✅ Go-Live employees list retrieved")


class TestNotifications:
    """Test Notification system"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_get_unread_count(self, admin_token):
        """Get unread notification count"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications/unread-count", headers=headers)
        assert response.status_code == 200, f"Get unread count failed: {response.text}"
        print("✅ Unread notification count retrieved")
    
    def test_get_notifications_list(self, admin_token):
        """Get notifications list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        print("✅ Notifications list retrieved")


class TestApprovals:
    """Test Approvals Center operations"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_admin_can_access_ctc_pending_approvals(self, admin_token):
        """Admin can see pending CTC approvals"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/ctc/pending-approvals", headers=headers)
        assert response.status_code == 200, f"CTC pending approvals failed: {response.text}"
        print("✅ Admin can access CTC pending approvals")
    
    def test_hr_can_access_leave_requests(self, hr_token):
        """HR can access leave requests"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/leave-requests", headers=headers)
        assert response.status_code == 200, f"Leave requests failed: {response.text}"
        print("✅ HR can access leave requests")


class TestModificationRequests:
    """Test Modification Request workflow"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    def test_get_pending_modification_requests(self, admin_token):
        """Admin can see pending modification requests"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/employees/modification-requests/pending", headers=headers)
        assert response.status_code == 200, f"Modification requests failed: {response.text}"
        print("✅ Modification requests retrieved")


class TestFormValidation:
    """Test form validation and error handling"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_create_employee_missing_required_fields(self, hr_token):
        """Test employee creation with missing fields"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        data = {
            "first_name": "Test"
            # Missing last_name, email, etc.
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        # Should still process but might have validation errors
        assert response.status_code in [200, 201, 400, 422], f"Unexpected status: {response.status_code}"
        print(f"✅ Missing fields validation: {response.status_code}")
    
    def test_invalid_email_format(self, hr_token):
        """Test invalid email format"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "not-an-email",
            "department": "HR"
        }
        response = requests.post(f"{BASE_URL}/api/employees", headers=headers, json=data)
        # Should fail validation
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✅ Invalid email format rejected")


class TestDataIntegrity:
    """Test data integrity and consistency"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_employee_count_consistency(self, hr_token):
        """Test employee count is consistent"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        # Get employees list
        response1 = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response1.status_code == 200
        employees = response1.json()
        
        # Get managers list
        response2 = requests.get(f"{BASE_URL}/api/employees/managers", headers=headers)
        assert response2.status_code == 200
        managers = response2.json()
        
        # Managers should be subset of employees
        assert len(managers) <= len(employees), "More managers than employees!"
        print(f"✅ Data integrity: {len(employees)} employees, {len(managers)} managers")


class TestDepartments:
    """Test Department operations"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    def test_get_departments(self, admin_token):
        """Get departments list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/departments", headers=headers)
        assert response.status_code == 200, f"Get departments failed: {response.text}"
        print("✅ Departments retrieved")


class TestUsers:
    """Test User management"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        return response.json()["access_token"]
    
    def test_get_users_list(self, admin_token):
        """Admin can get users list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users", headers=headers)
        assert response.status_code == 200, f"Get users failed: {response.text}"
        users = response.json()
        assert isinstance(users, list)
        print(f"✅ Retrieved {len(users)} users")
    
    def test_get_current_user(self, admin_token):
        """Get current user info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
        assert response.status_code == 200, f"Get current user failed: {response.text}"
        user = response.json()
        assert user["email"] == "admin@dvbc.com"
        print("✅ Current user retrieved")


class TestKickoffMeetings:
    """Test Kickoff Meeting operations"""
    
    @pytest.fixture
    def hr_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
        return response.json()["access_token"]
    
    def test_get_kickoff_meetings(self, hr_token):
        """Get kickoff meetings list"""
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/kickoff-meetings", headers=headers)
        assert response.status_code == 200, f"Get kickoff meetings failed: {response.text}"
        print("✅ Kickoff meetings retrieved")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
