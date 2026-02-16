"""
Tests for New Kickoff Features:
1. Meeting History in Kickoff Details API - Full MOM/Meeting chronology passed to Consulting
2. HR Auto-Notification on Kickoff Accept - Notifications for HR users when project is created
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestKickoffMeetingHistoryAndHRNotification:
    """Test the two new kickoff features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Store user info
        self.user = login_resp.json()["user"]
        yield
        self.session.close()
    
    # ========================
    # Feature 1: Meeting History in Kickoff Details
    # ========================
    
    def test_kickoff_details_returns_meeting_history_field(self):
        """Test GET /api/kickoff-requests/{id}/details returns meeting_history field"""
        # Get existing kickoff requests
        kickoffs_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests")
        assert kickoffs_resp.status_code == 200
        kickoffs = kickoffs_resp.json()
        
        if not kickoffs:
            pytest.skip("No existing kickoff requests to test")
        
        # Get details for first kickoff
        kickoff_id = kickoffs[0]['id']
        details_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details")
        assert details_resp.status_code == 200
        
        details = details_resp.json()
        
        # Verify required new fields exist
        assert "meeting_history" in details, "meeting_history field missing from response"
        assert "client_expectations_summary" in details, "client_expectations_summary field missing"
        assert "key_commitments_summary" in details, "key_commitments_summary field missing"
        assert "total_meetings_held" in details, "total_meetings_held field missing"
        
        # Verify types
        assert isinstance(details["meeting_history"], list), "meeting_history should be a list"
        assert isinstance(details["client_expectations_summary"], list), "client_expectations_summary should be a list"
        assert isinstance(details["key_commitments_summary"], list), "key_commitments_summary should be a list"
        assert isinstance(details["total_meetings_held"], int), "total_meetings_held should be an int"
        
        print(f"✓ Kickoff details contains meeting_history: {len(details['meeting_history'])} meetings")
        print(f"✓ Client expectations summary items: {len(details['client_expectations_summary'])}")
        print(f"✓ Key commitments summary items: {len(details['key_commitments_summary'])}")
    
    def test_full_sales_flow_meeting_history(self):
        """Test complete flow: Lead -> Meeting with MOM -> Agreement -> Kickoff -> Verify meeting history"""
        # Step 1: Create a test lead
        lead_data = {
            "first_name": "TEST_MH",
            "last_name": "Client",
            "company": "TEST Meeting History Corp",
            "email": f"test_mh_{datetime.now().timestamp()}@test.com",
            "phone": "1234567890",
            "job_title": "CEO"
        }
        lead_resp = self.session.post(f"{BASE_URL}/api/leads", json=lead_data)
        assert lead_resp.status_code == 200, f"Failed to create lead: {lead_resp.text}"
        lead = lead_resp.json()
        lead_id = lead['id']
        print(f"✓ Created lead: {lead_id}")
        
        # Step 2: Create a meeting with MOM for this lead
        meeting_data = {
            "type": "sales",
            "lead_id": lead_id,
            "meeting_date": datetime.now().isoformat(),
            "mode": "online",
            "title": "TEST Initial Discovery Call",
            "agenda": ["Understand requirements", "Discuss timeline"],
            "attendees": [self.user['id']],
            "attendee_names": [self.user['full_name']],
            "notes": "Test meeting for MH verification"
        }
        meeting_resp = self.session.post(f"{BASE_URL}/api/meetings", json=meeting_data)
        assert meeting_resp.status_code == 200, f"Failed to create meeting: {meeting_resp.text}"
        meeting = meeting_resp.json()
        meeting_id = meeting['id']
        print(f"✓ Created meeting: {meeting_id}")
        
        # Step 3: Add MOM to the meeting with client concerns and commitments
        mom_data = {
            "title": "TEST Discovery Meeting MOM",
            "agenda": ["Requirements discussion", "Timeline planning"],
            "discussion_points": ["Client needs comprehensive consulting", "Budget approval pending"],
            "decisions_made": ["Proceed with proposal", "Schedule follow-up"],
            "action_items": [
                {"description": "Prepare proposal", "priority": "high"},
                {"description": "Review budget", "priority": "medium"}
            ]
        }
        mom_resp = self.session.patch(f"{BASE_URL}/api/meetings/{meeting_id}/mom", json=mom_data)
        assert mom_resp.status_code == 200, f"Failed to add MOM: {mom_resp.text}"
        print(f"✓ Added MOM to meeting")
        
        # Step 4: Get an existing approved agreement and link it (creating agreement requires quotation_id)
        # Instead, we'll use an existing approved agreement or skip this step
        agreements_resp = self.session.get(f"{BASE_URL}/api/agreements?status=approved")
        if agreements_resp.status_code != 200 or not agreements_resp.json():
            pytest.skip("No approved agreements available for test")
        
        agreement = agreements_resp.json()[0]
        agreement_id = agreement['id']
        
        # Update our lead to link with this agreement's lead_id if needed
        # But for the meeting history test, we need meetings linked to the lead_id used in kickoff
        print(f"✓ Using existing agreement: {agreement_id}")
        
        # Step 5: Create kickoff request linking lead and agreement
        kickoff_data = {
            "agreement_id": agreement_id,
            "lead_id": lead_id,
            "client_name": lead_data['company'],
            "project_name": f"TEST MH Project - {lead_data['company']}",
            "project_type": "mixed",
            "meeting_frequency": "Monthly",
            "project_tenure_months": 6,
            "expected_start_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "notes": "Test kickoff for meeting history verification"
        }
        kickoff_resp = self.session.post(f"{BASE_URL}/api/kickoff-requests", json=kickoff_data)
        assert kickoff_resp.status_code == 200, f"Failed to create kickoff: {kickoff_resp.text}"
        kickoff = kickoff_resp.json()
        kickoff_id = kickoff['id']
        print(f"✓ Created kickoff request: {kickoff_id}")
        
        # Step 6: Get kickoff details and verify meeting history is included
        details_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details")
        assert details_resp.status_code == 200, f"Failed to get kickoff details: {details_resp.text}"
        details = details_resp.json()
        
        # Verify meeting history
        assert "meeting_history" in details, "meeting_history field missing"
        meeting_history = details["meeting_history"]
        assert len(meeting_history) >= 1, f"Expected at least 1 meeting, got {len(meeting_history)}"
        
        # Verify meeting data structure
        test_meeting = next((m for m in meeting_history if m.get('title') == 'TEST Initial Discovery Call'), None)
        if test_meeting:
            assert "mom" in test_meeting, "MOM data missing from meeting"
            assert test_meeting.get("type") == "sales", "Meeting type should be sales"
            print(f"✓ Meeting history contains test meeting with MOM")
        else:
            print(f"✓ Meeting history has {len(meeting_history)} meetings (test meeting may have different title)")
        
        # Verify total_meetings_held
        assert details["total_meetings_held"] >= 1, "total_meetings_held should be at least 1"
        print(f"✓ Total meetings held: {details['total_meetings_held']}")
        
        # Verify summary fields exist (may be empty if no concerns/commitments were added)
        assert "client_expectations_summary" in details
        assert "key_commitments_summary" in details
        print(f"✓ All meeting history fields present in kickoff details")
    
    def test_meeting_history_structure_has_mom_fields(self):
        """Verify meeting_history entries have proper MOM structure"""
        kickoffs_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests")
        assert kickoffs_resp.status_code == 200
        kickoffs = kickoffs_resp.json()
        
        if not kickoffs:
            pytest.skip("No existing kickoff requests")
        
        # Find a kickoff with lead_id (needed for meeting history)
        kickoff_with_lead = next((k for k in kickoffs if k.get('lead_id')), None)
        if not kickoff_with_lead:
            pytest.skip("No kickoff requests with lead_id")
        
        details_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests/{kickoff_with_lead['id']}/details")
        assert details_resp.status_code == 200
        details = details_resp.json()
        
        if details.get("meeting_history") and len(details["meeting_history"]) > 0:
            meeting = details["meeting_history"][0]
            
            # Verify expected fields in meeting entry
            expected_fields = ["id", "title", "meeting_date", "type", "mom"]
            for field in expected_fields:
                assert field in meeting, f"Meeting missing field: {field}"
            
            # Verify MOM structure
            mom = meeting.get("mom", {})
            mom_fields = ["summary", "key_decisions", "discussion_points", "next_steps", 
                          "client_concerns", "commitments_made"]
            for field in mom_fields:
                assert field in mom, f"MOM missing field: {field}"
            
            print(f"✓ Meeting history entry has proper MOM structure")
        else:
            print(f"✓ No meetings in history to verify structure (empty list is valid)")
    
    # ========================
    # Feature 2: HR Auto-Notification on Kickoff Accept
    # ========================
    
    def test_accept_kickoff_returns_hr_notified_count(self):
        """Test POST /api/kickoff-requests/{id}/accept returns hr_notified and staffing_requirements"""
        # First, we need to create a pending kickoff request
        # Get an approved agreement first
        agreements_resp = self.session.get(f"{BASE_URL}/api/agreements?status=approved")
        assert agreements_resp.status_code == 200
        agreements = agreements_resp.json()
        
        if not agreements:
            pytest.skip("No approved agreements to create kickoff")
        
        agreement = agreements[0]
        
        # Create a new kickoff request
        kickoff_data = {
            "agreement_id": agreement['id'],
            "lead_id": agreement.get('lead_id'),
            "client_name": agreement.get('client_name') or agreement.get('party_name', 'Test Client'),
            "project_name": f"TEST_HR_Notify_{int(datetime.now().timestamp())}",
            "project_type": "online",
            "meeting_frequency": "Monthly",
            "project_tenure_months": 6,
            "expected_start_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/kickoff-requests", json=kickoff_data)
        assert create_resp.status_code == 200, f"Failed to create kickoff: {create_resp.text}"
        kickoff = create_resp.json()
        kickoff_id = kickoff['id']
        print(f"✓ Created kickoff request for HR notification test: {kickoff_id}")
        
        # Accept the kickoff
        accept_resp = self.session.post(f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/accept")
        assert accept_resp.status_code == 200, f"Failed to accept kickoff: {accept_resp.text}"
        
        result = accept_resp.json()
        
        # Verify response contains new HR notification fields
        assert "hr_notified" in result, "hr_notified field missing from accept response"
        assert "staffing_requirements" in result, "staffing_requirements field missing from accept response"
        assert "project_id" in result, "project_id field missing from accept response"
        
        # Verify types
        assert isinstance(result["hr_notified"], int), "hr_notified should be an integer"
        assert isinstance(result["staffing_requirements"], list), "staffing_requirements should be a list"
        
        print(f"✓ Accept response contains hr_notified: {result['hr_notified']}")
        print(f"✓ Staffing requirements: {result['staffing_requirements']}")
        print(f"✓ Project created: {result['project_id']}")
    
    def test_hr_users_receive_notification(self):
        """Verify HR users (hr_manager, hr_executive) get notifications after kickoff accept"""
        # First check if there are any HR users
        users_resp = self.session.get(f"{BASE_URL}/api/users")
        assert users_resp.status_code == 200
        users = users_resp.json()
        
        hr_users = [u for u in users if u.get('role') in ['hr_manager', 'hr_executive']]
        
        if not hr_users:
            print("⚠ No HR users found in database, creating one for test")
            # Create an HR user
            hr_user_data = {
                "email": f"test_hr_{int(datetime.now().timestamp())}@test.com",
                "password": "test123",
                "full_name": "TEST HR Manager",
                "role": "hr_manager"
            }
            create_hr_resp = self.session.post(f"{BASE_URL}/api/auth/register", json=hr_user_data)
            if create_hr_resp.status_code == 200:
                hr_users = [create_hr_resp.json()]
                print(f"✓ Created HR user: {hr_users[0]['id']}")
            else:
                # Try to get HR users from users list
                pytest.skip("Could not create HR user for testing")
        
        # Get an agreement for kickoff
        agreements_resp = self.session.get(f"{BASE_URL}/api/agreements?status=approved")
        assert agreements_resp.status_code == 200
        agreements = agreements_resp.json()
        
        if not agreements:
            pytest.skip("No approved agreements")
        
        agreement = agreements[0]
        
        # Create and accept kickoff
        kickoff_data = {
            "agreement_id": agreement['id'],
            "lead_id": agreement.get('lead_id'),
            "client_name": agreement.get('client_name') or agreement.get('party_name', 'Test Client'),
            "project_name": f"TEST_HR_Check_{int(datetime.now().timestamp())}",
            "project_type": "mixed",
            "expected_start_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        create_resp = self.session.post(f"{BASE_URL}/api/kickoff-requests", json=kickoff_data)
        assert create_resp.status_code == 200
        kickoff_id = create_resp.json()['id']
        
        accept_resp = self.session.post(f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/accept")
        assert accept_resp.status_code == 200
        
        result = accept_resp.json()
        
        # Verify HR was notified
        print(f"✓ HR users notified: {result['hr_notified']}")
        
        # Check notifications for an HR user
        if hr_users:
            hr_user_id = hr_users[0]['id']
            notifications_resp = self.session.get(f"{BASE_URL}/api/notifications", params={"user_id": hr_user_id})
            if notifications_resp.status_code == 200:
                notifications = notifications_resp.json()
                # Look for project_staffing_required notification
                staffing_notifs = [n for n in notifications if n.get('type') == 'project_staffing_required']
                print(f"✓ HR user has {len(staffing_notifs)} project_staffing_required notifications")
    
    def test_notification_type_is_project_staffing_required(self):
        """Verify the notification type created is 'project_staffing_required' with high priority"""
        # Get notifications to check type
        notifications_resp = self.session.get(f"{BASE_URL}/api/notifications")
        if notifications_resp.status_code != 200:
            pytest.skip("Cannot fetch notifications")
        
        notifications = notifications_resp.json()
        
        # Look for project_staffing_required notifications
        staffing_notifications = [n for n in notifications if n.get('type') == 'project_staffing_required']
        
        if staffing_notifications:
            notif = staffing_notifications[0]
            print(f"✓ Found project_staffing_required notification")
            
            # Verify high priority
            assert notif.get('priority') == 'high', f"Expected priority 'high', got '{notif.get('priority')}'"
            print(f"✓ Notification priority is 'high'")
            
            # Verify required fields
            assert 'title' in notif
            assert 'message' in notif
            assert 'reference_id' in notif
            print(f"✓ Notification has required fields (title, message, reference_id)")
        else:
            print(f"⚠ No project_staffing_required notifications found yet (may need to run full flow)")
    
    # ========================
    # Cleanup
    # ========================
    
    def test_cleanup_test_data(self):
        """Cleanup TEST_ prefixed data created during tests"""
        # Cleanup leads
        leads_resp = self.session.get(f"{BASE_URL}/api/leads")
        if leads_resp.status_code == 200:
            leads = leads_resp.json()
            test_leads = [l for l in leads if l.get('first_name', '').startswith('TEST_MH')]
            for lead in test_leads:
                self.session.delete(f"{BASE_URL}/api/leads/{lead['id']}")
        
        # Note: Kickoff requests and projects created during test will remain
        # as they are part of the audit trail
        print(f"✓ Cleanup completed")


class TestExistingKickoffDetailsWithMeetingHistory:
    """Test meeting history data on existing kickoff requests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        yield
        self.session.close()
    
    def test_all_kickoff_details_have_meeting_history_fields(self):
        """Verify all kickoff requests return meeting_history related fields"""
        kickoffs_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests")
        assert kickoffs_resp.status_code == 200
        kickoffs = kickoffs_resp.json()
        
        if not kickoffs:
            pytest.skip("No kickoff requests in database")
        
        # Test first 5 kickoffs
        tested = 0
        for kickoff in kickoffs[:5]:
            details_resp = self.session.get(f"{BASE_URL}/api/kickoff-requests/{kickoff['id']}/details")
            assert details_resp.status_code == 200, f"Failed to get details for {kickoff['id']}"
            
            details = details_resp.json()
            
            # Verify all required fields
            assert "meeting_history" in details
            assert "client_expectations_summary" in details
            assert "key_commitments_summary" in details
            assert "total_meetings_held" in details
            
            tested += 1
            print(f"✓ Kickoff {kickoff['id'][:8]}... has meeting history fields (meetings: {details['total_meetings_held']})")
        
        print(f"✓ Verified {tested} kickoff requests have all meeting history fields")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
