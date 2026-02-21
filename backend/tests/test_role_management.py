"""
Test Role Management API - User Management and Permissions
Tests for:
- GET /api/roles - List all roles
- POST /api/roles - Create new role (Admin only)
- GET /api/roles/{role_id} - Get role with permissions
- PATCH /api/roles/{role_id} - Update role permissions
- DELETE /api/roles/{role_id} - Delete custom role
- GET /api/users-with-roles - List users with role info
- PATCH /api/users/{user_id}/role - Update user role
- GET /api/permission-modules - Get available permission modules
- GET /api/roles/categories/sow - Get SOW role categories
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestRoleManagement:
    """Role Management API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login as admin for testing"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        self.token = data['access_token']
        self.admin_user = data['user']
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_all_roles(self):
        """Test GET /api/roles - returns all 13 roles"""
        response = requests.get(f"{BASE_URL}/api/roles", headers=self.headers)
        assert response.status_code == 200, f"Failed to get roles: {response.text}"
        
        roles = response.json()
        assert isinstance(roles, list), "Roles should be a list"
        
        # Verify all 13 roles are present
        role_ids = [r['id'] for r in roles]
        expected_roles = [
            'admin', 'consultant', 'lean_consultant', 'lead_consultant', 
            'senior_consultant', 'project_manager', 'principal_consultant',
            'hr_executive', 'hr_manager', 'sales_manager', 
            'subject_matter_expert', 'manager', 'executive'
        ]
        
        for expected_role in expected_roles:
            assert expected_role in role_ids, f"Missing role: {expected_role}"
        
        print(f"✓ Found all {len(role_ids)} roles")
        
    def test_get_roles_with_system_badge(self):
        """Test roles have correct is_system_role flag"""
        response = requests.get(f"{BASE_URL}/api/roles", headers=self.headers)
        assert response.status_code == 200
        
        roles = response.json()
        system_roles = ['admin', 'consultant', 'manager', 'executive', 'project_manager', 'principal_consultant']
        
        for role in roles:
            if role['id'] in system_roles:
                assert role.get('is_system_role', False) is True, f"Role {role['id']} should be a system role"
            
        print("✓ System role badges verified")
        
    def test_get_single_role_with_permissions(self):
        """Test GET /api/roles/{role_id} - returns role with permissions"""
        response = requests.get(f"{BASE_URL}/api/roles/consultant", headers=self.headers)
        assert response.status_code == 200, f"Failed to get role: {response.text}"
        
        role = response.json()
        assert role['id'] == 'consultant'
        assert role['name'] == 'Consultant'
        assert 'permissions' in role, "Role should have permissions"
        assert 'sow' in role['permissions'], "Consultant should have sow permissions"
        assert role['permissions']['sow']['read'] == True, "Consultant should have SOW read permission"
        
        print(f"✓ Role consultant has permissions: {list(role['permissions'].keys())}")
        
    def test_create_custom_role(self):
        """Test POST /api/roles - create new custom role"""
        test_role_id = f"test_role_{datetime.now().strftime('%H%M%S')}"
        
        response = requests.post(f"{BASE_URL}/api/roles", headers=self.headers, json={
            "id": test_role_id,
            "name": "Test Custom Role",
            "description": "A test role for pytest"
        })
        
        assert response.status_code == 200, f"Failed to create role: {response.text}"
        result = response.json()
        assert 'role_id' in result or 'message' in result
        
        # Verify role was created
        verify_res = requests.get(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers)
        assert verify_res.status_code == 200, f"Role not found after creation"
        
        # Cleanup - delete the test role
        delete_res = requests.delete(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers)
        assert delete_res.status_code == 200, f"Failed to cleanup test role"
        
        print(f"✓ Created and deleted custom role: {test_role_id}")
        
    def test_create_duplicate_role_fails(self):
        """Test POST /api/roles - cannot create duplicate role"""
        response = requests.post(f"{BASE_URL}/api/roles", headers=self.headers, json={
            "id": "admin",
            "name": "Admin Duplicate",
            "description": "Should fail"
        })
        
        assert response.status_code == 400, "Creating duplicate role should fail"
        print("✓ Duplicate role creation correctly rejected")
        
    def test_update_role_permissions(self):
        """Test PATCH /api/roles/{role_id} - update permissions"""
        # Create a test role first
        test_role_id = f"test_perm_{datetime.now().strftime('%H%M%S')}"
        create_res = requests.post(f"{BASE_URL}/api/roles", headers=self.headers, json={
            "id": test_role_id,
            "name": "Test Permissions Role",
            "description": "For permission testing"
        })
        assert create_res.status_code == 200
        
        # Update permissions
        new_permissions = {
            "leads": {"create": True, "read": True, "update": True, "delete": False},
            "sow": {"create": False, "read": True, "update": False, "delete": False}
        }
        
        update_res = requests.patch(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers, json={
            "permissions": new_permissions
        })
        assert update_res.status_code == 200, f"Failed to update permissions: {update_res.text}"
        
        # Verify permissions were updated
        verify_res = requests.get(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers)
        assert verify_res.status_code == 200
        role_data = verify_res.json()
        assert role_data['permissions']['leads']['create'] == True
        assert role_data['permissions']['sow']['read'] == True
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers)
        print("✓ Role permissions updated and verified")
        
    def test_delete_custom_role(self):
        """Test DELETE /api/roles/{role_id} - delete custom role"""
        # Create a role to delete
        test_role_id = f"test_delete_{datetime.now().strftime('%H%M%S')}"
        create_res = requests.post(f"{BASE_URL}/api/roles", headers=self.headers, json={
            "id": test_role_id,
            "name": "Test Delete Role",
            "description": "Will be deleted"
        })
        assert create_res.status_code == 200
        
        # Delete the role
        delete_res = requests.delete(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers)
        assert delete_res.status_code == 200, f"Failed to delete role: {delete_res.text}"
        
        # Verify role is deleted
        verify_res = requests.get(f"{BASE_URL}/api/roles/{test_role_id}", headers=self.headers)
        assert verify_res.status_code == 404, "Deleted role should not be found"
        
        print("✓ Custom role deleted successfully")
        
    def test_cannot_delete_system_role(self):
        """Test DELETE /api/roles/{role_id} - cannot delete system role"""
        response = requests.delete(f"{BASE_URL}/api/roles/admin", headers=self.headers)
        assert response.status_code == 400, "Deleting system role should fail"
        
        response = requests.delete(f"{BASE_URL}/api/roles/consultant", headers=self.headers)
        assert response.status_code == 400, "Deleting consultant role should fail"
        
        print("✓ System role deletion correctly rejected")


class TestUserWithRoles:
    """User-Role Integration Tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data['access_token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_users_with_roles(self):
        """Test GET /api/users-with-roles - returns users with role info"""
        response = requests.get(f"{BASE_URL}/api/users-with-roles", headers=self.headers)
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        
        users = response.json()
        assert isinstance(users, list), "Should return a list of users"
        
        # Check users have role_info
        for user in users:
            assert 'role' in user, f"User {user.get('email')} missing role"
            # role_info may be present for enriched response
            
        print(f"✓ Found {len(users)} users with roles")
        
    def test_update_user_role(self):
        """Test PATCH /api/users/{user_id}/role - change user role"""
        # Create a test user
        test_email = f"test_role_user_{datetime.now().strftime('%H%M%S')}@example.com"
        
        create_res = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": test_email,
            "password": "testpassword123",
            "full_name": "Test Role User",
            "role": "consultant"
        })
        assert create_res.status_code == 200, f"Failed to create test user: {create_res.text}"
        user_id = create_res.json()['id']
        
        # Update the user's role to manager
        update_res = requests.patch(
            f"{BASE_URL}/api/users/{user_id}/role?role=manager", 
            headers=self.headers
        )
        assert update_res.status_code == 200, f"Failed to update role: {update_res.text}"
        
        # Verify role was updated
        users_res = requests.get(f"{BASE_URL}/api/users-with-roles", headers=self.headers)
        users = users_res.json()
        
        updated_user = next((u for u in users if u['id'] == user_id), None)
        assert updated_user is not None, "User not found after update"
        assert updated_user['role'] == 'manager', f"Role not updated, got: {updated_user['role']}"
        
        print(f"✓ User role updated from consultant to manager")
        
    def test_admin_only_can_change_roles(self):
        """Test that non-admin users cannot change roles"""
        # Login as executive (non-admin)
        exec_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        
        if exec_login.status_code != 200:
            pytest.skip("Executive user not available for testing")
            
        exec_headers = {"Authorization": f"Bearer {exec_login.json()['access_token']}"}
        
        # Try to change a user's role
        users_res = requests.get(f"{BASE_URL}/api/users-with-roles", headers=self.headers)
        users = users_res.json()
        if len(users) > 0:
            test_user_id = users[0]['id']
            response = requests.patch(
                f"{BASE_URL}/api/users/{test_user_id}/role?role=admin",
                headers=exec_headers
            )
            assert response.status_code == 403, "Non-admin should not be able to change roles"
            
        print("✓ Non-admin role change correctly rejected")


class TestPermissionModules:
    """Permission Module API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data['access_token']
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
    def test_get_permission_modules(self):
        """Test GET /api/permission-modules - returns all modules and actions"""
        response = requests.get(f"{BASE_URL}/api/permission-modules", headers=self.headers)
        assert response.status_code == 200, f"Failed to get permission modules: {response.text}"
        
        data = response.json()
        assert 'modules' in data, "Response should contain modules"
        assert 'actions' in data, "Response should contain actions"
        
        # Verify expected modules
        module_ids = [m['id'] for m in data['modules']]
        expected_modules = ['leads', 'pricing_plans', 'sow', 'quotations', 'agreements', 
                          'projects', 'tasks', 'consultants', 'users', 'reports']
        
        for expected in expected_modules:
            assert expected in module_ids, f"Missing module: {expected}"
            
        # Verify SOW has special actions
        assert 'sow' in data['actions'], "SOW should have special actions"
        assert 'approve' in data['actions']['sow'], "SOW should have approve action"
        
        print(f"✓ Found {len(data['modules'])} permission modules")
        
    def test_permission_modules_admin_only(self):
        """Test that non-admin cannot access permission modules"""
        # Login as executive
        exec_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        
        if exec_login.status_code != 200:
            pytest.skip("Executive user not available")
            
        exec_headers = {"Authorization": f"Bearer {exec_login.json()['access_token']}"}
        
        response = requests.get(f"{BASE_URL}/api/permission-modules", headers=exec_headers)
        assert response.status_code == 403, "Non-admin should not access permission modules"
        
        print("✓ Permission modules access restricted to admin")


class TestSOWRoleCategories:
    """SOW Role Categories API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup_auth(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        
    def test_get_sow_role_categories(self):
        """Test GET /api/roles/categories/sow - returns role categories"""
        response = requests.get(f"{BASE_URL}/api/roles/categories/sow", headers=self.headers)
        assert response.status_code == 200, f"Failed to get SOW role categories: {response.text}"
        
        data = response.json()
        
        # Verify sales roles
        assert 'sales_roles' in data, "Should have sales_roles"
        assert 'admin' in data['sales_roles']
        assert 'executive' in data['sales_roles']
        assert 'sales_manager' in data['sales_roles']
        
        # Verify consulting roles
        assert 'consulting_roles' in data, "Should have consulting_roles"
        assert 'consultant' in data['consulting_roles']
        assert 'senior_consultant' in data['consulting_roles']
        assert 'principal_consultant' in data['consulting_roles']
        
        # Verify PM roles
        assert 'pm_roles' in data, "Should have pm_roles"
        assert 'project_manager' in data['pm_roles']
        assert 'manager' in data['pm_roles']
        
        print(f"✓ SOW role categories verified: Sales={len(data['sales_roles'])}, Consulting={len(data['consulting_roles'])}, PM={len(data['pm_roles'])}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
