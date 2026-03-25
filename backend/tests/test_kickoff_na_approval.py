"""
Test Suite for Kickoff Client Confirmation and NA Approval Flow
Tests:
1. Kickoff client confirmation endpoint with Form() data
2. Date parsing with None/null expected_start_date fallback
3. NA approval flow: Consultant sets scope to 'na_pending'
4. NA approval flow: Manager approves NA request
5. NA approval flow: Manager rejects NA request
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
CONSULTANT_CREDS = {"employee_id": "EMP004", "password": "consultant123"}

# Known test data
PROJECT_SOW_ID = "c9013677-461c-4474-bf31-3ffa71e86c5f"
PROJECT_ID = "PROJ-20260315-0001"


class TestAuth:
    """Authentication helper tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def consultant_token(self):
        """Get consultant authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CONSULTANT_CREDS)
        assert response.status_code == 200, f"Consultant login failed: {response.text}"
        return response.json().get("access_token")


class TestKickoffClientConfirmation(TestAuth):
    """Test kickoff client confirmation endpoint with Form() data"""
    
    def test_client_confirm_endpoint_exists(self):
        """Verify the client confirm endpoint exists and handles invalid tokens"""
        # Test with invalid token - should return 404 HTML
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/client-approve/invalid-token/confirm",
            data={"start_date": "2026-03-20"}
        )
        assert response.status_code == 404
        assert "Invalid" in response.text or "invalid" in response.text.lower()
        print("PASSED: Client confirm endpoint exists and handles invalid tokens")
    
    def test_client_confirm_accepts_form_data(self):
        """Verify endpoint accepts form data (not JSON)"""
        # This tests that Form() is properly used
        # With invalid token, we just verify it doesn't crash on form parsing
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/client-approve/test-token-123/confirm",
            data={"start_date": "2026-04-01"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        # Should return 404 for invalid token, not 422 for validation error
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASSED: Endpoint accepts form data without validation errors")
    
    def test_client_confirm_handles_none_start_date(self):
        """Verify endpoint handles None/null start_date gracefully"""
        # Test with no start_date - should not crash
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/client-approve/test-token-456/confirm",
            data={}  # No start_date
        )
        assert response.status_code == 404  # Invalid token, but no crash
        print("PASSED: Endpoint handles missing start_date")
    
    def test_client_confirm_handles_none_string(self):
        """Verify endpoint handles 'None' string value"""
        response = requests.post(
            f"{BASE_URL}/api/kickoff-requests/client-approve/test-token-789/confirm",
            data={"start_date": "None"}
        )
        assert response.status_code == 404  # Invalid token, but no crash
        print("PASSED: Endpoint handles 'None' string value")


class TestProjectSOWRetrieval(TestAuth):
    """Test PROJECT_SOW retrieval"""
    
    def test_get_project_sow(self, admin_token):
        """Verify PROJECT_SOW can be retrieved"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to get PROJECT_SOW: {response.text}"
        data = response.json()
        assert "project_sow" in data
        assert data["project_sow"] is not None
        assert data["project_sow"]["id"] == PROJECT_SOW_ID
        print(f"PASSED: PROJECT_SOW retrieved - ID: {PROJECT_SOW_ID}")
        return data
    
    def test_project_sow_has_scopes(self, admin_token):
        """Verify PROJECT_SOW has scopes"""
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        scopes = data["project_sow"].get("scopes", [])
        assert len(scopes) > 0, "PROJECT_SOW should have scopes"
        print(f"PASSED: PROJECT_SOW has {len(scopes)} scopes")
        return scopes


class TestNAApprovalFlow(TestAuth):
    """Test Not Applicable approval flow"""
    
    def test_consultant_can_request_na(self, consultant_token, admin_token):
        """Test consultant can set scope status to 'na_pending'"""
        # First get scopes
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        scopes = data["project_sow"].get("scopes", [])
        
        # Find a scope that's not already na_pending or not_applicable
        target_scope = None
        for scope in scopes:
            if scope.get("status") not in ["na_pending", "not_applicable"]:
                target_scope = scope
                break
        
        if not target_scope:
            pytest.skip("No suitable scope found for NA request test")
        
        scope_id = target_scope["id"]
        
        # Consultant requests NA
        response = requests.patch(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/status?status=na_pending",
            headers={"Authorization": f"Bearer {consultant_token}"}
        )
        assert response.status_code == 200, f"Failed to request NA: {response.text}"
        print(f"PASSED: Consultant can request NA for scope {scope_id}")
        return scope_id
    
    def test_manager_can_approve_na(self, admin_token):
        """Test manager can approve NA request"""
        # Get scopes to find one with na_pending status
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        scopes = data["project_sow"].get("scopes", [])
        
        # Find a scope with na_pending status
        pending_scope = None
        for scope in scopes:
            if scope.get("status") == "na_pending":
                pending_scope = scope
                break
        
        if not pending_scope:
            # Create one first
            # Find a scope that's not already not_applicable
            for scope in scopes:
                if scope.get("status") not in ["not_applicable", "na_pending"]:
                    # Set to na_pending first
                    requests.patch(
                        f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope['id']}/status?status=na_pending",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
                    pending_scope = scope
                    break
        
        if not pending_scope:
            pytest.skip("No scope available for NA approval test")
        
        scope_id = pending_scope["id"]
        
        # Manager approves NA
        response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/approve-na?approve=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to approve NA: {response.text}"
        
        # Verify scope is now not_applicable
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        updated_scope = next((s for s in data["project_sow"]["scopes"] if s["id"] == scope_id), None)
        assert updated_scope["status"] == "not_applicable", f"Expected not_applicable, got {updated_scope['status']}"
        print(f"PASSED: Manager approved NA for scope {scope_id}")
    
    def test_manager_can_reject_na(self, admin_token, consultant_token):
        """Test manager can reject NA request"""
        # Get scopes
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        scopes = data["project_sow"].get("scopes", [])
        
        # Find a scope that's not not_applicable to test rejection
        target_scope = None
        for scope in scopes:
            if scope.get("status") not in ["not_applicable", "na_pending"]:
                target_scope = scope
                break
        
        if not target_scope:
            pytest.skip("No suitable scope for NA rejection test")
        
        scope_id = target_scope["id"]
        
        # First set to na_pending
        response = requests.patch(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/status?status=na_pending",
            headers={"Authorization": f"Bearer {consultant_token}"}
        )
        assert response.status_code == 200
        
        # Manager rejects NA
        response = requests.post(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/approve-na?approve=false",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to reject NA: {response.text}"
        
        # Verify scope reverted to wip
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        updated_scope = next((s for s in data["project_sow"]["scopes"] if s["id"] == scope_id), None)
        assert updated_scope["status"] == "wip", f"Expected wip after rejection, got {updated_scope['status']}"
        print(f"PASSED: Manager rejected NA for scope {scope_id}, status reverted to wip")
    
    def test_consultant_cannot_directly_set_not_applicable(self, consultant_token, admin_token):
        """Test consultant cannot directly set scope to not_applicable"""
        # Get scopes
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        scopes = data["project_sow"].get("scopes", [])
        
        # Find a scope that's not not_applicable
        target_scope = None
        for scope in scopes:
            if scope.get("status") not in ["not_applicable"]:
                target_scope = scope
                break
        
        if not target_scope:
            pytest.skip("No suitable scope for this test")
        
        scope_id = target_scope["id"]
        
        # Consultant tries to set directly to not_applicable
        response = requests.patch(
            f"{BASE_URL}/api/project-sow-delivery/{PROJECT_SOW_ID}/scope/{scope_id}/status?status=not_applicable",
            headers={"Authorization": f"Bearer {consultant_token}"}
        )
        # Should be forbidden for consultant
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print("PASSED: Consultant cannot directly set scope to not_applicable")


class TestSOWMasterLocking(TestAuth):
    """Test SOW Master locking after kickoff"""
    
    def test_sow_master_locked_check(self, admin_token):
        """Verify SOW Master lock status can be checked"""
        # Get PROJECT_SOW to find sow_master_id
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        sow_master_id = data["project_sow"].get("sow_master_id")
        
        if not sow_master_id:
            pytest.skip("No SOW Master ID found")
        
        # Check lock status
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/governance/sow-master/{sow_master_id}/is-locked",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Failed to check lock status: {response.text}"
        data = response.json()
        assert "is_locked" in data
        print(f"PASSED: SOW Master lock status: {data['is_locked']}")


class TestFrontendRoles(TestAuth):
    """Test role-based access in frontend"""
    
    def test_manager_roles_defined(self, admin_token):
        """Verify manager roles are properly defined"""
        # This is a code review check - verify MANAGER_ROLES in frontend
        # We test by checking if admin can approve NA (admin is in MANAGER_ROLES)
        response = requests.get(
            f"{BASE_URL}/api/project-sow-delivery/project/{PROJECT_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        data = response.json()
        permissions = data.get("permissions", {})
        
        # Admin should have can_reopen permission (manager role)
        assert permissions.get("can_reopen") == True, "Admin should have can_reopen permission"
        print("PASSED: Admin has manager permissions (can_reopen)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
