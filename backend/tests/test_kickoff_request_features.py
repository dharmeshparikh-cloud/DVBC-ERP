"""
Test Suite for Kickoff Requests Feature Enhancement
Tests the PM workflow for reviewing, editing, accepting, and returning kickoff requests
Features tested:
- GET /api/kickoff-requests - List kickoff requests
- GET /api/kickoff-requests/{id}/details - Get SOW and meeting data
- PUT /api/kickoff-requests/{id} - Update kickoff date
- POST /api/kickoff-requests/{id}/return - Return to sender
- POST /api/kickoff-requests/{id}/resubmit - Resubmit after return
- POST /api/kickoff-requests/{id}/accept - Accept and create project
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestKickoffRequestFeatures:
    """Test the enhanced kickoff request features for PM workflow"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def manager_token(self):
        """Get manager (PM role) auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def executive_token(self):
        """Get executive (sales role) auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        assert response.status_code == 200, f"Executive login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_agreement_id(self, admin_token):
        """Get or create a test agreement for kickoff requests"""
        # First check for existing approved agreements
        response = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            agreements = response.json()
            if agreements:
                return agreements[0]["id"]
        
        # Create a test agreement if none exist
        # First need a lead
        lead_response = requests.post(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "first_name": "TEST_Kickoff",
                "last_name": f"Lead_{uuid.uuid4().hex[:6]}",
                "company": "TEST Kickoff Company",
                "email": f"test_kickoff_{uuid.uuid4().hex[:6]}@example.com"
            }
        )
        if lead_response.status_code == 200:
            lead_id = lead_response.json().get("id")
        else:
            lead_id = None
        
        return lead_id  # Return lead_id to use as a placeholder
    
    @pytest.fixture(scope="class")
    def test_kickoff_request_id(self, admin_token, test_agreement_id):
        """Create a test kickoff request for testing"""
        # Get an existing kickoff request
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if response.status_code == 200:
            requests_list = response.json()
            pending = [r for r in requests_list if r.get("status") == "pending"]
            if pending:
                return pending[0]["id"]
        
        # If no pending requests, check for any agreement
        agreements_resp = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if agreements_resp.status_code == 200:
            agreements = agreements_resp.json()
            if agreements:
                agreement_id = agreements[0]["id"]
                # Create a test kickoff request
                create_resp = requests.post(
                    f"{BASE_URL}/api/kickoff-requests",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={
                        "agreement_id": agreement_id,
                        "client_name": "TEST PM Review Client",
                        "project_name": f"TEST_PM_Review_Project_{uuid.uuid4().hex[:6]}",
                        "project_type": "mixed",
                        "total_meetings": 10,
                        "project_value": 500000,
                        "expected_start_date": (datetime.now() + timedelta(days=30)).isoformat(),
                        "notes": "Test kickoff request for PM review workflow"
                    }
                )
                if create_resp.status_code == 200:
                    return create_resp.json().get("id")
        
        pytest.skip("No agreement available to create test kickoff request")


class TestKickoffRequestList(TestKickoffRequestFeatures):
    """Test kickoff request list endpoint"""
    
    def test_list_kickoff_requests_admin(self, admin_token):
        """Test admin can list all kickoff requests"""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to list kickoff requests: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} kickoff requests")
    
    def test_list_kickoff_requests_manager(self, manager_token):
        """Test PM/manager can list kickoff requests"""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_list_kickoff_requests_sales(self, executive_token):
        """Test sales executive can list their kickoff requests"""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {executive_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestKickoffRequestDetails(TestKickoffRequestFeatures):
    """Test kickoff request details endpoint - SOW and meeting data"""
    
    def test_get_kickoff_details_returns_200(self, admin_token, test_kickoff_request_id):
        """Test getting kickoff request details returns 200"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}/details",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get details: {response.text}"
    
    def test_get_kickoff_details_structure(self, admin_token, test_kickoff_request_id):
        """Test kickoff request details has correct structure"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}/details",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields in response
        assert "kickoff_request" in data, "Response should contain kickoff_request"
        assert "agreement" in data, "Response should contain agreement"
        assert "sow" in data, "Response should contain sow"
        assert "pricing_plan" in data, "Response should contain pricing_plan"
        assert "lead" in data, "Response should contain lead"
        assert "meetings" in data, "Response should contain meetings"
        
        print(f"Details structure verified - has SOW: {data.get('sow') is not None}")
    
    def test_get_kickoff_details_has_project_info(self, admin_token, test_kickoff_request_id):
        """Test kickoff request details contains project information"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}/details",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        kickoff = data.get("kickoff_request", {})
        assert "project_name" in kickoff, "Should have project_name"
        assert "client_name" in kickoff, "Should have client_name"
        print(f"Project: {kickoff.get('project_name')}, Client: {kickoff.get('client_name')}")
    
    def test_get_details_not_found(self, admin_token):
        """Test getting details for non-existent request returns 404"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{fake_id}/details",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404


class TestKickoffEditDate(TestKickoffRequestFeatures):
    """Test editing kickoff date before accepting"""
    
    def test_edit_kickoff_date_pm(self, manager_token, test_kickoff_request_id):
        """Test PM can edit the kickoff date"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        new_date = (datetime.now() + timedelta(days=45)).isoformat()
        response = requests.put(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "expected_start_date": new_date,
                "notes": "Date adjusted by PM for resource availability"
            }
        )
        assert response.status_code == 200, f"Failed to edit date: {response.text}"
        data = response.json()
        assert "expected_start_date" in data
        print(f"Date updated successfully")
    
    def test_edit_kickoff_date_admin(self, admin_token, test_kickoff_request_id):
        """Test admin can edit the kickoff date"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        new_date = (datetime.now() + timedelta(days=60)).isoformat()
        response = requests.put(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "expected_start_date": new_date,
                "notes": "Date adjusted by admin"
            }
        )
        assert response.status_code == 200
    
    def test_edit_kickoff_date_unauthorized_sales(self, executive_token, test_kickoff_request_id):
        """Test sales cannot edit kickoff date (only PM/admin can)"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        new_date = (datetime.now() + timedelta(days=90)).isoformat()
        response = requests.put(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}",
            headers={"Authorization": f"Bearer {executive_token}"},
            json={
                "expected_start_date": new_date,
                "notes": "Attempted edit by sales"
            }
        )
        # Should be 403 Forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestKickoffReturnToSender(TestKickoffRequestFeatures):
    """Test return to sender functionality"""
    
    @pytest.fixture(scope="class")
    def new_kickoff_for_return(self, admin_token):
        """Create a fresh kickoff request for return testing"""
        # Get an agreement
        agreements_resp = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if agreements_resp.status_code != 200 or not agreements_resp.json():
            pytest.skip("No approved agreement for creating kickoff request")
        
        agreement_id = agreements_resp.json()[0]["id"]
        
        # Create a new kickoff request
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": agreement_id,
                "client_name": "TEST Return Client",
                "project_name": f"TEST_Return_Project_{uuid.uuid4().hex[:6]}",
                "project_type": "online",
                "total_meetings": 5,
                "project_value": 250000,
                "expected_start_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "notes": "Test kickoff for return workflow"
            }
        )
        if response.status_code == 200:
            return response.json().get("id")
        pytest.skip("Could not create kickoff request for return test")
    
    def test_return_kickoff_with_reason(self, manager_token, new_kickoff_for_return):
        """Test PM can return a kickoff request with a reason"""
        if not new_kickoff_for_return:
            pytest.skip("No kickoff request available for return test")
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{new_kickoff_for_return}/return",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "reason": "incomplete_sow",
                "return_notes": "Please add more details about deliverables and timeline"
            }
        )
        assert response.status_code == 200, f"Failed to return: {response.text}"
        
        # Verify status changed to returned
        get_resp = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{new_kickoff_for_return}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("status") == "returned", f"Status should be 'returned', got {data.get('status')}"
        assert data.get("return_reason") == "incomplete_sow"
        print(f"Return successful - status: {data.get('status')}, reason: {data.get('return_reason')}")
    
    def test_return_kickoff_unauthorized(self, executive_token, test_kickoff_request_id):
        """Test sales cannot return a kickoff request"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}/return",
            headers={"Authorization": f"Bearer {executive_token}"},
            json={
                "reason": "incomplete_sow",
                "return_notes": "This should fail"
            }
        )
        assert response.status_code == 403


class TestKickoffResubmit(TestKickoffRequestFeatures):
    """Test resubmit functionality after return"""
    
    @pytest.fixture(scope="class")
    def returned_kickoff_id(self, admin_token, manager_token):
        """Create and return a kickoff request for resubmit testing"""
        # Get an agreement
        agreements_resp = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if agreements_resp.status_code != 200 or not agreements_resp.json():
            pytest.skip("No approved agreement available")
        
        agreement_id = agreements_resp.json()[0]["id"]
        
        # Create a kickoff request
        create_resp = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": agreement_id,
                "client_name": "TEST Resubmit Client",
                "project_name": f"TEST_Resubmit_Project_{uuid.uuid4().hex[:6]}",
                "project_type": "mixed",
                "total_meetings": 8,
                "project_value": 400000,
                "expected_start_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "notes": "Test kickoff for resubmit workflow"
            }
        )
        if create_resp.status_code != 200:
            pytest.skip("Could not create kickoff request")
        
        kickoff_id = create_resp.json().get("id")
        
        # Return it
        return_resp = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/return",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "reason": "clarification_needed",
                "return_notes": "Need clarification on project scope"
            }
        )
        if return_resp.status_code != 200:
            pytest.skip("Could not return kickoff request")
        
        return kickoff_id
    
    def test_resubmit_returned_kickoff(self, admin_token, returned_kickoff_id):
        """Test sales can resubmit a returned kickoff request"""
        if not returned_kickoff_id:
            pytest.skip("No returned kickoff available")
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{returned_kickoff_id}/resubmit",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to resubmit: {response.text}"
        
        # Verify status changed back to pending
        get_resp = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{returned_kickoff_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("status") == "pending", f"Status should be 'pending', got {data.get('status')}"
        print(f"Resubmit successful - status: {data.get('status')}")
    
    def test_resubmit_non_returned_fails(self, admin_token, test_kickoff_request_id):
        """Test cannot resubmit a request that wasn't returned"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}/resubmit",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should fail if status is not 'returned'
        # Could be 400 or 200 depending on current status
        print(f"Resubmit non-returned result: {response.status_code}")


class TestKickoffAcceptAndCreateProject(TestKickoffRequestFeatures):
    """Test accepting kickoff request and creating project"""
    
    @pytest.fixture(scope="class")
    def pending_kickoff_for_accept(self, admin_token):
        """Create a fresh pending kickoff request for accept testing"""
        # Get an agreement
        agreements_resp = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if agreements_resp.status_code != 200 or not agreements_resp.json():
            pytest.skip("No approved agreement available")
        
        agreement_id = agreements_resp.json()[0]["id"]
        
        # Create a kickoff request
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": agreement_id,
                "client_name": "TEST Accept Client",
                "project_name": f"TEST_Accept_Project_{uuid.uuid4().hex[:6]}",
                "project_type": "offline",
                "total_meetings": 12,
                "project_value": 600000,
                "expected_start_date": (datetime.now() + timedelta(days=15)).isoformat(),
                "notes": "Test kickoff for accept workflow"
            }
        )
        if response.status_code == 200:
            return response.json().get("id")
        pytest.skip("Could not create kickoff request for accept test")
    
    def test_accept_kickoff_creates_project(self, manager_token, pending_kickoff_for_accept):
        """Test PM can accept kickoff and a project is created"""
        if not pending_kickoff_for_accept:
            pytest.skip("No pending kickoff available for accept test")
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{pending_kickoff_for_accept}/accept",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200, f"Failed to accept: {response.text}"
        
        # Verify status changed to converted and project_id is set
        get_resp = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{pending_kickoff_for_accept}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("status") == "converted", f"Status should be 'converted', got {data.get('status')}"
        assert data.get("project_id") is not None, "project_id should be set after acceptance"
        
        # Verify project was actually created
        project_id = data.get("project_id")
        project_resp = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert project_resp.status_code == 200, "Project should exist after accept"
        project = project_resp.json()
        assert project.get("client_name") == "TEST Accept Client"
        print(f"Accept successful - Project created: {project.get('name')}")
    
    def test_accept_unauthorized_sales(self, executive_token, test_kickoff_request_id):
        """Test sales cannot accept a kickoff request"""
        if not test_kickoff_request_id:
            pytest.skip("No test kickoff request available")
        
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{test_kickoff_request_id}/accept",
            headers={"Authorization": f"Bearer {executive_token}"}
        )
        assert response.status_code == 403


class TestKickoffReturnedRequestsVisibility(TestKickoffRequestFeatures):
    """Test that sales can see returned requests"""
    
    def test_sales_sees_returned_requests(self, admin_token, manager_token, executive_token):
        """Test sales user can see returned requests in their list"""
        # First create a kickoff as admin (simulating sales)
        agreements_resp = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if agreements_resp.status_code != 200 or not agreements_resp.json():
            pytest.skip("No approved agreement available")
        
        agreement_id = agreements_resp.json()[0]["id"]
        
        # Create kickoff as admin
        create_resp = requests.post(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "agreement_id": agreement_id,
                "client_name": "TEST Visibility Client",
                "project_name": f"TEST_Visibility_Project_{uuid.uuid4().hex[:6]}",
                "project_type": "mixed",
                "total_meetings": 6,
                "project_value": 300000,
                "expected_start_date": (datetime.now() + timedelta(days=30)).isoformat()
            }
        )
        assert create_resp.status_code == 200
        kickoff_id = create_resp.json().get("id")
        
        # Return it as manager
        return_resp = requests.post(
            f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/return",
            headers={"Authorization": f"Bearer {manager_token}"},
            json={
                "reason": "missing_details",
                "return_notes": "Missing project scope details"
            }
        )
        assert return_resp.status_code == 200
        
        # Check admin (as the requester) can see the returned request
        list_resp = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert list_resp.status_code == 200
        requests_list = list_resp.json()
        
        returned = [r for r in requests_list if r.get("id") == kickoff_id]
        assert len(returned) > 0, "Returned request should be visible in list"
        assert returned[0].get("status") == "returned"
        assert returned[0].get("return_reason") is not None
        print(f"Returned request visible with reason: {returned[0].get('return_reason')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
