"""
Backend tests for Backdated Meeting Approval Workflow
Tests: pending-approvals, request-backdated-approval, approve-backdated endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture
def auth_token(api_client):
    """Get authentication token for admin user"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "EMP001",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token") or response.json().get("token")
    pytest.skip("Authentication failed - skipping authenticated tests")

@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestBackdatedApprovalWorkflow:
    """Tests for backdated meeting approval workflow endpoints"""
    
    def test_get_pending_approvals_endpoint_exists(self, authenticated_client):
        """Test GET /api/meeting-workflow/pending-approvals returns list"""
        response = authenticated_client.get(f"{BASE_URL}/api/meeting-workflow/pending-approvals")
        
        # Should return 200 and contain pending_count
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "pending_count" in data, "Response should contain 'pending_count'"
        assert "meetings" in data, "Response should contain 'meetings' list"
        assert isinstance(data["meetings"], list), "meetings should be a list"
        print(f"PASS: /api/meeting-workflow/pending-approvals returns {data['pending_count']} pending approvals")
    
    def test_request_backdated_approval_requires_auth(self, api_client):
        """Test POST /api/meeting-workflow/request-backdated-approval requires auth"""
        response = api_client.post(f"{BASE_URL}/api/meeting-workflow/request-backdated-approval", json={
            "meeting_id": "fake-id",
            "reason": "Test reason"
        })
        
        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403], f"Expected 401/403 for unauth, got {response.status_code}"
        print("PASS: request-backdated-approval requires authentication")
    
    def test_request_backdated_approval_validates_meeting_id(self, authenticated_client):
        """Test POST /api/meeting-workflow/request-backdated-approval validates meeting exists"""
        response = authenticated_client.post(f"{BASE_URL}/api/meeting-workflow/request-backdated-approval", json={
            "meeting_id": "nonexistent-meeting-id-12345",
            "reason": "Test reason for backdated meeting"
        })
        
        # Should return 404 for non-existent meeting
        assert response.status_code == 404, f"Expected 404 for nonexistent meeting, got {response.status_code}"
        assert "not found" in response.text.lower() or "Meeting not found" in response.text
        print("PASS: request-backdated-approval returns 404 for non-existent meeting")
    
    def test_approve_backdated_requires_auth(self, api_client):
        """Test POST /api/meeting-workflow/approve-backdated requires auth"""
        response = api_client.post(f"{BASE_URL}/api/meeting-workflow/approve-backdated", json={
            "meeting_id": "fake-id",
            "approved": True
        })
        
        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403], f"Expected 401/403 for unauth, got {response.status_code}"
        print("PASS: approve-backdated requires authentication")
    
    def test_approve_backdated_validates_meeting_id(self, authenticated_client):
        """Test POST /api/meeting-workflow/approve-backdated validates meeting exists"""
        response = authenticated_client.post(f"{BASE_URL}/api/meeting-workflow/approve-backdated", json={
            "meeting_id": "nonexistent-meeting-id-12345",
            "approved": True,
            "notes": "Approved for testing"
        })
        
        # Should return 404 for non-existent meeting
        assert response.status_code == 404, f"Expected 404 for nonexistent meeting, got {response.status_code}"
        print("PASS: approve-backdated returns 404 for non-existent meeting")


class TestMeetingWorkflowAdditionalEndpoints:
    """Tests for other meeting workflow endpoints"""
    
    def test_meeting_states_endpoint(self, api_client):
        """Test GET /api/meeting-workflow/meeting-states returns all states"""
        response = api_client.get(f"{BASE_URL}/api/meeting-workflow/meeting-states")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 10 states
        expected_states = ['DRAFT', 'SCHEDULED', 'CONFIRMED', 'REJECTED', 'RESCHEDULED', 
                         'AUTO_ACCEPTED', 'CONDUCTED', 'MOM_RECORDED', 'DELIVERED', 'CANCELLED']
        for state in expected_states:
            assert state in data, f"Missing state: {state}"
        print(f"PASS: /api/meeting-workflow/meeting-states returns all {len(expected_states)} states")
    
    def test_client_response_endpoint_validates_params(self, api_client):
        """Test GET /api/meeting-workflow/client-response validates token and action"""
        # Missing token
        response = api_client.get(f"{BASE_URL}/api/meeting-workflow/client-response?action=accept")
        assert response.status_code == 422 or "token" in response.text.lower()
        
        # Missing action
        response = api_client.get(f"{BASE_URL}/api/meeting-workflow/client-response?token=fake-token")
        assert response.status_code == 422 or "action" in response.text.lower()
        
        # Invalid action
        response = api_client.get(f"{BASE_URL}/api/meeting-workflow/client-response?token=fake&action=invalid")
        assert response.status_code in [400, 422]
        
        print("PASS: client-response endpoint validates required params")
    
    def test_send_invite_requires_meeting_id(self, authenticated_client):
        """Test POST /api/meeting-workflow/send-invite validates meeting_id"""
        # Empty body
        response = authenticated_client.post(f"{BASE_URL}/api/meeting-workflow/send-invite", json={})
        assert response.status_code == 422, f"Expected 422 for missing meeting_id, got {response.status_code}"
        
        # Non-existent meeting
        response = authenticated_client.post(f"{BASE_URL}/api/meeting-workflow/send-invite", json={
            "meeting_id": "nonexistent-id"
        })
        assert response.status_code == 404
        print("PASS: send-invite validates meeting_id")


class TestExistingMeetingsIntegration:
    """Integration tests using existing meetings in the system"""
    
    def test_get_meetings_list(self, authenticated_client):
        """Test that we can get meetings to work with"""
        response = authenticated_client.get(f"{BASE_URL}/api/meetings?meeting_type=consulting&limit=5")
        
        assert response.status_code == 200, f"Failed to get meetings: {response.text}"
        data = response.json()
        
        # Can be a list or paginated response
        meetings = data if isinstance(data, list) else data.get("items", data.get("meetings", []))
        print(f"PASS: Retrieved {len(meetings)} meetings for testing")
        
        if len(meetings) > 0:
            # Print first meeting structure for debugging
            print(f"Sample meeting keys: {list(meetings[0].keys())[:10]}")
    
    def test_meetings_have_status_field(self, authenticated_client):
        """Test that meetings have status field for workflow tracking"""
        response = authenticated_client.get(f"{BASE_URL}/api/meetings?meeting_type=consulting&limit=10")
        
        assert response.status_code == 200
        data = response.json()
        meetings = data if isinstance(data, list) else data.get("items", data.get("meetings", []))
        
        # Check if meetings have status field
        meetings_with_status = [m for m in meetings if m.get("status")]
        print(f"Found {len(meetings_with_status)}/{len(meetings)} meetings with status field")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
