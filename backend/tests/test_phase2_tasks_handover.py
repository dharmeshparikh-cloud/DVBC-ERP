"""
Phase 2 Testing - Task Management and Handover Alerts
Tests for:
- Task Management CRUD APIs
- Handover Alerts API
- Projects page navigation to tasks
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests for Phase 2 credentials"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        """Get manager token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_admin_login(self, admin_token):
        """Test admin can login"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful")
    
    def test_manager_login(self, manager_token):
        """Test manager can login"""
        assert manager_token is not None
        assert len(manager_token) > 0
        print(f"✓ Manager login successful")


class TestTaskManagement:
    """Task Management API tests"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get admin auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    @pytest.fixture(scope="class")
    def existing_project(self, auth_header):
        """Get or create a project for task testing"""
        # First try to get existing projects
        response = requests.get(f"{BASE_URL}/api/projects", headers=auth_header)
        assert response.status_code == 200
        projects = response.json()
        
        if projects:
            print(f"✓ Using existing project: {projects[0]['name']}")
            return projects[0]
        
        # Create a project if none exist
        project_data = {
            "name": "TEST_Task Testing Project",
            "client_name": "TEST Client",
            "start_date": datetime.now().isoformat(),
            "end_date": (datetime.now() + timedelta(days=90)).isoformat()
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_header)
        assert response.status_code == 200
        print(f"✓ Created new project for task testing")
        return response.json()
    
    def test_create_task_general(self, auth_header, existing_project):
        """Test creating a general task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_General Task",
            "description": "A test general task",
            "category": "general",
            "status": "to_do",
            "priority": "medium",
            "start_date": datetime.now().isoformat(),
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200, f"Failed to create task: {response.text}"
        
        task = response.json()
        assert task["title"] == "TEST_General Task"
        assert task["category"] == "general"
        assert task["status"] == "to_do"
        assert task["priority"] == "medium"
        print(f"✓ Created general task: {task['id']}")
        return task
    
    def test_create_task_meeting(self, auth_header, existing_project):
        """Test creating a meeting task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Client Meeting",
            "description": "Monthly status meeting with client",
            "category": "meeting",
            "status": "to_do",
            "priority": "high"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200
        task = response.json()
        assert task["category"] == "meeting"
        print(f"✓ Created meeting task: {task['id']}")
    
    def test_create_task_deliverable(self, auth_header, existing_project):
        """Test creating a deliverable task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Final Report Deliverable",
            "description": "Prepare and submit final report",
            "category": "deliverable",
            "status": "to_do",
            "priority": "urgent",
            "estimated_hours": 8.0
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200
        task = response.json()
        assert task["category"] == "deliverable"
        assert task["estimated_hours"] == 8.0
        print(f"✓ Created deliverable task: {task['id']}")
    
    def test_create_task_review(self, auth_header, existing_project):
        """Test creating a review task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Document Review",
            "category": "review",
            "status": "to_do",
            "priority": "low"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200
        task = response.json()
        assert task["category"] == "review"
        print(f"✓ Created review task: {task['id']}")
    
    def test_create_task_follow_up(self, auth_header, existing_project):
        """Test creating a follow up task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Client Follow Up",
            "category": "follow_up",
            "status": "to_do",
            "priority": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200
        task = response.json()
        assert task["category"] == "follow_up"
        print(f"✓ Created follow up task: {task['id']}")
    
    def test_create_task_admin(self, auth_header, existing_project):
        """Test creating an admin task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Admin Update Records",
            "category": "admin",
            "status": "to_do",
            "priority": "low"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200
        task = response.json()
        assert task["category"] == "admin"
        print(f"✓ Created admin task: {task['id']}")
    
    def test_create_task_client_communication(self, auth_header, existing_project):
        """Test creating a client communication task"""
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Send Client Update Email",
            "category": "client_communication",
            "status": "to_do",
            "priority": "high"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 200
        task = response.json()
        assert task["category"] == "client_communication"
        print(f"✓ Created client communication task: {task['id']}")
    
    def test_get_tasks_by_project(self, auth_header, existing_project):
        """Test getting tasks filtered by project"""
        response = requests.get(
            f"{BASE_URL}/api/tasks?project_id={existing_project['id']}", 
            headers=auth_header
        )
        assert response.status_code == 200
        tasks = response.json()
        assert isinstance(tasks, list)
        assert len(tasks) >= 7  # We created 7 tasks above
        print(f"✓ Retrieved {len(tasks)} tasks for project")
    
    def test_update_task_status_in_progress(self, auth_header, existing_project):
        """Test updating task status to in_progress"""
        # First get a task
        response = requests.get(
            f"{BASE_URL}/api/tasks?project_id={existing_project['id']}", 
            headers=auth_header
        )
        tasks = response.json()
        test_task = next((t for t in tasks if "TEST_" in t["title"]), tasks[0])
        
        # Update to in_progress
        response = requests.patch(
            f"{BASE_URL}/api/tasks/{test_task['id']}",
            json={"status": "in_progress"},
            headers=auth_header
        )
        assert response.status_code == 200
        print(f"✓ Updated task to in_progress status")
    
    def test_update_task_status_completed(self, auth_header, existing_project):
        """Test updating task status to completed"""
        response = requests.get(
            f"{BASE_URL}/api/tasks?project_id={existing_project['id']}", 
            headers=auth_header
        )
        tasks = response.json()
        test_task = next((t for t in tasks if t.get("status") == "in_progress"), tasks[0])
        
        response = requests.patch(
            f"{BASE_URL}/api/tasks/{test_task['id']}",
            json={"status": "completed"},
            headers=auth_header
        )
        assert response.status_code == 200
        print(f"✓ Updated task to completed status")
    
    def test_update_task_status_delegated(self, auth_header, existing_project):
        """Test updating task status to delegated"""
        response = requests.get(
            f"{BASE_URL}/api/tasks?project_id={existing_project['id']}", 
            headers=auth_header
        )
        tasks = response.json()
        test_task = next((t for t in tasks if t.get("status") == "to_do" and "TEST_" in t["title"]), None)
        
        if test_task:
            response = requests.patch(
                f"{BASE_URL}/api/tasks/{test_task['id']}",
                json={"status": "delegated"},
                headers=auth_header
            )
            assert response.status_code == 200
            print(f"✓ Updated task to delegated status")
        else:
            print("⚠ No suitable task found for delegated status test")
    
    def test_update_task_status_own_task(self, auth_header, existing_project):
        """Test updating task status to own_task"""
        response = requests.get(
            f"{BASE_URL}/api/tasks?project_id={existing_project['id']}", 
            headers=auth_header
        )
        tasks = response.json()
        test_task = next((t for t in tasks if t.get("status") == "to_do" and "TEST_" in t["title"]), None)
        
        if test_task:
            response = requests.patch(
                f"{BASE_URL}/api/tasks/{test_task['id']}",
                json={"status": "own_task"},
                headers=auth_header
            )
            assert response.status_code == 200
            print(f"✓ Updated task to own_task status")
        else:
            print("⚠ No suitable task found for own_task status test")
    
    def test_update_task_status_cancelled(self, auth_header, existing_project):
        """Test updating task status to cancelled"""
        # Create a task specifically for cancellation test
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Task to Cancel",
            "category": "general",
            "status": "to_do"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        task = response.json()
        
        response = requests.patch(
            f"{BASE_URL}/api/tasks/{task['id']}",
            json={"status": "cancelled"},
            headers=auth_header
        )
        assert response.status_code == 200
        print(f"✓ Updated task to cancelled status")
    
    def test_task_invalid_project(self, auth_header):
        """Test creating task with invalid project ID"""
        task_data = {
            "project_id": "invalid-project-id",
            "title": "TEST_Invalid Project Task",
            "category": "general"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        assert response.status_code == 404
        print(f"✓ Correctly rejected task with invalid project ID")
    
    def test_delete_task(self, auth_header, existing_project):
        """Test deleting a task"""
        # Create a task to delete
        task_data = {
            "project_id": existing_project["id"],
            "title": "TEST_Task to Delete",
            "category": "general",
            "status": "to_do"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=auth_header)
        task = response.json()
        
        # Delete the task
        response = requests.delete(f"{BASE_URL}/api/tasks/{task['id']}", headers=auth_header)
        assert response.status_code == 200
        
        # Verify it's deleted
        response = requests.get(f"{BASE_URL}/api/tasks/{task['id']}", headers=auth_header)
        assert response.status_code == 404
        print(f"✓ Task deleted successfully")
    
    def test_get_tasks_gantt_endpoint(self, auth_header, existing_project):
        """Test the gantt chart endpoint for tasks"""
        response = requests.get(
            f"{BASE_URL}/api/projects/{existing_project['id']}/tasks-gantt",
            headers=auth_header
        )
        assert response.status_code == 200
        gantt_data = response.json()
        assert isinstance(gantt_data, list)
        
        if gantt_data:
            first_task = gantt_data[0]
            assert "id" in first_task
            assert "name" in first_task
            assert "status" in first_task
            assert "progress" in first_task
        print(f"✓ Gantt endpoint returned {len(gantt_data)} tasks")


class TestHandoverAlerts:
    """Handover Alerts API tests"""
    
    @pytest.fixture(scope="class")
    def manager_header(self):
        """Get manager auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    @pytest.fixture(scope="class")
    def admin_header(self):
        """Get admin auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_handover_alerts_manager_access(self, manager_header):
        """Test manager can access handover alerts"""
        response = requests.get(f"{BASE_URL}/api/projects/handover-alerts", headers=manager_header)
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)
        print(f"✓ Manager can access handover alerts: {len(alerts)} alerts found")
    
    def test_handover_alerts_admin_access(self, admin_header):
        """Test admin can access handover alerts"""
        response = requests.get(f"{BASE_URL}/api/projects/handover-alerts", headers=admin_header)
        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)
        print(f"✓ Admin can access handover alerts: {len(alerts)} alerts found")
    
    def test_handover_alerts_structure(self, admin_header):
        """Test handover alerts response structure"""
        response = requests.get(f"{BASE_URL}/api/projects/handover-alerts", headers=admin_header)
        alerts = response.json()
        
        if alerts:
            alert = alerts[0]
            # Check expected fields
            assert "agreement" in alert
            assert "days_since_approval" in alert
            assert "days_remaining" in alert
            assert "alert_type" in alert
            assert "has_project" in alert
            assert "has_consultants_assigned" in alert
            
            # Check alert_type values
            assert alert["alert_type"] in ["overdue", "critical", "warning", "on_track"]
            print(f"✓ Handover alert structure is correct")
            print(f"  First alert: {alert['alert_type']} - {alert['days_remaining']} days remaining")
        else:
            print("⚠ No handover alerts found - may need approved agreements to test")
    
    def test_handover_alerts_executive_forbidden(self):
        """Test executive cannot access handover alerts (role restriction)"""
        # Login as executive
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        
        if response.status_code == 200:
            exec_header = {"Authorization": f"Bearer {response.json()['access_token']}"}
            response = requests.get(f"{BASE_URL}/api/projects/handover-alerts", headers=exec_header)
            assert response.status_code == 403
            print(f"✓ Executive correctly denied access to handover alerts")
        else:
            pytest.skip("Executive user not found")


class TestProjectsPageFeatures:
    """Test project page features including Tasks and Assign Consultant buttons"""
    
    @pytest.fixture(scope="class")
    def auth_header(self):
        """Get admin auth header"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}
    
    def test_projects_endpoint(self, auth_header):
        """Test projects endpoint works"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=auth_header)
        assert response.status_code == 200
        projects = response.json()
        assert isinstance(projects, list)
        print(f"✓ Projects endpoint returned {len(projects)} projects")
    
    def test_consultants_endpoint(self, auth_header):
        """Test consultants endpoint works (needed for assign consultant feature)"""
        response = requests.get(f"{BASE_URL}/api/consultants", headers=auth_header)
        assert response.status_code == 200
        consultants = response.json()
        assert isinstance(consultants, list)
        print(f"✓ Consultants endpoint returned {len(consultants)} consultants")
    
    def test_assign_consultant_to_project(self, auth_header):
        """Test assigning consultant to project"""
        # Get existing projects
        response = requests.get(f"{BASE_URL}/api/projects", headers=auth_header)
        projects = response.json()
        
        if not projects:
            pytest.skip("No projects available for assignment test")
        
        # Get existing consultants
        response = requests.get(f"{BASE_URL}/api/consultants", headers=auth_header)
        consultants = response.json()
        
        if not consultants:
            print("⚠ No consultants available to test assignment")
            return
        
        project = projects[0]
        consultant = consultants[0]
        
        # Try to assign consultant
        assignment_data = {
            "consultant_id": consultant["id"],
            "project_id": project["id"],
            "role_in_project": "consultant",
            "meetings_committed": 5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{project['id']}/assign-consultant",
            json=assignment_data,
            headers=auth_header
        )
        
        # Either success or already assigned
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            print(f"✓ Consultant assigned to project successfully")
        else:
            print(f"⚠ Consultant may already be assigned: {response.json()}")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests"""
    yield
    # Cleanup can be added here if needed
    print("\n✓ Test session completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
