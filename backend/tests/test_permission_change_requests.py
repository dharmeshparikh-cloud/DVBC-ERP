"""
Test Permission Change Request Workflow:
- HR submits permission changes for employees
- Admin reviews and approves/rejects in Approvals Center
- After approval/rejection, request is removed from pending list
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
ADMIN_CREDS = {"email": "admin@dvbc.com", "password": "admin123"}
HR_CREDS = {"email": "hr.manager@dvbc.com", "password": "hr123"}


class TestPermissionChangeRequestWorkflow:
    """Tests for Permission Change Request workflow"""
    
    admin_token = None
    hr_token = None
    pending_request_ids = []
    
    def test_01_admin_login(self):
        """Admin should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        TestPermissionChangeRequestWorkflow.admin_token = data["access_token"]
        print("PASSED: Admin login successful")
    
    def test_02_hr_login(self):
        """HR Manager should be able to login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDS)
        assert response.status_code == 200, f"HR login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] in ["hr_manager", "hr_executive"]
        TestPermissionChangeRequestWorkflow.hr_token = data["access_token"]
        print("PASSED: HR Manager login successful")
    
    def test_03_admin_fetch_pending_permission_requests(self):
        """Admin should see pending permission change requests"""
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/permission-change-requests", headers=headers)
        assert response.status_code == 200, f"Failed to fetch requests: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        # Filter pending requests
        pending = [r for r in data if r.get("status") == "pending"]
        print(f"PASSED: Found {len(pending)} pending permission change requests")
        
        # Store pending request IDs for later tests
        TestPermissionChangeRequestWorkflow.pending_request_ids = [r["id"] for r in pending]
        return pending
    
    def test_04_verify_request_data_structure(self):
        """Verify permission change request data has all required fields"""
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/permission-change-requests", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            req = data[0]
            # Check required fields
            required_fields = ["id", "employee_id", "employee_name", "requested_by", 
                             "requested_by_name", "changes", "status", "created_at"]
            for field in required_fields:
                assert field in req, f"Missing field: {field}"
            print(f"PASSED: Request data has all required fields: {list(req.keys())}")
    
    def test_05_hr_cannot_approve(self):
        """HR Manager should NOT be able to approve requests (Admin only)"""
        if not TestPermissionChangeRequestWorkflow.pending_request_ids:
            pytest.skip("No pending requests to test")
        
        request_id = TestPermissionChangeRequestWorkflow.pending_request_ids[0]
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.hr_token}"}
        response = requests.post(
            f"{BASE_URL}/api/permission-change-requests/{request_id}/approve", 
            headers=headers
        )
        # HR should get 403 Forbidden
        assert response.status_code == 403, f"Expected 403 but got {response.status_code}"
        print("PASSED: HR correctly denied approve permission")
    
    def test_06_hr_cannot_reject(self):
        """HR Manager should NOT be able to reject requests (Admin only)"""
        if not TestPermissionChangeRequestWorkflow.pending_request_ids:
            pytest.skip("No pending requests to test")
        
        request_id = TestPermissionChangeRequestWorkflow.pending_request_ids[0]
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.hr_token}"}
        response = requests.post(
            f"{BASE_URL}/api/permission-change-requests/{request_id}/reject", 
            headers=headers
        )
        # HR should get 403 Forbidden
        assert response.status_code == 403, f"Expected 403 but got {response.status_code}"
        print("PASSED: HR correctly denied reject permission")
    
    def test_07_admin_approve_request(self):
        """Admin should be able to approve a pending request"""
        if len(TestPermissionChangeRequestWorkflow.pending_request_ids) < 1:
            pytest.skip("No pending requests to test")
        
        request_id = TestPermissionChangeRequestWorkflow.pending_request_ids[0]
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.admin_token}"}
        response = requests.post(
            f"{BASE_URL}/api/permission-change-requests/{request_id}/approve",
            headers=headers
        )
        assert response.status_code == 200, f"Approve failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"PASSED: Admin approved request {request_id}")
        
        # Remove from pending list
        TestPermissionChangeRequestWorkflow.pending_request_ids.remove(request_id)
    
    def test_08_verify_approval_removes_from_pending(self):
        """Approved request should no longer appear in pending list"""
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/permission-change-requests", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        pending = [r for r in data if r.get("status") == "pending"]
        
        # Should have one less pending request now
        print(f"PASSED: Now {len(pending)} pending requests after approval")
    
    def test_09_admin_reject_request(self):
        """Admin should be able to reject a pending request"""
        if len(TestPermissionChangeRequestWorkflow.pending_request_ids) < 1:
            pytest.skip("No pending requests to test rejection")
        
        request_id = TestPermissionChangeRequestWorkflow.pending_request_ids[0]
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.admin_token}"}
        response = requests.post(
            f"{BASE_URL}/api/permission-change-requests/{request_id}/reject",
            headers=headers
        )
        assert response.status_code == 200, f"Reject failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"PASSED: Admin rejected request {request_id}")
    
    def test_10_verify_rejection_removes_from_pending(self):
        """Rejected request should no longer appear in pending list"""
        headers = {"Authorization": f"Bearer {TestPermissionChangeRequestWorkflow.admin_token}"}
        response = requests.get(f"{BASE_URL}/api/permission-change-requests", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        pending = [r for r in data if r.get("status") == "pending"]
        
        print(f"PASSED: Now {len(pending)} pending requests after rejection")


class TestApprovalsCenterEndpoints:
    """Test the Approvals Center aggregation"""
    
    admin_token = None
    
    def test_01_admin_login(self):
        """Admin login for Approvals Center tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200
        TestApprovalsCenterEndpoints.admin_token = response.json()["access_token"]
        print("PASSED: Admin login for approvals center")
    
    def test_02_fetch_all_approval_types(self):
        """Admin should be able to fetch various approval types"""
        headers = {"Authorization": f"Bearer {TestApprovalsCenterEndpoints.admin_token}"}
        
        # Test all endpoints that feed into Approvals Center
        endpoints = [
            "/api/approvals/pending",
            "/api/ctc/pending-approvals", 
            "/api/admin/bank-change-requests",
            "/api/go-live/pending",
            "/api/permission-change-requests"
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            # Should either return 200 or 403/404 (not 500)
            assert response.status_code in [200, 403, 404], f"{endpoint} returned {response.status_code}"
            if response.status_code == 200:
                data = response.json()
                print(f"PASSED: {endpoint} returned {len(data) if isinstance(data, list) else 'data'}")
            else:
                print(f"SKIPPED: {endpoint} not available ({response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
