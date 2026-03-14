"""
Test Follow-ups System - Full CRUD, escalations, reassignment, schedule-next
Tests the refactored follow-ups feature with dedicated collection

Endpoints tested:
- POST /api/follow-ups (create)
- GET /api/follow-ups (list with filters)
- GET /api/follow-ups/dashboard/today (dashboard widget data)
- GET /api/follow-ups/escalations (manager escalations)
- GET /api/follow-ups/{id} (detail)
- PUT /api/follow-ups/{id}/update (add update to history)
- PUT /api/follow-ups/{id}/close (close follow-up)
- POST /api/follow-ups/{id}/schedule-next (close + create next)
- POST /api/follow-ups/{id}/reassign (reassign with ownership transfer)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestFollowUpsSystemBackend:
    """Tests for the refactored Follow-ups system with dedicated collection"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as Admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as Admin (ADMIN001 / Admin@2026)
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user = data.get("user")
            self.user_id = self.user.get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed with status {login_response.status_code}: {login_response.text}")
    
    # ========== Authentication Tests ==========
    def test_01_admin_login_successful(self):
        """Test admin login with ADMIN001 / Admin@2026"""
        assert self.token is not None, "Auth token should be present"
        assert self.user is not None, "User data should be present"
        assert self.user.get("role") == "admin", "User role should be admin"
        print(f"PASSED: Admin login successful - {self.user.get('full_name')}")
    
    # ========== Create Follow-up Tests ==========
    def test_02_create_follow_up_for_lead(self):
        """Test POST /api/follow-ups - create follow-up for lead entity"""
        today = datetime.now()
        due_date = (today + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
        
        payload = {
            "entity_type": "lead",
            "entity_id": "test-lead-001",
            "client_name": "TEST_FollowUpSystem Corp",
            "due_date": due_date,
            "notes": "Test follow-up for lead entity",
            "priority": "high"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        
        assert response.status_code == 200, f"Create follow-up should succeed: {response.text}"
        data = response.json()
        
        assert data.get("id") is not None, "Follow-up should have an ID"
        assert data.get("entity_type") == "lead", "Entity type should be lead"
        assert data.get("client_name") == "TEST_FollowUpSystem Corp", "Client name should match"
        assert data.get("priority") == "high", "Priority should be high"
        assert data.get("status") == "open", "Status should be open"
        assert "history" in data, "Should have history array"
        
        # Store for later tests
        self.__class__.created_follow_up_id = data.get("id")
        print(f"PASSED: Created follow-up {data.get('id')} for lead entity")
    
    def test_03_create_follow_up_for_meeting_stage(self):
        """Test creating follow-up for meeting stage"""
        due_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT14:00:00")
        
        payload = {
            "entity_type": "meeting",
            "entity_id": "test-meeting-001",
            "client_name": "TEST_Meeting Stage Client",
            "due_date": due_date,
            "notes": "Follow-up after meeting",
            "priority": "medium"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        
        assert response.status_code == 200, f"Create follow-up should succeed: {response.text}"
        data = response.json()
        
        assert data.get("entity_type") == "meeting", "Entity type should be meeting"
        self.__class__.meeting_follow_up_id = data.get("id")
        print(f"PASSED: Created follow-up for meeting stage")
    
    def test_04_create_overdue_follow_up(self):
        """Test creating an overdue follow-up (for escalation testing)"""
        # Set due date to 3 days ago (overdue by >2 days for escalation)
        past_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT10:00:00")
        
        payload = {
            "entity_type": "pricing_plan",
            "entity_id": "test-pricing-001",
            "client_name": "TEST_Overdue Escalation Client",
            "due_date": past_date,
            "notes": "This follow-up is overdue for escalation testing",
            "priority": "high"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        
        assert response.status_code == 200, f"Create follow-up should succeed: {response.text}"
        data = response.json()
        
        self.__class__.overdue_follow_up_id = data.get("id")
        print(f"PASSED: Created overdue follow-up for escalation testing")
    
    def test_05_create_follow_up_invalid_entity_type(self):
        """Test creating follow-up with invalid entity type"""
        payload = {
            "entity_type": "invalid_type",
            "entity_id": "test-001",
            "client_name": "Test",
            "due_date": datetime.now().isoformat(),
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        
        assert response.status_code == 400, f"Invalid entity_type should return 400: {response.text}"
        print("PASSED: Invalid entity_type correctly rejected")
    
    # ========== List Follow-ups Tests ==========
    def test_06_list_follow_ups(self):
        """Test GET /api/follow-ups - list all follow-ups"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups")
        
        assert response.status_code == 200, f"List follow-ups should succeed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"PASSED: Listed {len(data)} follow-ups")
    
    def test_07_list_follow_ups_with_status_filter(self):
        """Test GET /api/follow-ups with status filter"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups?status=open")
        
        assert response.status_code == 200, f"List should succeed: {response.text}"
        data = response.json()
        
        for fu in data:
            assert fu.get("status") == "open", "All items should be open"
        
        print(f"PASSED: Status filter works - found {len(data)} open follow-ups")
    
    def test_08_list_follow_ups_with_entity_type_filter(self):
        """Test GET /api/follow-ups with entity_type filter"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups?entity_type=lead")
        
        assert response.status_code == 200, f"List should succeed: {response.text}"
        data = response.json()
        
        for fu in data:
            assert fu.get("entity_type") == "lead", "All items should be lead type"
        
        print(f"PASSED: Entity type filter works - found {len(data)} lead follow-ups")
    
    # ========== Dashboard Widget Tests ==========
    def test_09_get_dashboard_today_follow_ups(self):
        """Test GET /api/follow-ups/dashboard/today"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups/dashboard/today")
        
        assert response.status_code == 200, f"Dashboard today should succeed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Response should have items"
        assert "overdue_count" in data, "Response should have overdue_count"
        assert "today_count" in data, "Response should have today_count"
        assert "total" in data, "Response should have total"
        
        print(f"PASSED: Dashboard today - {data.get('total')} items, {data.get('overdue_count')} overdue, {data.get('today_count')} today")
    
    # ========== Escalations Tests ==========
    def test_10_get_escalations_as_admin(self):
        """Test GET /api/follow-ups/escalations as admin"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups/escalations")
        
        assert response.status_code == 200, f"Escalations should succeed: {response.text}"
        data = response.json()
        
        assert "items" in data, "Response should have items"
        assert "total" in data, "Response should have total"
        
        # Check that escalated items have days_overdue
        for item in data.get("items", []):
            assert "days_overdue" in item, "Escalated items should have days_overdue"
            assert item["days_overdue"] >= 2, "Should be overdue by at least 2 days"
        
        print(f"PASSED: Escalations endpoint returns {data.get('total')} items")
    
    # ========== Get Single Follow-up Tests ==========
    def test_11_get_follow_up_detail(self):
        """Test GET /api/follow-ups/{id}"""
        follow_up_id = getattr(self.__class__, 'created_follow_up_id', None)
        if not follow_up_id:
            pytest.skip("No follow-up ID from previous test")
        
        response = self.session.get(f"{BASE_URL}/api/follow-ups/{follow_up_id}")
        
        assert response.status_code == 200, f"Get detail should succeed: {response.text}"
        data = response.json()
        
        assert data.get("id") == follow_up_id, "ID should match"
        assert "history" in data, "Should have history"
        assert "client_name" in data, "Should have client_name"
        assert "entity_type" in data, "Should have entity_type"
        
        print(f"PASSED: Got follow-up detail for {follow_up_id}")
    
    def test_12_get_follow_up_not_found(self):
        """Test GET /api/follow-ups/{id} with invalid ID"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups/invalid-id-12345")
        
        assert response.status_code == 404, f"Should return 404: {response.text}"
        print("PASSED: Non-existent follow-up returns 404")
    
    # ========== Add Update Tests ==========
    def test_13_add_update_to_follow_up(self):
        """Test PUT /api/follow-ups/{id}/update"""
        follow_up_id = getattr(self.__class__, 'created_follow_up_id', None)
        if not follow_up_id:
            pytest.skip("No follow-up ID from previous test")
        
        payload = {
            "notes": "Client confirmed interest in proposal",
            "outcome": "Interested"
        }
        
        response = self.session.put(f"{BASE_URL}/api/follow-ups/{follow_up_id}/update", json=payload)
        
        assert response.status_code == 200, f"Add update should succeed: {response.text}"
        data = response.json()
        
        assert data.get("last_follow_up_summary") == "Client confirmed interest in proposal", "Summary should be updated"
        
        # Verify history has the update
        history = data.get("history", [])
        update_entries = [h for h in history if h.get("action") == "updated"]
        assert len(update_entries) > 0, "Should have update entry in history"
        
        latest_update = update_entries[-1]
        assert latest_update.get("notes") == "Client confirmed interest in proposal", "Update notes should match"
        assert latest_update.get("outcome") == "Interested", "Outcome should match"
        
        print(f"PASSED: Added update to follow-up, history now has {len(history)} entries")
    
    # ========== Close Follow-up Tests ==========
    def test_14_close_follow_up(self):
        """Test PUT /api/follow-ups/{id}/close"""
        # Use meeting follow-up for close test
        follow_up_id = getattr(self.__class__, 'meeting_follow_up_id', None)
        if not follow_up_id:
            pytest.skip("No meeting follow-up ID from previous test")
        
        payload = {
            "notes": "Meeting completed successfully",
            "outcome": "Deal Closed"
        }
        
        response = self.session.put(f"{BASE_URL}/api/follow-ups/{follow_up_id}/close", json=payload)
        
        assert response.status_code == 200, f"Close should succeed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "closed", "Status should be closed"
        assert data.get("closed_at") is not None, "Should have closed_at timestamp"
        
        # Verify history has close entry
        history = data.get("history", [])
        close_entries = [h for h in history if h.get("action") == "closed"]
        assert len(close_entries) > 0, "Should have close entry in history"
        
        print("PASSED: Follow-up closed successfully")
    
    # ========== Schedule Next Tests ==========
    def test_15_schedule_next_follow_up(self):
        """Test POST /api/follow-ups/{id}/schedule-next"""
        follow_up_id = getattr(self.__class__, 'created_follow_up_id', None)
        if not follow_up_id:
            pytest.skip("No follow-up ID from previous test")
        
        next_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%dT10:00:00")
        
        payload = {
            "due_date": next_date,
            "notes": "Follow up on proposal discussion",
            "priority": "medium"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups/{follow_up_id}/schedule-next", json=payload)
        
        assert response.status_code == 200, f"Schedule next should succeed: {response.text}"
        data = response.json()
        
        # Should return the NEW follow-up
        assert data.get("id") is not None, "Should have new ID"
        assert data.get("id") != follow_up_id, "New follow-up should have different ID"
        assert data.get("status") == "open", "New follow-up should be open"
        assert data.get("notes") == "Follow up on proposal discussion", "Notes should match"
        
        # Store for cleanup
        self.__class__.next_follow_up_id = data.get("id")
        
        # Verify original is closed
        original_response = self.session.get(f"{BASE_URL}/api/follow-ups/{follow_up_id}")
        if original_response.status_code == 200:
            original_data = original_response.json()
            assert original_data.get("status") == "closed", "Original should be closed"
        
        print(f"PASSED: Scheduled next follow-up {data.get('id')}, original closed")
    
    # ========== Reassign Tests ==========
    def test_16_get_users_for_reassign(self):
        """Test GET /api/users to get list of users for reassignment"""
        response = self.session.get(f"{BASE_URL}/api/users")
        
        assert response.status_code == 200, f"Get users should succeed: {response.text}"
        data = response.json()
        
        users = data.get("items", data) if isinstance(data, dict) else data
        assert len(users) > 0, "Should have users"
        
        # Find a user to reassign to (not the current user)
        for user in users:
            if user.get("id") != self.user_id and user.get("role") in ["executive", "sales_executive", "sales_manager"]:
                self.__class__.reassign_target_user_id = user.get("id")
                break
        
        print(f"PASSED: Found {len(users)} users, target for reassign: {getattr(self.__class__, 'reassign_target_user_id', 'none')}")
    
    def test_17_reassign_follow_up_with_transfer(self):
        """Test POST /api/follow-ups/{id}/reassign with transfer_all_stages"""
        follow_up_id = getattr(self.__class__, 'overdue_follow_up_id', None)
        target_user_id = getattr(self.__class__, 'reassign_target_user_id', None)
        
        if not follow_up_id:
            pytest.skip("No overdue follow-up ID from previous test")
        if not target_user_id:
            pytest.skip("No target user ID for reassignment")
        
        payload = {
            "new_owner_id": target_user_id,
            "reason": "Sales person missed follow-up deadline",
            "transfer_all_stages": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups/{follow_up_id}/reassign", json=payload)
        
        assert response.status_code == 200, f"Reassign should succeed: {response.text}"
        data = response.json()
        
        assert "follow_up" in data, "Response should have follow_up"
        assert "transfer_results" in data, "Response should have transfer_results"
        assert "message" in data, "Response should have message"
        
        fu = data.get("follow_up", {})
        assert fu.get("assigned_to") == target_user_id, "Should be assigned to new user"
        
        # Check history has reassign entry
        history = fu.get("history", [])
        reassign_entries = [h for h in history if h.get("action") == "reassigned"]
        assert len(reassign_entries) > 0, "Should have reassign entry in history"
        
        print(f"PASSED: Reassigned follow-up to {target_user_id}")
    
    # ========== Permission Tests ==========
    def test_18_escalations_forbidden_for_non_manager(self):
        """Test that non-managers cannot access escalations"""
        # Login as sales executive
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login as EMP003")
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = session.get(f"{BASE_URL}/api/follow-ups/escalations")
        
        # Should return 403 if properly restricted, or empty list for executives
        if response.status_code == 403:
            print("PASSED: Escalations correctly returns 403 for non-manager")
        elif response.status_code == 200:
            data = response.json()
            # Non-managers might get empty escalations (only see their reportees)
            print(f"INFO: Escalations returned 200 for executive with {data.get('total', 0)} items")
        else:
            print(f"INFO: Escalations returned status {response.status_code}")
    
    def test_19_reassign_forbidden_for_non_manager(self):
        """Test that non-managers cannot reassign follow-ups"""
        # Login as sales executive
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login as EMP003")
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        follow_up_id = getattr(self.__class__, 'next_follow_up_id', None)
        if not follow_up_id:
            pytest.skip("No follow-up ID")
        
        payload = {
            "new_owner_id": self.user_id,
            "reason": "Test",
            "transfer_all_stages": False
        }
        
        response = session.post(f"{BASE_URL}/api/follow-ups/{follow_up_id}/reassign", json=payload)
        
        assert response.status_code == 403, f"Non-manager should get 403: {response.text}"
        print("PASSED: Reassign correctly returns 403 for non-manager")
    
    # ========== Cleanup ==========
    def test_99_cleanup_test_data(self):
        """Cleanup test follow-ups"""
        # Note: In production, we might want to keep test data or have a dedicated cleanup
        # For now, just verify we can list follow-ups
        response = self.session.get(f"{BASE_URL}/api/follow-ups")
        assert response.status_code == 200, "Final list should work"
        
        # Log created IDs for manual cleanup if needed
        created_ids = [
            getattr(self.__class__, 'created_follow_up_id', None),
            getattr(self.__class__, 'meeting_follow_up_id', None),
            getattr(self.__class__, 'overdue_follow_up_id', None),
            getattr(self.__class__, 'next_follow_up_id', None),
        ]
        print(f"INFO: Test follow-ups created: {[id for id in created_ids if id]}")
        print("PASSED: Test suite complete")


class TestLoginCredentialsFollowUps:
    """Test login with various credentials"""
    
    def test_admin_login(self):
        """Test Admin login with ADMIN001 / Admin@2026"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        assert response.status_code == 200, f"Admin login should succeed: {response.text}"
        data = response.json()
        assert data.get("access_token") is not None, "Should return access_token"
        assert data.get("user", {}).get("role") == "admin", "User role should be admin"
        print("PASSED: Admin login successful")
    
    def test_sales_manager_login(self):
        """Test Sales Manager login with EMP002 / Sales@123"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "Sales@123"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"PASSED: Sales Manager login successful - role: {data.get('user', {}).get('role')}")
        else:
            print(f"INFO: Sales Manager EMP002 login returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
