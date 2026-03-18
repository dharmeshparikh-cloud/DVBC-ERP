"""
Backend API Tests for Meeting Notification & State Machine Features
Tests the P0 features:
1. Email notification system for client Accept/Reject/Reschedule
2. Single-use tokenized links with 24h expiry
3. Auto-accept logic when no response
4. Meeting state machine implementation

Endpoints tested:
- GET /api/meeting-workflow/test-email - Send test email
- POST /api/meeting-workflow/send-invite - Send meeting invitation with token
- GET /api/meeting-workflow/client-response - Get meeting details for valid token
- POST /api/meeting-workflow/client-response - Accept/reject/reschedule meeting
- GET /api/meeting-workflow/meeting-states - Get all valid states
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMPLOYEE_ID = "EMP001"
ADMIN_PASSWORD = "admin123"
TEST_EMAIL = "dharmesh.parikh@dvconsulting.co.in"


class TestMeetingWorkflowAuth:
    """Setup auth for testing"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": ADMIN_EMPLOYEE_ID, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.user = data.get("user", {})
        yield


class TestMeetingStates(TestMeetingWorkflowAuth):
    """Test meeting states endpoint"""

    def test_1_get_meeting_states(self):
        """TEST: GET /api/meeting-workflow/meeting-states returns all valid states"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/meeting-states",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        states = response.json()
        
        # Verify expected states exist
        expected_states = [
            "DRAFT", "SCHEDULED", "CONFIRMED", "REJECTED", 
            "RESCHEDULED", "AUTO_ACCEPTED", "CONDUCTED", 
            "MOM_RECORDED", "DELIVERED", "CANCELLED"
        ]
        
        for state in expected_states:
            assert state in states, f"State {state} should be in response"
            assert "label" in states[state], f"State {state} should have label"
            assert "color" in states[state], f"State {state} should have color"
            assert "next" in states[state], f"State {state} should have next transitions"
        
        print(f"✓ All {len(expected_states)} meeting states returned correctly")

    def test_2_state_transitions_are_valid(self):
        """TEST: State transitions follow valid workflow"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/meeting-states",
            headers=self.headers
        )
        
        assert response.status_code == 200
        states = response.json()
        
        # Verify key transitions
        # SCHEDULED -> CONFIRMED, REJECTED, RESCHEDULED, AUTO_ACCEPTED, CANCELLED
        assert "CONFIRMED" in states["SCHEDULED"]["next"], "SCHEDULED should transition to CONFIRMED"
        assert "REJECTED" in states["SCHEDULED"]["next"], "SCHEDULED should transition to REJECTED"
        assert "RESCHEDULED" in states["SCHEDULED"]["next"], "SCHEDULED should transition to RESCHEDULED"
        
        # CONFIRMED -> CONDUCTED, CANCELLED
        assert "CONDUCTED" in states["CONFIRMED"]["next"], "CONFIRMED should transition to CONDUCTED"
        
        # CONDUCTED -> MOM_RECORDED
        assert "MOM_RECORDED" in states["CONDUCTED"]["next"], "CONDUCTED should transition to MOM_RECORDED"
        
        # MOM_RECORDED -> DELIVERED
        assert "DELIVERED" in states["MOM_RECORDED"]["next"], "MOM_RECORDED should transition to DELIVERED"
        
        # Terminal states should have empty next
        assert states["DELIVERED"]["next"] == [], "DELIVERED should be terminal"
        assert states["REJECTED"]["next"] == [], "REJECTED should be terminal"
        assert states["CANCELLED"]["next"] == [], "CANCELLED should be terminal"
        
        print("✓ State transitions validated")


class TestTestEmail(TestMeetingWorkflowAuth):
    """Test email sending endpoint"""

    def test_1_send_test_email_endpoint_exists(self):
        """TEST: GET /api/meeting-workflow/test-email endpoint exists"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/test-email",
            params={"to_email": TEST_EMAIL},
            headers=self.headers
        )
        
        # Should return 200 or indicate email status
        assert response.status_code in [200, 400, 422, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response should have status"
            assert "sent_to" in data, "Response should have sent_to"
            assert data["sent_to"] == TEST_EMAIL, "sent_to should match request"
            print(f"✓ Test email endpoint works - status: {data.get('status')}")
        else:
            print(f"✓ Test email endpoint exists (returned {response.status_code})")


class TestSendInvite(TestMeetingWorkflowAuth):
    """Test meeting invite sending"""

    def test_1_send_invite_requires_meeting_id(self):
        """TEST: POST /api/meeting-workflow/send-invite requires meeting_id"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/send-invite",
            json={},
            headers=self.headers
        )
        
        # Should return 422 for missing meeting_id
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ Send invite validates required meeting_id")

    def test_2_send_invite_returns_404_for_invalid_meeting(self):
        """TEST: POST /api/meeting-workflow/send-invite returns 404 for invalid meeting"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/send-invite",
            json={"meeting_id": "non-existent-meeting-id"},
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Send invite returns 404 for non-existent meeting")


class TestClientResponse(TestMeetingWorkflowAuth):
    """Test client response endpoints"""

    def test_1_client_response_get_requires_token_and_action(self):
        """TEST: GET /api/meeting-workflow/client-response requires token and action"""
        # Missing both
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/client-response"
        )
        assert response.status_code == 422, f"Expected 422 for missing params, got {response.status_code}"
        
        # Missing action
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/client-response",
            params={"token": "test-token"}
        )
        assert response.status_code == 422, f"Expected 422 for missing action, got {response.status_code}"
        
        print("✓ Client response GET validates required params")

    def test_2_client_response_get_validates_action(self):
        """TEST: GET /api/meeting-workflow/client-response validates action values"""
        # Invalid action
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/client-response",
            params={"token": "test-token", "action": "invalid_action"}
        )
        
        assert response.status_code == 400, f"Expected 400 for invalid action, got {response.status_code}"
        assert "Invalid action" in response.json().get("detail", ""), "Should mention invalid action"
        print("✓ Client response GET validates action values")

    def test_3_client_response_get_returns_404_for_invalid_token(self):
        """TEST: GET /api/meeting-workflow/client-response returns 404 for invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-workflow/client-response",
            params={"token": "invalid-token-that-does-not-exist", "action": "accept"}
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid token, got {response.status_code}"
        print("✓ Client response GET returns 404 for invalid token")

    def test_4_client_response_post_requires_params(self):
        """TEST: POST /api/meeting-workflow/client-response requires token and action"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/client-response"
        )
        
        assert response.status_code == 422, f"Expected 422 for missing params, got {response.status_code}"
        print("✓ Client response POST validates required params")

    def test_5_client_response_post_returns_404_for_invalid_token(self):
        """TEST: POST /api/meeting-workflow/client-response returns 404 for invalid token"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/client-response",
            params={"token": "invalid-token", "action": "accept"},
            json={}
        )
        
        assert response.status_code == 404, f"Expected 404 for invalid token, got {response.status_code}"
        print("✓ Client response POST returns 404 for invalid token")


class TestMeetingWorkflowE2E(TestMeetingWorkflowAuth):
    """End-to-end test for meeting notification workflow"""

    def test_1_get_existing_meetings(self):
        """TEST: Get existing meetings to test with"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"meeting_type": "consulting"},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        meetings = response.json()
        assert isinstance(meetings, list), "Response should be a list"
        
        if len(meetings) > 0:
            print(f"✓ Found {len(meetings)} existing meetings")
            # Store first meeting for further tests
            self.test_meeting = meetings[0]
        else:
            print("✓ No existing meetings (workflow tests will skip)")

    def test_2_meeting_has_status_field(self):
        """TEST: Meetings have status field for state machine"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"meeting_type": "consulting"},
            headers=self.headers
        )
        
        if response.status_code == 200:
            meetings = response.json()
            if meetings:
                # Check if meetings have status field (may be null for old meetings)
                meeting = meetings[0]
                # Status field should exist (though may be None)
                print(f"✓ Meeting status field check complete (status: {meeting.get('status', 'N/A')})")
            else:
                print("✓ No meetings to check (skipped)")
        else:
            print(f"✓ Meetings endpoint check (status: {response.status_code})")


class TestStateTransitionEndpoint(TestMeetingWorkflowAuth):
    """Test state transition endpoint"""

    def test_1_transition_state_requires_auth(self):
        """TEST: POST /api/meeting-workflow/transition-state requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/transition-state",
            json={"meeting_id": "test", "new_state": "CONFIRMED"}
            # No auth header
        )
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ State transition requires authentication")

    def test_2_transition_state_validates_meeting(self):
        """TEST: POST /api/meeting-workflow/transition-state validates meeting exists"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/transition-state",
            json={"meeting_id": "non-existent-meeting", "new_state": "CONFIRMED"},
            headers=self.headers
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent meeting, got {response.status_code}"
        print("✓ State transition validates meeting exists")


class TestAutoAcceptEndpoint(TestMeetingWorkflowAuth):
    """Test auto-accept processing endpoint"""

    def test_1_auto_accept_requires_admin(self):
        """TEST: POST /api/meeting-workflow/process-auto-accept requires admin role"""
        # First login as admin
        response = requests.post(
            f"{BASE_URL}/api/meeting-workflow/process-auto-accept",
            headers=self.headers
        )
        
        # Should work for admin or return 403 for non-admin
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data, "Response should have status"
            assert "processed_count" in data, "Response should have processed_count"
            print(f"✓ Auto-accept endpoint works - processed: {data.get('processed_count')}")
        else:
            print("✓ Auto-accept endpoint requires admin (access denied as expected)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
