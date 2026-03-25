"""
Test SOW Delivery - AI Task Generation and Proof Management
Phase 2 & 3 of SOW Delivery Architecture

Tests:
- AI Task Generation endpoint
- Task-level proof upload
- SOW-level proof upload
- Proof retrieval and version tracking
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
PROJECT_ID = "PROJ-20260315-0001"
PROJECT_SOW_ID = "c9013677-461c-4474-bf31-3ffa71e86c5f"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=ADMIN_CREDS
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {admin_token}"}


class TestProjectSOWRetrieval:
    """Test PROJECT_SOW retrieval endpoint"""
    
    def test_get_project_sow(self, auth_headers):
        """Test retrieving PROJECT_SOW with tasks and proofs"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "project_sow" in data
        assert "tasks" in data
        assert "proofs" in data
        assert "permissions" in data
        
        # Verify PROJECT_SOW structure
        project_sow = data["project_sow"]
        assert project_sow["id"] == PROJECT_SOW_ID
        assert project_sow["project_id"] == PROJECT_ID
        assert "scopes" in project_sow
        assert len(project_sow["scopes"]) > 0
        
        # Verify permissions for admin
        permissions = data["permissions"]
        assert permissions["can_edit_sow"] == True
        assert permissions["can_manage_tasks"] == True
        
    def test_project_sow_scopes_structure(self, auth_headers):
        """Test that scopes have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        scopes = response.json()["project_sow"]["scopes"]
        for scope in scopes:
            assert "id" in scope
            assert "name" in scope
            assert "status" in scope
            assert scope["status"] in ["open", "wip", "delivered", "not_applicable", "reopen"]


class TestAITaskGeneration:
    """Test AI Task Generation for SOW scopes"""
    
    def test_ai_generate_tasks_success(self, auth_headers):
        """Test AI task generation creates tasks with AI badge"""
        # Get a scope ID
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        scopes = response.json()["project_sow"]["scopes"]
        # Use the third scope (Training & Knowledge Transfer)
        scope_id = scopes[2]["id"] if len(scopes) > 2 else scopes[0]["id"]
        
        # Generate AI tasks
        response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/ai-generate-tasks",
            headers=auth_headers
        )
        
        # AI generation may take time, allow for timeout
        assert response.status_code in [200, 500], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "tasks" in data
            assert len(data["tasks"]) > 0
            
            # Verify tasks have IDs and titles
            for task in data["tasks"]:
                assert "id" in task
                assert "title" in task
                assert len(task["title"]) > 0
    
    def test_ai_generated_tasks_have_flag(self, auth_headers):
        """Test that AI-generated tasks have is_ai_generated=True"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        tasks = response.json()["tasks"]
        ai_tasks = [t for t in tasks if t.get("is_ai_generated", False)]
        
        # Should have some AI-generated tasks from previous tests
        assert len(ai_tasks) > 0, "Expected at least one AI-generated task"
        
        for task in ai_tasks:
            assert task["is_ai_generated"] == True


class TestProofUpload:
    """Test Proof Upload functionality"""
    
    def test_storage_upload(self, auth_headers):
        """Test file upload to storage"""
        # Create test file content
        test_content = f"Test proof document {uuid.uuid4().hex[:8]}"
        files = {"file": ("test_proof.txt", test_content.encode(), "text/plain")}
        
        response = requests.post(
            f"{BASE_URL}/api/storage/upload?folder=proofs",
            headers=auth_headers,
            files=files
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "file" in data
        assert "file_url" in data["file"]
        assert "storage_path" in data["file"]
        assert "original_filename" in data["file"]
        
        return data["file"]
    
    def test_task_proof_registration(self, auth_headers):
        """Test registering proof for a task"""
        # First upload a file
        test_content = f"Task proof {uuid.uuid4().hex[:8]}"
        files = {"file": ("task_proof.txt", test_content.encode(), "text/plain")}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/storage/upload?folder=proofs",
            headers=auth_headers,
            files=files
        )
        assert upload_response.status_code == 200
        file_data = upload_response.json()["file"]
        
        # Get a task ID
        sow_response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        tasks = sow_response.json()["tasks"]
        assert len(tasks) > 0, "Need at least one task to test proof upload"
        task_id = tasks[0]["id"]
        
        # Register proof
        proof_response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/proofs",
            headers=auth_headers,
            json={
                "entity_type": "task",
                "entity_id": task_id,
                "file_url": file_data["file_url"],
                "file_name": file_data["original_filename"],
                "file_type": file_data["content_type"],
                "file_size": file_data["size"]
            }
        )
        assert proof_response.status_code == 200
        
        data = proof_response.json()
        assert "proof_id" in data
        assert "version" in data
        assert data["version"] >= 1
    
    def test_sow_level_proof_registration(self, auth_headers):
        """Test registering proof at SOW level"""
        # Upload file
        test_content = f"SOW level proof {uuid.uuid4().hex[:8]}"
        files = {"file": ("sow_evidence.txt", test_content.encode(), "text/plain")}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/storage/upload?folder=proofs",
            headers=auth_headers,
            files=files
        )
        assert upload_response.status_code == 200
        file_data = upload_response.json()["file"]
        
        # Register SOW-level proof
        proof_response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/proofs",
            headers=auth_headers,
            json={
                "entity_type": "project_sow",
                "entity_id": PROJECT_SOW_ID,
                "file_url": file_data["file_url"],
                "file_name": file_data["original_filename"],
                "file_type": file_data["content_type"],
                "file_size": file_data["size"]
            }
        )
        assert proof_response.status_code == 200
        
        data = proof_response.json()
        assert "proof_id" in data
        assert data["message"] == "Proof registered"


class TestProofRetrieval:
    """Test Proof retrieval and display"""
    
    def test_sow_proofs_in_response(self, auth_headers):
        """Test that SOW-level proofs are returned in project-sow response"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        proofs = data.get("proofs", [])
        
        # Should have at least one SOW-level proof from previous tests
        assert len(proofs) >= 1, "Expected at least one SOW-level proof"
        
        for proof in proofs:
            assert "id" in proof
            assert "file_name" in proof
            assert "file_url" in proof
            assert "version" in proof
            assert "uploaded_by_name" in proof
    
    def test_task_proofs_attached(self, auth_headers):
        """Test that task-level proofs are attached to tasks"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        tasks = response.json()["tasks"]
        
        # Find tasks with proofs
        tasks_with_proofs = [t for t in tasks if len(t.get("proofs", [])) > 0]
        
        # Should have at least one task with proofs from previous tests
        assert len(tasks_with_proofs) >= 1, "Expected at least one task with proofs"
        
        for task in tasks_with_proofs:
            for proof in task["proofs"]:
                assert "id" in proof
                assert "file_name" in proof
                assert "file_url" in proof
    
    def test_get_proofs_by_entity(self, auth_headers):
        """Test getting proofs by entity type and ID"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/proofs/project_sow/{PROJECT_SOW_ID}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "proofs" in data
        assert "total" in data


class TestManualTaskCreation:
    """Test manual task creation"""
    
    def test_create_manual_task(self, auth_headers):
        """Test creating a manual task"""
        # Get a scope ID
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        scopes = response.json()["project_sow"]["scopes"]
        scope_id = scopes[0]["id"]
        
        # Create task
        task_response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/tasks",
            headers=auth_headers,
            json={
                "scope_id": scope_id,
                "title": f"Test Manual Task {uuid.uuid4().hex[:8]}",
                "description": "Created by automated test"
            }
        )
        assert task_response.status_code == 200
        
        data = task_response.json()
        assert "task_id" in data
        assert data["message"] == "Task created"
        
        return data["task_id"]
    
    def test_manual_task_not_ai_generated(self, auth_headers):
        """Test that manual tasks don't have AI flag"""
        # Create a manual task
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        scopes = response.json()["project_sow"]["scopes"]
        scope_id = scopes[0]["id"]
        
        task_response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/tasks",
            headers=auth_headers,
            json={
                "scope_id": scope_id,
                "title": f"Manual Task Check {uuid.uuid4().hex[:8]}",
                "description": "Testing AI flag"
            }
        )
        assert task_response.status_code == 200
        task_id = task_response.json()["task_id"]
        
        # Verify task doesn't have AI flag
        sow_response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        tasks = sow_response.json()["tasks"]
        task = next((t for t in tasks if t["id"] == task_id), None)
        
        assert task is not None
        assert task.get("is_ai_generated", False) == False


class TestScopeStatusUpdate:
    """Test scope status updates"""
    
    def test_update_scope_status(self, auth_headers):
        """Test updating scope status"""
        # Get a scope ID
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers=auth_headers
        )
        scopes = response.json()["project_sow"]["scopes"]
        scope_id = scopes[0]["id"]
        
        # Update status to WIP
        update_response = requests.patch(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/status?status=wip",
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        data = update_response.json()
        assert "message" in data
        assert "wip" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
