"""
Test RBAC Export Permission (system.can_export_data)
=====================================================
Tests the global export permission that controls all downloads/exports across the ERP.

Admin and manager-level roles should have this permission.
Regular employees (sales_executive, executive) should NOT have this permission.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRBACExportPermission:
    """Test system.can_export_data permission across different roles"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token (EMP001)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture
    def sales_exec_token(self):
        """Get sales executive token (EMP003)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        assert response.status_code == 200, f"Sales exec login failed: {response.text}"
        return response.json().get("access_token")
    
    @pytest.fixture
    def hr_manager_token(self):
        """Get HR manager token (EMP002)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "hr123"
        })
        if response.status_code != 200:
            pytest.skip("HR Manager login failed - user may not exist")
        return response.json().get("access_token")
    
    # ==================== Admin Tests ====================
    
    def test_admin_has_wildcard_permission(self, admin_token):
        """Admin should have '*' (wildcard) permission which includes export"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/my-permissions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # Admin should have wildcard permission
        assert "*" in permissions, "Admin should have '*' wildcard permission"
        assert data.get("level") == 100, "Admin should have level 100"
        assert data.get("role") == "admin", "Role should be 'admin'"
        
        print(f"✅ Admin has wildcard permission: {permissions}")
    
    def test_admin_can_export_data(self, admin_token):
        """Admin should be able to export data (has '*' permission)"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/my-permissions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # Admin has '*' which means they have ALL permissions including export
        has_export = "*" in permissions or "system.can_export_data" in permissions
        assert has_export, "Admin should have export permission (via '*' or explicit)"
        
        print(f"✅ Admin can export data")
    
    # ==================== Sales Executive Tests ====================
    
    def test_sales_exec_does_not_have_export_permission(self, sales_exec_token):
        """Sales Executive should NOT have system.can_export_data permission"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/my-permissions",
            headers={"Authorization": f"Bearer {sales_exec_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # Sales executive should NOT have export permission
        assert "*" not in permissions, "Sales exec should NOT have wildcard permission"
        assert "system.can_export_data" not in permissions, "Sales exec should NOT have export permission"
        
        # Verify role and level
        assert data.get("role") in ["executive", "sales_executive"], f"Role should be executive/sales_executive, got {data.get('role')}"
        assert data.get("level") == 40, f"Level should be 40, got {data.get('level')}"
        
        print(f"✅ Sales Executive does NOT have export permission")
        print(f"   Permissions: {permissions}")
    
    def test_sales_exec_has_limited_permissions(self, sales_exec_token):
        """Sales Executive should only have limited permissions"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/my-permissions",
            headers={"Authorization": f"Bearer {sales_exec_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # Expected permissions for sales executive
        expected_permissions = ["leads.own", "meetings.own", "quotations.create", "agreements.create"]
        
        for perm in expected_permissions:
            assert perm in permissions, f"Sales exec should have '{perm}' permission"
        
        # Should NOT have manager-level permissions
        manager_permissions = ["system.can_export_data", "team.*", "reports.*", "approvals.*"]
        for perm in manager_permissions:
            assert perm not in permissions, f"Sales exec should NOT have '{perm}' permission"
        
        print(f"✅ Sales Executive has correct limited permissions")
    
    # ==================== HR Manager Tests ====================
    
    def test_hr_manager_has_export_permission(self, hr_manager_token):
        """HR Manager should have system.can_export_data permission"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/my-permissions",
            headers={"Authorization": f"Bearer {hr_manager_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        permissions = data.get("permissions", [])
        
        # HR Manager should have export permission
        has_export = "*" in permissions or "system.can_export_data" in permissions
        assert has_export, f"HR Manager should have export permission. Got: {permissions}"
        
        print(f"✅ HR Manager has export permission")
    
    # ==================== Permission Check Endpoint Tests ====================
    
    def test_permission_check_endpoint_admin(self, admin_token):
        """Test /permissions/check endpoint for admin"""
        response = requests.post(
            f"{BASE_URL}/api/permissions/check",
            params={"feature": "system.can_export_data"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("has_permission") == True, "Admin should have export permission"
        
        print(f"✅ Permission check endpoint works for admin")
    
    def test_permission_check_endpoint_sales_exec(self, sales_exec_token):
        """Test /permissions/check endpoint for sales executive"""
        response = requests.post(
            f"{BASE_URL}/api/permissions/check",
            params={"feature": "system.can_export_data"},
            headers={"Authorization": f"Bearer {sales_exec_token}"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("has_permission") == False, "Sales exec should NOT have export permission"
        
        print(f"✅ Permission check endpoint works for sales exec")
    
    # ==================== Role Definition Tests ====================
    
    def test_rbac_seeder_has_export_permission_for_managers(self):
        """Verify RBAC seeder defines export permission for manager roles"""
        # This test verifies the seeder configuration
        # The actual seeder should have system.can_export_data for:
        # - admin, hr_manager, sales_manager, principal_consultant, manager
        
        expected_roles_with_export = [
            "admin",
            "hr_manager", 
            "sales_manager",
            "principal_consultant",
            "manager"
        ]
        
        # Read the seeder file to verify
        import sys
        sys.path.insert(0, '/app/backend')
        from routers.rbac_seeder import ROLE_DEFINITIONS
        
        for role in expected_roles_with_export:
            if role in ROLE_DEFINITIONS:
                permissions = ROLE_DEFINITIONS[role].get("permissions", [])
                has_export = "*" in permissions or "system.can_export_data" in permissions
                assert has_export, f"Role '{role}' should have export permission in seeder"
                print(f"✅ Role '{role}' has export permission in seeder")
        
        # Verify sales_executive does NOT have export permission
        if "sales_executive" in ROLE_DEFINITIONS:
            permissions = ROLE_DEFINITIONS["sales_executive"].get("permissions", [])
            has_export = "*" in permissions or "system.can_export_data" in permissions
            assert not has_export, "sales_executive should NOT have export permission"
            print(f"✅ Role 'sales_executive' does NOT have export permission in seeder")
        
        if "executive" in ROLE_DEFINITIONS:
            permissions = ROLE_DEFINITIONS["executive"].get("permissions", [])
            has_export = "*" in permissions or "system.can_export_data" in permissions
            assert not has_export, "executive should NOT have export permission"
            print(f"✅ Role 'executive' does NOT have export permission in seeder")


class TestFeatureFlagsExportPermission:
    """Test that system.can_export_data is properly defined in FEATURE_FLAGS"""
    
    def test_export_permission_in_feature_flags(self):
        """Verify system.can_export_data is defined in FEATURE_FLAGS"""
        import sys
        sys.path.insert(0, '/app/backend')
        from routers.permissions import FEATURE_FLAGS
        
        assert "system.can_export_data" in FEATURE_FLAGS, "system.can_export_data should be in FEATURE_FLAGS"
        
        export_config = FEATURE_FLAGS["system.can_export_data"]
        assert export_config.get("category") == "admin", "Export permission should be in 'admin' category"
        assert "admin" in export_config.get("default_roles", []), "Admin should have export by default"
        assert "hr_manager" in export_config.get("default_roles", []), "HR Manager should have export by default"
        assert "sales_manager" in export_config.get("default_roles", []), "Sales Manager should have export by default"
        
        print(f"✅ system.can_export_data is properly defined in FEATURE_FLAGS")
        print(f"   Default roles: {export_config.get('default_roles')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
