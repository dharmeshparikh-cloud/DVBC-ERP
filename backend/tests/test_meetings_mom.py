"""
Tests for Meeting MOM (Minutes of Meeting) Feature
Covers: Meeting CRUD, MOM updates, Action Items, Send MOM to Client, Follow-up Tasks
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for admin user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture(scope="module")
def project_id(headers):
    """Get or create a project for testing"""
    # First try to get existing project
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    
    # Create new project if none exists
    project_data = {
        "name": "TEST_MOM_Project",
        "client_name": "Test MOM Client",
        "project_type": "mixed",
        "start_date": datetime.now().isoformat()
    }
    response = requests.post(f"{BASE_URL}/api/projects", headers=headers, json=project_data)
    assert response.status_code == 200, f"Failed to create project: {response.text}"
    return response.json()["id"]

@pytest.fixture(scope="module")
def lead_with_email(headers):
    """Get or create a lead with email for MOM sending tests"""
    response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
    if response.status_code == 200:
        leads_with_email = [l for l in response.json() if l.get("email")]
        if leads_with_email:
            return leads_with_email[0]
    
    # Create new lead with email
    lead_data = {
        "first_name": "TEST_MOM",
        "last_name": "Lead",
        "company": "Test MOM Company",
        "email": "testmom@example.com"
    }
    response = requests.post(f"{BASE_URL}/api/leads", headers=headers, json=lead_data)
    if response.status_code == 200:
        return response.json()
    return None


class TestMeetingCRUD:
    """Test Meeting creation and retrieval"""
    
    def test_create_meeting_with_title_agenda_attendees(self, headers, project_id):
        """POST /api/meetings - Create meeting with title, agenda, attendees"""
        meeting_data = {
            "project_id": project_id,
            "meeting_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "mode": "online",
            "duration_minutes": 60,
            "title": "TEST_Weekly Sync Meeting",
            "agenda": ["Review Q1 progress", "Discuss budget allocation", "Action item review"],
            "attendees": [],
            "attendee_names": ["John Doe", "Jane Smith"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=headers, json=meeting_data)
        
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["title"] == "TEST_Weekly Sync Meeting"
        assert data["project_id"] == project_id
        assert len(data["agenda"]) == 3
        assert "Review Q1 progress" in data["agenda"]
        assert data["mode"] == "online"
        assert data["duration_minutes"] == 60
        assert data["mom_generated"] == False
        assert data["mom_sent_to_client"] == False
        
        # Store for later tests
        TestMeetingCRUD.created_meeting_id = data["id"]
    
    def test_get_meeting_by_id(self, headers):
        """GET /api/meetings/{id} - Get meeting details"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        assert meeting_id is not None, "No meeting ID from previous test"
        
        response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get meeting: {response.text}"
        data = response.json()
        
        assert data["id"] == meeting_id
        assert data["title"] == "TEST_Weekly Sync Meeting"
        assert "agenda" in data
        assert "discussion_points" in data
        assert "decisions_made" in data
        assert "action_items" in data
    
    def test_get_meetings_list(self, headers, project_id):
        """GET /api/meetings - Get meetings list"""
        response = requests.get(f"{BASE_URL}/api/meetings", headers=headers)
        
        assert response.status_code == 200, f"Failed to get meetings: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Verify at least one meeting has expected fields
        meeting = data[0]
        assert "id" in meeting
        assert "project_id" in meeting
        assert "meeting_date" in meeting
        assert "mode" in meeting
    
    def test_get_meetings_filtered_by_project(self, headers, project_id):
        """GET /api/meetings?project_id={id} - Get meetings for specific project"""
        response = requests.get(f"{BASE_URL}/api/meetings?project_id={project_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get filtered meetings: {response.text}"
        data = response.json()
        
        # All returned meetings should belong to the specified project
        for meeting in data:
            assert meeting["project_id"] == project_id


class TestMOMUpdate:
    """Test MOM (Minutes of Meeting) update functionality"""
    
    def test_update_mom_data(self, headers):
        """PATCH /api/meetings/{id}/mom - Update MOM data"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        assert meeting_id is not None, "No meeting ID from previous test"
        
        mom_data = {
            "title": "TEST_Updated Weekly Sync",
            "agenda": ["Updated agenda item 1", "Updated agenda item 2"],
            "discussion_points": ["Discussed Q1 metrics", "Budget review completed"],
            "decisions_made": ["Approved Q1 budget", "Scheduled phase 2 kickoff"],
            "next_meeting_date": (datetime.now() + timedelta(weeks=1)).isoformat()
        }
        
        response = requests.patch(f"{BASE_URL}/api/meetings/{meeting_id}/mom", headers=headers, json=mom_data)
        
        assert response.status_code == 200, f"Failed to update MOM: {response.text}"
        data = response.json()
        
        assert data["message"] == "MOM updated successfully"
        assert data["meeting_id"] == meeting_id
    
    def test_verify_mom_update_persisted(self, headers):
        """GET /api/meetings/{id} - Verify MOM update was persisted"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        assert meeting_id is not None, "No meeting ID from previous test"
        
        response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get meeting: {response.text}"
        data = response.json()
        
        # Verify MOM data was persisted
        assert data["title"] == "TEST_Updated Weekly Sync"
        assert len(data["agenda"]) == 2
        assert "Updated agenda item 1" in data["agenda"]
        assert len(data["discussion_points"]) == 2
        assert "Discussed Q1 metrics" in data["discussion_points"]
        assert len(data["decisions_made"]) == 2
        assert data["mom_generated"] == True
        assert data["next_meeting_date"] is not None


class TestActionItems:
    """Test Action Items CRUD and follow-up task creation"""
    
    def test_add_action_item(self, headers):
        """POST /api/meetings/{id}/action-items - Add action item"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        assert meeting_id is not None, "No meeting ID from previous test"
        
        action_item_data = {
            "description": "TEST_Complete Q1 financial report",
            "assigned_to_id": None,
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "priority": "high",
            "create_follow_up_task": True,
            "notify_reporting_manager": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/{meeting_id}/action-items",
            headers=headers,
            json=action_item_data
        )
        
        assert response.status_code == 200, f"Failed to add action item: {response.text}"
        data = response.json()
        
        assert data["message"] == "Action item added"
        assert "action_item" in data
        assert data["action_item"]["description"] == "TEST_Complete Q1 financial report"
        assert data["action_item"]["priority"] == "high"
        assert data["action_item"]["status"] == "pending"
        assert "id" in data["action_item"]
        
        # Store for later tests
        TestActionItems.action_item_id = data["action_item"]["id"]
    
    def test_action_item_persisted_in_meeting(self, headers):
        """Verify action item is persisted in meeting"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        
        response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["action_items"]) > 0
        action_item = next((a for a in data["action_items"] if a["description"] == "TEST_Complete Q1 financial report"), None)
        assert action_item is not None
        assert action_item["priority"] == "high"
        assert action_item["status"] == "pending"
    
    def test_update_action_item_status_to_in_progress(self, headers):
        """PATCH /api/meetings/{id}/action-items/{action_item_id} - Update status to in_progress"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        action_item_id = getattr(TestActionItems, 'action_item_id', None)
        assert action_item_id is not None, "No action item ID from previous test"
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{meeting_id}/action-items/{action_item_id}?status=in_progress",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to update action item status: {response.text}"
        data = response.json()
        
        assert data["message"] == "Action item status updated"
    
    def test_update_action_item_status_to_completed(self, headers):
        """PATCH /api/meetings/{id}/action-items/{action_item_id} - Update status to completed"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        action_item_id = getattr(TestActionItems, 'action_item_id', None)
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{meeting_id}/action-items/{action_item_id}?status=completed",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to update action item status: {response.text}"
        
        # Verify status update persisted
        meeting_response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        meeting_data = meeting_response.json()
        
        action_item = next((a for a in meeting_data["action_items"] if a["id"] == action_item_id), None)
        assert action_item is not None
        assert action_item["status"] == "completed"
        assert action_item.get("completed_at") is not None
    
    def test_add_action_item_with_different_priorities(self, headers):
        """Test action items with low, medium, high priorities"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        
        priorities = ["low", "medium", "high"]
        
        for priority in priorities:
            action_item_data = {
                "description": f"TEST_{priority.upper()} priority task",
                "priority": priority,
                "create_follow_up_task": False,
                "notify_reporting_manager": False
            }
            
            response = requests.post(
                f"{BASE_URL}/api/meetings/{meeting_id}/action-items",
                headers=headers,
                json=action_item_data
            )
            
            assert response.status_code == 200, f"Failed to add {priority} priority item: {response.text}"
            assert response.json()["action_item"]["priority"] == priority


class TestSendMOM:
    """Test sending MOM to client"""
    
    def test_send_mom_to_client_with_lead_email(self, headers, project_id, lead_with_email):
        """POST /api/meetings/{id}/send-mom - Send MOM to client via lead email"""
        if lead_with_email is None:
            pytest.skip("No lead with email available")
        
        # Create a meeting linked to the lead
        meeting_data = {
            "project_id": project_id,
            "lead_id": lead_with_email["id"],
            "meeting_date": (datetime.now() + timedelta(days=2)).isoformat(),
            "mode": "online",
            "title": "TEST_MOM_Send_Meeting",
            "agenda": ["Test sending MOM"]
        }
        
        create_response = requests.post(f"{BASE_URL}/api/meetings", headers=headers, json=meeting_data)
        assert create_response.status_code == 200
        meeting_id = create_response.json()["id"]
        
        # Update MOM with content
        mom_data = {
            "title": "Test MOM Email",
            "discussion_points": ["Discussed project scope"],
            "decisions_made": ["Approved timeline"]
        }
        requests.patch(f"{BASE_URL}/api/meetings/{meeting_id}/mom", headers=headers, json=mom_data)
        
        # Send MOM
        response = requests.post(f"{BASE_URL}/api/meetings/{meeting_id}/send-mom", headers=headers)
        
        assert response.status_code == 200, f"Failed to send MOM: {response.text}"
        data = response.json()
        
        assert "MOM sent to client" in data["message"]
        assert "client_email" in data
        assert data["client_email"] == lead_with_email["email"]
        
        # Verify meeting updated
        verify_response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        verify_data = verify_response.json()
        
        assert verify_data["mom_sent_to_client"] == True
        assert verify_data["mom_sent_at"] is not None
        
        # Store for cleanup
        TestSendMOM.test_meeting_id = meeting_id
    
    def test_send_mom_without_client_email_fails(self, headers, project_id):
        """POST /api/meetings/{id}/send-mom - Should fail if no client email"""
        # Create meeting without lead/client
        meeting_data = {
            "project_id": project_id,
            "meeting_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "mode": "online",
            "title": "TEST_MOM_No_Email_Meeting"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/meetings", headers=headers, json=meeting_data)
        assert create_response.status_code == 200
        meeting_id = create_response.json()["id"]
        
        # Try to send MOM
        response = requests.post(f"{BASE_URL}/api/meetings/{meeting_id}/send-mom", headers=headers)
        
        # Should fail with 400 because no client email
        assert response.status_code == 400
        assert "No client email found" in response.json().get("detail", "")


class TestFollowUpTasks:
    """Test follow-up tasks creation from action items"""
    
    def test_get_follow_up_tasks(self, headers):
        """GET /api/follow-up-tasks - Get follow-up tasks"""
        response = requests.get(f"{BASE_URL}/api/follow-up-tasks", headers=headers)
        
        assert response.status_code == 200, f"Failed to get follow-up tasks: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        # Follow-up tasks may or may not exist depending on previous tests
        # Just verify the endpoint returns proper structure
    
    def test_get_follow_up_tasks_filtered_by_status(self, headers):
        """GET /api/follow-up-tasks?status=pending - Get filtered follow-up tasks"""
        response = requests.get(f"{BASE_URL}/api/follow-up-tasks?status=pending", headers=headers)
        
        assert response.status_code == 200, f"Failed to get filtered follow-up tasks: {response.text}"
        data = response.json()
        
        # All returned tasks should have pending status
        for task in data:
            assert task.get("status") == "pending" or task.get("status") is None


class TestErrorHandling:
    """Test error cases"""
    
    def test_get_nonexistent_meeting(self, headers):
        """GET /api/meetings/{id} - Should return 404 for non-existent meeting"""
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/meetings/{fake_id}", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()
    
    def test_update_mom_nonexistent_meeting(self, headers):
        """PATCH /api/meetings/{id}/mom - Should return 404 for non-existent meeting"""
        fake_id = str(uuid.uuid4())
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{fake_id}/mom",
            headers=headers,
            json={"title": "Test"}
        )
        
        assert response.status_code == 404
    
    def test_add_action_item_nonexistent_meeting(self, headers):
        """POST /api/meetings/{id}/action-items - Should return 404 for non-existent meeting"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/meetings/{fake_id}/action-items",
            headers=headers,
            json={"description": "Test", "priority": "medium"}
        )
        
        assert response.status_code == 404
    
    def test_update_action_item_nonexistent_meeting(self, headers):
        """PATCH /api/meetings/{id}/action-items/{action_item_id} - Should return 404"""
        fake_meeting_id = str(uuid.uuid4())
        fake_action_id = str(uuid.uuid4())
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{fake_meeting_id}/action-items/{fake_action_id}?status=completed",
            headers=headers
        )
        
        assert response.status_code == 404
    
    def test_update_nonexistent_action_item(self, headers):
        """PATCH - Should return 404 for non-existent action item"""
        meeting_id = getattr(TestMeetingCRUD, 'created_meeting_id', None)
        if meeting_id is None:
            pytest.skip("No meeting ID available")
        
        fake_action_id = str(uuid.uuid4())
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{meeting_id}/action-items/{fake_action_id}?status=completed",
            headers=headers
        )
        
        assert response.status_code == 404
        assert "Action item not found" in response.json().get("detail", "")


class TestMeetingModes:
    """Test different meeting modes"""
    
    def test_create_online_meeting(self, headers, project_id):
        """Create online mode meeting"""
        meeting_data = {
            "project_id": project_id,
            "meeting_date": datetime.now().isoformat(),
            "mode": "online",
            "title": "TEST_Online_Meeting"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=headers, json=meeting_data)
        assert response.status_code == 200
        assert response.json()["mode"] == "online"
    
    def test_create_offline_meeting(self, headers, project_id):
        """Create offline (in-person) mode meeting"""
        meeting_data = {
            "project_id": project_id,
            "meeting_date": datetime.now().isoformat(),
            "mode": "offline",
            "title": "TEST_Offline_Meeting"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=headers, json=meeting_data)
        assert response.status_code == 200
        assert response.json()["mode"] == "offline"
    
    def test_create_telecall_meeting(self, headers, project_id):
        """Create tele_call mode meeting"""
        meeting_data = {
            "project_id": project_id,
            "meeting_date": datetime.now().isoformat(),
            "mode": "tele_call",
            "title": "TEST_TeleCall_Meeting"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=headers, json=meeting_data)
        assert response.status_code == 200
        assert response.json()["mode"] == "tele_call"
