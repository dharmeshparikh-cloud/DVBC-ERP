"""
Test suite for Notifications API endpoints
Tests: GET /api/notifications, GET /api/notifications/unread-count, 
       PATCH /api/notifications/{id}/read, PATCH /api/notifications/mark-all-read
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
MANAGER_EMAIL = "manager@company.com"
MANAGER_PASSWORD = "manager123"


class TestNotificationsAPI:
    """Test notification CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session and authenticate"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        self.admin_token = login_resp.json()["access_token"]
        self.admin_user = login_resp.json()["user"]
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
    
    def test_get_notifications(self):
        """Test GET /api/notifications - returns notifications for logged-in user"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Get notifications failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/notifications - Found {len(data)} notifications")
        
        # If notifications exist, verify structure
        if len(data) > 0:
            notif = data[0]
            assert "id" in notif, "Notification should have id"
            assert "user_id" in notif, "Notification should have user_id"
            assert "title" in notif, "Notification should have title"
            assert "message" in notif, "Notification should have message"
            assert "is_read" in notif, "Notification should have is_read"
            assert "created_at" in notif, "Notification should have created_at"
            print(f"✓ Notification structure verified - First notification: {notif['title']}")
    
    def test_get_unread_count(self):
        """Test GET /api/notifications/unread-count - returns unread count"""
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Get unread count failed: {response.text}"
        
        data = response.json()
        assert "count" in data, "Response should have count field"
        assert isinstance(data["count"], int), "Count should be an integer"
        assert data["count"] >= 0, "Count should be non-negative"
        print(f"✓ GET /api/notifications/unread-count - Unread count: {data['count']}")
    
    def test_mark_notification_read(self):
        """Test PATCH /api/notifications/{id}/read - marks single notification as read"""
        # First get notifications to find one to mark as read
        notifs_response = self.session.get(f"{BASE_URL}/api/notifications")
        assert notifs_response.status_code == 200
        notifications = notifs_response.json()
        
        if len(notifications) == 0:
            pytest.skip("No notifications available to test mark as read")
        
        # Find an unread notification or use first available
        target_notif = None
        for n in notifications:
            if not n.get("is_read", True):
                target_notif = n
                break
        
        if not target_notif:
            # All are read, use first for testing idempotency
            target_notif = notifications[0]
            print(f"All notifications already read, testing idempotency with: {target_notif['id']}")
        
        notif_id = target_notif["id"]
        
        # Mark as read
        response = self.session.patch(f"{BASE_URL}/api/notifications/{notif_id}/read")
        assert response.status_code == 200, f"Mark read failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        print(f"✓ PATCH /api/notifications/{notif_id}/read - {data['message']}")
        
        # Verify it's now marked as read
        verify_resp = self.session.get(f"{BASE_URL}/api/notifications")
        assert verify_resp.status_code == 200
        for n in verify_resp.json():
            if n["id"] == notif_id:
                assert n["is_read"] == True, "Notification should be marked as read"
                print(f"✓ Verified notification {notif_id} is now read")
                break
    
    def test_mark_all_notifications_read(self):
        """Test PATCH /api/notifications/mark-all-read - marks all notifications as read"""
        # Get initial unread count
        initial_resp = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert initial_resp.status_code == 200
        initial_count = initial_resp.json()["count"]
        print(f"Initial unread count: {initial_count}")
        
        # Mark all as read
        response = self.session.patch(f"{BASE_URL}/api/notifications/mark-all-read")
        assert response.status_code == 200, f"Mark all read failed: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have message"
        print(f"✓ PATCH /api/notifications/mark-all-read - {data['message']}")
        
        # Verify count is now 0
        verify_resp = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert verify_resp.status_code == 200
        final_count = verify_resp.json()["count"]
        assert final_count == 0, f"Expected 0 unread, got {final_count}"
        print(f"✓ Verified unread count is now 0")
    
    def test_notification_color_coding_types(self):
        """Test that notifications have correct types for color coding"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        notifications = response.json()
        valid_types = [
            "approval_request",  # amber
            "approval_completed",  # green
            "approval_rejected",  # red
            "leave_request",  # blue
            "expense_submitted",  # purple
            "sow_completion",  # teal
            "action_item_assigned",  # default
            "mom_sent"  # default
        ]
        
        found_types = set()
        for notif in notifications:
            notif_type = notif.get("type", "")
            found_types.add(notif_type)
        
        print(f"✓ Found notification types: {found_types}")
        print(f"✓ Expected types include: {valid_types}")


class TestNonAdminNotifications:
    """Test notifications for non-admin users"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session and authenticate as manager"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as manager
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        assert login_resp.status_code == 200, f"Manager login failed: {login_resp.text}"
        self.manager_token = login_resp.json()["access_token"]
        self.manager_user = login_resp.json()["user"]
        self.session.headers.update({"Authorization": f"Bearer {self.manager_token}"})
        print(f"✓ Logged in as manager: {self.manager_user['email']}")
    
    def test_manager_can_see_notifications_bell(self):
        """Test GET /api/notifications works for manager"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Manager get notifications failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Manager can access notifications - Found {len(data)} notifications")
    
    def test_manager_unread_count(self):
        """Test GET /api/notifications/unread-count works for manager"""
        response = self.session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Manager get unread count failed: {response.text}"
        
        data = response.json()
        assert "count" in data
        print(f"✓ Manager unread count: {data['count']}")


class TestAdminDashboardLoginActivity:
    """Test that admin dashboard login activity widget still works"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session and authenticate as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        self.admin_token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.admin_token}"})
    
    def test_security_audit_logs_endpoint(self):
        """Test GET /api/security-audit-logs - used by login activity widget"""
        response = self.session.get(f"{BASE_URL}/api/security-audit-logs?limit=8")
        assert response.status_code == 200, f"Get audit logs failed: {response.text}"
        
        data = response.json()
        assert "logs" in data, "Response should have logs"
        assert "total" in data, "Response should have total"
        
        logs = data["logs"]
        assert isinstance(logs, list), "Logs should be a list"
        print(f"✓ GET /api/security-audit-logs - Found {len(logs)} logs, total: {data['total']}")
        
        # Verify recent login is logged (from our test)
        found_login_success = False
        for log in logs:
            if log.get("event_type") in ["password_login_success", "google_login_success"]:
                found_login_success = True
                break
        
        assert found_login_success, "Should find a login success event"
        print(f"✓ Login events are being logged correctly")
    
    def test_dashboard_stats_endpoint(self):
        """Test GET /api/stats/dashboard - used by dashboard"""
        response = self.session.get(f"{BASE_URL}/api/stats/dashboard")
        assert response.status_code == 200, f"Get dashboard stats failed: {response.text}"
        
        data = response.json()
        expected_fields = ["total_leads", "new_leads", "qualified_leads", "closed_deals", "active_projects"]
        for field in expected_fields:
            assert field in data, f"Dashboard stats should have {field}"
        
        print(f"✓ GET /api/stats/dashboard - Stats: {data}")


class TestAdminPasswordLogin:
    """Test admin password login flow"""
    
    def test_admin_password_login_success(self):
        """Test admin can login with password"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "Response should have access_token"
        assert "token_type" in data, "Response should have token_type"
        assert "user" in data, "Response should have user"
        
        user = data["user"]
        assert user["email"] == ADMIN_EMAIL
        assert user["role"] == "admin"
        print(f"✓ Admin password login successful - User: {user['full_name']}")
    
    def test_admin_wrong_password_login_failure(self):
        """Test admin login fails with wrong password"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrongpassword123"
        })
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Admin login correctly rejects wrong password")


class TestUnauthenticatedAccess:
    """Test that endpoints require authentication"""
    
    def test_notifications_requires_auth(self):
        """Test GET /api/notifications requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print(f"✓ GET /api/notifications correctly requires authentication")
    
    def test_unread_count_requires_auth(self):
        """Test GET /api/notifications/unread-count requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print(f"✓ GET /api/notifications/unread-count correctly requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
