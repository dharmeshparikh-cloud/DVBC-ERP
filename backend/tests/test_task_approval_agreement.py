"""
Test Suite for Task Approval Workflow and Agreement E-Signature Features

Tests the following features:
1. Task management in SOW scopes - Add task to scope
2. Task approval workflow - Request approval, manager/client approve  
3. Agreement page viewing and API
4. E-signature API endpoint
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
MANAGER_EMAIL = "manager@company.com"
MANAGER_PASSWORD = "manager123"

# Test IDs from context
PRICING_PLAN_ID = "ede84071-204d-4a36-bc3b-8b1d5acf1635"
AGREEMENT_ID = "f6ae033a-a004-4970-88c1-5ab906dc0988"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def manager_token():
    """Get manager auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Manager authentication failed: {response.status_code}")


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ============== SOW and Task Management Tests ==============

class TestSOWTaskManagement:
    """Test task creation and management under SOW scopes"""
    
    def test_get_enhanced_sow_by_pricing_plan(self, api_client, admin_token):
        """Test fetching enhanced SOW by pricing plan ID"""
        response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        print(f"GET SOW by pricing plan: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "SOW should have an id"
        assert "scopes" in data, "SOW should have scopes array"
        assert len(data.get("scopes", [])) > 0, "SOW should have at least one scope"
        
        print(f"SOW ID: {data.get('id')}, Scopes count: {len(data.get('scopes', []))}")
        return data
    
    def test_create_task_under_scope(self, api_client, admin_token):
        """Test creating a task under a specific scope"""
        # First get SOW
        sow_response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert sow_response.status_code == 200
        
        sow = sow_response.json()
        sow_id = sow.get("id")
        scope_id = sow.get("scopes", [{}])[0].get("id")
        
        assert sow_id, "SOW ID required"
        assert scope_id, "Scope ID required"
        
        # Create task
        task_data = {
            "name": f"TEST_Task_{uuid.uuid4().hex[:8]}",
            "description": "Test task created by automated test",
            "priority": "high",
            "due_date": "2026-03-01",
            "notes": "Automated test task"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks",
            json=task_data,
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        print(f"Create task: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "task" in data, "Response should include task object"
        assert data.get("task", {}).get("name") == task_data["name"], "Task name should match"
        assert data.get("task", {}).get("status") == "pending", "New task should be pending"
        
        return data.get("task")
    
    def test_update_task_status(self, api_client, admin_token):
        """Test updating task status to completed"""
        # Get SOW and create a task
        sow_response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        sow = sow_response.json()
        sow_id = sow.get("id")
        scope_id = sow.get("scopes", [{}])[0].get("id")
        
        # Create task for testing update
        create_response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks",
            json={"name": f"TEST_UpdateTask_{uuid.uuid4().hex[:8]}", "description": "Task to update"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        task = create_response.json().get("task", {})
        task_id = task.get("id")
        
        assert task_id, "Task ID required for update"
        
        # Update status
        update_response = api_client.patch(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}",
            json={"status": "completed"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        print(f"Update task status: {update_response.status_code}")
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}"
        
        data = update_response.json()
        assert data.get("task", {}).get("status") == "completed", "Task status should be completed"


# ============== Task Approval Workflow Tests ==============

class TestTaskApprovalWorkflow:
    """Test parallel approval workflow for tasks"""
    
    def test_request_task_approval(self, api_client, admin_token):
        """Test requesting approval for a task"""
        # Get SOW
        sow_response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        sow = sow_response.json()
        sow_id = sow.get("id")
        scope_id = sow.get("scopes", [{}])[0].get("id")
        
        # Create task
        create_response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks",
            json={"name": f"TEST_ApprovalTask_{uuid.uuid4().hex[:8]}", "description": "Task for approval test"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        task = create_response.json().get("task", {})
        task_id = task.get("id")
        
        # Request approval
        approval_request = {
            "manager_id": "manager-test-id",
            "manager_name": "Test Manager",
            "client_name": "Test Client",
            "client_email": "client@test.com",
            "notes": "Please approve this task"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/request-approval",
            json=approval_request,
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        print(f"Request approval: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Should have message"
        assert data.get("approval_status") == "pending", "Approval should be pending"
        
        return {"sow_id": sow_id, "scope_id": scope_id, "task_id": task_id}
    
    def test_manager_approve_task(self, api_client, admin_token):
        """Test manager approving a task"""
        # Get SOW and create task with approval request
        sow_response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        sow = sow_response.json()
        sow_id = sow.get("id")
        scope_id = sow.get("scopes", [{}])[0].get("id")
        
        # Create task
        create_response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks",
            json={"name": f"TEST_ManagerApproval_{uuid.uuid4().hex[:8]}", "description": "Task for manager approval"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        task_id = create_response.json().get("task", {}).get("id")
        
        # Request approval first
        api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/request-approval",
            json={"manager_id": "mgr-id", "manager_name": "Manager", "client_email": "client@test.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        # Manager approval
        approval_data = {
            "approval_type": "manager",
            "approved": True,
            "notes": "Approved by manager"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve",
            json=approval_data,
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "manager-id", "current_user_name": "Manager", "current_user_role": "manager"}
        )
        
        print(f"Manager approve: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("manager_status") == "approved", "Manager status should be approved"
        assert data.get("approval_status") == "manager_approved", "Overall status should be manager_approved"
    
    def test_client_approve_task_after_manager(self, api_client, admin_token):
        """Test client approving task after manager - should result in fully_approved"""
        # Get SOW
        sow_response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        sow = sow_response.json()
        sow_id = sow.get("id")
        scope_id = sow.get("scopes", [{}])[0].get("id")
        
        # Create task
        create_response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks",
            json={"name": f"TEST_FullApproval_{uuid.uuid4().hex[:8]}", "description": "Task for full approval"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        task_id = create_response.json().get("task", {}).get("id")
        
        # Request approval
        api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/request-approval",
            json={"manager_id": "mgr-id", "manager_name": "Manager", "client_email": "client@test.com"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_name": "Test User"}
        )
        
        # Manager approval
        api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve",
            json={"approval_type": "manager", "approved": True, "notes": "Manager approved"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "manager-id", "current_user_name": "Manager", "current_user_role": "manager"}
        )
        
        # Client approval
        response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve",
            json={"approval_type": "client", "approved": True, "notes": "Client approved"},
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "client-id", "current_user_name": "Client", "current_user_role": "client"}
        )
        
        print(f"Client approve (after manager): {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("client_status") == "approved", "Client status should be approved"
        assert data.get("manager_status") == "approved", "Manager status should still be approved"
        assert data.get("approval_status") == "fully_approved", "Overall should be fully_approved"


# ============== Agreement Tests ==============

class TestAgreementAPI:
    """Test agreement viewing and e-signature"""
    
    def test_get_agreement_full_details(self, api_client, admin_token):
        """Test fetching full agreement details with related data"""
        response = api_client.get(
            f"{BASE_URL}/api/agreements/{AGREEMENT_ID}/full",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Get agreement full: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        # Agreement may not exist, so we check for both outcomes
        if response.status_code == 404:
            print("Agreement not found - testing with a new agreement")
            pytest.skip("Agreement ID from context does not exist")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "agreement" in data, "Should have agreement object"
        
        return data
    
    def test_list_agreements(self, api_client, admin_token):
        """Test listing all agreements"""
        response = api_client.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"List agreements: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list of agreements"
        print(f"Total agreements: {len(data)}")
        
        return data
    
    def test_sign_agreement_endpoint(self, api_client, admin_token):
        """Test agreement e-signature endpoint"""
        # First check if agreement exists
        check_response = api_client.get(
            f"{BASE_URL}/api/agreements/{AGREEMENT_ID}/full",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if check_response.status_code == 404:
            # Create a new agreement for testing
            agreements = api_client.get(
                f"{BASE_URL}/api/agreements",
                headers={"Authorization": f"Bearer {admin_token}"}
            ).json()
            
            # Find an unsigned agreement
            unsigned_agreement = None
            for agr in agreements:
                agr_data = agr.get("agreement", agr)
                if agr_data.get("status") != "signed":
                    unsigned_agreement = agr_data
                    break
            
            if not unsigned_agreement:
                pytest.skip("No unsigned agreements available for e-signature test")
            
            test_agreement_id = unsigned_agreement.get("id")
        else:
            data = check_response.json()
            agreement = data.get("agreement", {})
            if agreement.get("status") == "signed":
                pytest.skip("Agreement already signed, cannot test signing")
            test_agreement_id = AGREEMENT_ID
        
        # Sign the agreement
        signature_data = {
            "signer_name": "Test Signer",
            "signer_designation": "CEO",
            "signer_email": "testsigner@test.com",
            "signature_date": "2026-01-15",
            "signature_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="  # Minimal valid PNG
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/agreements/{test_agreement_id}/sign",
            json=signature_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Sign agreement: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        # Either success or already signed
        if response.status_code == 400 and "already signed" in response.text.lower():
            print("Agreement already signed - expected behavior")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "signed_at" in data, "Should have signed_at timestamp"


# ============== Pending Approvals Test ==============

class TestPendingApprovals:
    """Test fetching pending task approvals"""
    
    def test_get_pending_approvals(self, api_client, admin_token):
        """Test fetching pending task approvals for a SOW"""
        # Get SOW
        sow_response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/by-pricing-plan/{PRICING_PLAN_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        sow_id = sow_response.json().get("id")
        
        response = api_client.get(
            f"{BASE_URL}/api/enhanced-sow/{sow_id}/tasks/pending-approvals",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"current_user_id": "test-user", "current_user_role": "admin"}
        )
        
        print(f"Get pending approvals: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Should return a list of pending approvals"
        print(f"Pending approvals count: {len(data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
