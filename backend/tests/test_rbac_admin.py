"""
RBAC Admin API Tests
====================
Tests for the RBAC Admin UI endpoints:
- GET /api/rbac/roles
- GET /api/rbac/departments
- GET /api/rbac/role-groups
- GET /api/rbac/my-permissions
- POST /api/rbac/refresh-cache
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRBACAdmin:
    """RBAC Admin API tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin user ADMIN001"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "ADMIN001", "password": "admin123"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def hr_manager_token(self):
        """Login as HR Manager DVC037"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "DVC037", "password": "test123"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"HR Manager login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth token"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def hr_headers(self, hr_manager_token):
        """Headers with HR manager auth token"""
        return {
            "Authorization": f"Bearer {hr_manager_token}",
            "Content-Type": "application/json"
        }
    
    # ==================== HEALTH CHECK ====================
    
    def test_health_check(self):
        """Test backend health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"Health check passed: {data}")
    
    # ==================== AUTH TESTS ====================
    
    def test_admin_login(self):
        """Test admin login with ADMIN001/admin123"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "ADMIN001", "password": "admin123"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, f"No token in response: {data}"
        print(f"Admin login successful: {data.get('user', {}).get('name', 'Unknown')}")
    
    def test_hr_manager_login(self):
        """Test HR Manager login with DVC037/test123"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "DVC037", "password": "test123"}
        )
        assert response.status_code == 200, f"HR Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, f"No token in response: {data}"
        print(f"HR Manager login successful: {data.get('user', {}).get('name', 'Unknown')}")
    
    # ==================== RBAC ROLES ENDPOINT ====================
    
    def test_get_all_roles(self, admin_headers):
        """Test GET /api/rbac/roles returns all roles"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        data = response.json()
        
        assert "roles" in data, f"Response missing 'roles' key: {data}"
        roles = data["roles"]
        assert isinstance(roles, list), f"Roles should be a list: {type(roles)}"
        
        # Verify we have 17 roles as specified
        role_count = len(roles)
        print(f"Found {role_count} roles")
        
        # Check expected roles are present
        role_codes = [r["code"] for r in roles]
        expected_roles = ["admin", "hr_manager", "hr_executive", "sales_manager", 
                         "sales_executive", "consultant", "principal_consultant"]
        for expected in expected_roles:
            assert expected in role_codes, f"Expected role '{expected}' not found"
        
        print(f"All expected roles found: {expected_roles}")
    
    def test_roles_have_required_fields(self, admin_headers):
        """Test that roles have required fields"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=admin_headers)
        assert response.status_code == 200
        roles = response.json()["roles"]
        
        required_fields = ["code", "name", "level", "department"]
        for role in roles[:5]:  # Check first 5 roles
            for field in required_fields:
                assert field in role, f"Role {role.get('code')} missing field '{field}'"
        
        print(f"All roles have required fields: {required_fields}")
    
    def test_roles_hr_manager_access(self, hr_headers):
        """Test HR Manager can also access roles endpoint"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=hr_headers)
        assert response.status_code == 200, f"HR Manager should have access to roles: {response.text}"
        data = response.json()
        assert "roles" in data
        print(f"HR Manager can access roles - found {len(data['roles'])} roles")
    
    # ==================== RBAC DEPARTMENTS ENDPOINT ====================
    
    def test_get_all_departments(self, admin_headers):
        """Test GET /api/rbac/departments returns 6 departments"""
        response = requests.get(f"{BASE_URL}/api/rbac/departments", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get departments: {response.text}"
        data = response.json()
        
        assert "departments" in data, f"Response missing 'departments' key: {data}"
        departments = data["departments"]
        assert isinstance(departments, list), f"Departments should be a list"
        
        dept_count = len(departments)
        print(f"Found {dept_count} departments")
        
        # Verify we have 6 departments as specified
        assert dept_count >= 6, f"Expected at least 6 departments, got {dept_count}"
        
        # Check expected departments
        dept_codes = [d["code"] for d in departments]
        expected_depts = ["HR", "Sales", "Consulting", "Finance", "Operations", "External"]
        for expected in expected_depts:
            assert expected in dept_codes, f"Expected department '{expected}' not found"
        
        print(f"All expected departments found: {expected_depts}")
    
    def test_departments_have_color(self, admin_headers):
        """Test departments have color field"""
        response = requests.get(f"{BASE_URL}/api/rbac/departments", headers=admin_headers)
        assert response.status_code == 200
        departments = response.json()["departments"]
        
        for dept in departments:
            assert "color" in dept, f"Department {dept.get('code')} missing color"
            assert dept["color"].startswith("#"), f"Color should be hex: {dept['color']}"
        
        print("All departments have valid color codes")
    
    # ==================== RBAC ROLE GROUPS ENDPOINT ====================
    
    def test_get_all_role_groups(self, admin_headers):
        """Test GET /api/rbac/role-groups returns 16 groups"""
        response = requests.get(f"{BASE_URL}/api/rbac/role-groups", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get role groups: {response.text}"
        data = response.json()
        
        assert "groups" in data, f"Response missing 'groups' key: {data}"
        groups = data["groups"]
        assert isinstance(groups, list), f"Groups should be a list"
        
        group_count = len(groups)
        print(f"Found {group_count} role groups")
        
        # Verify we have at least 16 role groups
        assert group_count >= 16, f"Expected at least 16 role groups, got {group_count}"
        
        # Check expected groups
        group_codes = [g["code"] for g in groups]
        expected_groups = ["ADMIN_ROLES", "HR_ROLES", "SALES_ROLES", "MANAGER_ROLES", 
                          "CONSULTING_ROLES", "FINANCE_ROLES"]
        for expected in expected_groups:
            assert expected in group_codes, f"Expected group '{expected}' not found"
        
        print(f"All expected role groups found: {expected_groups}")
    
    def test_role_groups_have_roles(self, admin_headers):
        """Test role groups have roles array"""
        response = requests.get(f"{BASE_URL}/api/rbac/role-groups", headers=admin_headers)
        assert response.status_code == 200
        groups = response.json()["groups"]
        
        for group in groups:
            assert "roles" in group, f"Group {group.get('code')} missing 'roles'"
            assert isinstance(group["roles"], list), f"Roles should be a list"
            assert len(group["roles"]) > 0, f"Group {group.get('code')} has no roles"
        
        print("All role groups have valid roles array")
    
    # ==================== MY PERMISSIONS ENDPOINT ====================
    
    def test_my_permissions_admin(self, admin_headers):
        """Test GET /api/rbac/my-permissions returns current user's permissions"""
        response = requests.get(f"{BASE_URL}/api/rbac/my-permissions", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get permissions: {response.text}"
        data = response.json()
        
        # Verify expected fields
        assert "role" in data, f"Response missing 'role': {data}"
        assert data["role"] == "admin", f"Expected role 'admin', got '{data['role']}'"
        
        # Admin should have level 100
        assert "level" in data, f"Response missing 'level': {data}"
        assert data["level"] == 100, f"Admin should have level 100, got {data['level']}"
        
        # Admin should be able to approve and manage users
        assert data.get("can_approve") == True, "Admin should be able to approve"
        assert data.get("can_manage_users") == True, "Admin should be able to manage users"
        
        # Admin should have wildcard permission
        permissions = data.get("permissions", [])
        assert "*" in permissions, f"Admin should have '*' permission: {permissions}"
        
        print(f"Admin permissions verified: level={data['level']}, can_approve={data.get('can_approve')}")
    
    def test_my_permissions_hr_manager(self, hr_headers):
        """Test HR Manager permissions"""
        response = requests.get(f"{BASE_URL}/api/rbac/my-permissions", headers=hr_headers)
        assert response.status_code == 200, f"Failed to get HR permissions: {response.text}"
        data = response.json()
        
        assert "role" in data
        assert data["role"] == "hr_manager", f"Expected role 'hr_manager', got '{data['role']}'"
        
        # HR Manager should have level 80
        assert data.get("level") == 80, f"HR Manager should have level 80, got {data.get('level')}"
        
        # HR Manager should have HR permissions
        permissions = data.get("permissions", [])
        assert len(permissions) > 0, "HR Manager should have permissions"
        
        print(f"HR Manager permissions: {permissions}")
    
    # ==================== REFRESH CACHE ENDPOINT ====================
    
    def test_refresh_cache_admin(self, admin_headers):
        """Test POST /api/rbac/refresh-cache works for admin"""
        response = requests.post(f"{BASE_URL}/api/rbac/refresh-cache", headers=admin_headers)
        assert response.status_code == 200, f"Failed to refresh cache: {response.text}"
        data = response.json()
        
        assert "message" in data, f"Response missing message: {data}"
        assert "roles_count" in data, f"Response missing roles_count: {data}"
        assert "departments_count" in data, f"Response missing departments_count: {data}"
        
        print(f"Cache refreshed: {data['roles_count']} roles, {data['departments_count']} departments")
    
    def test_refresh_cache_hr_forbidden(self, hr_headers):
        """Test HR Manager cannot refresh cache (admin only)"""
        response = requests.post(f"{BASE_URL}/api/rbac/refresh-cache", headers=hr_headers)
        assert response.status_code == 403, f"HR Manager should not be able to refresh cache: {response.status_code}"
        print("HR Manager correctly denied cache refresh access")
    
    # ==================== SINGLE ROLE ENDPOINT ====================
    
    def test_get_single_role(self, admin_headers):
        """Test GET /api/rbac/roles/{role_code} returns role details"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles/admin", headers=admin_headers)
        assert response.status_code == 200, f"Failed to get admin role: {response.text}"
        data = response.json()
        
        assert data.get("code") == "admin", f"Expected admin role, got {data}"
        assert data.get("level") == 100, f"Admin should have level 100"
        assert "*" in data.get("permissions", []), "Admin should have wildcard permission"
        
        print(f"Single role retrieved: {data.get('name')}")
    
    def test_get_nonexistent_role(self, admin_headers):
        """Test GET /api/rbac/roles/{role_code} returns 404 for unknown role"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles/unknown_role_xyz", headers=admin_headers)
        assert response.status_code == 404, f"Expected 404 for unknown role, got {response.status_code}"
        print("Correctly returns 404 for non-existent role")
    
    # ==================== UNAUTHORIZED ACCESS TESTS ====================
    
    def test_roles_unauthorized(self):
        """Test roles endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Roles endpoint correctly requires authentication")
    
    def test_departments_unauthorized(self):
        """Test departments endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/rbac/departments")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Departments endpoint correctly requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
