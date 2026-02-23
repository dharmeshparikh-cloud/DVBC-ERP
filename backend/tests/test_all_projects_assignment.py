"""
Test All Projects Assignment Endpoints for Principal Consultants
Tests the new consultant assignment features:
- GET /api/projects/all/for-assignment
- POST /api/projects/{id}/assign-consultant
- DELETE /api/projects/{id}/unassign-consultant/{consultant_id}
- GET /api/projects/{id}/assignment-history
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAllProjectsAssignment:
    """Test consultant assignment endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and tokens"""
        # Login as Principal Consultant
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "PC001",
            "password": "test123"
        })
        assert login_resp.status_code == 200, f"PC001 login failed: {login_resp.text}"
        self.pc_token = login_resp.json().get('access_token')
        self.pc_user = login_resp.json().get('user')
        
        # Login as Senior Consultant
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SC001",
            "password": "test123"
        })
        assert login_resp.status_code == 200, f"SC001 login failed: {login_resp.text}"
        self.sc_token = login_resp.json().get('access_token')
        
        # Get consultants list
        consultants_resp = requests.get(
            f"{BASE_URL}/api/consultants",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        if consultants_resp.status_code == 200:
            consultants = consultants_resp.json()
            if consultants:
                self.consultant_id = consultants[0].get('id')
                self.consultant_name = consultants[0].get('full_name')
    
    def test_get_all_projects_for_assignment_as_pc(self):
        """Test GET /api/projects/all/for-assignment as Principal Consultant"""
        response = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert 'projects' in data, "Response should contain 'projects' key"
        assert 'total' in data, "Response should contain 'total' key"
        assert 'needs_assignment_count' in data, "Response should contain 'needs_assignment_count' key"
        assert isinstance(data['projects'], list), "Projects should be a list"
        
        # Validate project structure if projects exist
        if data['projects']:
            project = data['projects'][0]
            assert 'id' in project, "Project should have 'id'"
            assert 'has_consultants' in project, "Project should have 'has_consultants' flag"
            assert 'consultant_assignments' in project, "Project should have 'consultant_assignments'"
        
        print(f"✓ Retrieved {data['total']} projects, {data['needs_assignment_count']} need assignment")
    
    def test_get_projects_with_needs_assignment_filter_true(self):
        """Test filtering projects that need assignment"""
        response = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment?needs_assignment=true",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # All returned projects should not have consultants
        for project in data['projects']:
            assert project.get('has_consultants') == False, \
                f"Project {project.get('id')} should not have consultants when needs_assignment=true"
        
        print(f"✓ Needs assignment filter works - {len(data['projects'])} projects without consultants")
    
    def test_get_projects_with_needs_assignment_filter_false(self):
        """Test filtering projects that already have assignments"""
        response = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment?needs_assignment=false",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # All returned projects should have consultants
        for project in data['projects']:
            assert project.get('has_consultants') == True, \
                f"Project {project.get('id')} should have consultants when needs_assignment=false"
        
        print(f"✓ Assigned filter works - {len(data['projects'])} projects with consultants")
    
    def test_get_all_projects_as_senior_consultant(self):
        """Test Senior Consultant also has access"""
        response = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment",
            headers={"Authorization": f"Bearer {self.sc_token}"}
        )
        
        assert response.status_code == 200, f"SC001 should have access: {response.text}"
        print("✓ Senior Consultant has access to all projects view")
    
    def test_assign_consultant_to_project(self):
        """Test POST /api/projects/{id}/assign-consultant"""
        # Get a project that needs assignment
        projects_resp = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment?needs_assignment=true",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if projects_resp.status_code != 200 or not projects_resp.json().get('projects'):
            pytest.skip("No projects available for assignment test")
        
        project_id = projects_resp.json()['projects'][0]['id']
        
        # Assign consultant
        assign_resp = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/assign-consultant",
            headers={"Authorization": f"Bearer {self.pc_token}"},
            json={
                "consultant_id": self.consultant_id,
                "role_in_project": "consultant",
                "meetings_committed": 3,
                "notes": "Pytest test assignment"
            }
        )
        
        assert assign_resp.status_code == 200, f"Assignment failed: {assign_resp.text}"
        data = assign_resp.json()
        
        assert 'message' in data, "Response should contain message"
        assert 'assignment_id' in data, "Response should contain assignment_id"
        
        # Store for cleanup
        self.test_project_id = project_id
        self.test_assignment_id = data['assignment_id']
        
        print(f"✓ Consultant assigned successfully - Assignment ID: {data['assignment_id']}")
    
    def test_get_assignment_history(self):
        """Test GET /api/projects/{id}/assignment-history"""
        # Get a project
        projects_resp = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if projects_resp.status_code != 200 or not projects_resp.json().get('projects'):
            pytest.skip("No projects available for history test")
        
        project_id = projects_resp.json()['projects'][0]['id']
        
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/assignment-history",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert 'project_id' in data, "Response should contain project_id"
        assert 'assignments' in data, "Response should contain assignments list"
        assert 'active_count' in data, "Response should contain active_count"
        assert 'total_count' in data, "Response should contain total_count"
        
        print(f"✓ Assignment history retrieved - {data['total_count']} total, {data['active_count']} active")
    
    def test_unassign_consultant_from_project(self):
        """Test DELETE /api/projects/{id}/unassign-consultant/{consultant_id}"""
        # First assign a consultant
        projects_resp = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment?needs_assignment=true",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if projects_resp.status_code != 200 or not projects_resp.json().get('projects'):
            pytest.skip("No projects available for unassign test")
        
        project_id = projects_resp.json()['projects'][0]['id']
        
        # Assign consultant first
        assign_resp = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/assign-consultant",
            headers={"Authorization": f"Bearer {self.pc_token}"},
            json={
                "consultant_id": self.consultant_id,
                "role_in_project": "consultant"
            }
        )
        
        if assign_resp.status_code != 200:
            pytest.skip("Could not assign consultant for unassign test")
        
        # Now unassign
        unassign_resp = requests.delete(
            f"{BASE_URL}/api/projects/{project_id}/unassign-consultant/{self.consultant_id}",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        assert unassign_resp.status_code == 200, f"Unassign failed: {unassign_resp.text}"
        data = unassign_resp.json()
        assert 'message' in data, "Response should contain message"
        
        # Verify consultant is marked as inactive in history
        history_resp = requests.get(
            f"{BASE_URL}/api/projects/{project_id}/assignment-history",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if history_resp.status_code == 200:
            history = history_resp.json()
            # Find the unassigned consultant
            for assignment in history.get('assignments', []):
                if assignment.get('consultant_id') == self.consultant_id:
                    assert assignment.get('is_active') == False, \
                        "Unassigned consultant should be marked inactive"
                    break
        
        print(f"✓ Consultant unassigned successfully - history preserved")
    
    def test_duplicate_assignment_prevention(self):
        """Test that duplicate assignments are prevented"""
        # Get a project
        projects_resp = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment?needs_assignment=true",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if projects_resp.status_code != 200 or not projects_resp.json().get('projects'):
            pytest.skip("No projects available for duplicate test")
        
        project_id = projects_resp.json()['projects'][0]['id']
        
        # First assignment
        assign_resp1 = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/assign-consultant",
            headers={"Authorization": f"Bearer {self.pc_token}"},
            json={"consultant_id": self.consultant_id}
        )
        
        if assign_resp1.status_code != 200:
            pytest.skip("First assignment failed")
        
        # Second assignment (should fail)
        assign_resp2 = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/assign-consultant",
            headers={"Authorization": f"Bearer {self.pc_token}"},
            json={"consultant_id": self.consultant_id}
        )
        
        assert assign_resp2.status_code == 400, \
            f"Duplicate assignment should return 400, got {assign_resp2.status_code}"
        assert 'already assigned' in assign_resp2.json().get('detail', '').lower(), \
            "Error message should mention already assigned"
        
        # Cleanup - unassign
        requests.delete(
            f"{BASE_URL}/api/projects/{project_id}/unassign-consultant/{self.consultant_id}",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        print("✓ Duplicate assignment prevention working")
    
    def test_assign_consultant_missing_consultant_id(self):
        """Test assignment without consultant_id returns 400"""
        projects_resp = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if projects_resp.status_code != 200 or not projects_resp.json().get('projects'):
            pytest.skip("No projects available")
        
        project_id = projects_resp.json()['projects'][0]['id']
        
        response = requests.post(
            f"{BASE_URL}/api/projects/{project_id}/assign-consultant",
            headers={"Authorization": f"Bearer {self.pc_token}"},
            json={}
        )
        
        assert response.status_code == 400, \
            f"Missing consultant_id should return 400, got {response.status_code}"
        
        print("✓ Validation for missing consultant_id working")
    
    def test_assign_consultant_invalid_project(self):
        """Test assignment to non-existent project returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/projects/invalid-project-id/assign-consultant",
            headers={"Authorization": f"Bearer {self.pc_token}"},
            json={"consultant_id": self.consultant_id}
        )
        
        assert response.status_code == 404, \
            f"Invalid project should return 404, got {response.status_code}"
        
        print("✓ Invalid project ID returns 404")
    
    def test_unassign_non_assigned_consultant(self):
        """Test unassigning a consultant not assigned to project"""
        projects_resp = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment?needs_assignment=true",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        if projects_resp.status_code != 200 or not projects_resp.json().get('projects'):
            pytest.skip("No projects available")
        
        project_id = projects_resp.json()['projects'][0]['id']
        
        response = requests.delete(
            f"{BASE_URL}/api/projects/{project_id}/unassign-consultant/non-existent-consultant-id",
            headers={"Authorization": f"Bearer {self.pc_token}"}
        )
        
        assert response.status_code == 404, \
            f"Non-assigned consultant should return 404, got {response.status_code}"
        
        print("✓ Unassign non-existent assignment returns 404")


class TestAccessControl:
    """Test access control for assignment endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for different roles"""
        # Get PC token
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "PC001",
            "password": "test123"
        })
        if login_resp.status_code == 200:
            self.pc_token = login_resp.json().get('access_token')
        
        # Get consultant token (CON001)
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "CON001",
            "password": "test123"
        })
        if login_resp.status_code == 200:
            self.con_token = login_resp.json().get('access_token')
        else:
            self.con_token = None
    
    def test_regular_consultant_cannot_access_for_assignment(self):
        """Test that regular consultants cannot access all projects view"""
        if not self.con_token:
            pytest.skip("CON001 login not available")
        
        response = requests.get(
            f"{BASE_URL}/api/projects/all/for-assignment",
            headers={"Authorization": f"Bearer {self.con_token}"}
        )
        
        assert response.status_code == 403, \
            f"Regular consultant should get 403, got {response.status_code}"
        
        print("✓ Regular consultant access denied correctly")
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        response = requests.get(f"{BASE_URL}/api/projects/all/for-assignment")
        
        assert response.status_code in [401, 403], \
            f"Unauthenticated should get 401/403, got {response.status_code}"
        
        print("✓ Unauthenticated access denied")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
