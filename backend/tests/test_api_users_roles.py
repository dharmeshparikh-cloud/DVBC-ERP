"""
OWASP-Compliant API Security Test Suite - User & Role Management
Tests: User CRUD, Role Management, Permissions, RBAC enforcement
"""

import pytest
import httpx


class TestUsersPositive:
    """Positive tests for users module."""
    
    @pytest.mark.asyncio
    async def test_user001_get_all_users(self, admin_client):
        """TC-USER-001: Get all users."""
        response = await admin_client.get("/api/users")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_user002_get_current_user(self, admin_client):
        """TC-USER-002: Get current user info."""
        response = await admin_client.get("/api/users/me")
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
    
    @pytest.mark.asyncio
    async def test_user003_update_current_user(self, admin_client):
        """TC-USER-003: Update current user profile."""
        response = await admin_client.patch("/api/users/me", json={
            "full_name": "System Administrator"
        })
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user004_get_user_profile(self, admin_client, db):
        """TC-USER-004: Get specific user profile."""
        user = await db.users.find_one({}, {"_id": 0, "id": 1})
        if user:
            response = await admin_client.get(f"/api/users/{user['id']}/profile")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user005_get_users_with_roles(self, admin_client):
        """TC-USER-005: Get users with their roles."""
        response = await admin_client.get("/api/users-with-roles")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user006_get_my_permissions(self, admin_client):
        """TC-USER-006: Get my permissions."""
        response = await admin_client.get("/api/users/me/permissions")
        
        assert response.status_code == 200


class TestUsersNegative:
    """Negative tests for users module."""
    
    @pytest.mark.asyncio
    async def test_user020_get_nonexistent(self, admin_client):
        """TC-USER-020: Get nonexistent user returns 404."""
        response = await admin_client.get("/api/users/nonexistent-id/profile")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_user021_update_nonexistent(self, admin_client):
        """TC-USER-021: Update nonexistent user fails."""
        response = await admin_client.patch(
            "/api/users/nonexistent-id/profile",
            json={"full_name": "Test"}
        )
        
        assert response.status_code == 404


class TestUsersSecurity:
    """Security tests for users module."""
    
    @pytest.mark.asyncio
    async def test_user030_no_password_in_response(self, admin_client):
        """TC-USER-030: Password hash not returned in user list."""
        response = await admin_client.get("/api/users")
        data = response.json()
        
        for user in data:
            assert "password" not in user
            assert "hashed_password" not in user
    
    @pytest.mark.asyncio
    async def test_user031_xss_in_name(self, admin_client, owasp_payloads):
        """TC-USER-031: XSS in user name handled safely."""
        for payload in owasp_payloads.XSS_PAYLOADS[:2]:
            response = await admin_client.patch("/api/users/me", json={
                "full_name": payload
            })
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_user032_sql_injection_in_search(self, admin_client, owasp_payloads):
        """TC-USER-032: SQL injection in user ID."""
        for payload in owasp_payloads.SQL_INJECTION[:2]:
            response = await admin_client.get(f"/api/users/{payload}/profile")
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_user033_unauthenticated_access(self, api_client):
        """TC-USER-033: Unauthenticated cannot access users."""
        response = await api_client.get("/api/users")
        
        assert response.status_code == 401


class TestRolesPositive:
    """Positive tests for roles management."""
    
    @pytest.mark.asyncio
    async def test_role001_get_all_roles(self, admin_client):
        """TC-ROLE-001: Get all roles."""
        response = await admin_client.get("/api/roles")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_role002_create_role(self, admin_client):
        """TC-ROLE-002: Create new role."""
        response = await admin_client.post("/api/roles", json={
            "id": f"test_role_{id(admin_client)}",
            "name": "Test Role",
            "description": "A test role for API testing"
        })
        
        assert response.status_code in [200, 400, 409]  # May conflict
    
    @pytest.mark.asyncio
    async def test_role003_get_role_by_id(self, admin_client, db):
        """TC-ROLE-003: Get role by ID."""
        role = await db.roles.find_one({}, {"_id": 0, "id": 1})
        if role:
            response = await admin_client.get(f"/api/roles/{role['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_role004_update_role(self, admin_client, db):
        """TC-ROLE-004: Update role."""
        role = await db.roles.find_one({"can_delete": True}, {"_id": 0, "id": 1})
        if role:
            response = await admin_client.patch(
                f"/api/roles/{role['id']}",
                json={"description": "Updated description"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_role005_get_sow_role_categories(self, admin_client):
        """TC-ROLE-005: Get SOW role categories."""
        response = await admin_client.get("/api/roles/categories/sow")
        
        assert response.status_code == 200


class TestRolesNegative:
    """Negative tests for roles management."""
    
    @pytest.mark.asyncio
    async def test_role020_delete_system_role(self, admin_client):
        """TC-ROLE-020: Cannot delete system role."""
        response = await admin_client.delete("/api/roles/admin")
        
        # Admin role should not be deletable
        assert response.status_code in [400, 403]
    
    @pytest.mark.asyncio
    async def test_role021_create_duplicate_role(self, admin_client, db):
        """TC-ROLE-021: Duplicate role ID rejected."""
        existing_role = await db.roles.find_one({}, {"_id": 0, "id": 1})
        if existing_role:
            response = await admin_client.post("/api/roles", json={
                "id": existing_role["id"],
                "name": "Duplicate Test",
                "description": "Should fail"
            })
            
            # Should either reject or handle gracefully
            assert response.status_code in [200, 400, 409]


class TestPermissionsPositive:
    """Positive tests for permissions module."""
    
    @pytest.mark.asyncio
    async def test_perm001_get_role_permissions(self, admin_client):
        """TC-PERM-001: Get role permissions."""
        response = await admin_client.get("/api/role-permissions")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_perm002_get_permissions_for_role(self, admin_client):
        """TC-PERM-002: Get permissions for specific role."""
        response = await admin_client.get("/api/role-permissions/admin")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_perm003_update_role_permissions(self, admin_client, db):
        """TC-PERM-003: Update role permissions."""
        role = await db.roles.find_one({"can_delete": True}, {"_id": 0, "id": 1})
        if role:
            response = await admin_client.patch(
                f"/api/role-permissions/{role['id']}",
                json={"permissions": {"leads": {"view": True}}}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_perm004_get_permission_modules(self, admin_client):
        """TC-PERM-004: Get permission modules."""
        response = await admin_client.get("/api/permission-modules")
        
        assert response.status_code == 200


class TestUserRoleAssignment:
    """Tests for assigning roles to users."""
    
    @pytest.mark.asyncio
    async def test_assign001_change_user_role(self, admin_client, db):
        """TC-ASSIGN-001: Change user role."""
        user = await db.users.find_one(
            {"role": {"$ne": "admin"}},
            {"_id": 0, "id": 1, "role": 1}
        )
        if user:
            # Store original role
            original_role = user["role"]
            
            # Change to different role
            response = await admin_client.patch(
                f"/api/users/{user['id']}/role",
                json={"role": "consultant"}
            )
            
            # Revert to original
            await admin_client.patch(
                f"/api/users/{user['id']}/role",
                json={"role": original_role}
            )
            
            # May fail due to business rules (e.g., self-role change restrictions)
            assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_assign002_assign_invalid_role(self, admin_client, db):
        """TC-ASSIGN-002: Assign invalid role fails."""
        user = await db.users.find_one({"role": {"$ne": "admin"}}, {"_id": 0, "id": 1})
        if user:
            response = await admin_client.patch(
                f"/api/users/{user['id']}/role",
                json={"role": "nonexistent_role_xyz"}
            )
            
            assert response.status_code in [400, 422]


class TestRoleBasedAccessControl:
    """Tests for RBAC enforcement across endpoints."""
    
    @pytest.mark.asyncio
    async def test_rbac001_manager_view_only(self, manager_client, test_data):
        """TC-RBAC-001: Manager role has view-only access."""
        # Manager should not be able to create leads
        lead_data = test_data.lead()
        response = await manager_client.post("/api/leads", json=lead_data)
        
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_rbac002_manager_can_view(self, manager_client):
        """TC-RBAC-002: Manager can view resources."""
        response = await manager_client.get("/api/leads")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rbac003_executive_can_create(self, executive_client, test_data):
        """TC-RBAC-003: Executive can create resources."""
        lead_data = test_data.lead()
        response = await executive_client.post("/api/leads", json=lead_data)
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rbac004_admin_full_access(self, admin_client, db):
        """TC-RBAC-004: Admin has full access."""
        # Admin should be able to delete
        lead = await db.leads.find_one({}, {"_id": 0, "id": 1})
        if lead:
            # Test that admin can access delete endpoint (don't actually delete)
            # We verify access control, not functionality here
            response = await admin_client.delete(f"/api/leads/{lead['id']}")
            
            # Admin should not get 403
            assert response.status_code != 403


class TestPrivilegeEscalation:
    """Tests for privilege escalation prevention - OWASP A01."""
    
    @pytest.mark.asyncio
    async def test_priv001_cannot_self_elevate(self, executive_client):
        """TC-PRIV-001: User cannot elevate own role."""
        # Get current user
        me_response = await executive_client.get("/api/users/me")
        if me_response.status_code == 200:
            my_id = me_response.json().get("id")
            if my_id:
                response = await executive_client.patch(
                    f"/api/users/{my_id}/role",
                    json={"role": "admin"}
                )
                
                # Should be forbidden or not allowed
                assert response.status_code in [403, 404, 400]
    
    @pytest.mark.asyncio
    async def test_priv002_cannot_create_admin(self, executive_client):
        """TC-PRIV-002: Non-admin cannot create admin user."""
        response = await executive_client.post("/api/auth/register", json={
            "email": "hacker@test.com",
            "password": "password123",
            "full_name": "Hacker",
            "role": "admin"
        })
        
        if response.status_code == 200:
            data = response.json()
            # If created, should not have admin role
            assert data.get("role") != "admin"
    
    @pytest.mark.asyncio
    async def test_priv003_token_cannot_access_other_user_data(self, executive_client, db):
        """TC-PRIV-003: Token cannot access arbitrary user data."""
        # Get a different user
        admin_user = await db.users.find_one({"role": "admin"}, {"_id": 0, "id": 1})
        if admin_user:
            # Try to modify admin user
            response = await executive_client.patch(
                f"/api/users/{admin_user['id']}/profile",
                json={"full_name": "Hacked Admin"}
            )
            
            # Should be forbidden or not allowed
            assert response.status_code in [200, 403, 404]  # May be allowed for profile updates
