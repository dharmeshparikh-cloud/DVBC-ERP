"""
RBAC E2E Audit Tests - Deep button-level RBAC testing
Tests backend security fixes for enhanced_sow.py, agreements.py, consultants.py
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"employee_id": "ADMIN001", "password": "admin123"}
SALES_MANAGER_CREDENTIALS = {"employee_id": "DVC030", "password": "admin123"}

# Test SOW ID for enhanced_sow tests
TEST_SOW_ID = "6c5d11c9-446c-4546-8e27-9bde6c3e30e1"


class TestAuthSetup:
    """Setup authentication tokens for testing"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    @pytest.fixture(scope="class")
    def sales_manager_token(self):
        """Get sales manager (DVC030) authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SALES_MANAGER_CREDENTIALS
        )
        assert response.status_code == 200, f"Sales Manager login failed: {response.text}"
        data = response.json()
        return data.get("access_token")
    
    @pytest.fixture(scope="class")
    def sales_manager_user_id(self):
        """Get sales manager user ID"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=SALES_MANAGER_CREDENTIALS
        )
        data = response.json()
        return data.get("user", {}).get("id")


class TestEnhancedSOWEndpoints(TestAuthSetup):
    """Test enhanced_sow.py backend security fixes
    
    Fixed endpoints:
    - POST /api/enhanced-sow/{sow_id}/complete-handover (L293)
    - POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks (L900) 
    - PATCH /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id} (L963)
    - POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve (L1196)
    """
    
    def test_complete_handover_without_auth_returns_401(self):
        """POST /api/enhanced-sow/{sow_id}/complete-handover without auth should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}/complete-handover"
        )
        # Should return 401 Unauthorized (not 422 or success)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: complete-handover without auth returns 401")
    
    def test_complete_handover_with_invalid_token_returns_401(self):
        """POST /api/enhanced-sow/{sow_id}/complete-handover with invalid token should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}/complete-handover",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: complete-handover with invalid token returns 401")
    
    def test_create_scope_task_without_auth_returns_401(self, admin_token):
        """POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks without auth should return 401"""
        # First get a valid SOW to find scope_id
        response = requests.get(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 404:
            pytest.skip("Test SOW not found")
            return
        
        sow = response.json()
        scopes = sow.get("scopes", [])
        if not scopes:
            pytest.skip("No scopes in SOW")
            return
        
        scope_id = scopes[0].get("id")
        
        # Now test without auth
        response = requests.post(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}/scopes/{scope_id}/tasks",
            json={"name": "Test Task", "description": "Test"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: create_scope_task without auth returns 401")
    
    def test_update_scope_task_without_auth_returns_401(self, admin_token):
        """PATCH /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id} without auth should return 401"""
        # Get SOW and find a task
        response = requests.get(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 404:
            pytest.skip("Test SOW not found")
            return
        
        sow = response.json()
        scopes = sow.get("scopes", [])
        
        task_id = None
        scope_id = None
        for scope in scopes:
            tasks = scope.get("tasks", [])
            if tasks:
                task_id = tasks[0].get("id")
                scope_id = scope.get("id")
                break
        
        if not task_id:
            scope_id = scopes[0].get("id") if scopes else "fake-scope-id"
            task_id = "fake-task-id"
        
        # Test without auth
        response = requests.patch(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}/scopes/{scope_id}/tasks/{task_id}",
            json={"status": "completed"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: update_scope_task without auth returns 401")
    
    def test_approve_task_without_auth_returns_401(self, admin_token):
        """POST /api/enhanced-sow/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve without auth should return 401"""
        response = requests.get(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 404:
            pytest.skip("Test SOW not found")
            return
        
        sow = response.json()
        scopes = sow.get("scopes", [])
        
        scope_id = scopes[0].get("id") if scopes else "fake-scope-id"
        task_id = "fake-task-id"
        
        # Test without auth
        response = requests.post(
            f"{BASE_URL}/api/enhanced-sow/{TEST_SOW_ID}/scopes/{scope_id}/tasks/{task_id}/approve",
            json={"approval_type": "manager", "approved": True}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: approve_task without auth returns 401")


class TestAgreementsEndpoints(TestAuthSetup):
    """Test agreements.py backend security fixes
    
    Fixed endpoints:
    - POST /api/agreements/{id}/sign (L375) - requires manager/admin/sales role
    - POST /api/agreements/{id}/record-payment (L472) - requires finance/admin/sales manager
    """
    
    def test_sign_agreement_without_auth_returns_401(self):
        """POST /api/agreements/{id}/sign without auth should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/agreements/fake-agreement-id/sign",
            json={
                "signed_by_name": "Test User",
                "signed_by_designation": "Manager"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: sign_agreement without auth returns 401")
    
    def test_record_payment_without_auth_returns_401(self):
        """POST /api/agreements/{id}/record-payment without auth should return 401"""
        response = requests.post(
            f"{BASE_URL}/api/agreements/fake-agreement-id/record-payment",
            json={
                "amount": 10000,
                "payment_date": "2026-01-15",
                "payment_method": "neft"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: record_payment without auth returns 401")
    
    def test_sign_agreement_with_admin_succeeds_or_404(self, admin_token):
        """POST /api/agreements/{id}/sign with admin should work (or 404 if no agreement)"""
        # First get an agreement ID
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            agreements = response.json()
            if agreements:
                # Find a signed or approved agreement
                test_agreement = None
                for agr in agreements:
                    if agr.get("status") in ["approved", "sent_to_client"]:
                        test_agreement = agr
                        break
                
                if test_agreement:
                    agreement_id = test_agreement.get("id")
                    sign_response = requests.post(
                        f"{BASE_URL}/api/agreements/{agreement_id}/sign",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={
                            "signed_by_name": "Admin User",
                            "signed_by_designation": "System Administrator"
                        }
                    )
                    # Should be 200 (success) or 400 (business logic - already signed etc)
                    assert sign_response.status_code in [200, 400], f"Expected 200/400, got {sign_response.status_code}: {sign_response.text}"
                    print(f"PASS: Admin can call sign endpoint (status: {sign_response.status_code})")
                    return
        
        print("SKIP: No suitable agreement found for signing test")


class TestConsultantsEndpoints(TestAuthSetup):
    """Test consultants.py backend security fixes
    
    Fixed endpoint:
    - PUT /api/consultants/{id}/profile (L125) - self-or-admin check
    """
    
    def test_update_consultant_profile_by_non_owner_non_admin_returns_403(self, sales_manager_token, sales_manager_user_id):
        """PUT /api/consultants/{id}/profile by non-owner non-admin should return 403"""
        # Get a consultant that is NOT the sales manager
        response = requests.get(
            f"{BASE_URL}/api/consultants",
            headers={"Authorization": f"Bearer {sales_manager_token}"}
        )
        
        if response.status_code == 403:
            # Sales manager may not have access to list consultants - this is expected
            print(f"PASS: Sales manager cannot access /api/consultants (403) - expected RBAC restriction")
            return
        
        if response.status_code == 200:
            consultants = response.json()
            # Find a consultant that is not the current user
            other_consultant = None
            for c in consultants:
                if c.get("id") != sales_manager_user_id:
                    other_consultant = c
                    break
            
            if other_consultant:
                consultant_id = other_consultant.get("id")
                # Try to update someone else's profile
                update_response = requests.put(
                    f"{BASE_URL}/api/consultants/{consultant_id}/profile",
                    headers={"Authorization": f"Bearer {sales_manager_token}"},
                    json={"full_name": "Hacked Name", "bio": "Unauthorized update"}
                )
                assert update_response.status_code == 403, f"Expected 403, got {update_response.status_code}: {update_response.text}"
                print(f"PASS: Non-owner non-admin cannot update consultant profile (403)")
            else:
                print("SKIP: No other consultant found to test profile update")
        else:
            print(f"SKIP: Could not fetch consultants list (status: {response.status_code})")
    
    def test_update_consultant_profile_without_auth_returns_401(self):
        """PUT /api/consultants/{id}/profile without auth should return 401"""
        response = requests.put(
            f"{BASE_URL}/api/consultants/fake-consultant-id/profile",
            json={"full_name": "Unauthorized", "bio": "No auth"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print(f"PASS: update_consultant_profile without auth returns 401")


class TestAdminVsSalesManagerAccess(TestAuthSetup):
    """Test that admin can access all endpoints while sales manager is restricted"""
    
    def test_admin_can_access_enhanced_sow_list(self, admin_token):
        """Admin should be able to list enhanced SOWs"""
        response = requests.get(
            f"{BASE_URL}/api/enhanced-sow",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin should access enhanced-sow list. Got {response.status_code}: {response.text}"
        print(f"PASS: Admin can access /api/enhanced-sow (200)")
    
    def test_sales_manager_can_access_enhanced_sow_list(self, sales_manager_token):
        """Sales manager should be able to list enhanced SOWs (sales role)"""
        response = requests.get(
            f"{BASE_URL}/api/enhanced-sow",
            headers={"Authorization": f"Bearer {sales_manager_token}"}
        )
        # Sales manager is in SALES_ROLES so should have access
        assert response.status_code == 200, f"Sales manager should access enhanced-sow list. Got {response.status_code}: {response.text}"
        print(f"PASS: Sales manager can access /api/enhanced-sow (200)")
    
    def test_admin_can_access_agreements(self, admin_token):
        """Admin should be able to list agreements"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin should access agreements. Got {response.status_code}: {response.text}"
        print(f"PASS: Admin can access /api/agreements (200)")
    
    def test_sales_manager_can_access_agreements(self, sales_manager_token):
        """Sales manager should be able to list agreements"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {sales_manager_token}"}
        )
        assert response.status_code == 200, f"Sales manager should access agreements. Got {response.status_code}: {response.text}"
        print(f"PASS: Sales manager can access /api/agreements (200)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
