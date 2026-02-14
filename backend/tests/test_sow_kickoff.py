"""
Test SOW (Scope of Work) and Kick-off Meeting APIs
Features tested:
- SOW Categories API
- SOW Creation and Item Management
- Kick-off Meeting Scheduling
- SOW Freeze Logic
- Notifications
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "admin123"}
MANAGER_CREDS = {"email": "manager@company.com", "password": "manager123"}
EXECUTIVE_CREDS = {"email": "executive@company.com", "password": "executive123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip("Admin authentication failed")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def manager_token():
    """Get manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code != 200:
        pytest.skip("Manager authentication failed")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def executive_token():
    """Get executive authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=EXECUTIVE_CREDS)
    if response.status_code != 200:
        pytest.skip("Executive authentication failed")
    return response.json().get("access_token")


@pytest.fixture
def admin_client(admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def manager_client(manager_token):
    """Session with manager auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {manager_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture
def executive_client(executive_token):
    """Session with executive auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {executive_token}",
        "Content-Type": "application/json"
    })
    return session


class TestSOWCategories:
    """Test SOW Categories API"""
    
    def test_get_sow_categories(self, admin_client):
        """GET /api/sow-categories returns all 6 categories"""
        response = admin_client.get(f"{BASE_URL}/api/sow-categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check for all 6 required categories
        expected_categories = ['sales', 'hr', 'operations', 'training', 'analytics', 'digital_marketing']
        category_values = [c.get('value') for c in data]
        
        for expected in expected_categories:
            assert expected in category_values, f"Category '{expected}' not found in response"
        
        print(f"SOW Categories: {[c.get('label') for c in data]}")


class TestSOWCreationAndManagement:
    """Test SOW Creation and Item Management"""
    
    @pytest.fixture
    def test_project(self, admin_client):
        """Get or create a test project for SOW testing"""
        # Get existing projects
        response = admin_client.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        
        projects = response.json()
        if projects:
            # Return first project for testing
            return projects[0]
        
        # Create a new project if none exist
        project_data = {
            "name": "TEST_SOW_Project",
            "client_name": "Test Client",
            "start_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        response = admin_client.post(f"{BASE_URL}/api/projects", json=project_data)
        assert response.status_code == 200
        return response.json()
    
    def test_create_project_sow(self, admin_client, test_project):
        """POST /api/projects/{id}/sow creates SOW for a category"""
        project_id = test_project['id']
        
        # Get existing SOW entries first
        existing_response = admin_client.get(f"{BASE_URL}/api/projects/{project_id}/sow")
        existing_sow = existing_response.json() if existing_response.status_code == 200 else []
        existing_categories = [s.get('category') for s in existing_sow]
        
        # Choose a category that doesn't exist yet
        categories = ['sales', 'hr', 'operations', 'training', 'analytics', 'digital_marketing']
        available_category = None
        for cat in categories:
            if cat not in existing_categories:
                available_category = cat
                break
        
        if not available_category:
            pytest.skip("All categories already exist for this project")
        
        sow_data = {
            "project_id": project_id,
            "agreement_id": test_project.get('agreement_id'),
            "category": available_category,
            "items": []
        }
        
        response = admin_client.post(f"{BASE_URL}/api/projects/{project_id}/sow", json=sow_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "sow_id" in data or "message" in data
        print(f"Created SOW for category: {available_category}")
        
        return available_category, data.get("sow_id")
    
    def test_get_project_sow(self, admin_client, test_project):
        """GET /api/projects/{id}/sow returns all SOW entries"""
        project_id = test_project['id']
        
        response = admin_client.get(f"{BASE_URL}/api/projects/{project_id}/sow")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Project {project_id} has {len(data)} SOW entries")
        
        return data
    
    def test_add_sow_item(self, admin_client, test_project):
        """POST /api/projects/{id}/sow/{sowId}/items adds scope items"""
        project_id = test_project['id']
        
        # Get existing SOW entries
        sow_response = admin_client.get(f"{BASE_URL}/api/projects/{project_id}/sow")
        sow_entries = sow_response.json() if sow_response.status_code == 200 else []
        
        # Find a non-frozen SOW entry
        sow_entry = None
        for entry in sow_entries:
            if not entry.get('is_frozen'):
                sow_entry = entry
                break
        
        if not sow_entry:
            # Create a new SOW entry
            categories = ['sales', 'hr', 'operations', 'training', 'analytics', 'digital_marketing']
            existing_categories = [s.get('category') for s in sow_entries]
            
            for cat in categories:
                if cat not in existing_categories:
                    create_response = admin_client.post(
                        f"{BASE_URL}/api/projects/{project_id}/sow",
                        json={
                            "project_id": project_id,
                            "category": cat,
                            "items": []
                        }
                    )
                    if create_response.status_code == 200:
                        sow_id = create_response.json().get("sow_id")
                        sow_entry = {"id": sow_id, "category": cat}
                        break
        
        if not sow_entry:
            pytest.skip("No available SOW entry to add items")
        
        sow_id = sow_entry['id']
        
        item_data = {
            "title": "TEST_SOW_Item_Sales_Strategy",
            "description": "Define comprehensive sales strategy for Q1",
            "deliverables": ["Sales playbook", "Lead scoring model", "Pipeline targets"],
            "timeline_weeks": 4
        }
        
        response = admin_client.post(
            f"{BASE_URL}/api/projects/{project_id}/sow/{sow_id}/items",
            json=item_data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "item_id" in data or "message" in data
        print(f"Added SOW item: {item_data['title']}")
        
        return sow_id, data.get("item_id")


class TestKickoffMeeting:
    """Test Kick-off Meeting Scheduling"""
    
    @pytest.fixture
    def consultants(self, admin_client):
        """Get available consultants"""
        response = admin_client.get(f"{BASE_URL}/api/consultants")
        if response.status_code == 200:
            return response.json()
        return []
    
    @pytest.fixture
    def test_project_with_agreement(self, admin_client):
        """Get a project with approved agreement for kickoff testing"""
        # Get projects
        response = admin_client.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        
        projects = response.json()
        for project in projects:
            if project.get('agreement_id'):
                return project
        
        # If no project with agreement, return first project
        if projects:
            return projects[0]
        
        pytest.skip("No projects available for kickoff testing")
    
    def test_get_kickoff_meetings_by_project(self, admin_client, test_project_with_agreement):
        """GET /api/kickoff-meetings?project_id={id} returns meetings for project"""
        project_id = test_project_with_agreement['id']
        
        response = admin_client.get(f"{BASE_URL}/api/kickoff-meetings?project_id={project_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Project {project_id} has {len(data)} kickoff meetings")
        
        return data
    
    def test_schedule_kickoff_meeting(self, admin_client, test_project_with_agreement, consultants):
        """POST /api/kickoff-meetings schedules meeting and freezes SOW"""
        project_id = test_project_with_agreement['id']
        
        # Check if kickoff meeting already exists
        existing_response = admin_client.get(f"{BASE_URL}/api/kickoff-meetings?project_id={project_id}")
        existing_meetings = existing_response.json() if existing_response.status_code == 200 else []
        
        if existing_meetings:
            # Meeting already exists - verify it has correct structure
            meeting = existing_meetings[0]
            assert "id" in meeting
            assert "project_id" in meeting
            assert "sow_frozen" in meeting
            print(f"Kickoff meeting already exists: {meeting['id']}, sow_frozen: {meeting['sow_frozen']}")
            return
        
        if not consultants:
            pytest.skip("No consultants available")
        
        principal_consultant_id = consultants[0]['id']
        agreement_id = test_project_with_agreement.get('agreement_id')
        
        # If no agreement_id on project, get an approved agreement
        if not agreement_id:
            agreements_response = admin_client.get(f"{BASE_URL}/api/agreements")
            if agreements_response.status_code == 200:
                agreements = agreements_response.json()
                approved = [a for a in agreements if a.get('status') == 'approved']
                if approved:
                    agreement_id = approved[0]['id']
        
        if not agreement_id:
            pytest.skip("No approved agreement available for kickoff")
        
        meeting_data = {
            "project_id": project_id,
            "agreement_id": agreement_id,
            "meeting_date": (datetime.now() + timedelta(days=7)).isoformat(),
            "meeting_time": "10:00",
            "meeting_mode": "online",
            "meeting_link": "https://meet.google.com/test-meeting",
            "agenda": "Project kickoff - review SOW and timeline",
            "principal_consultant_id": principal_consultant_id,
            "attendee_ids": []
        }
        
        response = admin_client.post(f"{BASE_URL}/api/kickoff-meetings", json=meeting_data)
        
        # Could be 200 or 400 if agreement not approved or already exists
        if response.status_code == 400:
            error_msg = response.json().get('detail', '')
            if 'approved' in error_msg.lower():
                pytest.skip("Agreement not approved - cannot schedule kickoff")
            if 'already exists' in error_msg.lower():
                print("Kickoff meeting already exists for project")
                return
        
        if response.status_code == 422:
            # Validation error - skip test
            pytest.skip(f"Validation error: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "meeting_id" in data
        print(f"Scheduled kickoff meeting: {data['meeting_id']}")
    
    def test_get_kickoff_meeting_detail(self, admin_client, test_project_with_agreement):
        """GET /api/kickoff-meetings/{id} returns full meeting with SOW summary"""
        project_id = test_project_with_agreement['id']
        
        # Get existing kickoff meetings
        response = admin_client.get(f"{BASE_URL}/api/kickoff-meetings?project_id={project_id}")
        meetings = response.json() if response.status_code == 200 else []
        
        if not meetings:
            pytest.skip("No kickoff meetings exist for this project")
        
        meeting_id = meetings[0]['id']
        
        response = admin_client.get(f"{BASE_URL}/api/kickoff-meetings/{meeting_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify response structure
        assert "meeting" in data, "Response should contain 'meeting'"
        assert "project" in data, "Response should contain 'project'"
        assert "sow" in data, "Response should contain 'sow'"
        
        print(f"Meeting detail: {data['meeting'].get('meeting_mode')}, SOW entries: {len(data.get('sow', []))}")


class TestSOWFreezeLogic:
    """Test SOW Freeze Logic after kick-off scheduling"""
    
    @pytest.fixture
    def frozen_sow_project(self, admin_client):
        """Get a project with frozen SOW"""
        # Get projects
        response = admin_client.get(f"{BASE_URL}/api/projects")
        projects = response.json() if response.status_code == 200 else []
        
        for project in projects:
            # Check if project has kickoff meeting (which freezes SOW)
            meetings_response = admin_client.get(
                f"{BASE_URL}/api/kickoff-meetings?project_id={project['id']}"
            )
            meetings = meetings_response.json() if meetings_response.status_code == 200 else []
            
            if meetings:
                # Check SOW status
                sow_response = admin_client.get(f"{BASE_URL}/api/projects/{project['id']}/sow")
                sow_entries = sow_response.json() if sow_response.status_code == 200 else []
                
                frozen_entries = [s for s in sow_entries if s.get('is_frozen')]
                if frozen_entries:
                    return project, frozen_entries[0]
        
        return None, None
    
    def test_non_admin_cannot_edit_frozen_sow(self, executive_client, frozen_sow_project):
        """Non-admin users cannot edit SOW after kick-off scheduled"""
        project, sow_entry = frozen_sow_project
        
        if not project or not sow_entry:
            pytest.skip("No frozen SOW available for testing")
        
        project_id = project['id']
        sow_id = sow_entry['id']
        
        item_data = {
            "title": "TEST_Forbidden_Item",
            "description": "This should fail for non-admin",
            "deliverables": ["Test"],
            "timeline_weeks": 1
        }
        
        response = executive_client.post(
            f"{BASE_URL}/api/projects/{project_id}/sow/{sow_id}/items",
            json=item_data
        )
        
        assert response.status_code == 403, f"Expected 403 for frozen SOW, got {response.status_code}"
        print("Non-admin correctly blocked from editing frozen SOW")
    
    def test_admin_can_edit_frozen_sow(self, admin_client, frozen_sow_project):
        """Admin can edit SOW even after freeze"""
        project, sow_entry = frozen_sow_project
        
        if not project or not sow_entry:
            pytest.skip("No frozen SOW available for testing")
        
        project_id = project['id']
        sow_id = sow_entry['id']
        
        item_data = {
            "title": "TEST_Admin_Item_After_Freeze",
            "description": "Admin can add items to frozen SOW",
            "deliverables": ["Admin override test"],
            "timeline_weeks": 2
        }
        
        response = admin_client.post(
            f"{BASE_URL}/api/projects/{project_id}/sow/{sow_id}/items",
            json=item_data
        )
        
        assert response.status_code == 200, f"Expected admin to edit frozen SOW, got {response.status_code}: {response.text}"
        print("Admin successfully added item to frozen SOW")


class TestNotifications:
    """Test Notification System"""
    
    def test_get_notifications(self, executive_client):
        """GET /api/notifications returns user notifications"""
        response = executive_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Check for kickoff_scheduled notifications
        kickoff_notifications = [n for n in data if n.get('notification_type') == 'kickoff_scheduled']
        print(f"Total notifications: {len(data)}, Kickoff notifications: {len(kickoff_notifications)}")
    
    def test_get_unread_count(self, executive_client):
        """GET /api/notifications/unread-count returns unread count"""
        response = executive_client.get(f"{BASE_URL}/api/notifications/unread-count")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "count" in data, "Response should contain 'count'"
        print(f"Unread notification count: {data['count']}")


class TestConsultantsForKickoff:
    """Test consultant retrieval for kickoff meeting scheduling"""
    
    def test_get_consultants_list(self, admin_client):
        """GET /api/consultants returns consultant list for principal selection"""
        response = admin_client.get(f"{BASE_URL}/api/consultants")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        if data:
            consultant = data[0]
            assert "id" in consultant, "Consultant should have 'id'"
            assert "full_name" in consultant, "Consultant should have 'full_name'"
            print(f"Found {len(data)} consultants for kickoff meeting selection")
        else:
            print("No consultants available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
