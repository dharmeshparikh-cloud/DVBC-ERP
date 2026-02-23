"""
Test Suite: Sales Funnel Meeting-Lead Linkage Feature
Tests for new endpoints and features:
- POST /api/meetings/record - Record sales funnel meeting with MOM
- GET /api/meetings/lead/{lead_id} - List all meetings for a lead
- GET /api/leads/{lead_id}/funnel-progress - Returns completed steps including meeting_count
- GET /api/kickoff-requests/{id}/details - Returns meeting_history, funnel_steps_summary
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "ADMIN001", "password": "test123"}
SALES_CREDS = {"employee_id": "SE001", "password": "test123"}

# Test lead ID from the request
TEST_LEAD_ID = "604b0885-0225-4028-94a6-d19b4261181f"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def sales_token(self):
        """Get sales exec authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        assert response.status_code == 200, f"Sales login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"Admin login successful: {data['user'].get('full_name')}")
    
    def test_sales_login(self):
        """Test sales exec login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        print(f"Sales login successful: {data['user'].get('full_name')}")


class TestMeetingRecordEndpoint:
    """Tests for POST /api/meetings/record endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get auth header for sales user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_record_meeting_success(self, auth_header):
        """Test successful meeting recording with MOM"""
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "14:00",
            "meeting_type": "Online",
            "title": "Test Sales Meeting - Feature Test",
            "attendees": ["John Doe", "Jane Smith"],
            "mom": "Test meeting MOM - discussed project requirements, pricing structure, and timeline. Key decisions: proceed with phase 1 implementation.",
            "notes": "Initial sales discussion",
            "discussion_points": ["Project requirements", "Pricing structure", "Timeline"],
            "decisions_made": ["Proceed with phase 1"],
            "client_expectations": ["Quick delivery", "Regular updates"],
            "key_commitments": ["Weekly status calls", "Dedicated team"],
            "next_steps": "Prepare detailed proposal"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=payload,
            headers=auth_header
        )
        
        assert response.status_code == 200, f"Meeting record failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "message" in data
        assert "meeting_id" in data
        assert "meeting" in data
        assert data["message"] == "Meeting recorded successfully with MOM"
        
        meeting = data["meeting"]
        assert meeting["lead_id"] == TEST_LEAD_ID
        assert meeting["mom"] == payload["mom"]
        assert meeting["mom_generated"] == True
        assert "client_expectations" in meeting
        assert "key_commitments" in meeting
        
        print(f"Meeting recorded: {data['meeting_id']}")
        return data["meeting_id"]
    
    def test_record_meeting_without_mom_fails(self, auth_header):
        """Test that meeting cannot be recorded without MOM"""
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "15:00",
            "meeting_type": "Offline",
            "mom": "",  # Empty MOM should fail
            "notes": "Test meeting without MOM"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=payload,
            headers=auth_header
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "MOM" in data["detail"] or "Minutes" in data["detail"]
        print("Correctly rejected meeting without MOM")
    
    def test_record_meeting_without_lead_id_fails(self, auth_header):
        """Test that lead_id is required"""
        payload = {
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "15:00",
            "meeting_type": "Online",
            "mom": "Test MOM content"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=payload,
            headers=auth_header
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "lead_id" in data["detail"].lower()
        print("Correctly rejected meeting without lead_id")
    
    def test_record_meeting_invalid_lead_fails(self, auth_header):
        """Test that invalid lead_id returns 404"""
        payload = {
            "lead_id": "non-existent-lead-id-12345",
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "15:00",
            "meeting_type": "Online",
            "mom": "Test MOM content"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=payload,
            headers=auth_header
        )
        
        assert response.status_code == 404
        print("Correctly returned 404 for invalid lead")


class TestMeetingsByLeadEndpoint:
    """Tests for GET /api/meetings/lead/{lead_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_meetings_by_lead(self, auth_header):
        """Test fetching all meetings for a lead"""
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{TEST_LEAD_ID}",
            headers=auth_header
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        print(f"Found {len(data)} meetings for lead")
        
        # Verify meeting structure if any exist
        if len(data) > 0:
            meeting = data[0]
            assert "id" in meeting
            assert "lead_id" in meeting
            assert meeting["lead_id"] == TEST_LEAD_ID
            # Check for MOM fields
            if meeting.get("mom"):
                print(f"Meeting {meeting['id']} has MOM: {meeting['mom'][:50]}...")
    
    def test_get_meetings_invalid_lead_404(self, auth_header):
        """Test 404 for non-existent lead"""
        response = requests.get(
            f"{BASE_URL}/api/meetings/lead/non-existent-lead-xyz",
            headers=auth_header
        )
        
        assert response.status_code == 404
        print("Correctly returned 404 for non-existent lead")


class TestFunnelProgressEndpoint:
    """Tests for GET /api/leads/{lead_id}/funnel-progress endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_funnel_progress_structure(self, auth_header):
        """Test funnel progress returns correct structure with meeting data"""
        response = requests.get(
            f"{BASE_URL}/api/leads/{TEST_LEAD_ID}/funnel-progress",
            headers=auth_header
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "lead_id" in data
        assert data["lead_id"] == TEST_LEAD_ID
        assert "completed_steps" in data
        assert "current_step" in data
        assert "total_steps" in data
        assert "progress_percentage" in data
        
        # Verify meeting-related fields
        assert "meeting_count" in data
        assert "meeting_ids" in data
        assert isinstance(data["meeting_ids"], list)
        
        print(f"Funnel progress: {data['completed_count']}/{data['total_steps']} steps completed ({data['progress_percentage']}%)")
        print(f"Meetings: {data['meeting_count']} recorded, IDs: {data['meeting_ids']}")
        
        # Check if record_meeting step is marked complete when meetings exist
        if data["meeting_count"] > 0:
            assert "record_meeting" in data["completed_steps"], "record_meeting step should be complete when meetings exist"
            print("record_meeting step correctly marked as completed")
    
    def test_funnel_progress_includes_linked_ids(self, auth_header):
        """Test that funnel progress includes all linked IDs"""
        response = requests.get(
            f"{BASE_URL}/api/leads/{TEST_LEAD_ID}/funnel-progress",
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for all linked ID fields
        expected_fields = [
            "lead_id", "meeting_ids", "meeting_count", "last_meeting_date",
            "pricing_plan_id", "sow_id", "quotation_id", "agreement_id",
            "kickoff_id", "project_id"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"All linked ID fields present in funnel progress response")


class TestKickoffDetailsEndpoint:
    """Tests for GET /api/kickoff-requests/{id}/details endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_kickoff_list(self, auth_header):
        """First get list of kickoff requests to find one to test"""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=auth_header
        )
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                return data[0]["id"]
        return None
    
    def test_kickoff_details_structure(self, auth_header):
        """Test kickoff details returns full sales funnel summary"""
        # First get a kickoff request ID
        list_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=auth_header
        )
        
        if list_response.status_code != 200 or len(list_response.json()) == 0:
            pytest.skip("No kickoff requests available to test")
        
        kickoff_id = list_response.json()[0]["id"]
        
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details",
            headers=auth_header
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "kickoff_request" in data
        assert "meeting_history" in data
        assert "client_expectations_summary" in data
        assert "key_commitments_summary" in data
        assert "funnel_steps_summary" in data
        
        # Verify funnel_steps_summary structure
        funnel_summary = data["funnel_steps_summary"]
        expected_steps = ["lead_capture", "meetings", "pricing_plan", "sow", "quotation", "agreement", "payments"]
        
        for step in expected_steps:
            assert step in funnel_summary, f"Missing step in funnel_steps_summary: {step}"
            assert "completed" in funnel_summary[step]
            assert "data" in funnel_summary[step]
        
        # Check meetings summary
        meetings_summary = funnel_summary["meetings"]
        assert "count" in meetings_summary
        assert "data" in meetings_summary
        if meetings_summary["data"]:
            assert "total_meetings" in meetings_summary["data"]
            assert "client_expectations" in meetings_summary["data"]
            assert "key_commitments" in meetings_summary["data"]
        
        print(f"Kickoff details verified for: {kickoff_id}")
        print(f"Meeting history count: {len(data['meeting_history'])}")
        print(f"Client expectations: {data['client_expectations_summary']}")
        print(f"Key commitments: {data['key_commitments_summary']}")


class TestLeadAutoRedirect:
    """Tests for lead creation and auto-redirect behavior"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_create_lead_returns_id(self, auth_header):
        """Test lead creation returns ID for redirect"""
        payload = {
            "first_name": "TEST_MeetingLink",
            "last_name": "TestLead",
            "company": "TEST Meeting Link Company",
            "email": f"test_meeting_link_{datetime.now().timestamp()}@test.com",
            "phone": "9876543210",
            "source": "Testing"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/leads",
            json=payload,
            headers=auth_header
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["first_name"] == "TEST_MeetingLink"
        
        # Verify we can use this ID to access funnel-progress
        progress_response = requests.get(
            f"{BASE_URL}/api/leads/{data['id']}/funnel-progress",
            headers=auth_header
        )
        assert progress_response.status_code == 200
        progress = progress_response.json()
        
        # New lead should have lead_capture completed
        assert "lead_capture" in progress["completed_steps"]
        assert progress["current_step"] == "record_meeting"
        
        print(f"Created lead {data['id']} - ready for funnel navigation")
        print(f"Current step is: {progress['current_step']}")


class TestMeetingMOMIntegration:
    """Integration tests for meeting with MOM workflow"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_full_meeting_flow(self, auth_header):
        """Test complete meeting recording and verification flow"""
        # Step 1: Create a meeting with MOM
        meeting_payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": datetime.now().strftime("%Y-%m-%d"),
            "meeting_time": "11:00",
            "meeting_type": "Online",
            "title": "Integration Test Meeting",
            "attendees": ["Client Rep", "Sales Rep"],
            "mom": "Integration test MOM - full workflow verification. Discussed scope and next steps.",
            "discussion_points": ["Scope discussion", "Timeline review"],
            "decisions_made": ["Proceed with proposal"],
            "client_expectations": ["Fast turnaround"],
            "key_commitments": ["Proposal by Friday"],
            "next_steps": "Send proposal document"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=meeting_payload,
            headers=auth_header
        )
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        meeting_id = create_response.json()["meeting_id"]
        print(f"Step 1: Created meeting {meeting_id}")
        
        # Step 2: Verify meeting appears in lead's meetings list
        list_response = requests.get(
            f"{BASE_URL}/api/meetings/lead/{TEST_LEAD_ID}",
            headers=auth_header
        )
        
        assert list_response.status_code == 200
        meetings = list_response.json()
        meeting_ids = [m["id"] for m in meetings]
        assert meeting_id in meeting_ids, "Created meeting not found in lead's meeting list"
        print(f"Step 2: Meeting appears in lead's list ({len(meetings)} total)")
        
        # Step 3: Verify funnel progress reflects meeting
        progress_response = requests.get(
            f"{BASE_URL}/api/leads/{TEST_LEAD_ID}/funnel-progress",
            headers=auth_header
        )
        
        assert progress_response.status_code == 200
        progress = progress_response.json()
        assert progress["meeting_count"] > 0
        assert "record_meeting" in progress["completed_steps"]
        print(f"Step 3: Funnel progress shows {progress['meeting_count']} meetings")
        
        # Step 4: Verify meeting details via direct GET
        detail_response = requests.get(
            f"{BASE_URL}/api/meetings/{meeting_id}",
            headers=auth_header
        )
        
        assert detail_response.status_code == 200
        meeting_detail = detail_response.json()
        assert meeting_detail["mom"] == meeting_payload["mom"]
        assert meeting_detail["mom_generated"] == True
        print("Step 4: Meeting details verified")
        
        print("Full meeting flow integration test PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
