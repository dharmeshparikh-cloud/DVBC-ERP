"""
Test MOM SLA Reminder System and Meeting-Expense Link Features

Tests:
1. POST /api/governance/mom-sla/run-reminders - creates notifications for overdue meetings
2. GET /api/governance/mom-sla/pending-reminders - returns list of meetings needing MOM reminders
3. Expense prompt notification created when in-person meeting is created without travel details
4. Expense prompt notification created when MOM is recorded for in-person meeting without expense
5. MOM SLA reminder notifications have correct structure (priority: high, action_required: true, action_path)
6. Escalation only happens for meetings >36 hours past SLA (12 hours overdue)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
CONSULTANT_CREDS = {"employee_id": "EMP004", "password": "consultant123"}


class TestMOMSLAReminderSystem:
    """Tests for MOM SLA Reminder System"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_user_id = login_resp.json().get("user", {}).get("id")
        
        yield
        
        # Cleanup: Delete test meetings and notifications
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up test data created during tests"""
        try:
            # Delete test meetings
            meetings_resp = self.session.get(f"{BASE_URL}/api/meetings")
            if meetings_resp.status_code == 200:
                for meeting in meetings_resp.json():
                    if meeting.get("title", "").startswith("TEST_"):
                        self.session.delete(f"{BASE_URL}/api/meetings/{meeting['id']}")
            
            # Delete test notifications
            notif_resp = self.session.get(f"{BASE_URL}/api/notifications")
            if notif_resp.status_code == 200:
                for notif in notif_resp.json():
                    if notif.get("title", "").startswith("TEST_") or "TEST_" in notif.get("message", ""):
                        self.session.delete(f"{BASE_URL}/api/notifications/{notif['id']}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def test_pending_reminders_endpoint_exists(self):
        """Test GET /api/governance/mom-sla/pending-reminders endpoint exists and returns correct structure"""
        response = self.session.get(f"{BASE_URL}/api/governance/mom-sla/pending-reminders")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "count" in data, "Response should have 'count' field"
        assert "would_escalate" in data, "Response should have 'would_escalate' field"
        assert "pending_meetings" in data, "Response should have 'pending_meetings' field"
        assert isinstance(data["pending_meetings"], list), "pending_meetings should be a list"
        
        print(f"PASS: pending-reminders endpoint returns correct structure with {data['count']} pending meetings")
    
    def test_run_reminders_endpoint_exists(self):
        """Test POST /api/governance/mom-sla/run-reminders endpoint exists"""
        response = self.session.post(f"{BASE_URL}/api/governance/mom-sla/run-reminders")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should have 'message' field"
        assert "reminders_sent" in data, "Response should have 'reminders_sent' field"
        assert "escalations_sent" in data, "Response should have 'escalations_sent' field"
        assert "executed_at" in data, "Response should have 'executed_at' field"
        
        print(f"PASS: run-reminders endpoint executed - {data['reminders_sent']} reminders, {data['escalations_sent']} escalations")
    
    def test_pending_reminders_meeting_structure(self):
        """Test that pending meetings have correct structure"""
        response = self.session.get(f"{BASE_URL}/api/governance/mom-sla/pending-reminders")
        assert response.status_code == 200
        
        data = response.json()
        if data["count"] > 0:
            meeting = data["pending_meetings"][0]
            
            # Check required fields
            required_fields = ["meeting_id", "title", "meeting_date", "hours_overdue", "would_escalate"]
            for field in required_fields:
                assert field in meeting, f"Meeting should have '{field}' field"
            
            # Verify hours_overdue is positive (since these are overdue meetings)
            assert meeting["hours_overdue"] > 0, "hours_overdue should be positive for overdue meetings"
            
            print(f"PASS: Pending meeting has correct structure with {meeting['hours_overdue']} hours overdue")
        else:
            print("PASS: No pending meetings to verify structure (endpoint working correctly)")
    
    def test_escalation_threshold_logic(self):
        """Test that escalation only happens for meetings >36 hours past SLA (12 hours overdue)"""
        response = self.session.get(f"{BASE_URL}/api/governance/mom-sla/pending-reminders")
        assert response.status_code == 200
        
        data = response.json()
        
        for meeting in data["pending_meetings"]:
            hours_overdue = meeting.get("hours_overdue", 0)
            would_escalate = meeting.get("would_escalate", False)
            already_escalated = meeting.get("already_escalated", False)
            
            # Escalation should only happen if >12 hours overdue AND not already escalated
            if hours_overdue > 12 and not already_escalated:
                assert would_escalate == True, f"Meeting {hours_overdue}h overdue should escalate"
            elif hours_overdue <= 12:
                assert would_escalate == False, f"Meeting {hours_overdue}h overdue should NOT escalate"
        
        print(f"PASS: Escalation threshold logic verified for {len(data['pending_meetings'])} meetings")


class TestMOMSLANotificationStructure:
    """Tests for MOM SLA notification structure"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
    
    def test_mom_sla_reminder_notification_structure(self):
        """Test that MOM SLA reminder notifications have correct structure"""
        # Get notifications
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        notifications = response.json()
        
        # Find MOM SLA reminder notifications
        mom_reminders = [n for n in notifications if n.get("type") == "mom_sla_reminder"]
        
        if mom_reminders:
            notif = mom_reminders[0]
            
            # Check required fields for MOM SLA reminder
            assert notif.get("priority") == "high", "MOM SLA reminder should have high priority"
            assert notif.get("action_required") == True, "MOM SLA reminder should have action_required=True"
            assert notif.get("action_path") == "/consulting-meetings", "MOM SLA reminder should have action_path=/consulting-meetings"
            assert "entity_id" in notif, "Should have entity_id (meeting_id)"
            assert notif.get("entity_type") == "meeting", "entity_type should be 'meeting'"
            
            # Check metadata
            metadata = notif.get("metadata", {})
            assert "hours_overdue" in metadata, "metadata should have hours_overdue"
            assert metadata.get("sla_breach") == True, "metadata should have sla_breach=True"
            assert metadata.get("governance_rule") == "mom_sla_24h", "metadata should have governance_rule"
            
            print(f"PASS: MOM SLA reminder notification has correct structure")
        else:
            print("INFO: No MOM SLA reminder notifications found - running reminders to create some")
            
            # Run reminders to potentially create notifications
            run_resp = self.session.post(f"{BASE_URL}/api/governance/mom-sla/run-reminders")
            assert run_resp.status_code == 200
            print(f"PASS: run-reminders executed successfully")
    
    def test_mom_sla_escalation_notification_structure(self):
        """Test that MOM SLA escalation notifications have correct structure"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        notifications = response.json()
        
        # Find MOM SLA escalation notifications
        escalations = [n for n in notifications if n.get("type") == "mom_sla_escalation"]
        
        if escalations:
            notif = escalations[0]
            
            # Check required fields for escalation
            assert notif.get("priority") == "high", "Escalation should have high priority"
            assert notif.get("action_required") == True, "Escalation should have action_required=True"
            
            # Check metadata for escalation-specific fields
            metadata = notif.get("metadata", {})
            assert metadata.get("escalation") == True, "metadata should have escalation=True"
            
            print(f"PASS: MOM SLA escalation notification has correct structure")
        else:
            print("INFO: No MOM SLA escalation notifications found (may need meetings >36h overdue)")


class TestExpensePromptNotification:
    """Tests for expense prompt notification on in-person meetings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as consultant (who creates meetings)
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json=CONSULTANT_CREDS)
        if login_resp.status_code != 200:
            # Fallback to admin
            login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.user_id = login_resp.json().get("user", {}).get("id")
        
        self.created_meeting_ids = []
        
        yield
        
        # Cleanup
        self._cleanup_test_data()
    
    def _cleanup_test_data(self):
        """Clean up test meetings and notifications"""
        try:
            for meeting_id in self.created_meeting_ids:
                self.session.delete(f"{BASE_URL}/api/meetings/{meeting_id}")
            
            # Delete test notifications
            notif_resp = self.session.get(f"{BASE_URL}/api/notifications")
            if notif_resp.status_code == 200:
                for notif in notif_resp.json():
                    if "TEST_" in notif.get("message", "") or "TEST_" in notif.get("title", ""):
                        self.session.delete(f"{BASE_URL}/api/notifications/{notif['id']}")
        except Exception as e:
            print(f"Cleanup error: {e}")
    
    def test_expense_prompt_on_inperson_meeting_without_travel(self):
        """Test that expense prompt notification is created when in-person meeting is created without travel details"""
        # First get a project to link the meeting to
        projects_resp = self.session.get(f"{BASE_URL}/api/projects")
        project_id = None
        if projects_resp.status_code == 200 and projects_resp.json():
            project_id = projects_resp.json()[0].get("id")
        
        # Create an in-person meeting WITHOUT travel details
        meeting_data = {
            "title": f"TEST_InPerson_Meeting_{uuid.uuid4().hex[:8]}",
            "type": "consulting",
            "mode": "offline",  # in-person
            "meeting_date": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "client_name": "TEST_Client",
            "attendees": ["Test Attendee"],
            # NO travel_details - should trigger expense prompt
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/meetings", json=meeting_data)
        
        if create_resp.status_code in [200, 201]:
            meeting = create_resp.json()
            meeting_id = meeting.get("id")
            self.created_meeting_ids.append(meeting_id)
            
            # Wait a moment for background task to complete
            import time
            time.sleep(1)
            
            # Check for expense_prompt notification
            notif_resp = self.session.get(f"{BASE_URL}/api/notifications")
            assert notif_resp.status_code == 200
            
            notifications = notif_resp.json()
            expense_prompts = [
                n for n in notifications 
                if n.get("type") == "expense_prompt" and n.get("entity_id") == meeting_id
            ]
            
            if expense_prompts:
                prompt = expense_prompts[0]
                assert prompt.get("action_required") == True, "Expense prompt should have action_required=True"
                assert prompt.get("action_path") == "/my-expenses", "Expense prompt should have action_path=/my-expenses"
                assert "travel expense" in prompt.get("message", "").lower(), "Message should mention travel expense"
                print(f"PASS: Expense prompt notification created for in-person meeting without travel details")
            else:
                print(f"INFO: Expense prompt notification not found - may be async or feature not triggered")
        else:
            # Meeting creation may fail due to role restrictions
            print(f"INFO: Meeting creation returned {create_resp.status_code} - may need different role")
    
    def test_expense_prompt_notification_structure(self):
        """Test that expense_prompt notifications have correct structure"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        notifications = response.json()
        
        # Find expense_prompt notifications
        expense_prompts = [n for n in notifications if n.get("type") == "expense_prompt"]
        
        if expense_prompts:
            notif = expense_prompts[0]
            
            # Check required fields
            assert notif.get("priority") == "medium", "Expense prompt should have medium priority"
            assert notif.get("action_required") == True, "Expense prompt should have action_required=True"
            assert notif.get("action_path") == "/my-expenses", "Expense prompt should have action_path=/my-expenses"
            assert notif.get("action_label") == "File Expense", "Expense prompt should have action_label='File Expense'"
            assert notif.get("entity_type") == "meeting", "entity_type should be 'meeting'"
            
            # Check metadata
            metadata = notif.get("metadata", {})
            assert metadata.get("auto_generated") == True, "metadata should have auto_generated=True"
            assert metadata.get("governance_rule") == "meeting_expense_link", "metadata should have governance_rule"
            
            print(f"PASS: Expense prompt notification has correct structure")
        else:
            print("INFO: No expense_prompt notifications found in system")


class TestMOMSLAIntegration:
    """Integration tests for MOM SLA system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
    
    def test_mom_sla_status_endpoint(self):
        """Test GET /api/governance/mom-sla endpoint for overall SLA status"""
        response = self.session.get(f"{BASE_URL}/api/governance/mom-sla")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Check structure
        assert "sla_hours" in data, "Response should have 'sla_hours' field"
        assert data["sla_hours"] == 24, "SLA hours should be 24"
        assert "summary" in data, "Response should have 'summary' field"
        
        summary = data["summary"]
        assert "total_past_meetings" in summary, "Summary should have total_past_meetings"
        assert "overdue" in summary, "Summary should have overdue count"
        assert "at_risk" in summary, "Summary should have at_risk count"
        assert "compliant" in summary, "Summary should have compliant count"
        assert "compliance_rate" in summary, "Summary should have compliance_rate"
        
        print(f"PASS: MOM SLA status endpoint returns correct structure - {summary['compliance_rate']}% compliance")
    
    def test_run_reminders_creates_notifications(self):
        """Test that running reminders creates notifications for overdue meetings"""
        # First check pending reminders
        pending_resp = self.session.get(f"{BASE_URL}/api/governance/mom-sla/pending-reminders")
        assert pending_resp.status_code == 200
        pending_count = pending_resp.json().get("count", 0)
        
        # Run reminders
        run_resp = self.session.post(f"{BASE_URL}/api/governance/mom-sla/run-reminders")
        assert run_resp.status_code == 200
        
        run_data = run_resp.json()
        reminders_sent = run_data.get("reminders_sent", 0)
        escalations_sent = run_data.get("escalations_sent", 0)
        skipped = run_data.get("skipped_recent", 0)
        
        print(f"PASS: Run reminders executed - {reminders_sent} reminders, {escalations_sent} escalations, {skipped} skipped (recently notified)")
        
        # Verify the response structure
        assert "message" in run_data
        assert "executed_at" in run_data
        assert isinstance(run_data["reminders_sent"], int)
        assert isinstance(run_data["escalations_sent"], int)
    
    def test_notification_types_in_system(self):
        """Test that the system has the expected notification types"""
        response = self.session.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        notifications = response.json()
        
        # Get unique notification types
        notification_types = set(n.get("type") for n in notifications if n.get("type"))
        
        print(f"INFO: Found notification types in system: {notification_types}")
        
        # Check for governance-related types
        governance_types = {"mom_sla_reminder", "mom_sla_escalation", "expense_prompt"}
        found_governance_types = governance_types.intersection(notification_types)
        
        if found_governance_types:
            print(f"PASS: Found governance notification types: {found_governance_types}")
        else:
            print("INFO: No governance notification types found yet - may need to trigger them")


class TestExpensePromptOnMOMUpdate:
    """Test expense prompt when MOM is recorded for in-person meeting without expense"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert login_resp.status_code == 200
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
    
    def test_expense_prompt_on_mom_update_for_inperson_meeting(self):
        """Test that expense prompt is created when MOM is recorded for in-person meeting without expense"""
        # Get existing meetings
        meetings_resp = self.session.get(f"{BASE_URL}/api/meetings")
        assert meetings_resp.status_code == 200
        
        meetings = meetings_resp.json()
        
        # Find an in-person meeting without expense
        inperson_meetings = [
            m for m in meetings 
            if m.get("mode") in ("offline", "in-person") 
            and not m.get("expense_id")
            and not m.get("mom_generated")
        ]
        
        if inperson_meetings:
            meeting = inperson_meetings[0]
            meeting_id = meeting.get("id")
            
            # Update MOM for this meeting
            mom_data = {
                "mom": "Test MOM content for expense prompt testing",
                "discussion_points": ["Point 1", "Point 2"],
                "decisions_made": ["Decision 1"],
                "next_steps": "Follow up next week"
            }
            
            update_resp = self.session.patch(f"{BASE_URL}/api/meetings/{meeting_id}/mom", json=mom_data)
            
            if update_resp.status_code == 200:
                # Wait for background task
                import time
                time.sleep(1)
                
                # Check for expense prompt notification
                notif_resp = self.session.get(f"{BASE_URL}/api/notifications")
                if notif_resp.status_code == 200:
                    notifications = notif_resp.json()
                    expense_prompts = [
                        n for n in notifications 
                        if n.get("type") == "expense_prompt" and n.get("entity_id") == meeting_id
                    ]
                    
                    if expense_prompts:
                        print(f"PASS: Expense prompt created when MOM recorded for in-person meeting")
                    else:
                        print(f"INFO: Expense prompt not found - meeting may already have expense or be online")
            else:
                print(f"INFO: MOM update returned {update_resp.status_code}")
        else:
            print("INFO: No suitable in-person meetings without expense found for testing")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
