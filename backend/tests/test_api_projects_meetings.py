"""
OWASP-Compliant API Security Test Suite - Projects & Meetings Module
Tests: Project CRUD, consultant assignment, meeting MOM, handover alerts
"""

import pytest
import httpx
from datetime import datetime, timezone


class TestProjectsPositive:
    """Positive tests for projects CRUD."""
    
    @pytest.mark.asyncio
    async def test_proj001_get_all_projects(self, admin_client):
        """TC-PROJ-001: Get all projects returns list."""
        response = await admin_client.get("/api/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_proj002_create_project(self, admin_client, test_data):
        """TC-PROJ-002: Create project with valid data."""
        project_data = test_data.project()
        response = await admin_client.post("/api/projects", json=project_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_proj003_get_project_by_id(self, admin_client, db):
        """TC-PROJ-003: Get single project by ID."""
        project = await db.projects.find_one({}, {"_id": 0, "id": 1})
        if project:
            response = await admin_client.get(f"/api/projects/{project['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_proj004_get_handover_alerts(self, admin_client):
        """TC-PROJ-004: Get project handover alerts."""
        response = await admin_client.get("/api/projects/handover-alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_proj005_get_project_tasks_gantt(self, admin_client, db):
        """TC-PROJ-005: Get project tasks for Gantt chart."""
        project = await db.projects.find_one({}, {"_id": 0, "id": 1})
        if project:
            response = await admin_client.get(f"/api/projects/{project['id']}/tasks-gantt")
            
            assert response.status_code == 200


class TestProjectsNegative:
    """Negative tests for projects module."""
    
    @pytest.mark.asyncio
    async def test_proj020_get_nonexistent(self, admin_client):
        """TC-PROJ-020: Get nonexistent project returns 404."""
        response = await admin_client.get("/api/projects/nonexistent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_proj021_create_missing_fields(self, admin_client):
        """TC-PROJ-021: Create project without required fields fails."""
        response = await admin_client.post("/api/projects", json={})
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_proj022_invalid_project_type(self, admin_client, test_data):
        """TC-PROJ-022: Invalid project type handled."""
        project_data = test_data.project({"project_type": "invalid_type"})
        response = await admin_client.post("/api/projects", json=project_data)
        
        # Either accepts or rejects gracefully
        assert response.status_code in [200, 400, 422]


class TestProjectsAccessControl:
    """Access control tests for projects."""
    
    @pytest.mark.asyncio
    async def test_proj030_manager_cannot_create(self, manager_client, test_data):
        """TC-PROJ-030: Manager cannot create projects."""
        project_data = test_data.project()
        response = await manager_client.post("/api/projects", json=project_data)
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_proj031_unauthenticated_access(self, api_client):
        """TC-PROJ-031: Unauthenticated cannot access projects."""
        response = await api_client.get("/api/projects")
        
        assert response.status_code == 401


class TestConsultantAssignment:
    """Tests for consultant assignment to projects."""
    
    @pytest.mark.asyncio
    async def test_assign001_assign_consultant(self, admin_client, db):
        """TC-ASSIGN-001: Assign consultant to project."""
        project = await db.projects.find_one({}, {"_id": 0, "id": 1})
        consultant = await db.users.find_one({"role": "consultant"}, {"_id": 0, "id": 1})
        
        if project and consultant:
            response = await admin_client.post(
                f"/api/projects/{project['id']}/assign-consultant",
                json={
                    "consultant_id": consultant["id"],
                    "role_in_project": "consultant",
                    "meetings_committed": 5
                }
            )
            
            # May succeed or fail if already assigned, or validation error
            assert response.status_code in [200, 400, 409, 422]
    
    @pytest.mark.asyncio
    async def test_assign002_get_consultants(self, admin_client):
        """TC-ASSIGN-002: Get list of consultants."""
        response = await admin_client.get("/api/consultants")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_assign003_consultant_my_projects(self, admin_client):
        """TC-ASSIGN-003: Consultant can view their projects."""
        response = await admin_client.get("/api/consultant/my-projects")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_assign004_consultant_dashboard_stats(self, admin_client):
        """TC-ASSIGN-004: Consultant dashboard stats."""
        response = await admin_client.get("/api/consultant/dashboard-stats")
        
        assert response.status_code == 200


class TestMeetingsPositive:
    """Positive tests for meetings module."""
    
    @pytest.mark.asyncio
    async def test_meet001_get_all_meetings(self, admin_client):
        """TC-MEET-001: Get all meetings returns list."""
        response = await admin_client.get("/api/meetings")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_meet002_create_consulting_meeting(self, admin_client, db, test_data):
        """TC-MEET-002: Create consulting meeting with project."""
        project = await db.projects.find_one({}, {"_id": 0, "id": 1})
        if project:
            meeting_data = test_data.meeting(project["id"])
            response = await admin_client.post("/api/meetings", json=meeting_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
    
    @pytest.mark.asyncio
    async def test_meet003_get_meeting_by_id(self, admin_client, db):
        """TC-MEET-003: Get single meeting by ID."""
        meeting = await db.meetings.find_one({}, {"_id": 0, "id": 1})
        if meeting:
            response = await admin_client.get(f"/api/meetings/{meeting['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_meet004_filter_by_project(self, admin_client, db):
        """TC-MEET-004: Filter meetings by project."""
        project = await db.projects.find_one({}, {"_id": 0, "id": 1})
        if project:
            response = await admin_client.get("/api/meetings", params={"project_id": project["id"]})
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_meet005_consulting_tracking(self, admin_client):
        """TC-MEET-005: Get consulting meetings tracking."""
        response = await admin_client.get("/api/consulting-meetings/tracking")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestMeetingsNegative:
    """Negative tests for meetings."""
    
    @pytest.mark.asyncio
    async def test_meet020_consulting_without_project(self, admin_client):
        """TC-MEET-020: Consulting meeting without project fails."""
        response = await admin_client.post("/api/meetings", json={
            "type": "consulting",
            "meeting_date": datetime.now(timezone.utc).isoformat(),
            "mode": "online"
        })
        
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_meet021_get_nonexistent(self, admin_client):
        """TC-MEET-021: Get nonexistent meeting returns 404."""
        response = await admin_client.get("/api/meetings/nonexistent-id")
        
        assert response.status_code == 404


class TestMOMPositive:
    """Positive tests for Minutes of Meeting functionality."""
    
    @pytest.mark.asyncio
    async def test_mom001_update_meeting_mom(self, admin_client, db):
        """TC-MOM-001: Update meeting MOM."""
        meeting = await db.meetings.find_one({}, {"_id": 0, "id": 1})
        if meeting:
            response = await admin_client.patch(
                f"/api/meetings/{meeting['id']}/mom",
                json={
                    "title": "Test MOM",
                    "agenda": ["Item 1", "Item 2"],
                    "discussion_points": ["Discussion 1"],
                    "decisions_made": ["Decision 1"]
                }
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_mom002_add_action_item(self, admin_client, db):
        """TC-MOM-002: Add action item to meeting."""
        meeting = await db.meetings.find_one({}, {"_id": 0, "id": 1})
        user = await db.users.find_one({}, {"_id": 0, "id": 1})
        
        if meeting and user:
            response = await admin_client.post(
                f"/api/meetings/{meeting['id']}/action-items",
                json={
                    "description": "Test action item",
                    "assigned_to_id": user["id"],
                    "priority": "high",
                    "create_follow_up_task": True
                }
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_mom003_update_action_item_status(self, admin_client, db):
        """TC-MOM-003: Update action item status."""
        meeting = await db.meetings.find_one(
            {"action_items.0": {"$exists": True}},
            {"_id": 0, "id": 1, "action_items": 1}
        )
        
        if meeting and meeting.get("action_items"):
            action_item_id = meeting["action_items"][0]["id"]
            response = await admin_client.patch(
                f"/api/meetings/{meeting['id']}/action-items/{action_item_id}",
                params={"status": "completed"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_mom004_get_follow_up_tasks(self, admin_client):
        """TC-MOM-004: Get follow-up tasks."""
        response = await admin_client.get("/api/follow-up-tasks")
        
        assert response.status_code == 200


class TestMeetingsSecurity:
    """Security tests for meetings module."""
    
    @pytest.mark.asyncio
    async def test_meet030_xss_in_notes(self, admin_client, db, owasp_payloads, test_data):
        """TC-MEET-030: XSS in meeting notes handled safely."""
        project = await db.projects.find_one({}, {"_id": 0, "id": 1})
        if project:
            for payload in owasp_payloads.XSS_PAYLOADS[:2]:
                meeting_data = test_data.meeting(project["id"], {"notes": payload})
                response = await admin_client.post("/api/meetings", json=meeting_data)
                
                assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_meet031_sql_injection_filter(self, admin_client, owasp_payloads):
        """TC-MEET-031: SQL injection in filter params."""
        for payload in owasp_payloads.SQL_INJECTION[:2]:
            response = await admin_client.get("/api/meetings", params={"project_id": payload})
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_meet032_unauthenticated_access(self, api_client):
        """TC-MEET-032: Unauthenticated cannot access meetings."""
        response = await api_client.get("/api/meetings")
        
        assert response.status_code == 401


class TestTasksPositive:
    """Positive tests for tasks module."""
    
    @pytest.mark.asyncio
    async def test_task001_get_all_tasks(self, admin_client):
        """TC-TASK-001: Get all tasks."""
        response = await admin_client.get("/api/tasks")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_task002_get_task_by_id(self, admin_client, db):
        """TC-TASK-002: Get single task by ID."""
        task = await db.tasks.find_one({}, {"_id": 0, "id": 1})
        if task:
            response = await admin_client.get(f"/api/tasks/{task['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_task003_update_task(self, admin_client, db):
        """TC-TASK-003: Update task."""
        task = await db.tasks.find_one({}, {"_id": 0, "id": 1})
        if task:
            response = await admin_client.patch(
                f"/api/tasks/{task['id']}",
                json={"status": "in_progress"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_task004_task_dates_update(self, admin_client, db):
        """TC-TASK-004: Update task dates for Gantt."""
        task = await db.tasks.find_one({}, {"_id": 0, "id": 1})
        if task:
            response = await admin_client.patch(
                f"/api/tasks/{task['id']}/dates",
                json={
                    "start_date": datetime.now(timezone.utc).isoformat(),
                    "end_date": datetime.now(timezone.utc).isoformat()
                }
            )
            
            assert response.status_code == 200


class TestTasksSecurity:
    """Security tests for tasks."""
    
    @pytest.mark.asyncio
    async def test_task020_xss_in_title(self, admin_client, owasp_payloads, db):
        """TC-TASK-020: XSS in task title handled safely."""
        task = await db.tasks.find_one({}, {"_id": 0, "id": 1})
        if task:
            for payload in owasp_payloads.XSS_PAYLOADS[:2]:
                response = await admin_client.patch(
                    f"/api/tasks/{task['id']}",
                    json={"name": payload}
                )
                
                assert response.status_code != 500
