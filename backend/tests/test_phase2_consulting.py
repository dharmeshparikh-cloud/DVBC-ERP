"""
Phase 2 Consulting Flow Testing - SOW Change Requests and Payment Reminders
Tests for:
- POST /api/sow-change-requests - Create SOW change request
- GET /api/sow-change-requests - Get user's change requests
- GET /api/sow-change-requests/pending - Get pending requests (PM only)
- POST /api/sow-change-requests/{id}/approve - Approve change request
- POST /api/sow-change-requests/{id}/reject - Reject change request
- GET /api/payment-reminders - Get payment reminders for all projects
- GET /api/payment-reminders/project/{id} - Get payment schedule for project
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "admin123"}
MANAGER_CREDS = {"email": "manager@company.com", "password": "manager123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def manager_token():
    """Get manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=MANAGER_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Manager login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin token"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def manager_headers(manager_token):
    """Headers with manager token"""
    return {
        "Authorization": f"Bearer {manager_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def existing_sow(admin_headers):
    """Get or create an existing SOW for testing"""
    # First, try to get an existing SOW
    response = requests.get(f"{BASE_URL}/api/enhanced-sow/list", headers=admin_headers)
    if response.status_code == 200:
        sows = response.json()
        if sows:
            return sows[0]
    
    # If no SOW exists, we'll use a placeholder ID and tests may fail gracefully
    return {"id": str(uuid.uuid4()), "name": "TEST_PLACEHOLDER_SOW"}


@pytest.fixture(scope="module")
def existing_project(admin_headers):
    """Get or create an existing project for testing"""
    response = requests.get(f"{BASE_URL}/api/projects", headers=admin_headers)
    if response.status_code == 200:
        projects = response.json()
        if projects:
            return projects[0]
    
    # Create a test project if none exists
    project_data = {
        "name": "TEST_Phase2_Project",
        "client_name": "TEST_Client",
        "project_type": "mixed",
        "start_date": datetime.now(timezone.utc).isoformat()
    }
    response = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=admin_headers)
    if response.status_code == 200:
        return response.json()
    
    return {"id": str(uuid.uuid4()), "name": "TEST_PLACEHOLDER_PROJECT"}


class TestSOWChangeRequests:
    """Tests for SOW Change Requests API"""
    
    created_request_id = None
    
    def test_create_change_request_without_auth(self):
        """Test that creating change request without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/sow-change-requests", json={
            "sow_id": "test-sow-id",
            "change_type": "add_scope",
            "title": "Test Change",
            "description": "Test description",
            "proposed_changes": {}
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Create change request without auth returns 401")
    
    def test_create_change_request(self, admin_headers, existing_sow):
        """Test creating a SOW change request"""
        change_request_data = {
            "sow_id": existing_sow.get("id"),
            "change_type": "add_scope",
            "title": "TEST_Add New Consulting Scope",
            "description": "Request to add new consulting scope for Phase 2 requirements",
            "proposed_changes": {
                "new_scope": {
                    "name": "Process Optimization",
                    "description": "Additional process optimization scope"
                }
            },
            "requires_client_approval": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sow-change-requests",
            json=change_request_data,
            headers=admin_headers
        )
        
        # SOW may not exist, which is acceptable
        if response.status_code == 404:
            print(f"⚠ SOW not found (ID: {existing_sow.get('id')}) - expected when no SOWs exist")
            pytest.skip("No SOW exists for testing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should contain 'id'"
        assert data.get("status") == "pending", f"Expected status 'pending', got {data.get('status')}"
        
        TestSOWChangeRequests.created_request_id = data.get("id")
        print(f"✓ Created change request with ID: {TestSOWChangeRequests.created_request_id}")
    
    def test_get_my_change_requests(self, admin_headers):
        """Test getting user's own change requests"""
        response = requests.get(
            f"{BASE_URL}/api/sow-change-requests",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Retrieved {len(data)} change requests")
        
        # If we created a request, verify it's in the list
        if TestSOWChangeRequests.created_request_id:
            request_ids = [req.get("id") for req in data]
            assert TestSOWChangeRequests.created_request_id in request_ids, "Created request should be in the list"
            print(f"✓ Created request found in list")
    
    def test_get_pending_change_requests_as_pm(self, manager_headers):
        """Test getting pending requests as PM/Manager"""
        response = requests.get(
            f"{BASE_URL}/api/sow-change-requests/pending",
            headers=manager_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Retrieved {len(data)} pending change requests (PM view)")
    
    def test_get_pending_change_requests_as_admin(self, admin_headers):
        """Test getting pending requests as Admin"""
        response = requests.get(
            f"{BASE_URL}/api/sow-change-requests/pending",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Retrieved {len(data)} pending change requests (Admin view)")
    
    def test_approve_change_request(self, admin_headers):
        """Test approving a change request"""
        if not TestSOWChangeRequests.created_request_id:
            pytest.skip("No change request created to approve")
        
        response = requests.post(
            f"{BASE_URL}/api/sow-change-requests/{TestSOWChangeRequests.created_request_id}/approve",
            params={"approval_type": "rm", "comments": "Approved for testing"},
            headers=admin_headers
        )
        
        if response.status_code == 404:
            print("⚠ Change request not found - may have been deleted")
            pytest.skip("Change request not found")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "message" in data, "Response should contain 'message'"
        assert data.get("status") in ["rm_approved", "pending_client", "applied"], \
            f"Unexpected status: {data.get('status')}"
        print(f"✓ Approved change request, status: {data.get('status')}")
    
    def test_create_and_reject_change_request(self, admin_headers, existing_sow):
        """Test creating and rejecting a change request"""
        # First create a new change request
        change_request_data = {
            "sow_id": existing_sow.get("id"),
            "change_type": "modify_scope",
            "title": "TEST_Modify Scope for Rejection",
            "description": "This request will be rejected for testing",
            "proposed_changes": {"updates": {"name": "Modified Scope"}},
            "requires_client_approval": False
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/sow-change-requests",
            json=change_request_data,
            headers=admin_headers
        )
        
        if create_response.status_code == 404:
            pytest.skip("No SOW exists for testing rejection flow")
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        request_id = create_response.json().get("id")
        
        # Now reject it
        reject_response = requests.post(
            f"{BASE_URL}/api/sow-change-requests/{request_id}/reject",
            params={"rejection_reason": "Test rejection - not a real rejection"},
            headers=admin_headers
        )
        
        assert reject_response.status_code == 200, f"Reject failed: {reject_response.text}"
        data = reject_response.json()
        
        assert data.get("status") == "rejected", f"Expected 'rejected', got {data.get('status')}"
        print(f"✓ Successfully rejected change request {request_id}")
    
    def test_reject_nonexistent_request(self, admin_headers):
        """Test rejecting a non-existent change request"""
        fake_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/sow-change-requests/{fake_id}/reject",
            params={"rejection_reason": "Test rejection"},
            headers=admin_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Rejecting non-existent request returns 404")


class TestPaymentReminders:
    """Tests for Payment Reminders API"""
    
    def test_get_payment_reminders_without_auth(self):
        """Test that getting payment reminders without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/payment-reminders")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Payment reminders without auth returns 401")
    
    def test_get_payment_reminders(self, admin_headers):
        """Test getting payment reminders"""
        response = requests.get(
            f"{BASE_URL}/api/payment-reminders",
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Retrieved payment reminders for {len(data)} projects")
        
        # Validate structure if data exists
        if data:
            first_reminder = data[0]
            assert "project_id" in first_reminder, "Reminder should have project_id"
            assert "project_name" in first_reminder, "Reminder should have project_name"
            assert "payment_frequency" in first_reminder, "Reminder should have payment_frequency"
            assert "upcoming_payments" in first_reminder, "Reminder should have upcoming_payments"
            
            # Validate upcoming payments structure
            if first_reminder["upcoming_payments"]:
                payment = first_reminder["upcoming_payments"][0]
                assert "due_date" in payment, "Payment should have due_date"
                assert "installment_number" in payment, "Payment should have installment_number"
                assert "days_until_due" in payment, "Payment should have days_until_due"
            
            print(f"✓ Payment reminder structure validated")
    
    def test_get_project_payment_schedule(self, admin_headers, existing_project):
        """Test getting payment schedule for a specific project"""
        project_id = existing_project.get("id")
        
        response = requests.get(
            f"{BASE_URL}/api/payment-reminders/project/{project_id}",
            headers=admin_headers
        )
        
        if response.status_code == 404:
            print(f"⚠ Project {project_id} not found")
            pytest.skip("Project not found for payment schedule testing")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "project_id" in data, "Response should have project_id"
        assert "project_name" in data, "Response should have project_name"
        assert "payment_frequency" in data, "Response should have payment_frequency"
        assert "schedule" in data, "Response should have schedule"
        
        print(f"✓ Retrieved payment schedule for project: {data.get('project_name')}")
        print(f"  - Payment frequency: {data.get('payment_frequency')}")
        print(f"  - Schedule items: {len(data.get('schedule', []))}")
    
    def test_get_nonexistent_project_payment_schedule(self, admin_headers):
        """Test getting payment schedule for a non-existent project"""
        fake_id = str(uuid.uuid4())
        response = requests.get(
            f"{BASE_URL}/api/payment-reminders/project/{fake_id}",
            headers=admin_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Non-existent project payment schedule returns 404")


class TestSOWChangeRequestFiltering:
    """Tests for SOW Change Request filtering"""
    
    def test_filter_by_status(self, admin_headers):
        """Test filtering change requests by status"""
        # Filter by 'pending' status
        response = requests.get(
            f"{BASE_URL}/api/sow-change-requests",
            params={"status": "pending"},
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # All returned requests should have 'pending' status
        for req in data:
            assert req.get("status") == "pending", f"Found non-pending request: {req.get('status')}"
        
        print(f"✓ Filtered by status 'pending': {len(data)} results")
    
    def test_filter_by_sow_id(self, admin_headers, existing_sow):
        """Test filtering change requests by SOW ID"""
        sow_id = existing_sow.get("id")
        
        response = requests.get(
            f"{BASE_URL}/api/sow-change-requests",
            params={"sow_id": sow_id},
            headers=admin_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # All returned requests should have the specified SOW ID
        for req in data:
            assert req.get("sow_id") == sow_id, f"Found request with different SOW ID: {req.get('sow_id')}"
        
        print(f"✓ Filtered by SOW ID: {len(data)} results")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
