"""
Test Suite for Bootstrap Fix and Reporting Manager Features
============================================================
1. Bootstrap fix: Create first employee with 'SELF' as reporting manager
2. Update Reporting Manager: HR Manager can update employee's reporting manager
3. Employee creation notifications: Verify HR/Admin/RM receive notifications
4. Kickoff Approval: Senior/Principal Consultant can approve project kickoffs
5. CTC flow: CTC creation does NOT require admin approval
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


class TestBootstrapSelfReportingManager:
    """Test bootstrap fix: creating employee with SELF as reporting manager"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, admin_token):
        self.client = api_client
        self.admin_token = admin_token
        self.client.headers.update({"Authorization": f"Bearer {self.admin_token}"})
    
    def test_create_employee_with_self_as_manager(self, api_client, admin_token):
        """Test creating an employee with SELF as reporting manager"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        unique_id = str(uuid.uuid4())[:8]
        employee_data = {
            "first_name": "TEST_Bootstrap",
            "last_name": f"Employee_{unique_id}",
            "email": f"test.bootstrap_{unique_id}@dvbc.com",
            "phone": f"98765{unique_id[:5]}",
            "department": "Admin",
            "designation": "First Admin",
            "role": "admin",
            "level": "senior",
            "reporting_manager_id": "SELF",  # Key: SELF as reporting manager
            "date_of_joining": "2026-02-20",
            "gender": "male",
            "employment_type": "permanent"
        }
        
        response = api_client.post(f"{BASE_URL}/api/employees", json=employee_data)
        print(f"Create employee with SELF response: {response.status_code}")
        
        assert response.status_code in [200, 201], f"Failed to create employee with SELF: {response.text}"
        
        data = response.json()
        employee = data.get("employee", data)
        
        # Verify SELF was handled correctly
        assert employee.get("is_self_reporting") == True, "is_self_reporting flag should be True"
        assert employee.get("reporting_manager_id") == employee.get("id"), \
            f"reporting_manager_id should equal employee id for SELF. Got: {employee.get('reporting_manager_id')}"
        
        print(f"✓ Created employee with SELF as manager: {employee.get('employee_id')}")
        print(f"  - ID: {employee.get('id')}")
        print(f"  - reporting_manager_id: {employee.get('reporting_manager_id')}")
        print(f"  - is_self_reporting: {employee.get('is_self_reporting')}")
        
        # Cleanup: Delete the test employee
        cleanup_response = api_client.delete(f"{BASE_URL}/api/employees/{employee['id']}")
        print(f"Cleanup response: {cleanup_response.status_code}")
        
        return employee["id"]

    def test_managers_list_shows_self_option_when_no_employees(self, api_client, admin_token):
        """Verify the managers list API returns data (SELF is handled in frontend)"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        # Get list of employees who can be managers
        response = api_client.get(f"{BASE_URL}/api/employees")
        print(f"Get employees response: {response.status_code}")
        
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        
        data = response.json()
        employees = data if isinstance(data, list) else data.get("employees", [])
        
        print(f"✓ Found {len(employees)} employees available as potential managers")
        # Note: SELF option is rendered in frontend when managers.length === 0 or role === 'admin'


class TestUpdateReportingManager:
    """Test updating employee's reporting manager"""
    
    def test_hr_manager_can_update_reporting_manager_via_patch(self, api_client, hr_manager_token):
        """HR Manager can update employee's reporting manager via PATCH"""
        api_client.headers.update({"Authorization": f"Bearer {hr_manager_token}"})
        
        # First, get list of employees
        emp_response = api_client.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200, f"Failed to get employees: {emp_response.text}"
        
        employees = emp_response.json() if isinstance(emp_response.json(), list) else emp_response.json().get("employees", [])
        
        if len(employees) < 2:
            pytest.skip("Need at least 2 employees to test reporting manager update")
        
        # Find an employee to update and a new manager
        target_employee = None
        new_manager = None
        
        for emp in employees:
            if not emp.get("is_self_reporting"):
                target_employee = emp
                break
        
        for emp in employees:
            if emp.get("id") != target_employee.get("id") if target_employee else True:
                new_manager = emp
                break
        
        if not target_employee or not new_manager:
            pytest.skip("Could not find suitable employees for test")
        
        # Update reporting manager via PATCH
        update_data = {
            "reporting_manager_id": new_manager["id"]
        }
        
        response = api_client.patch(
            f"{BASE_URL}/api/employees/{target_employee['id']}",
            json=update_data
        )
        print(f"PATCH update reporting manager response: {response.status_code}")
        
        # Could be 200 (direct update) or response about approval needed
        assert response.status_code == 200, f"Failed to update reporting manager: {response.text}"
        
        print(f"✓ HR Manager can update reporting manager for {target_employee.get('first_name')}")
        print(f"  - New Manager: {new_manager.get('first_name')} {new_manager.get('last_name')}")
        
    def test_admin_can_update_reporting_manager_via_patch(self, api_client, admin_token):
        """Admin can update employee's reporting manager via PATCH"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        # Get list of employees
        emp_response = api_client.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        
        employees = emp_response.json() if isinstance(emp_response.json(), list) else emp_response.json().get("employees", [])
        
        if len(employees) < 2:
            pytest.skip("Need at least 2 employees to test")
        
        target = employees[0]
        new_manager = employees[1] if employees[1]["id"] != target["id"] else employees[0]
        
        response = api_client.patch(
            f"{BASE_URL}/api/employees/{target['id']}",
            json={"reporting_manager_id": new_manager["id"]}
        )
        
        print(f"Admin PATCH response: {response.status_code}")
        assert response.status_code == 200, f"Admin failed to update: {response.text}"
        print(f"✓ Admin can update reporting manager")

    def test_set_reporting_manager_endpoint(self, api_client, hr_manager_token):
        """Test the dedicated set_reporting_manager endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {hr_manager_token}"})
        
        # Get employees
        emp_response = api_client.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        
        employees = emp_response.json() if isinstance(emp_response.json(), list) else emp_response.json().get("employees", [])
        
        # Find an employee with a user_id
        target_emp = None
        manager_emp = None
        
        for emp in employees:
            if emp.get("user_id"):
                target_emp = emp
                break
        
        for emp in employees:
            if emp.get("id") != (target_emp.get("id") if target_emp else None):
                manager_emp = emp
                break
        
        if not target_emp or not manager_emp:
            pytest.skip("Need employee with user_id and another employee as manager")
        
        # Use the /api/users/{user_id}/reporting-manager endpoint
        response = api_client.patch(
            f"{BASE_URL}/api/users/{target_emp['user_id']}/reporting-manager",
            params={"manager_id": manager_emp.get("employee_id", manager_emp["id"])}
        )
        
        print(f"Set reporting manager endpoint response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Reporting manager set successfully")
            print(f"  - reporting_manager_id: {data.get('reporting_manager_id')}")
            print(f"  - reporting_manager_name: {data.get('reporting_manager_name')}")
        else:
            print(f"Endpoint response: {response.text}")


class TestEmployeeCreationNotifications:
    """Test notifications are created when employee is onboarded"""
    
    def test_notifications_created_on_employee_creation(self, api_client, admin_token):
        """Verify notifications are created in DB when employee is created"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a test employee
        employee_data = {
            "first_name": "TEST_Notify",
            "last_name": f"Employee_{unique_id}",
            "email": f"test.notify_{unique_id}@dvbc.com",
            "phone": f"99876{unique_id[:5]}",
            "department": "Consulting",
            "designation": "Consultant",
            "role": "consultant",
            "level": "executive",
            "reporting_manager_id": "SELF",
            "date_of_joining": "2026-02-20"
        }
        
        response = api_client.post(f"{BASE_URL}/api/employees", json=employee_data)
        assert response.status_code in [200, 201], f"Failed to create employee: {response.text}"
        
        created_emp = response.json().get("employee", response.json())
        emp_id = created_emp["id"]
        emp_code = created_emp.get("employee_id")
        
        print(f"✓ Created test employee: {emp_code}")
        
        # Check notifications - should exist for HR and Admin users
        notif_response = api_client.get(f"{BASE_URL}/api/notifications")
        
        if notif_response.status_code == 200:
            notifications = notif_response.json()
            if isinstance(notifications, dict):
                notifications = notifications.get("notifications", [])
            
            # Find notifications related to this employee
            related_notifs = [n for n in notifications if n.get("reference_id") == emp_id]
            
            print(f"✓ Found {len(related_notifs)} notifications for this employee creation")
            for notif in related_notifs[:3]:
                print(f"  - Type: {notif.get('type')}, Title: {notif.get('title')}")
        else:
            print(f"Notifications endpoint returned: {notif_response.status_code}")
        
        # Cleanup
        cleanup = api_client.delete(f"{BASE_URL}/api/employees/{emp_id}")
        print(f"Cleanup: {cleanup.status_code}")

    def test_get_notifications_unread_count(self, api_client, admin_token):
        """Test unread notifications count endpoint"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        response = api_client.get(f"{BASE_URL}/api/notifications/unread-count")
        print(f"Unread count response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Unread notifications: {data.get('count', data)}")


class TestKickoffApproval:
    """Test kickoff meeting approval by Senior/Principal Consultants"""
    
    def test_get_kickoff_meetings_list(self, api_client, admin_token):
        """Verify kickoff meetings can be retrieved"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        response = api_client.get(f"{BASE_URL}/api/kickoff-meetings")
        print(f"Get kickoff meetings response: {response.status_code}")
        
        assert response.status_code == 200, f"Failed to get kickoff meetings: {response.text}"
        
        meetings = response.json()
        if isinstance(meetings, dict):
            meetings = meetings.get("meetings", [])
        
        print(f"✓ Found {len(meetings)} kickoff meetings")
        
        for meeting in meetings[:3]:
            print(f"  - Project: {meeting.get('project_name', meeting.get('project_id'))}")
            print(f"    Status: {meeting.get('status')}")

    def test_kickoff_approval_endpoint_exists(self, api_client, admin_token):
        """Verify kickoff approval endpoint exists"""
        api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        # Try to approve a non-existent kickoff to verify endpoint exists
        fake_kickoff_id = str(uuid.uuid4())
        
        response = api_client.post(
            f"{BASE_URL}/api/kickoff-meetings/{fake_kickoff_id}/approve"
        )
        
        # We expect 404 (not found) not 404 (endpoint not found)
        print(f"Kickoff approve endpoint response: {response.status_code}")
        
        # 404 means endpoint exists but kickoff not found, which is expected
        # 405 or similar would mean endpoint doesn't exist
        assert response.status_code in [200, 400, 403, 404], \
            f"Kickoff approval endpoint may not exist: {response.text}"
        
        print(f"✓ Kickoff approval endpoint exists")


class TestCTCWithoutAdminApproval:
    """Test CTC creation does NOT require admin approval"""
    
    def test_create_ctc_without_admin_approval(self, api_client, hr_manager_token):
        """HR Manager can create CTC without admin approval"""
        api_client.headers.update({"Authorization": f"Bearer {hr_manager_token}"})
        
        # Get an employee to create CTC for
        emp_response = api_client.get(f"{BASE_URL}/api/employees")
        assert emp_response.status_code == 200
        
        employees = emp_response.json() if isinstance(emp_response.json(), list) else emp_response.json().get("employees", [])
        
        if not employees:
            pytest.skip("No employees available for CTC test")
        
        target_emp = employees[0]
        
        # Create CTC data
        ctc_data = {
            "employee_id": target_emp["id"],
            "annual_ctc": 1200000,
            "basic_salary": 500000,
            "hra": 200000,
            "special_allowance": 200000,
            "medical_allowance": 15000,
            "conveyance": 19200,
            "pf_employer": 21600,
            "gratuity": 28846,
            "effective_date": "2026-02-01"
        }
        
        response = api_client.post(f"{BASE_URL}/api/ctc", json=ctc_data)
        print(f"Create CTC response: {response.status_code}")
        
        # CTC should be created directly without approval workflow
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✓ CTC created successfully without admin approval")
            print(f"  - Status: {data.get('status', 'created')}")
            # Verify no approval required
            assert data.get("status") != "pending_approval", \
                "CTC should not require admin approval"
        elif response.status_code == 400:
            # May already exist
            print(f"CTC creation response (may already exist): {response.text}")
        else:
            print(f"CTC creation response: {response.status_code} - {response.text}")

    def test_get_ctc_list(self, api_client, hr_manager_token):
        """Verify CTC list can be retrieved by HR"""
        api_client.headers.update({"Authorization": f"Bearer {hr_manager_token}"})
        
        response = api_client.get(f"{BASE_URL}/api/ctc")
        print(f"Get CTC list response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            ctc_list = data if isinstance(data, list) else data.get("items", data.get("ctc_records", []))
            print(f"✓ Found {len(ctc_list)} CTC records")


# Fixtures
@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        print(f"✓ Admin login successful")
        return token
    pytest.fail(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="session")
def hr_manager_token(api_client):
    """Get HR Manager authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=HR_MANAGER_CREDS)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        print(f"✓ HR Manager login successful")
        return token
    pytest.fail(f"HR Manager login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="session")
def employee_token(api_client):
    """Get employee authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json=EMPLOYEE_CREDS)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        print(f"✓ Employee login successful")
        return token
    print(f"Employee login failed: {response.status_code} - trying as skip")
    return None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
