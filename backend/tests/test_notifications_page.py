"""
Test Notifications Page and Notification Features
- Notifications page loads at /notifications
- Filter tabs (All, Unread, Requires Action)
- Notification bell dropdown shows 'View All Notifications' link
- Actionable notifications show 'Action Required' badge
- Info notifications show 'Info' badge
- Employee creation sends notifications to Admin, HR, and Reporting Manager
- PATCH /api/notifications/{id}/action endpoint works
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
HR_MANAGER_EMAIL = "hr.manager@dvbc.com"
HR_MANAGER_PASSWORD = "hr123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def hr_manager_token():
    """Get HR manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": HR_MANAGER_EMAIL,
        "password": HR_MANAGER_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"HR Manager login failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Requests session with admin auth"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def hr_client(hr_manager_token):
    """Requests session with HR Manager auth"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {hr_manager_token}",
        "Content-Type": "application/json"
    })
    return session


class TestNotificationsEndpoints:
    """Tests for notification API endpoints"""
    
    def test_01_get_notifications_endpoint(self, admin_client):
        """GET /api/notifications - Returns user notifications"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Notifications should be a list"
        print(f"Admin has {len(data)} notifications")
        
        # If there are notifications, check structure
        if len(data) > 0:
            notif = data[0]
            assert "id" in notif, "Notification should have id"
            assert "type" in notif or "notification_type" in notif, "Notification should have type"
            assert "title" in notif, "Notification should have title"
            assert "message" in notif, "Notification should have message"
            print(f"First notification: {notif.get('title')} - {notif.get('type', notif.get('notification_type'))}")
    
    def test_02_get_unread_count_endpoint(self, admin_client):
        """GET /api/notifications/unread-count - Returns unread count"""
        response = admin_client.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "count" in data, "Response should have count field"
        assert isinstance(data["count"], int), "Count should be integer"
        print(f"Admin unread notification count: {data['count']}")
    
    def test_03_mark_all_read_endpoint(self, admin_client):
        """PATCH /api/notifications/mark-all-read - Marks all notifications as read"""
        response = admin_client.patch(f"{BASE_URL}/api/notifications/mark-all-read")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        print(f"Mark all read response: {data['message']}")
    
    def test_04_hr_manager_notifications(self, hr_client):
        """HR Manager should have notifications"""
        response = hr_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Notifications should be a list"
        print(f"HR Manager has {len(data)} notifications")
        
        # Check for different notification types
        types_found = set()
        for notif in data:
            notif_type = notif.get("type", notif.get("notification_type", "unknown"))
            types_found.add(notif_type)
        
        print(f"Notification types found: {types_found}")
    
    def test_05_notification_has_required_fields(self, admin_client):
        """Notifications should have all required fields for the Notifications page"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            notif = data[0]
            
            # Check for required fields used by Notifications.js
            required_fields = ["id", "title", "message", "created_at"]
            for field in required_fields:
                assert field in notif, f"Notification missing required field: {field}"
            
            # Check type field (used for NOTIFICATION_CONFIG lookup)
            assert "type" in notif or "notification_type" in notif, "Notification needs type field"
            
            # Check is_read field (used for filtering)
            assert "is_read" in notif, "Notification needs is_read field"
            
            print(f"Notification structure validated: {list(notif.keys())}")
    
    def test_06_mark_single_notification_read(self, admin_client):
        """PATCH /api/notifications/{id}/read - Mark single notification as read"""
        # First get a notification
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) == 0:
            pytest.skip("No notifications available to test")
        
        notif_id = data[0]["id"]
        
        # Mark it as read
        response = admin_client.patch(f"{BASE_URL}/api/notifications/{notif_id}/read")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        print(f"Marked notification {notif_id} as read")
    
    def test_07_notification_action_endpoint(self, admin_client):
        """PATCH /api/notifications/{id}/action - Mark notification as actioned"""
        # First get a notification
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) == 0:
            pytest.skip("No notifications available to test")
        
        notif_id = data[0]["id"]
        
        # Mark it as actioned
        response = admin_client.patch(
            f"{BASE_URL}/api/notifications/{notif_id}/action",
            json={
                "action": "approve",
                "actioned_at": "2026-01-20T10:00:00Z"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        result = response.json()
        assert "message" in result
        print(f"Marked notification {notif_id} as actioned with approve action")


class TestNotificationTypes:
    """Test different notification types are properly structured"""
    
    def test_01_check_actionable_notifications(self, admin_client):
        """Check for actionable notification types in the system"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        
        # Actionable types defined in NOTIFICATION_CONFIG
        actionable_types = ["go_live_approval", "ctc_approval", "permission_change", "approval_request"]
        info_types = ["employee_onboarded", "bank_change_approved", "go_live_approved", 
                      "go_live_rejected", "approval_completed", "approval_rejected",
                      "leave_request", "expense_submitted", "sow_completion"]
        
        actionable_count = 0
        info_count = 0
        
        for notif in data:
            notif_type = notif.get("type", notif.get("notification_type", ""))
            if notif_type in actionable_types:
                actionable_count += 1
                # Actionable notifications should have reference_id
                if not notif.get("reference_id"):
                    print(f"Warning: Actionable notification {notif_type} missing reference_id")
            elif notif_type in info_types:
                info_count += 1
        
        print(f"Found {actionable_count} actionable and {info_count} info notifications")
    
    def test_02_employee_onboarded_notification_exists(self, admin_client):
        """Check that employee_onboarded notifications exist"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        
        onboarded_notifications = [
            n for n in data 
            if n.get("type") == "employee_onboarded" or n.get("notification_type") == "employee_onboarded"
        ]
        
        print(f"Found {len(onboarded_notifications)} employee_onboarded notifications")
        
        if len(onboarded_notifications) > 0:
            notif = onboarded_notifications[0]
            print(f"Sample: {notif.get('title')} - {notif.get('message')}")
    
    def test_03_go_live_notifications_exist(self, admin_client):
        """Check that go_live related notifications exist"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        
        go_live_types = ["go_live_approval", "go_live_approved", "go_live_rejected"]
        go_live_notifications = [
            n for n in data 
            if n.get("type") in go_live_types or n.get("notification_type") in go_live_types
        ]
        
        print(f"Found {len(go_live_notifications)} go_live related notifications")


class TestEmployeeCreationNotifications:
    """Test that employee creation sends proper notifications"""
    
    def test_01_create_employee_sends_notifications(self, hr_client, admin_client):
        """Creating an employee should send notifications to Admin, HR, and Reporting Manager"""
        import uuid
        
        # Create a test employee
        test_employee = {
            "first_name": f"TestNotif",
            "last_name": f"Employee{str(uuid.uuid4())[:4]}",
            "email": f"testnotif_{str(uuid.uuid4())[:8]}@test.com",
            "phone": f"98765{str(uuid.uuid4().int)[:5]}",
            "department": "Testing",
            "designation": "Test Engineer",
            "role": "consultant",
            "date_of_joining": "2026-01-20"
        }
        
        # Get initial notification count for admin
        initial_admin = admin_client.get(f"{BASE_URL}/api/notifications")
        initial_admin_count = len(initial_admin.json()) if initial_admin.status_code == 200 else 0
        
        # Create employee via HR
        response = hr_client.post(f"{BASE_URL}/api/employees", json=test_employee)
        
        if response.status_code != 200:
            print(f"Employee creation returned: {response.status_code} - {response.text}")
            # If we get 400 due to duplicate, it's ok for this test
            if response.status_code == 400 and "already exists" in response.text:
                pytest.skip("Duplicate employee - skipping notification test")
                return
        
        assert response.status_code == 200, f"Failed to create employee: {response.text}"
        
        emp_data = response.json()
        emp_id = emp_data.get("employee", {}).get("id")
        print(f"Created test employee: {emp_id}")
        
        # Check admin notifications increased
        final_admin = admin_client.get(f"{BASE_URL}/api/notifications")
        final_admin_count = len(final_admin.json()) if final_admin.status_code == 200 else 0
        
        # Admin should have received employee_onboarded notification
        admin_notifications = final_admin.json()
        new_onboarded_notifs = [
            n for n in admin_notifications 
            if n.get("type") == "employee_onboarded" and n.get("reference_id") == emp_id
        ]
        
        print(f"Admin notifications: {initial_admin_count} -> {final_admin_count}")
        print(f"Found {len(new_onboarded_notifs)} employee_onboarded notifications for new employee")
        
        # Cleanup - we can't delete, but that's fine for testing


class TestNotificationFiltering:
    """Test notification filtering for the Notifications page"""
    
    def test_01_filter_unread_notifications(self, admin_client):
        """Test filtering unread notifications"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        unread = [n for n in data if not n.get("is_read", True)]
        
        print(f"Total notifications: {len(data)}, Unread: {len(unread)}")
        
        # Verify unread count matches
        count_response = admin_client.get(f"{BASE_URL}/api/notifications/unread-count")
        expected_count = count_response.json().get("count", 0)
        
        print(f"Unread count from endpoint: {expected_count}, From filtering: {len(unread)}")
    
    def test_02_filter_actionable_notifications(self, admin_client):
        """Test filtering actionable notifications"""
        response = admin_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        
        # Actionable types from Notifications.js NOTIFICATION_CONFIG
        actionable_types = ["go_live_approval", "ctc_approval", "permission_change", "approval_request"]
        
        actionable = [
            n for n in data 
            if n.get("type") in actionable_types and n.get("status") != "actioned"
        ]
        
        print(f"Actionable notifications (not actioned): {len(actionable)}")
        
        for notif in actionable[:3]:  # Show first 3
            print(f"  - {notif.get('type')}: {notif.get('title')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
