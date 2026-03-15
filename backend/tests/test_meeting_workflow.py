"""
Backend API Tests for Sales Meeting/MOM Workflow
Tests the fixes for:
1. Meeting History API endpoint fix (/meetings/lead/{lead_id})
2. MOM recording and email notification
3. Previous meetings context retrieval
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SALES_EMPLOYEE_ID = "EMP003"
SALES_PASSWORD = "Sales@123"
TEST_LEAD_ID = "2e8724b1-b9b7-4983-b3cc-6c47e5de4851"


class TestMeetingWorkflow:
    """Tests for Meeting Record and MOM functionality"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": SALES_EMPLOYEE_ID, "password": SALES_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.user = data.get("user", {})
        yield

    def test_1_meetings_lead_endpoint_returns_meetings(self):
        """TEST: /api/meetings/lead/{lead_id} returns meetings for lead - BUG FIX"""
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{TEST_LEAD_ID}",
            headers=self.headers
        )
        
        # Status code check
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Data validation
        meetings = response.json()
        assert isinstance(meetings, list), "Response should be a list of meetings"
        assert len(meetings) > 0, "Should have at least one meeting for this lead"
        
        # Validate meeting structure
        first_meeting = meetings[0]
        assert "id" in first_meeting, "Meeting should have id"
        assert "lead_id" in first_meeting, "Meeting should have lead_id"
        assert first_meeting["lead_id"] == TEST_LEAD_ID, f"Meeting lead_id should match {TEST_LEAD_ID}"
        assert "mom" in first_meeting, "Meeting should have mom field"
        assert "meeting_date" in first_meeting, "Meeting should have meeting_date"
        
        print(f"✓ Found {len(meetings)} meeting(s) for lead - BUG FIX VERIFIED")

    def test_2_meeting_history_shows_mom_filled(self):
        """TEST: Meetings show MOM filled status"""
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{TEST_LEAD_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        meetings = response.json()
        
        # Check all meetings have MOM
        for meeting in meetings:
            assert meeting.get("mom_generated", False) == True, "Meeting should have mom_generated=True"
            assert meeting.get("mom"), "Meeting should have MOM summary filled"
        
        print(f"✓ All {len(meetings)} meetings have MOM filled")

    def test_3_meeting_has_timestamp_fields(self):
        """TEST: Meetings have proper timestamp (date and time)"""
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{TEST_LEAD_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        meetings = response.json()
        
        for meeting in meetings:
            # Check meeting_date exists
            assert "meeting_date" in meeting, "Meeting should have meeting_date"
            assert meeting["meeting_date"], "meeting_date should not be empty"
            
            # Check meeting_time exists
            assert "meeting_time" in meeting, "Meeting should have meeting_time"
            
            # Check created_at timestamp
            assert "created_at" in meeting, "Meeting should have created_at"
        
        print("✓ Timestamp fields verified for all meetings")

    def test_4_meeting_has_attendees(self):
        """TEST: Meetings have attendee information"""
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{TEST_LEAD_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200
        meetings = response.json()
        
        for meeting in meetings:
            assert "attendees" in meeting, "Meeting should have attendees field"
            # Attendees should be a list
            assert isinstance(meeting.get("attendees", []), list), "Attendees should be a list"
        
        print("✓ Attendee information verified")

    def test_5_meeting_record_endpoint_validates_mom_required(self):
        """TEST: POST /api/meetings/record requires MOM"""
        # Try to create meeting without MOM
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": "2026-03-15",
            "meeting_time": "14:00",
            "meeting_type": "Online",
            "attendees": ["Test Attendee"],
            # mom field intentionally missing
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=payload,
            headers=self.headers
        )
        
        # Should fail because MOM is required
        assert response.status_code == 400, f"Should return 400 without MOM, got {response.status_code}"
        assert "MOM" in response.json().get("detail", ""), "Error should mention MOM is required"
        
        print("✓ MOM validation working - prevents submission without MOM")

    def test_6_meeting_record_endpoint_creates_meeting_with_mom(self):
        """TEST: POST /api/meetings/record creates meeting with MOM"""
        import uuid
        test_id = str(uuid.uuid4())[:8]
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": "2026-03-15",
            "meeting_time": "15:00",
            "meeting_type": "Online",
            "title": f"TEST_Meeting_{test_id}",
            "attendees": ["Test Attendee"],
            "notes": "Test notes",
            "mom": f"TEST MOM Summary - {test_id}",
            "discussion_points": ["Point 1", "Point 2"],
            "client_expectations": ["Expectation 1"],
            "key_commitments": ["Commitment 1"],
            "next_steps": "Follow up next week"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=payload,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Should return 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "meeting_id" in data, "Response should contain meeting_id"
        assert "meeting" in data, "Response should contain meeting object"
        
        meeting = data["meeting"]
        assert meeting["mom"] == payload["mom"], "MOM should match submitted value"
        assert meeting["title"] == payload["title"], "Title should match"
        
        print(f"✓ Meeting created successfully with ID: {data['meeting_id']}")

    def test_7_lead_exists_for_meetings(self):
        """TEST: Lead exists for meeting operations"""
        response = requests.get(
            f"{BASE_URL}/api/leads/{TEST_LEAD_ID}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Lead should exist, got {response.status_code}"
        
        lead = response.json()
        assert lead.get("id") == TEST_LEAD_ID, "Lead ID should match"
        assert lead.get("company"), "Lead should have company name"
        
        # Check lead has email for MOM notification
        email = lead.get("email") or lead.get("contact_email")
        print(f"✓ Lead exists: {lead.get('first_name')} {lead.get('last_name')} - {lead.get('company')}")
        if email:
            print(f"  Client email available: {email}")
        else:
            print("  Note: No client email configured for MOM notification")


class TestEmailTemplates:
    """Tests for MOM email template functionality"""

    def test_email_template_import(self):
        """TEST: Email template function exists and returns proper structure"""
        # This tests the funnel_notifications module structure
        try:
            from services.funnel_notifications import meeting_mom_filled_email
            
            result = meeting_mom_filled_email(
                lead_name="Test Lead",
                company="Test Company",
                meeting_title="Test Meeting",
                meeting_date="2026-03-15",
                meeting_time="10:00",
                meeting_type="Online",
                attendees=["Attendee 1"],
                mom_summary="Test MOM Summary",
                client_expectations=["Expectation 1"],
                key_commitments=["Commitment 1"],
                salesperson_name="Test Sales",
                app_url="https://example.com",
                previous_meetings=[{"meeting_date": "2026-03-14", "mom": "Previous MOM"}],
                is_client_copy=False
            )
            
            assert "subject" in result, "Email result should have subject"
            assert "html" in result, "Email result should have html content"
            assert "plain" in result, "Email result should have plain text"
            
            # Verify previous meeting context is included
            assert "Previous Meeting Context" in result["html"], "Should include previous meeting context"
            
            print("✓ Email template function works with previous meetings context")
        except ImportError as e:
            pytest.skip(f"Cannot import email template: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
