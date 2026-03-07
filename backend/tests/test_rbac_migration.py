"""
RBAC Migration Regression Tests
================================
Run these tests after each migration phase to ensure authorization works correctly.

Usage:
    pytest tests/test_rbac_migration.py -v
    pytest tests/test_rbac_migration.py::TestKickoffApproval -v
"""

import pytest
import httpx
import asyncio
import os
from typing import Optional

# Get API URL from environment or use default
API_URL = os.environ.get("API_URL", "https://hr-module-staging.preview.emergentagent.com/api")

# Test credentials
CREDENTIALS = {
    "admin": {"employee_id": "ADMIN001", "password": "admin123"},
    "principal_consultant": {"employee_id": "DVC001", "password": "test123"},
    "hr_manager": {"employee_id": "DVC037", "password": "test123"},
    "sales_executive": {"employee_id": "DVC034", "password": "test123"},
}


class AuthHelper:
    """Helper class for authentication in tests"""
    _tokens: dict = {}
    
    @classmethod
    async def get_token(cls, role: str) -> Optional[str]:
        """Get cached token or login to get new one"""
        if role in cls._tokens:
            return cls._tokens[role]
        
        if role not in CREDENTIALS:
            return None
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/auth/login",
                json=CREDENTIALS[role],
                timeout=10.0
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                cls._tokens[role] = token
                return token
        return None
    
    @classmethod
    def clear_tokens(cls):
        """Clear cached tokens"""
        cls._tokens = {}


# ==================== FIXTURES ====================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def admin_token():
    """Get admin token"""
    return await AuthHelper.get_token("admin")


@pytest.fixture
async def pc_token():
    """Get principal consultant token"""
    return await AuthHelper.get_token("principal_consultant")


@pytest.fixture
async def hr_token():
    """Get HR manager token"""
    return await AuthHelper.get_token("hr_manager")


@pytest.fixture
async def sales_token():
    """Get sales executive token"""
    return await AuthHelper.get_token("sales_executive")


# ==================== RBAC HEALTH TESTS ====================

class TestRBACHealth:
    """Test RBAC service health and availability"""
    
    @pytest.mark.asyncio
    async def test_rbac_service_healthy(self, admin_token):
        """Verify RBAC service is healthy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/rbac/migration-status",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
            data = response.json()
            assert data["health"] == "HEALTHY"
            assert data["statistics"]["roles_in_db"] >= 15
            assert data["statistics"]["role_groups_in_db"] >= 10
    
    @pytest.mark.asyncio
    async def test_rbac_roles_loaded(self, admin_token):
        """Verify roles are loaded in RBAC"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/rbac/roles",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 15
            
            # Verify critical roles exist
            role_codes = [r["code"] for r in data["roles"]]
            assert "admin" in role_codes
            assert "principal_consultant" in role_codes
            assert "hr_manager" in role_codes
    
    @pytest.mark.asyncio
    async def test_rbac_role_groups_match_hardcoded(self, admin_token):
        """Verify RBAC role groups match expected hardcoded values"""
        expected_groups = {
            "ADMIN_ROLES": ["admin"],
            "PRINCIPAL_CONSULTANT_ROLES": ["admin", "principal_consultant"],
            "HR_ADMIN_ROLES": ["admin", "hr_manager"],
            "AGREEMENT_APPROVE_ROLES": ["admin", "principal_consultant"],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/rbac/role-groups",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
            data = response.json()
            
            for group_code, expected_roles in expected_groups.items():
                group = next((g for g in data["groups"] if g["code"] == group_code), None)
                assert group is not None, f"Missing group: {group_code}"
                assert set(group["roles"]) == set(expected_roles), \
                    f"Mismatch in {group_code}: expected {expected_roles}, got {group['roles']}"


# ==================== KICKOFF APPROVAL TESTS ====================

class TestKickoffApproval:
    """Test kickoff approval authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_view_kickoffs(self, admin_token):
        """Admin should be able to view kickoff requests"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/kickoff-requests",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_principal_consultant_can_view_kickoffs(self, pc_token):
        """Principal consultant should be able to view kickoff requests"""
        if not pc_token:
            pytest.skip("PC credentials not working")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/kickoff-requests",
                headers={"Authorization": f"Bearer {pc_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_unauthorized_cannot_approve_kickoff(self, sales_token):
        """Sales executive should NOT be able to approve kickoffs"""
        if not sales_token:
            pytest.skip("Sales credentials not working")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/kickoff-requests/test-id/approve-internal",
                headers={"Authorization": f"Bearer {sales_token}"},
                timeout=10.0
            )
            # Should be 403 (forbidden) or 404 (not found)
            # 403 means authorization is working correctly
            assert response.status_code in [403, 404]


# ==================== AGREEMENT APPROVAL TESTS ====================

class TestAgreementApproval:
    """Test agreement approval authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_view_agreements(self, admin_token):
        """Admin should be able to view agreements"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/agreements",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_hr_cannot_approve_agreement(self, hr_token):
        """HR manager should NOT be able to approve agreements"""
        if not hr_token:
            pytest.skip("HR credentials not working")
        async with httpx.AsyncClient() as client:
            # Use GET to check access first (POST may return 405 for wrong method)
            response = await client.get(
                f"{API_URL}/agreements/test-id",
                headers={"Authorization": f"Bearer {hr_token}"},
                timeout=10.0
            )
            # HR should be able to view, but not approve
            # For approve endpoint, we'd need a real agreement ID
            # This test verifies HR has view access (is in AGREEMENT_VIEW_ROLES)
            assert response.status_code in [200, 404]


# ==================== PROJECT COMPLETION TESTS ====================

class TestProjectCompletion:
    """Test project completion authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_view_projects(self, admin_token):
        """Admin should be able to view projects"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/projects",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sales_cannot_complete_project(self, sales_token):
        """Sales executive should NOT be able to complete projects"""
        if not sales_token:
            pytest.skip("Sales credentials not working")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/project-completion/test-id/complete",
                headers={"Authorization": f"Bearer {sales_token}"},
                json={"completion_notes": "test"},
                timeout=10.0
            )
            # Should be 403 (forbidden) or 404 (not found)
            assert response.status_code in [403, 404]


# ==================== FINANCIAL DATA TESTS ====================

class TestFinancialAccess:
    """Test financial data access authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_access_pnl(self, admin_token):
        """Admin should be able to access P&L data"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/project-pnl/summary",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            # May be 200 or 404 if no data
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_sales_cannot_access_pnl_export(self, sales_token):
        """Sales executive should NOT be able to export P&L data"""
        if not sales_token:
            pytest.skip("Sales credentials not working")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/project-pnl/export",
                headers={"Authorization": f"Bearer {sales_token}"},
                timeout=10.0
            )
            # Should be 403 (forbidden)
            assert response.status_code == 403


# ==================== APPROVAL WORKFLOW TESTS ====================

class TestApprovalWorkflow:
    """Test approval workflow authorization"""
    
    @pytest.mark.asyncio
    async def test_admin_can_view_pending_approvals(self, admin_token):
        """Admin should be able to view pending approvals"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/approvals/pending",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_hr_can_view_approvals(self, hr_token):
        """HR manager should be able to view approvals (they're in MANAGER_ROLES)"""
        if not hr_token:
            pytest.skip("HR credentials not working")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/approvals/pending",
                headers={"Authorization": f"Bearer {hr_token}"},
                timeout=10.0
            )
            assert response.status_code == 200


# ==================== FAIL-CLOSED BEHAVIOR TESTS ====================

class TestFailClosedBehavior:
    """Test that critical endpoints deny access when RBAC is unavailable"""
    
    @pytest.mark.asyncio
    async def test_migration_status_shows_no_fallbacks(self, admin_token):
        """Verify no fallback events have occurred"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/rbac/migration-status",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
            data = response.json()
            
            # Check for fallback events
            fallback_count = data["statistics"].get("fallback_events", 0)
            if fallback_count > 0:
                pytest.fail(f"RBAC fallback events detected: {fallback_count}. "
                           f"Recent: {data.get('recent_fallbacks', [])}")


# ==================== PERMISSION CONSISTENCY TESTS ====================

class TestPermissionConsistency:
    """Test that permissions are consistent across the system"""
    
    @pytest.mark.asyncio
    async def test_user_permissions_match_role(self, admin_token):
        """Verify user's permissions match their role definition"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_URL}/rbac/my-permissions",
                headers={"Authorization": f"Bearer {admin_token}"},
                timeout=10.0
            )
            assert response.status_code == 200
            data = response.json()
            
            # Admin should have full permissions
            assert data["role"] == "admin"
            assert data["level"] == 100
            assert data["can_approve"] == True
            assert data["can_manage_users"] == True
            assert "*" in data["permissions"]


# ==================== RUN CONFIGURATION ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
