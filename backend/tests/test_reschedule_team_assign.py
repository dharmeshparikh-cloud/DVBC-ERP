"""
Test Reschedule Requests and Team Assignment Features
- POST /api/projects/{project_id}/reschedule-requests
- GET /api/projects/{project_id}/reschedule-requests
- Team Assignment Dialog state variables in KickoffRequests.js
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRescheduleRequests:
    """Test reschedule request endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a project to test with
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200, f"Failed to get projects: {projects_response.text}"
        projects = projects_response.json()
        assert len(projects) > 0, "No projects found for testing"
        self.test_project = projects[0]
        self.project_id = self.test_project.get("id")
        print(f"Using project: {self.project_id} - {self.test_project.get('name', 'Unknown')}")
    
    def test_create_reschedule_request(self):
        """Test creating a reschedule request"""
        # Create reschedule request with query params
        params = {
            "reason": "Client unavailable",
            "preferred_date": "2026-02-15",
            "preferred_time": "10:00",
            "notes": "Test reschedule request from automated testing"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/reschedule-requests",
            params=params
        )
        
        print(f"Create reschedule response: {response.status_code} - {response.text}")
        assert response.status_code == 200, f"Failed to create reschedule request: {response.text}"
        
        data = response.json()
        assert "request_id" in data, "Response should contain request_id"
        assert data.get("message") == "Reschedule request submitted", f"Unexpected message: {data.get('message')}"
        
        self.request_id = data.get("request_id")
        print(f"Created reschedule request: {self.request_id}")
    
    def test_get_reschedule_requests(self):
        """Test getting reschedule requests for a project"""
        response = self.session.get(f"{BASE_URL}/api/projects/{self.project_id}/reschedule-requests")
        
        print(f"Get reschedule requests response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get reschedule requests: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"Found {len(data)} reschedule requests for project {self.project_id}")
        
        # Verify structure of requests
        if len(data) > 0:
            req = data[0]
            assert "id" in req, "Request should have id"
            assert "reason" in req, "Request should have reason"
            assert "status" in req, "Request should have status"
            assert "requested_by" in req, "Request should have requested_by"
            print(f"Sample request: id={req.get('id')}, reason={req.get('reason')}, status={req.get('status')}")
    
    def test_create_reschedule_with_different_reasons(self):
        """Test creating reschedule requests with different reasons"""
        reasons = [
            "Resource conflict",
            "Scope change needed",
            "Technical dependencies"
        ]
        
        for reason in reasons:
            params = {
                "reason": reason,
                "notes": f"Testing {reason}"
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/projects/{self.project_id}/reschedule-requests",
                params=params
            )
            
            assert response.status_code == 200, f"Failed to create reschedule with reason '{reason}': {response.text}"
            print(f"Created reschedule request with reason: {reason}")
    
    def test_reschedule_request_without_reason_fails(self):
        """Test that creating reschedule without reason fails"""
        # Try without reason parameter
        response = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/reschedule-requests"
        )
        
        # Should fail with 422 (validation error) since reason is required
        print(f"No reason response: {response.status_code}")
        assert response.status_code == 422, f"Expected 422 for missing reason, got {response.status_code}"
    
    def test_reschedule_for_nonexistent_project(self):
        """Test reschedule request for non-existent project"""
        params = {"reason": "Test reason"}
        response = self.session.post(
            f"{BASE_URL}/api/projects/NONEXISTENT-PROJECT-ID/reschedule-requests",
            params=params
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent project, got {response.status_code}"


class TestKickoffRequestsEndpoints:
    """Test kickoff requests endpoints for team assignment flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def test_get_kickoff_requests(self):
        """Test getting kickoff requests"""
        response = self.session.get(f"{BASE_URL}/api/kickoff-requests")
        
        print(f"Get kickoff requests response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get kickoff requests: {response.text}"
        
        data = response.json()
        print(f"Found {len(data)} kickoff requests")
        
        # Check for pending requests
        pending = [r for r in data if r.get("status") == "pending"]
        print(f"Pending kickoff requests: {len(pending)}")
    
    def test_get_consultants_for_assignment(self):
        """Test getting consultants list for team assignment"""
        response = self.session.get(f"{BASE_URL}/api/employees/consultants")
        
        print(f"Get consultants response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get consultants: {response.text}"
        
        data = response.json()
        print(f"Found {len(data)} consultants available for assignment")
        
        if len(data) > 0:
            consultant = data[0]
            print(f"Sample consultant: {consultant.get('first_name')} {consultant.get('last_name')}")


class TestProjectAssignConsultant:
    """Test consultant assignment to project"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Get a project
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200
        projects = projects_response.json()
        assert len(projects) > 0
        self.test_project = projects[0]
        self.project_id = self.test_project.get("id")
        
        # Get a consultant
        consultants_response = self.session.get(f"{BASE_URL}/api/employees/consultants")
        if consultants_response.status_code == 200:
            consultants = consultants_response.json()
            if len(consultants) > 0:
                self.test_consultant = consultants[0]
            else:
                self.test_consultant = None
        else:
            self.test_consultant = None
    
    def test_assign_consultant_endpoint_exists(self):
        """Test that assign consultant endpoint exists"""
        if not self.test_consultant:
            pytest.skip("No consultants available for testing")
        
        # Try to assign consultant
        response = self.session.post(
            f"{BASE_URL}/api/projects/{self.project_id}/assign-consultant",
            json={
                "consultant_id": self.test_consultant.get("user_id"),
                "role_in_project": "consultant"
            }
        )
        
        print(f"Assign consultant response: {response.status_code} - {response.text}")
        # Should be 200 (success) or 400 (already assigned)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
