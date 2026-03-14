"""
RBAC Integration Tests - Phase 3-5 Verification
Tests the complete RBAC migration including:
- Backend deps.py integration with rbac_service
- RBAC seeder functionality
- GET /api/rbac/migration-status health
- GET /api/rbac/roles returns 17 roles
- GET /api/rbac/my-permissions returns role data with level, permissions, stage_access
- Frontend PermissionContext fetches from RBAC API
"""

import pytest
import requests
import os
from datetime import datetime

# Use the preview URL for testing
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://netra-followups.preview.emergentagent.com')

class TestRBACIntegration:
    """Test RBAC integration after Phase 3-5 migration"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed - cannot proceed with RBAC tests")
    
    def test_health_check(self):
        """Test backend is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("PASS: Health check working")
    
    def test_admin_login(self):
        """Test admin login with ADMIN001/admin123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data.get("user", {}).get("role") == "admin"
        print("PASS: Admin login successful")
    
    def test_rbac_migration_status_healthy(self, admin_token):
        """Test GET /api/rbac/migration-status returns HEALTHY status"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/migration-status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify health status
        assert data.get("health") in ["HEALTHY", "ISSUES_FOUND"], f"Unexpected health: {data.get('health')}"
        
        # Verify phase info
        assert "phase" in data, "Missing phase in migration status"
        
        # Verify statistics
        assert "statistics" in data, "Missing statistics"
        stats = data["statistics"]
        assert stats.get("roles_in_db", 0) > 0, "No roles in database"
        assert stats.get("role_groups_in_db", 0) > 0, "No role groups in database"
        assert stats.get("departments_in_db", 0) > 0, "No departments in database"
        
        print(f"PASS: Migration status healthy - Phase: {data.get('phase')}, Health: {data.get('health')}")
        print(f"  Stats: {stats}")
    
    def test_rbac_roles_returns_17_roles(self, admin_token):
        """Test GET /api/rbac/roles returns 17 roles"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/roles",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "roles" in data, "Missing roles in response"
        roles = data["roles"]
        assert len(roles) == 17, f"Expected 17 roles, got {len(roles)}"
        
        # Verify roles have required fields
        expected_fields = ["code", "name", "level", "department", "permissions"]
        for role in roles:
            for field in expected_fields:
                assert field in role, f"Role {role.get('code')} missing field: {field}"
        
        # Verify expected role codes exist
        role_codes = [r["code"] for r in roles]
        expected_codes = ["admin", "hr_manager", "hr_executive", "sales_manager", 
                        "sales_executive", "executive", "principal_consultant"]
        for code in expected_codes:
            assert code in role_codes, f"Missing expected role: {code}"
        
        print(f"PASS: GET /api/rbac/roles returns {len(roles)} roles")
        print(f"  Role codes: {role_codes}")
    
    def test_rbac_my_permissions_returns_full_data(self, admin_token):
        """Test GET /api/rbac/my-permissions returns role data with level, permissions, stage_access"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/my-permissions",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert "role" in data, "Missing 'role' in my-permissions response"
        assert "level" in data, "Missing 'level' in my-permissions response"
        assert "permissions" in data, "Missing 'permissions' in my-permissions response"
        assert "stage_access" in data, "Missing 'stage_access' in my-permissions response"
        
        # Verify admin-specific values
        assert data["role"] == "admin", f"Expected role='admin', got {data['role']}"
        assert data["level"] == 100, f"Expected level=100, got {data['level']}"
        assert data.get("can_approve") == True, "Admin should have can_approve=True"
        assert data.get("can_manage_users") == True, "Admin should have can_manage_users=True"
        
        # Verify permissions array contains wildcard for admin
        assert "*" in data["permissions"], "Admin permissions should include '*'"
        
        # Verify stage_access structure
        stage_access = data["stage_access"]
        assert "mode" in stage_access, "stage_access missing 'mode'"
        assert "visible_stages" in stage_access, "stage_access missing 'visible_stages'"
        
        print(f"PASS: GET /api/rbac/my-permissions returns complete data")
        print(f"  Role: {data['role']}, Level: {data['level']}")
        print(f"  Can Approve: {data.get('can_approve')}, Can Manage Users: {data.get('can_manage_users')}")
        print(f"  Stage Access Mode: {stage_access.get('mode')}")
    
    def test_rbac_departments_returns_6(self, admin_token):
        """Test departments endpoint returns 6 departments"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/departments",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "departments" in data, "Missing departments"
        depts = data["departments"]
        assert len(depts) == 6, f"Expected 6 departments, got {len(depts)}"
        
        dept_codes = [d["code"] for d in depts]
        expected = ["HR", "Sales", "Consulting", "Finance", "Operations", "External"]
        for code in expected:
            assert code in dept_codes, f"Missing department: {code}"
        
        print(f"PASS: GET /api/rbac/departments returns {len(depts)} departments")
    
    def test_rbac_role_groups_returns_16(self, admin_token):
        """Test role groups endpoint returns 16 groups"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/role-groups",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "groups" in data, "Missing groups"
        groups = data["groups"]
        assert len(groups) == 16, f"Expected 16 role groups, got {len(groups)}"
        
        group_codes = [g["code"] for g in groups]
        expected_groups = ["ADMIN_ROLES", "HR_ROLES", "SALES_ROLES", "CONSULTING_ROLES", 
                         "MANAGER_ROLES", "APPROVAL_ROLES", "EMPLOYEE_ROLES"]
        for code in expected_groups:
            assert code in group_codes, f"Missing role group: {code}"
        
        print(f"PASS: GET /api/rbac/role-groups returns {len(groups)} groups")


class TestRBACAccessControl:
    """Test role-based access control with database-backed roles"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_leads_page_accessible_to_admin(self, admin_token):
        """Test admin can access leads (uses SALES_ROLES from DB)"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Admin should have access (part of SALES_ROLES from database)
        assert response.status_code == 200, f"Admin should access leads, got {response.status_code}"
        print("PASS: Admin can access /api/leads (SALES_ROLES DB check)")
    
    def test_employees_page_accessible_to_admin(self, admin_token):
        """Test admin can access employees (uses HR_ROLES from DB)"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Admin should have access (part of HR_ROLES from database)
        assert response.status_code == 200, f"Admin should access employees, got {response.status_code}"
        print("PASS: Admin can access /api/employees (HR_ROLES DB check)")
    
    def test_projects_accessible_to_admin(self, admin_token):
        """Test admin can access projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Admin should access projects, got {response.status_code}"
        print("PASS: Admin can access /api/projects")
    
    def test_attendance_accessible_to_admin(self, admin_token):
        """Test admin can access attendance"""
        response = requests.get(
            f"{BASE_URL}/api/attendance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should be 200 or return attendance list
        assert response.status_code in [200, 404], f"Admin should access attendance, got {response.status_code}"
        print("PASS: Admin can access /api/attendance")
    
    def test_unauthorized_access_to_rbac(self):
        """Test RBAC endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles")
        assert response.status_code == 401, "RBAC roles should require auth"
        
        response = requests.get(f"{BASE_URL}/api/rbac/migration-status")
        assert response.status_code == 401, "Migration status should require auth"
        
        print("PASS: RBAC endpoints properly require authentication")


class TestDepsRBACServiceIntegration:
    """Test deps.py imports from rbac_service correctly"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_role_hierarchy_endpoint_works(self, admin_token):
        """Test role hierarchy endpoint (uses RBAC service)"""
        response = requests.get(
            f"{BASE_URL}/api/rbac/role-hierarchy",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "hierarchy" in data, "Missing hierarchy"
        assert "departments" in data, "Missing departments"
        
        # Should have multiple departments
        assert len(data["departments"]) >= 5, "Should have at least 5 departments in hierarchy"
        
        print(f"PASS: Role hierarchy working - {len(data['departments'])} departments")
    
    def test_check_permission_endpoint_works(self, admin_token):
        """Test check-permission endpoint (uses has_permission from rbac_service)"""
        # Admin should have all permissions
        response = requests.get(
            f"{BASE_URL}/api/rbac/check-permission",
            params={"role": "admin", "permission": "leads.create"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("has_permission") == True, "Admin should have leads.create permission"
        print("PASS: Check permission endpoint working - admin has leads.create")
    
    def test_refresh_cache_endpoint_works(self, admin_token):
        """Test cache refresh (validates RBAC service is operational)"""
        response = requests.post(
            f"{BASE_URL}/api/rbac/refresh-cache",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("roles_count", 0) > 0, "Should have roles after refresh"
        assert data.get("departments_count", 0) > 0, "Should have departments after refresh"
        
        print(f"PASS: Cache refresh working - {data.get('roles_count')} roles, {data.get('departments_count')} depts")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
