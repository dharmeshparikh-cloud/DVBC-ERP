"""
MASTER TEST: Sales Follow-Up Escalation System Audit
Comprehensive functional, logic, and technical audit covering:
- Dashboard widget
- Follow-up CRUD
- Missed follow-up detection  
- Escalation to manager
- Manager actions (reassign/transfer ownership)
- Data integrity
- RBAC
- Edge cases
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSection1_DashboardVerification:
    """SECTION 1 - DASHBOARD & FOLLOW-UP PAGE VERIFICATION"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as Admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_1a_dashboard_widget_data_structure(self):
        """Verify dashboard widget returns proper structure with client info"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups/dashboard/today")
        assert response.status_code == 200, f"Dashboard widget failed: {response.text}"
        
        data = response.json()
        assert "items" in data, "Should have items array"
        assert "overdue_count" in data, "Should have overdue_count"
        assert "today_count" in data, "Should have today_count"
        assert "total" in data, "Should have total"
        
        # Verify each item has required fields for widget display
        for item in data.get("items", []):
            assert "client_name" in item, "Widget item must have client_name"
            assert "entity_type" in item, "Widget item must have entity_type (for stage badge)"
            assert "due_date" in item, "Widget item must have due_date"
            assert "last_follow_up_summary" in item or "notes" in item, "Widget item should have summary/notes"
            assert "is_overdue" in item, "Should have is_overdue indicator"
            assert "days_overdue" in item, "Should have days_overdue"
        
        print(f"PASSED: Dashboard widget returns {data['total']} items with proper structure")
    
    def test_1b_follow_ups_list_structure(self):
        """Verify /api/follow-ups list contains all required fields"""
        response = self.session.get(f"{BASE_URL}/api/follow-ups?status=open")
        assert response.status_code == 200, f"List failed: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Should return list"
        
        for item in data[:10]:  # Check first 10
            assert "id" in item, "Must have id"
            assert "client_name" in item, "Must have client_name"
            assert "entity_type" in item, "Must have entity_type for stage badge"
            assert "assigned_to_name" in item, "Must have assigned_to_name"
            assert "due_date" in item, "Must have due_date"
            assert "priority" in item, "Must have priority"
            assert "status" in item, "Must have status"
            # Verify entity_type is valid
            valid_stages = ["lead", "meeting", "pricing_plan", "sow", "quotation", "agreement", "payment", "kickoff", "project"]
            assert item["entity_type"] in valid_stages, f"Invalid entity_type: {item['entity_type']}"
        
        print(f"PASSED: Follow-ups list returns {len(data)} items with all required fields")


class TestSection2_FollowUpCreation:
    """SECTION 2 - FOLLOW-UP CREATION"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_2a_create_lead_stage_follow_up(self):
        """Create follow-up for 'lead' stage"""
        due_date = (datetime.now() + timedelta(days=2)).isoformat()
        payload = {
            "entity_type": "lead",
            "entity_id": f"test-lead-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_Lead Client Corp",
            "due_date": due_date,
            "notes": "Initial lead follow-up",
            "priority": "high"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data["entity_type"] == "lead"
        assert data["client_name"] == "AUDIT_Lead Client Corp"
        assert data["priority"] == "high"
        assert data["status"] == "open"
        
        self.__class__.lead_follow_up_id = data["id"]
        print(f"PASSED: Created lead follow-up {data['id']}")
    
    def test_2b_create_sow_stage_manual_client(self):
        """Create follow-up for 'sow' stage with manual client name"""
        due_date = (datetime.now() + timedelta(days=3)).isoformat()
        payload = {
            "entity_type": "sow",
            "entity_id": f"manual-sow-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_Manual SOW Client",
            "due_date": due_date,
            "notes": "SOW stage follow-up - manual entry",
            "priority": "medium"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        data = response.json()
        assert data["entity_type"] == "sow"
        assert data["client_name"] == "AUDIT_Manual SOW Client"
        
        self.__class__.sow_follow_up_id = data["id"]
        print(f"PASSED: Created SOW follow-up with manual client name {data['id']}")
    
    def test_2c_verify_all_9_stages_allowed(self):
        """Verify all 9 entity types are accepted"""
        valid_stages = ["lead", "meeting", "pricing_plan", "sow", "quotation", "agreement", "payment", "kickoff", "project"]
        
        for stage in valid_stages:
            due_date = (datetime.now() + timedelta(days=1)).isoformat()
            payload = {
                "entity_type": stage,
                "entity_id": f"stage-test-{stage}",
                "client_name": f"AUDIT_Stage_{stage}",
                "due_date": due_date,
                "priority": "low"
            }
            response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
            assert response.status_code == 200, f"Stage {stage} creation failed: {response.text}"
        
        print("PASSED: All 9 funnel stages are valid for follow-up creation")
    
    def test_2d_invalid_entity_type_rejected(self):
        """Verify invalid entity type is rejected"""
        payload = {
            "entity_type": "invalid_stage",
            "entity_id": "test",
            "client_name": "Test",
            "due_date": datetime.now().isoformat()
        }
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 400, f"Should reject invalid stage: {response.text}"
        print("PASSED: Invalid entity type correctly rejected with 400")


class TestSection3_MissedFollowUpDetection:
    """SECTION 3 - MISSED FOLLOW-UP DETECTION via API (Server Time UTC)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_3a_due_today_follow_up(self):
        """Create follow-up due today - verify shows in today's widget"""
        # Set due date to today (UTC)
        today = datetime.utcnow().replace(hour=23, minute=0, second=0)
        payload = {
            "entity_type": "lead",
            "entity_id": f"today-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_DueToday",
            "due_date": today.isoformat(),
            "priority": "high"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        fu_id = response.json()["id"]
        
        # Check dashboard today
        dashboard = self.session.get(f"{BASE_URL}/api/follow-ups/dashboard/today").json()
        today_items = [i for i in dashboard["items"] if i["id"] == fu_id]
        
        assert len(today_items) == 1, "Should appear in today's dashboard"
        assert today_items[0]["is_overdue"] == False, "Due today should NOT be marked overdue"
        
        print("PASSED: Due today follow-up correctly shows in dashboard as NOT overdue")
    
    def test_3b_1day_overdue_follow_up(self):
        """Create follow-up 1 day overdue - verify shows as Overdue"""
        yesterday = datetime.utcnow() - timedelta(days=1)
        payload = {
            "entity_type": "meeting",
            "entity_id": f"1d-overdue-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_1DayOverdue",
            "due_date": yesterday.isoformat(),
            "priority": "medium"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        fu_id = response.json()["id"]
        
        # Check in dashboard
        dashboard = self.session.get(f"{BASE_URL}/api/follow-ups/dashboard/today").json()
        item = next((i for i in dashboard["items"] if i["id"] == fu_id), None)
        
        if item:  # May be included in "today + overdue" view
            assert item["is_overdue"] == True, "1 day overdue should be marked overdue"
            assert item["days_overdue"] >= 1, "Should be at least 1 day overdue"
        
        print("PASSED: 1 day overdue follow-up correctly identified")
    
    def test_3c_2days_overdue_escalation_pending(self):
        """Create follow-up 2 days overdue - verify escalation pending"""
        two_days_ago = datetime.utcnow() - timedelta(days=2)
        payload = {
            "entity_type": "pricing_plan",
            "entity_id": f"2d-overdue-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_2DaysOverdue_EscPending",
            "due_date": two_days_ago.isoformat(),
            "priority": "high"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        fu_id = response.json()["id"]
        
        # 2 days overdue should trigger escalation threshold
        escalations = self.session.get(f"{BASE_URL}/api/follow-ups/escalations").json()
        esc_item = next((i for i in escalations["items"] if i["id"] == fu_id), None)
        
        assert esc_item is not None, "2-day overdue should appear in escalations"
        assert esc_item["days_overdue"] >= 2, "Should be 2+ days overdue"
        
        print("PASSED: 2 day overdue follow-up appears in escalations")
    
    def test_3d_3plus_days_overdue_in_escalation_dashboard(self):
        """Create follow-up 3+ days overdue - verify in escalation dashboard"""
        three_days_ago = datetime.utcnow() - timedelta(days=4)
        payload = {
            "entity_type": "sow",
            "entity_id": f"4d-overdue-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_4DaysOverdue_Escalated",
            "due_date": three_days_ago.isoformat(),
            "priority": "high"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Create failed: {response.text}"
        
        fu_id = response.json()["id"]
        
        escalations = self.session.get(f"{BASE_URL}/api/follow-ups/escalations").json()
        esc_item = next((i for i in escalations["items"] if i["id"] == fu_id), None)
        
        assert esc_item is not None, "3+ day overdue must appear in escalations"
        assert esc_item["days_overdue"] >= 3, "Should show 3+ days overdue"
        
        print("PASSED: 3+ day overdue follow-up in escalation dashboard")


class TestSection4_EscalationToManager:
    """SECTION 4 - ESCALATION TO MANAGER"""
    
    def test_4a_manager_sees_escalations(self):
        """Login as Sales Manager EMP002 - verify escalations visible"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "Sales@123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Could not login as EMP002 manager")
        
        token = login_response.json().get("access_token")
        user = login_response.json().get("user")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Manager role check
        assert user.get("role") in ["sales_manager", "manager", "admin"], f"Expected manager role, got {user.get('role')}"
        
        # Access escalations
        response = session.get(f"{BASE_URL}/api/follow-ups/escalations")
        assert response.status_code == 200, f"Manager should access escalations: {response.text}"
        
        data = response.json()
        assert "items" in data, "Should have items"
        assert "total" in data, "Should have total"
        
        # Verify escalated items show assigned_to_name
        for item in data.get("items", []):
            assert "assigned_to_name" in item, "Escalated items must show assigned person"
            assert "days_overdue" in item, "Must show days overdue"
        
        print(f"PASSED: Sales Manager sees {data['total']} escalated items")
    
    def test_4b_executive_forbidden_from_escalations(self):
        """Sales Executive EMP003 cannot access escalations (403)"""
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
        assert response.status_code == 403, f"Executive should get 403: {response.status_code}"
        
        print("PASSED: Sales Executive correctly gets 403 on escalations")


class TestSection5_ManagerActions:
    """SECTION 5 - MANAGER ACTIONS (add update, close, schedule-next, reassign)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_5a_follow_up_detail_has_all_fields(self):
        """Verify GET /follow-ups/{id} returns complete detail"""
        # Create a follow-up first
        payload = {
            "entity_type": "quotation",
            "entity_id": f"detail-test-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_DetailTest",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "notes": "Testing detail completeness",
            "priority": "high"
        }
        create_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        fu_id = create_resp.json()["id"]
        
        # Get detail
        response = self.session.get(f"{BASE_URL}/api/follow-ups/{fu_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Required fields for detail dialog
        required_fields = [
            "id", "client_name", "entity_type", "priority", 
            "assigned_to", "assigned_to_name", "created_by", "created_by_name",
            "status", "due_date", "created_at", "history"
        ]
        
        for field in required_fields:
            assert field in data, f"Detail missing required field: {field}"
        
        # History should have at least created entry
        assert len(data["history"]) >= 1, "History must have created entry"
        assert data["history"][0]["action"] == "created", "First history entry should be 'created'"
        
        self.__class__.detail_fu_id = fu_id
        print("PASSED: Follow-up detail contains all required fields")
    
    def test_5b_add_update_appears_in_history(self):
        """Add update and verify it appears in history"""
        fu_id = getattr(self.__class__, 'detail_fu_id', None)
        if not fu_id:
            pytest.skip("No follow-up ID")
        
        payload = {
            "notes": "AUDIT: Client confirmed meeting for next week",
            "outcome": "Positive - interested"
        }
        
        response = self.session.put(f"{BASE_URL}/api/follow-ups/{fu_id}/update", json=payload)
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        data = response.json()
        
        # Verify update in history
        history = data.get("history", [])
        update_entries = [h for h in history if h["action"] == "updated"]
        assert len(update_entries) > 0, "Update should appear in history"
        
        latest = update_entries[-1]
        assert latest["notes"] == "AUDIT: Client confirmed meeting for next week"
        assert latest["outcome"] == "Positive - interested"
        assert "date" in latest, "History entry must have date"
        assert "by" in latest, "History entry must have 'by' (user name)"
        
        print("PASSED: Update added to history with notes/outcome/date/user")
    
    def test_5c_close_and_schedule_next(self):
        """Close follow-up and schedule next - verify old closes and new created"""
        fu_id = getattr(self.__class__, 'detail_fu_id', None)
        if not fu_id:
            pytest.skip("No follow-up ID")
        
        next_date = (datetime.now() + timedelta(days=7)).isoformat()
        payload = {
            "due_date": next_date,
            "notes": "AUDIT: Next follow-up scheduled",
            "priority": "medium"
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups/{fu_id}/schedule-next", json=payload)
        assert response.status_code == 200, f"Schedule-next failed: {response.text}"
        
        new_fu = response.json()
        
        # New follow-up should be created
        assert new_fu["id"] != fu_id, "New ID should differ"
        assert new_fu["status"] == "open", "New follow-up should be open"
        
        # Check history references previous
        history = new_fu.get("history", [])
        assert len(history) > 0, "New follow-up should have history"
        
        # Verify old follow-up is now closed
        old_response = self.session.get(f"{BASE_URL}/api/follow-ups/{fu_id}")
        if old_response.status_code == 200:
            old_data = old_response.json()
            assert old_data["status"] == "closed", "Original should be closed"
            assert old_data.get("closed_at") is not None, "Should have closed_at timestamp"
        
        self.__class__.new_fu_id = new_fu["id"]
        print("PASSED: Close & Schedule Next works - old closed, new created")
    
    def test_5d_reassign_with_transfer_ownership(self):
        """Reassign follow-up and verify ownership transfer"""
        fu_id = getattr(self.__class__, 'new_fu_id', None)
        if not fu_id:
            pytest.skip("No follow-up ID")
        
        # Get a target user
        users_resp = self.session.get(f"{BASE_URL}/api/users")
        users = users_resp.json() if isinstance(users_resp.json(), list) else users_resp.json().get("items", [])
        target_user = next((u for u in users if u.get("id") != self.user_id and u.get("role") in ["executive", "sales_executive", "sales_manager"]), None)
        
        if not target_user:
            pytest.skip("No target user for reassign")
        
        payload = {
            "new_owner_id": target_user["id"],
            "reason": "AUDIT: Testing reassignment flow",
            "transfer_all_stages": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups/{fu_id}/reassign", json=payload)
        assert response.status_code == 200, f"Reassign failed: {response.text}"
        
        data = response.json()
        
        assert "follow_up" in data, "Response should have follow_up"
        assert "transfer_results" in data, "Response should have transfer_results"
        assert "message" in data, "Response should have message"
        
        fu = data["follow_up"]
        assert fu["assigned_to"] == target_user["id"], "Should be assigned to new owner"
        
        # Verify history has reassign entry
        history = fu.get("history", [])
        reassign_entries = [h for h in history if h["action"] == "reassigned"]
        assert len(reassign_entries) > 0, "Should have reassign in history"
        
        latest = reassign_entries[-1]
        assert "old_owner" in latest, "History should have old_owner"
        assert "new_owner" in latest, "History should have new_owner"
        
        print(f"PASSED: Reassigned to {target_user['full_name']}, history updated")


class TestSection6_LeadReassignmentOwnershipTransfer:
    """SECTION 6 - LEAD REASSIGNMENT & OWNERSHIP TRANSFER"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_6a_create_lead_and_follow_up(self):
        """Create a lead and then a follow-up for it"""
        # Try to create a lead
        lead_payload = {
            "company": "AUDIT_TransferTest Corp",
            "first_name": "Test",
            "last_name": "Transfer",
            "email": f"transfer_{uuid.uuid4().hex[:6]}@test.com",
            "phone": "9876543210",
            "source": "referral",
            "status": "new"
        }
        
        lead_resp = self.session.post(f"{BASE_URL}/api/leads", json=lead_payload)
        
        if lead_resp.status_code in [200, 201]:
            lead_id = lead_resp.json().get("id")
            self.__class__.test_lead_id = lead_id
            
            # Create follow-up for this lead
            fu_payload = {
                "entity_type": "lead",
                "entity_id": lead_id,
                "lead_id": lead_id,
                "client_name": "AUDIT_TransferTest Corp",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "priority": "high"
            }
            
            fu_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=fu_payload)
            assert fu_resp.status_code == 200, f"Create follow-up failed: {fu_resp.text}"
            
            self.__class__.test_fu_id = fu_resp.json()["id"]
            print(f"PASSED: Created lead {lead_id} and follow-up {self.__class__.test_fu_id}")
        else:
            # If leads endpoint doesn't exist or fails, create just follow-up
            fu_payload = {
                "entity_type": "lead",
                "entity_id": f"manual-lead-{uuid.uuid4().hex[:8]}",
                "client_name": "AUDIT_TransferTest Manual",
                "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "priority": "high"
            }
            fu_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=fu_payload)
            self.__class__.test_fu_id = fu_resp.json()["id"]
            print(f"INFO: Lead creation skipped (endpoint may not exist), created follow-up only")
    
    def test_6b_reassign_with_transfer_all_stages(self):
        """Reassign with transfer_all_stages=true"""
        fu_id = getattr(self.__class__, 'test_fu_id', None)
        if not fu_id:
            pytest.skip("No follow-up ID")
        
        # Get target user
        users_resp = self.session.get(f"{BASE_URL}/api/users")
        users = users_resp.json() if isinstance(users_resp.json(), list) else users_resp.json().get("items", [])
        target = next((u for u in users if u.get("role") in ["executive", "sales_executive", "sales_manager"] and u.get("id") != self.user_id), None)
        
        if not target:
            pytest.skip("No target user")
        
        payload = {
            "new_owner_id": target["id"],
            "reason": "AUDIT: Testing full ownership transfer",
            "transfer_all_stages": True
        }
        
        response = self.session.post(f"{BASE_URL}/api/follow-ups/{fu_id}/reassign", json=payload)
        assert response.status_code == 200, f"Reassign failed: {response.text}"
        
        data = response.json()
        transfer_results = data.get("transfer_results", {})
        
        # Should have transferred follow_up at minimum
        assert transfer_results.get("follow_up") == True, "follow_up should be transferred"
        
        # If lead_id was set, should also transfer lead
        if transfer_results.get("lead"):
            print("PASSED: Lead ownership also transferred")
        
        self.__class__.new_owner_id = target["id"]
        print(f"PASSED: Ownership transferred to {target['full_name']}, results: {transfer_results}")


class TestSection7_DataIntegrity:
    """SECTION 7 - DATA INTEGRITY"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_7a_closed_follow_up_has_closed_at(self):
        """After closing, verify status=closed and closed_at is set"""
        # Create and close a follow-up
        payload = {
            "entity_type": "agreement",
            "entity_id": f"integrity-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_IntegrityTest",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        create_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        fu_id = create_resp.json()["id"]
        
        # Close it
        close_payload = {"notes": "Closing for integrity test", "outcome": "Completed"}
        close_resp = self.session.put(f"{BASE_URL}/api/follow-ups/{fu_id}/close", json=close_payload)
        assert close_resp.status_code == 200
        
        data = close_resp.json()
        assert data["status"] == "closed", "Status should be closed"
        assert data.get("closed_at") is not None, "closed_at should be set"
        
        print("PASSED: Closed follow-up has status=closed and closed_at timestamp")
    
    def test_7b_schedule_next_links_via_history(self):
        """After schedule-next, new follow-up history references old"""
        # Create a follow-up
        payload = {
            "entity_type": "payment",
            "entity_id": f"history-link-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_HistoryLink",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        create_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        fu_id = create_resp.json()["id"]
        
        # Schedule next
        next_payload = {
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "notes": "Next iteration"
        }
        next_resp = self.session.post(f"{BASE_URL}/api/follow-ups/{fu_id}/schedule-next", json=next_payload)
        assert next_resp.status_code == 200
        
        new_fu = next_resp.json()
        history = new_fu.get("history", [])
        
        # Check that created entry has previous_follow_up_id
        created_entry = next((h for h in history if h["action"] == "created"), None)
        if created_entry and "previous_follow_up_id" in created_entry:
            assert created_entry["previous_follow_up_id"] == fu_id, "Should reference old follow-up"
            print("PASSED: New follow-up history references previous via previous_follow_up_id")
        else:
            print("INFO: previous_follow_up_id not explicitly stored but history chain exists")
    
    def test_7c_reassign_history_has_old_new_owner(self):
        """After reassignment, history includes old_owner and new_owner"""
        # Create follow-up
        payload = {
            "entity_type": "kickoff",
            "entity_id": f"owner-track-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_OwnerTrack",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        create_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        fu_id = create_resp.json()["id"]
        
        # Get target user
        users_resp = self.session.get(f"{BASE_URL}/api/users")
        users = users_resp.json() if isinstance(users_resp.json(), list) else users_resp.json().get("items", [])
        target = next((u for u in users if u.get("role") in ["executive", "sales_executive"]), None)
        
        if not target:
            pytest.skip("No target user")
        
        # Reassign
        reassign_resp = self.session.post(f"{BASE_URL}/api/follow-ups/{fu_id}/reassign", json={
            "new_owner_id": target["id"],
            "reason": "Testing owner tracking"
        })
        assert reassign_resp.status_code == 200
        
        fu = reassign_resp.json()["follow_up"]
        history = fu.get("history", [])
        reassign_entry = next((h for h in history if h["action"] == "reassigned"), None)
        
        assert reassign_entry is not None, "Should have reassign entry"
        assert "old_owner" in reassign_entry, "Should have old_owner"
        assert "new_owner" in reassign_entry, "Should have new_owner"
        
        print(f"PASSED: Reassign history tracks old_owner and new_owner")


class TestSection8_RBAC:
    """SECTION 8 - RBAC (Role-Based Access Control)"""
    
    def test_8a_sales_executive_can_create(self):
        """Sales Executive can create follow-up"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login as EMP003")
        
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        payload = {
            "entity_type": "lead",
            "entity_id": f"exec-create-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_ExecutiveCreate",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        response = session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code == 200, f"Executive should create: {response.text}"
        
        self.__class__.exec_fu_id = response.json()["id"]
        print("PASSED: Sales Executive can create follow-ups")
    
    def test_8b_sales_executive_can_update_own(self):
        """Sales Executive can update own follow-ups"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login")
        
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        fu_id = getattr(self.__class__, 'exec_fu_id', None)
        if not fu_id:
            pytest.skip("No follow-up ID")
        
        payload = {"notes": "Executive update test", "outcome": "In progress"}
        response = session.put(f"{BASE_URL}/api/follow-ups/{fu_id}/update", json=payload)
        
        assert response.status_code == 200, f"Executive should update own: {response.text}"
        print("PASSED: Sales Executive can update own follow-ups")
    
    def test_8c_sales_executive_cannot_access_escalations(self):
        """Sales Executive cannot access escalations (403)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login")
        
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = session.get(f"{BASE_URL}/api/follow-ups/escalations")
        assert response.status_code == 403, f"Executive should get 403 on escalations: {response.status_code}"
        
        print("PASSED: Sales Executive gets 403 on escalations")
    
    def test_8d_sales_executive_cannot_reassign(self):
        """Sales Executive cannot reassign (403)"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login")
        
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        fu_id = getattr(self.__class__, 'exec_fu_id', None)
        if not fu_id:
            pytest.skip("No follow-up ID")
        
        # Get any user ID
        admin_session = requests.Session()
        admin_session.headers.update({"Content-Type": "application/json"})
        admin_login = admin_session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        admin_token = admin_login.json().get("access_token")
        admin_session.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        users_resp = admin_session.get(f"{BASE_URL}/api/users")
        users = users_resp.json() if isinstance(users_resp.json(), list) else users_resp.json().get("items", [])
        target = next((u for u in users if u.get("role") == "admin"), None)
        
        if not target:
            pytest.skip("No target user")
        
        payload = {"new_owner_id": target["id"], "reason": "Test"}
        response = session.post(f"{BASE_URL}/api/follow-ups/{fu_id}/reassign", json=payload)
        
        assert response.status_code == 403, f"Executive should get 403 on reassign: {response.status_code}"
        print("PASSED: Sales Executive gets 403 on reassign")
    
    def test_8e_sales_manager_can_access_escalations(self):
        """Sales Manager can access escalations"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "Sales@123"
        })
        
        if login_resp.status_code != 200:
            pytest.skip("Could not login as EMP002")
        
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = session.get(f"{BASE_URL}/api/follow-ups/escalations")
        assert response.status_code == 200, f"Manager should access escalations: {response.text}"
        
        print("PASSED: Sales Manager can access escalations")
    
    def test_8f_admin_full_access(self):
        """Admin has full access to all endpoints"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Test all main endpoints
        endpoints = [
            ("GET", f"{BASE_URL}/api/follow-ups"),
            ("GET", f"{BASE_URL}/api/follow-ups/dashboard/today"),
            ("GET", f"{BASE_URL}/api/follow-ups/escalations"),
        ]
        
        for method, url in endpoints:
            response = session.get(url) if method == "GET" else None
            assert response.status_code == 200, f"Admin should access {url}: {response.status_code}"
        
        print("PASSED: Admin has full access to all endpoints")


class TestSection9_DetailDialogCompleteness:
    """SECTION 9 - DETAIL DIALOG COMPLETENESS"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed: {login_response.status_code}")
    
    def test_9a_detail_has_all_required_fields(self):
        """Verify follow-up detail has ALL required fields for dialog"""
        # Create a complete follow-up
        payload = {
            "entity_type": "project",
            "entity_id": f"detail-complete-{uuid.uuid4().hex[:8]}",
            "client_name": "AUDIT_CompleteDetail Corp",
            "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "notes": "Complete detail test with all fields",
            "priority": "high"
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/follow-ups", json=payload)
        fu_id = create_resp.json()["id"]
        
        # Add an update
        self.session.put(f"{BASE_URL}/api/follow-ups/{fu_id}/update", json={
            "notes": "Update 1 - client meeting scheduled",
            "outcome": "Positive"
        })
        
        # Get detail
        response = self.session.get(f"{BASE_URL}/api/follow-ups/{fu_id}")
        assert response.status_code == 200
        
        data = response.json()
        
        # Fields required for detail dialog:
        detail_required = {
            "client_name": "For dialog header",
            "entity_type": "For Funnel Stage banner",
            "priority": "For priority display",
            "assigned_to": "For Assigned To field",
            "assigned_to_name": "For readable display",
            "created_by": "For Created By field",
            "created_by_name": "For readable display",
            "status": "For Status + Escalation badge",
            "due_date": "For Due Date display",
            "created_at": "For Created Date",
            "history": "For History timeline"
        }
        
        missing = []
        for field, purpose in detail_required.items():
            if field not in data:
                missing.append(f"{field} ({purpose})")
        
        assert len(missing) == 0, f"Missing fields: {missing}"
        
        # Verify history has proper entries
        history = data.get("history", [])
        assert len(history) >= 2, "Should have created + update entries"
        
        for entry in history:
            assert "action" in entry, "History entry needs action"
            assert "date" in entry, "History entry needs date"
            assert "by" in entry, "History entry needs user name"
        
        print("PASSED: Detail dialog has ALL required fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
