"""
Test Gantt Chart Feature - Backend API Tests
- GET /api/projects/{project_id}/tasks-gantt - returns task data with start/end dates
- PATCH /api/tasks/{task_id}/dates - updates task start_date and due_date
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGanttChartBackend:
    """Test Gantt Chart backend endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for each test - login and get token"""
        self.session = requests.Session()
        # Login as admin
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
    def test_admin_login_works(self):
        """Verify admin login works"""
        resp = self.session.get(f"{BASE_URL}/api/auth/me")
        assert resp.status_code == 200
        user_data = resp.json()
        assert user_data.get("email") == "admin@company.com"
        assert user_data.get("role") == "admin"
        print("PASSED: Admin login verified")
        
    def test_get_projects_list(self):
        """Get list of all projects"""
        resp = self.session.get(f"{BASE_URL}/api/projects")
        assert resp.status_code == 200
        projects = resp.json()
        assert isinstance(projects, list), "Projects should be a list"
        print(f"PASSED: Got {len(projects)} projects")
        return projects
        
    def test_get_tasks_gantt_endpoint(self):
        """Test GET /api/projects/{project_id}/tasks-gantt endpoint"""
        # First get a project
        projects_resp = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_resp.status_code == 200
        projects = projects_resp.json()
        
        if not projects:
            pytest.skip("No projects available to test with")
        
        project_id = projects[0].get("id")
        project_name = projects[0].get("name")
        print(f"Testing with project: {project_name} ({project_id})")
        
        # Test tasks-gantt endpoint
        resp = self.session.get(f"{BASE_URL}/api/projects/{project_id}/tasks-gantt")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        tasks_gantt = resp.json()
        assert isinstance(tasks_gantt, list), "Response should be a list"
        print(f"PASSED: GET /api/projects/{project_id}/tasks-gantt returned {len(tasks_gantt)} tasks")
        
        # Verify response format for tasks
        if tasks_gantt:
            task = tasks_gantt[0]
            assert "id" in task, "Task should have 'id'"
            assert "name" in task, "Task should have 'name'"
            assert "start" in task, "Task should have 'start'"
            assert "end" in task, "Task should have 'end'"
            assert "status" in task, "Task should have 'status'"
            assert "priority" in task, "Task should have 'priority'"
            print(f"PASSED: Task format verified - keys: {list(task.keys())}")
            
        return project_id, tasks_gantt
    
    def test_get_tasks_gantt_invalid_project(self):
        """Test tasks-gantt with invalid project ID returns empty list"""
        fake_project_id = str(uuid.uuid4())
        resp = self.session.get(f"{BASE_URL}/api/projects/{fake_project_id}/tasks-gantt")
        # Should return 200 with empty list (not 404)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        tasks = resp.json()
        assert isinstance(tasks, list), "Response should be a list"
        assert len(tasks) == 0, "Should return empty list for non-existent project"
        print("PASSED: Invalid project returns empty task list")
        
    def test_patch_task_dates_endpoint(self):
        """Test PATCH /api/tasks/{task_id}/dates endpoint"""
        # Get a project with tasks
        projects_resp = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_resp.json()
        
        if not projects:
            pytest.skip("No projects available")
            
        # Find a project with tasks
        task_to_update = None
        for project in projects:
            tasks_resp = self.session.get(f"{BASE_URL}/api/projects/{project['id']}/tasks-gantt")
            if tasks_resp.status_code == 200:
                tasks = tasks_resp.json()
                if tasks:
                    task_to_update = tasks[0]
                    break
                    
        if not task_to_update:
            pytest.skip("No tasks available to test date update")
        
        task_id = task_to_update['id']
        
        # Test updating dates
        new_start = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        new_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        resp = self.session.patch(
            f"{BASE_URL}/api/tasks/{task_id}/dates",
            json={"start_date": new_start, "due_date": new_end}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        result = resp.json()
        assert "message" in result, "Response should have 'message'"
        print(f"PASSED: PATCH /api/tasks/{task_id}/dates - {result.get('message')}")
        
        # Verify the dates were updated by fetching the task again
        # Need to fetch via the gantt endpoint since that's our task source
        return task_id
        
    def test_patch_task_dates_with_end_date(self):
        """Test PATCH task dates accepts 'end_date' param (alternative to due_date)"""
        # Get a task
        projects_resp = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_resp.json()
        
        task_to_update = None
        for project in projects:
            tasks_resp = self.session.get(f"{BASE_URL}/api/projects/{project['id']}/tasks-gantt")
            if tasks_resp.status_code == 200:
                tasks = tasks_resp.json()
                if tasks:
                    task_to_update = tasks[0]
                    break
                    
        if not task_to_update:
            pytest.skip("No tasks available")
        
        task_id = task_to_update['id']
        new_end = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        
        # Test with 'end_date' instead of 'due_date'
        resp = self.session.patch(
            f"{BASE_URL}/api/tasks/{task_id}/dates",
            json={"end_date": new_end}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASSED: PATCH accepts 'end_date' parameter")
        
    def test_patch_task_dates_invalid_task(self):
        """Test PATCH dates with invalid task ID returns 404"""
        fake_task_id = str(uuid.uuid4())
        resp = self.session.patch(
            f"{BASE_URL}/api/tasks/{fake_task_id}/dates",
            json={"start_date": "2025-01-15"}
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        print("PASSED: Invalid task ID returns 404")
        
    def test_tasks_gantt_data_format(self):
        """Verify Gantt task data includes all required fields for UI"""
        projects_resp = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_resp.json()
        
        task_found = False
        for project in projects:
            tasks_resp = self.session.get(f"{BASE_URL}/api/projects/{project['id']}/tasks-gantt")
            tasks = tasks_resp.json()
            if tasks:
                task = tasks[0]
                # Check all fields needed by GanttChart.js
                required_fields = ['id', 'name', 'start', 'end', 'status', 'priority', 'progress']
                for field in required_fields:
                    assert field in task, f"Missing field: {field}"
                
                # Verify status is one of expected values
                valid_statuses = ['to_do', 'in_progress', 'completed', 'delayed', 'delegated', 'cancelled']
                assert task.get('status') in valid_statuses, f"Invalid status: {task.get('status')}"
                
                # Progress should be 0, 50, or 100
                assert task.get('progress') in [0, 50, 100], f"Invalid progress: {task.get('progress')}"
                
                task_found = True
                print(f"PASSED: Task data format verified - {task['name']} has all required fields")
                break
                
        if not task_found:
            pytest.skip("No tasks with data found to verify format")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
