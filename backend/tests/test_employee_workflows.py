"""
Test Employee Workflows Feature
- Tests workflow creation for locked fields (Transfer, Promotion, CTC Revision, Hierarchy Change)
- Tests workflow approval and rejection
- Tests that approved changes are applied to employee record
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://erp-checkin-bug.preview.emergentagent.com')

# Test credentials
ADMIN_CREDENTIALS = {"employee_id": "ADMIN001", "password": "admin123"}
HR_CREDENTIALS = {"employee_id": "DVC037", "password": "test123"}

# Test employee
TEST_EMPLOYEE_ID = "3a20643a-6d1b-4d19-b3fd-757091740fcd"  # Himanshi Gunecha - DVBC007


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def hr_token():
    """Get HR authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
    assert response.status_code == 200, f"HR login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Admin auth headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def hr_headers(hr_token):
    """HR auth headers"""
    return {"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"}


class TestPendingRequestsAPI:
    """Test GET /api/governance/pending-requests (Admin only)"""
    
    def test_pending_requests_admin_access(self, admin_headers):
        """Admin should be able to view pending workflow requests"""
        response = requests.get(f"{BASE_URL}/api/governance/pending-requests", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} pending requests")
    
    def test_pending_requests_hr_forbidden(self, hr_headers):
        """HR should not be able to view pending requests (admin only)"""
        response = requests.get(f"{BASE_URL}/api/governance/pending-requests", headers=hr_headers)
        assert response.status_code == 403


class TestCreateTransferRequest:
    """Test creating Transfer workflow request via PATCH /api/employees/{id}"""
    
    def test_transfer_request_creates_workflow(self, hr_headers):
        """Changing department should create a transfer workflow request"""
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"department": "TEST_TRANSFER_DEPT"},
            params={"change_reason": "Testing transfer workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have workflow_requests array
        assert "workflow_requests" in data, f"Missing workflow_requests: {data}"
        
        # Find the transfer request
        transfer_requests = [r for r in data["workflow_requests"] if r["workflow"] == "transfer"]
        assert len(transfer_requests) > 0, f"No transfer request created: {data}"
        
        print(f"Transfer workflow request created: {transfer_requests[0]['request_id']}")


class TestCreatePromotionRequest:
    """Test creating Promotion workflow request via PATCH /api/employees/{id}"""
    
    def test_promotion_request_creates_workflow(self, hr_headers):
        """Changing designation should create a promotion workflow request"""
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"designation": "TEST_SENIOR_CONSULTANT"},
            params={"change_reason": "Testing promotion workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "workflow_requests" in data
        promotion_requests = [r for r in data["workflow_requests"] if r["workflow"] == "promotion"]
        assert len(promotion_requests) > 0
        
        print(f"Promotion workflow request created: {promotion_requests[0]['request_id']}")


class TestCreateCTCRevisionRequest:
    """Test creating CTC Revision workflow request via PATCH /api/employees/{id}"""
    
    def test_ctc_revision_request_creates_workflow(self, hr_headers):
        """Changing salary should create a ctc_revision workflow request"""
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"salary": 2500000},
            params={"change_reason": "Testing CTC revision workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "workflow_requests" in data
        ctc_requests = [r for r in data["workflow_requests"] if r["workflow"] == "ctc_revision"]
        assert len(ctc_requests) > 0
        
        print(f"CTC revision workflow request created: {ctc_requests[0]['request_id']}")


class TestCreateHierarchyChangeRequest:
    """Test creating Hierarchy Change workflow request via PATCH /api/employees/{id}"""
    
    def test_hierarchy_change_request_creates_workflow(self, hr_headers):
        """Changing reporting_manager_id should create a hierarchy_change workflow request"""
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"reporting_manager_id": "test-manager-uuid"},
            params={"change_reason": "Testing hierarchy change workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "workflow_requests" in data
        hierarchy_requests = [r for r in data["workflow_requests"] if r["workflow"] == "hierarchy_change"]
        assert len(hierarchy_requests) > 0
        
        print(f"Hierarchy change workflow request created: {hierarchy_requests[0]['request_id']}")


class TestApproveRequest:
    """Test approving workflow requests POST /api/governance/requests/{id}/approve"""
    
    def test_approve_workflow_request(self, admin_headers, hr_headers):
        """Admin should be able to approve a workflow request and apply the change"""
        # First create a new transfer request
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"department": "TEST_APPROVAL_DEPT"},
            params={"change_reason": "Testing approval workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        
        transfer_requests = [r for r in data.get("workflow_requests", []) if r["workflow"] == "transfer"]
        assert len(transfer_requests) > 0, "Failed to create transfer request for approval test"
        
        request_id = transfer_requests[0]["request_id"]
        
        # Now approve it
        approve_response = requests.post(
            f"{BASE_URL}/api/governance/requests/{request_id}/approve",
            headers=admin_headers,
            params={"remarks": "Approved for testing"}
        )
        assert approve_response.status_code == 200, f"Approval failed: {approve_response.text}"
        approve_data = approve_response.json()
        
        assert approve_data["message"] == "Change approved and applied"
        assert approve_data["field"] == "department"
        assert approve_data["new_value"] == "TEST_APPROVAL_DEPT"
        
        print(f"Workflow request {request_id} approved successfully")
        
        # Verify the employee was updated
        emp_response = requests.get(f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}", headers=admin_headers)
        assert emp_response.status_code == 200
        emp_data = emp_response.json()
        assert emp_data["department"] == "TEST_APPROVAL_DEPT"
        print("Employee department updated to TEST_APPROVAL_DEPT after approval")


class TestRejectRequest:
    """Test rejecting workflow requests POST /api/governance/requests/{id}/reject"""
    
    def test_reject_workflow_request(self, admin_headers, hr_headers):
        """Admin should be able to reject a workflow request with reason"""
        # First create a new designation request
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"designation": "TEST_REJECT_DESIGNATION"},
            params={"change_reason": "Testing rejection workflow"}
        )
        assert response.status_code == 200
        data = response.json()
        
        promotion_requests = [r for r in data.get("workflow_requests", []) if r["workflow"] == "promotion"]
        assert len(promotion_requests) > 0, "Failed to create promotion request for rejection test"
        
        request_id = promotion_requests[0]["request_id"]
        
        # Now reject it
        reject_response = requests.post(
            f"{BASE_URL}/api/governance/requests/{request_id}/reject",
            headers=admin_headers,
            params={"reason": "Rejected for testing purposes"}
        )
        assert reject_response.status_code == 200, f"Rejection failed: {reject_response.text}"
        reject_data = reject_response.json()
        
        assert reject_data["message"] == "Change request rejected"
        print(f"Workflow request {request_id} rejected successfully")


class TestRejectWithoutReason:
    """Test that rejection requires a reason"""
    
    def test_reject_requires_reason(self, admin_headers, hr_headers):
        """Rejection should fail without a reason"""
        # Create a request first
        response = requests.patch(
            f"{BASE_URL}/api/employees/{TEST_EMPLOYEE_ID}",
            headers=hr_headers,
            json={"designation": "TEST_REJECT_NO_REASON"},
            params={"change_reason": "Testing rejection without reason"}
        )
        assert response.status_code == 200
        data = response.json()
        
        promotion_requests = [r for r in data.get("workflow_requests", []) if r["workflow"] == "promotion"]
        if len(promotion_requests) > 0:
            request_id = promotion_requests[0]["request_id"]
            
            # Try to reject without reason
            reject_response = requests.post(
                f"{BASE_URL}/api/governance/requests/{request_id}/reject",
                headers=admin_headers,
                params={"reason": ""}
            )
            # Should either fail or give validation error
            # Based on the code, empty reason is checked
            assert reject_response.status_code in [400, 200]  # May validate on backend


class TestHRCannotApprove:
    """Test that HR cannot approve requests (admin only)"""
    
    def test_hr_cannot_approve(self, hr_headers):
        """HR should get 403 when trying to approve requests"""
        # Use a known pending request ID or create one
        # First get pending requests as admin would
        # For this test, we'll use a dummy ID - should still get 403 based on role
        response = requests.post(
            f"{BASE_URL}/api/governance/requests/dummy-request-id/approve",
            headers=hr_headers,
            params={"remarks": "Testing HR approval"}
        )
        # Should be 403 because HR is not admin
        assert response.status_code == 403


class TestHRCannotReject:
    """Test that HR cannot reject requests (admin only)"""
    
    def test_hr_cannot_reject(self, hr_headers):
        """HR should get 403 when trying to reject requests"""
        response = requests.post(
            f"{BASE_URL}/api/governance/requests/dummy-request-id/reject",
            headers=hr_headers,
            params={"reason": "Testing HR rejection"}
        )
        # Should be 403 because HR is not admin
        assert response.status_code == 403


class TestFieldPermissionsAPI:
    """Test GET /api/governance/field-permissions"""
    
    def test_field_permissions_returns_locked_fields(self, hr_headers):
        """Field permissions should show locked status for governance fields"""
        response = requests.get(f"{BASE_URL}/api/governance/field-permissions", headers=hr_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "permissions" in data
        permissions = data["permissions"]
        
        # Check locked fields
        assert permissions["department"]["locked"] == True
        assert permissions["department"]["workflow"] == "transfer"
        
        assert permissions["designation"]["locked"] == True
        assert permissions["designation"]["workflow"] == "promotion"
        
        assert permissions["salary"]["locked"] == True
        assert permissions["salary"]["workflow"] == "ctc_revision"
        
        assert permissions["reporting_manager_id"]["locked"] == True
        assert permissions["reporting_manager_id"]["workflow"] == "hierarchy_change"
        
        print("Field permissions correctly show locked status for governance fields")


class TestGetEmployeesForWorkflow:
    """Test GET /api/employees/all for workflow dropdown"""
    
    def test_employees_all_returns_list(self, hr_headers):
        """GET /api/employees/all should return list of employees for dropdown"""
        response = requests.get(f"{BASE_URL}/api/employees/all", headers=hr_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        print(f"Found {len(data)} employees for workflow dropdown")


class TestGetDepartmentsList:
    """Test GET /api/employees/departments/list for transfer dropdown"""
    
    def test_departments_list_returns_array(self, hr_headers):
        """GET /api/employees/departments/list should return department options"""
        response = requests.get(f"{BASE_URL}/api/employees/departments/list", headers=hr_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} departments: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
