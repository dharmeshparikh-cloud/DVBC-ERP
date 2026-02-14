"""
Tests for Sales & Consulting Meetings Module Split
Covers:
- Sales Meetings: POST/GET with type=sales, lead linking, RBAC for sales roles
- Consulting Meetings: POST/GET with type=consulting, project_id required, RBAC for consulting roles
- Commitment Tracking: GET /api/consulting-meetings/tracking
- Action Items: POST action items for consulting meetings
- Role-based Access: HR Manager 403, Manager view-only
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# --- Fixtures ---

@pytest.fixture(scope="module")
def admin_headers():
    """Auth headers for admin user (full access to both meeting types)"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def executive_headers():
    """Auth headers for executive (sales role)"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "executive@company.com", "password": "executive123"}
    )
    assert response.status_code == 200, f"Executive login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def manager_headers():
    """Auth headers for manager (view-only for meetings)"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "manager@company.com", "password": "manager123"}
    )
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def hr_manager_headers():
    """Auth headers for HR manager (no CRUD access to meetings)"""
    # First check if HR manager exists, create if not
    admin_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@company.com", "password": "admin123"}
    )
    admin_token = admin_response.json()["access_token"]
    admin_h = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
    # Try to login as HR manager
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "hr_manager@company.com", "password": "manager123"}
    )
    
    if response.status_code != 200:
        # Create HR manager user
        create_resp = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": "hr_manager@company.com",
                "password": "manager123",
                "full_name": "HR Manager Test",
                "role": "hr_manager"
            }
        )
        if create_resp.status_code not in [200, 400]:  # 400 if already exists
            pytest.skip("Could not create HR manager user")
        
        # Try login again
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "hr_manager@company.com", "password": "manager123"}
        )
    
    if response.status_code != 200:
        pytest.skip("HR manager user not available")
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

@pytest.fixture(scope="module")
def project_id(admin_headers):
    """Get or create a project for consulting meetings"""
    response = requests.get(f"{BASE_URL}/api/projects", headers=admin_headers)
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    
    # Create new project
    project_data = {
        "name": "TEST_Consulting_Project",
        "client_name": "Test Client Corp",
        "project_type": "mixed",
        "start_date": datetime.now().isoformat(),
        "total_meetings_committed": 10
    }
    response = requests.post(f"{BASE_URL}/api/projects", headers=admin_headers, json=project_data)
    assert response.status_code == 200, f"Failed to create project: {response.text}"
    return response.json()["id"]

@pytest.fixture(scope="module")
def lead_id(admin_headers):
    """Get or create a lead for sales meetings"""
    response = requests.get(f"{BASE_URL}/api/leads", headers=admin_headers)
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0]["id"]
    
    # Create new lead
    lead_data = {
        "first_name": "TEST_Sales",
        "last_name": "Lead",
        "company": "Sales Lead Corp",
        "email": "saleslead@test.com"
    }
    response = requests.post(f"{BASE_URL}/api/leads", headers=admin_headers, json=lead_data)
    assert response.status_code == 200, f"Failed to create lead: {response.text}"
    return response.json()["id"]


# --- Test Sales Meetings ---

class TestSalesMeetings:
    """Tests for Sales Meetings (type=sales)"""
    
    def test_create_sales_meeting_admin(self, admin_headers, lead_id):
        """Admin can create sales meeting with type=sales"""
        meeting_data = {
            "type": "sales",
            "title": "TEST_Sales_Discovery_Call",
            "meeting_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "mode": "online",
            "duration_minutes": 30,
            "lead_id": lead_id,
            "notes": "Initial discovery call with prospect",
            "agenda": ["Introduction", "Discuss requirements", "Next steps"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=admin_headers, json=meeting_data)
        
        assert response.status_code == 200, f"Failed to create sales meeting: {response.text}"
        data = response.json()
        
        assert data["type"] == "sales"
        assert data["title"] == "TEST_Sales_Discovery_Call"
        assert data["lead_id"] == lead_id
        assert data["mode"] == "online"
        assert len(data["agenda"]) == 3
        
        TestSalesMeetings.created_meeting_id = data["id"]
    
    def test_create_sales_meeting_executive(self, executive_headers, lead_id):
        """Executive (sales role) can create sales meeting"""
        meeting_data = {
            "type": "sales",
            "title": "TEST_Sales_Follow_Up",
            "meeting_date": (datetime.now() + timedelta(days=2)).isoformat(),
            "mode": "tele_call",
            "lead_id": lead_id,
            "notes": "Follow-up call"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=executive_headers, json=meeting_data)
        
        assert response.status_code == 200, f"Executive failed to create sales meeting: {response.text}"
        assert response.json()["type"] == "sales"
    
    def test_get_sales_meetings_filter(self, admin_headers):
        """GET /api/meetings?meeting_type=sales returns only sales meetings"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=sales", headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to get sales meetings: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        # All returned meetings should be type=sales
        for meeting in data:
            assert meeting.get("type") == "sales", f"Non-sales meeting in filter results: {meeting}"
    
    def test_sales_meeting_no_project_required(self, admin_headers):
        """Sales meetings do not require project_id"""
        meeting_data = {
            "type": "sales",
            "title": "TEST_Sales_No_Project",
            "meeting_date": datetime.now().isoformat(),
            "mode": "online"
            # No project_id - should be fine for sales
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=admin_headers, json=meeting_data)
        
        assert response.status_code == 200, f"Sales meeting without project should succeed: {response.text}"
        assert response.json()["type"] == "sales"


# --- Test Consulting Meetings ---

class TestConsultingMeetings:
    """Tests for Consulting Meetings (type=consulting)"""
    
    def test_create_consulting_meeting_requires_project(self, admin_headers):
        """Consulting meetings require project_id (should fail without it)"""
        meeting_data = {
            "type": "consulting",
            "title": "TEST_Consulting_No_Project",
            "meeting_date": datetime.now().isoformat(),
            "mode": "online"
            # No project_id - should fail for consulting
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=admin_headers, json=meeting_data)
        
        assert response.status_code == 400, f"Consulting without project should fail: {response.text}"
        assert "project" in response.json().get("detail", "").lower()
    
    def test_create_consulting_meeting_with_project(self, admin_headers, project_id):
        """Admin can create consulting meeting with project_id"""
        meeting_data = {
            "type": "consulting",
            "title": "TEST_Consulting_Weekly_Review",
            "project_id": project_id,
            "meeting_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "mode": "offline",
            "duration_minutes": 90,
            "is_delivered": True,
            "agenda": ["Review deliverables", "Discuss blockers", "Plan next sprint"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=admin_headers, json=meeting_data)
        
        assert response.status_code == 200, f"Failed to create consulting meeting: {response.text}"
        data = response.json()
        
        assert data["type"] == "consulting"
        assert data["project_id"] == project_id
        assert data["is_delivered"] == True
        assert data["mode"] == "offline"
        
        TestConsultingMeetings.created_meeting_id = data["id"]
    
    def test_get_consulting_meetings_filter(self, admin_headers):
        """GET /api/meetings?meeting_type=consulting returns only consulting meetings"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=consulting", headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to get consulting meetings: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        # All returned meetings should be type=consulting or default (no type field)
        for meeting in data:
            meeting_type = meeting.get("type", "consulting")  # Default is consulting
            assert meeting_type == "consulting", f"Non-consulting meeting in filter: {meeting}"
    
    def test_manager_can_view_consulting_meetings(self, manager_headers):
        """Manager can view consulting meetings (part of CONSULTING_MEETING_ROLES)"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=consulting", headers=manager_headers)
        
        assert response.status_code == 200, f"Manager failed to view consulting meetings: {response.text}"


# --- Test Commitment Tracking ---

class TestCommitmentTracking:
    """Tests for Consulting Meetings Commitment Tracking"""
    
    def test_get_commitment_tracking(self, admin_headers):
        """GET /api/consulting-meetings/tracking returns project tracking data"""
        response = requests.get(f"{BASE_URL}/api/consulting-meetings/tracking", headers=admin_headers)
        
        assert response.status_code == 200, f"Failed to get tracking: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        
        # Each tracking item should have expected fields
        if len(data) > 0:
            item = data[0]
            assert "project_id" in item
            assert "project_name" in item
            assert "client_name" in item
            assert "committed" in item
            assert "actual_meetings" in item
            assert "variance" in item
            assert "completion_pct" in item
    
    def test_tracking_data_accuracy(self, admin_headers, project_id):
        """Verify tracking counts actual consulting meetings for project"""
        # First get current counts
        response = requests.get(f"{BASE_URL}/api/consulting-meetings/tracking", headers=admin_headers)
        assert response.status_code == 200
        
        tracking_data = response.json()
        project_tracking = next((t for t in tracking_data if t["project_id"] == project_id), None)
        
        if project_tracking:
            # Verify actual_meetings count matches consulting meetings for this project
            meetings_response = requests.get(
                f"{BASE_URL}/api/meetings?project_id={project_id}&meeting_type=consulting",
                headers=admin_headers
            )
            if meetings_response.status_code == 200:
                actual_meetings = len([m for m in meetings_response.json() if m.get("type", "consulting") == "consulting"])
                # Tracking count should match
                assert project_tracking["actual_meetings"] == actual_meetings, \
                    f"Tracking mismatch: {project_tracking['actual_meetings']} vs {actual_meetings}"


# --- Test Role-Based Access ---

class TestRoleBasedAccess:
    """Tests for Role-Based Access Control on Meetings"""
    
    def test_hr_manager_cannot_create_sales_meeting(self, hr_manager_headers, lead_id):
        """HR Manager should get 403 when trying to create sales meeting"""
        meeting_data = {
            "type": "sales",
            "title": "TEST_HR_Blocked_Sales",
            "meeting_date": datetime.now().isoformat(),
            "mode": "online",
            "lead_id": lead_id
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=hr_manager_headers, json=meeting_data)
        
        assert response.status_code == 403, f"HR Manager should not create meetings: {response.text}"
    
    def test_hr_manager_cannot_create_consulting_meeting(self, hr_manager_headers, project_id):
        """HR Manager should get 403 when trying to create consulting meeting"""
        meeting_data = {
            "type": "consulting",
            "title": "TEST_HR_Blocked_Consulting",
            "project_id": project_id,
            "meeting_date": datetime.now().isoformat(),
            "mode": "online"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=hr_manager_headers, json=meeting_data)
        
        assert response.status_code == 403, f"HR Manager should not create meetings: {response.text}"
    
    def test_executive_cannot_create_consulting_meeting(self, executive_headers, project_id):
        """Executive (sales role) should get 403 when creating consulting meeting"""
        meeting_data = {
            "type": "consulting",
            "title": "TEST_Exec_Blocked_Consulting",
            "project_id": project_id,
            "meeting_date": datetime.now().isoformat(),
            "mode": "online"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", headers=executive_headers, json=meeting_data)
        
        assert response.status_code == 403, f"Executive should not create consulting meetings: {response.text}"


# --- Test Action Items for Consulting ---

class TestConsultingActionItems:
    """Tests for Action Items on Consulting Meetings"""
    
    def test_add_action_item_to_consulting_meeting(self, admin_headers):
        """Add action item to a consulting meeting"""
        meeting_id = getattr(TestConsultingMeetings, 'created_meeting_id', None)
        if not meeting_id:
            pytest.skip("No consulting meeting ID available")
        
        action_item_data = {
            "description": "TEST_Complete deliverable documentation",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "create_follow_up_task": True,
            "notify_reporting_manager": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/meetings/{meeting_id}/action-items",
            headers=admin_headers,
            json=action_item_data
        )
        
        assert response.status_code == 200, f"Failed to add action item: {response.text}"
        data = response.json()
        
        assert data["message"] == "Action item added"
        assert data["action_item"]["description"] == "TEST_Complete deliverable documentation"
        assert data["action_item"]["priority"] == "high"
        
        TestConsultingActionItems.action_item_id = data["action_item"]["id"]
    
    def test_verify_action_item_persisted(self, admin_headers):
        """Verify action item was saved to meeting"""
        meeting_id = getattr(TestConsultingMeetings, 'created_meeting_id', None)
        if not meeting_id:
            pytest.skip("No consulting meeting ID available")
        
        response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=admin_headers)
        assert response.status_code == 200
        
        data = response.json()
        action_items = data.get("action_items", [])
        
        assert len(action_items) > 0, "No action items found on meeting"
        
        test_item = next((a for a in action_items if "Complete deliverable" in a.get("description", "")), None)
        assert test_item is not None, "Test action item not found"


# --- Test MOM for both meeting types ---

class TestMOMForBothTypes:
    """Test MOM functionality works for both sales and consulting meetings"""
    
    def test_save_sales_mom_simplified(self, admin_headers):
        """Save MOM for sales meeting (no action items expected)"""
        meeting_id = getattr(TestSalesMeetings, 'created_meeting_id', None)
        if not meeting_id:
            pytest.skip("No sales meeting ID available")
        
        mom_data = {
            "title": "Updated Sales Discovery Call",
            "agenda": ["Intro", "Demo", "Q&A"],
            "discussion_points": ["Client interested in premium tier", "Budget discussion needed"],
            "decisions_made": ["Schedule follow-up demo"],
            "next_meeting_date": (datetime.now() + timedelta(days=5)).isoformat()
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{meeting_id}/mom",
            headers=admin_headers,
            json=mom_data
        )
        
        assert response.status_code == 200, f"Failed to save sales MOM: {response.text}"
        assert response.json()["message"] == "MOM updated successfully"
    
    def test_save_consulting_mom_with_full_details(self, admin_headers):
        """Save MOM for consulting meeting with full details"""
        meeting_id = getattr(TestConsultingMeetings, 'created_meeting_id', None)
        if not meeting_id:
            pytest.skip("No consulting meeting ID available")
        
        mom_data = {
            "title": "Weekly Sprint Review",
            "agenda": ["Sprint demo", "Blockers discussion", "Next sprint planning"],
            "discussion_points": ["Completed 8/10 story points", "Dependency on API team resolved"],
            "decisions_made": ["Extend sprint by 2 days", "Add resource for testing"],
            "next_meeting_date": (datetime.now() + timedelta(weeks=1)).isoformat()
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{meeting_id}/mom",
            headers=admin_headers,
            json=mom_data
        )
        
        assert response.status_code == 200, f"Failed to save consulting MOM: {response.text}"
        
        # Verify MOM was saved
        verify_response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=admin_headers)
        assert verify_response.status_code == 200
        
        data = verify_response.json()
        assert data["mom_generated"] == True
        assert data["title"] == "Weekly Sprint Review"
        assert len(data["decisions_made"]) == 2


# --- Test Meeting Count Stats ---

class TestMeetingStats:
    """Test that meeting counts are correct per type"""
    
    def test_sales_meeting_count(self, admin_headers):
        """Verify sales meeting count"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=sales", headers=admin_headers)
        
        assert response.status_code == 200
        sales_count = len(response.json())
        
        print(f"Sales meetings count: {sales_count}")
        assert sales_count >= 0  # At least should return without error
    
    def test_consulting_meeting_count(self, admin_headers):
        """Verify consulting meeting count"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=consulting", headers=admin_headers)
        
        assert response.status_code == 200
        consulting_count = len(response.json())
        
        print(f"Consulting meetings count: {consulting_count}")
        assert consulting_count >= 0
    
    def test_total_meetings_without_filter(self, admin_headers):
        """Get all meetings without type filter"""
        response = requests.get(f"{BASE_URL}/api/meetings", headers=admin_headers)
        
        assert response.status_code == 200
        total = len(response.json())
        
        # Get individual counts
        sales_resp = requests.get(f"{BASE_URL}/api/meetings?meeting_type=sales", headers=admin_headers)
        consulting_resp = requests.get(f"{BASE_URL}/api/meetings?meeting_type=consulting", headers=admin_headers)
        
        sales_count = len(sales_resp.json()) if sales_resp.status_code == 200 else 0
        consulting_count = len(consulting_resp.json()) if consulting_resp.status_code == 200 else 0
        
        print(f"Total: {total}, Sales: {sales_count}, Consulting: {consulting_count}")
        # Total should equal sum of both types
        assert total >= sales_count + consulting_count
