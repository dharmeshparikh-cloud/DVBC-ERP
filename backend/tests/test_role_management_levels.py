"""
Test Suite for Role Management - Employee Levels and Approval Workflow
Tests for:
- GET /api/role-management/levels - Returns 3 levels (executive, manager, leader)
- GET /api/role-management/level-permissions - Returns permission configs for all levels  
- PUT /api/role-management/level-permissions - Admin can update level permissions
- POST /api/role-management/role-requests - HR can create role creation request
- GET /api/role-management/role-requests/pending - Admin sees pending requests
- POST /api/role-management/role-requests/{id}/approve - Admin can approve/reject
- POST /api/role-management/assignment-requests - HR can submit role assignment
- GET /api/role-management/stats - Returns statistics
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
HR_EMAIL = "hr.manager@dvbc.com"
HR_PASSWORD = "hr123"


class TestSetup:
    """Fixtures for authentication"""
    
    @staticmethod
    def get_admin_token():
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @staticmethod
    def get_hr_token():
        """Get HR manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200, f"HR login failed: {response.text}"
        return response.json()["access_token"]


# ============== Employee Levels Tests ==============

class TestEmployeeLevels:
    """Tests for GET /api/role-management/levels"""
    
    def test_get_levels_returns_three_levels(self):
        """Verify endpoint returns exactly 3 levels: executive, manager, leader"""
        token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/levels",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "levels" in data
        levels = data["levels"]
        assert len(levels) == 3
        
        # Verify level IDs
        level_ids = [l["id"] for l in levels]
        assert "executive" in level_ids
        assert "manager" in level_ids
        assert "leader" in level_ids
        
    def test_levels_have_required_fields(self):
        """Verify each level has id, name, description"""
        token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/levels",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        levels = response.json()["levels"]
        
        for level in levels:
            assert "id" in level
            assert "name" in level
            assert "description" in level
            assert isinstance(level["id"], str)
            assert isinstance(level["name"], str)
            
    def test_levels_requires_authentication(self):
        """Verify endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/role-management/levels")
        assert response.status_code == 401


# ============== Level Permissions Tests ==============

class TestLevelPermissions:
    """Tests for GET/PUT /api/role-management/level-permissions"""
    
    def test_get_level_permissions_returns_all_levels(self):
        """Verify endpoint returns permissions for all 3 levels"""
        token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "executive" in data
        assert "manager" in data
        assert "leader" in data
        
    def test_permissions_have_all_keys(self):
        """Verify permission objects have expected boolean keys"""
        token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        expected_keys = [
            "can_view_own_data", "can_edit_own_profile", "can_submit_requests",
            "can_view_team_data", "can_approve_requests", "can_manage_team",
            "can_access_reports", "can_access_financials", "can_create_projects",
            "can_assign_tasks"
        ]
        
        for level in ["executive", "manager", "leader"]:
            for key in expected_keys:
                assert key in data[level], f"Missing {key} in {level} permissions"
                assert isinstance(data[level][key], bool)
                
    def test_executive_has_basic_permissions(self):
        """Verify executive level has basic (limited) permissions"""
        token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        exec_perms = response.json()["executive"]
        
        # Executive should have basic access only
        assert exec_perms["can_view_own_data"] == True
        assert exec_perms["can_edit_own_profile"] == True
        assert exec_perms["can_view_team_data"] == False
        assert exec_perms["can_access_financials"] == False
        
    def test_leader_has_full_permissions(self):
        """Verify leader level has full permissions"""
        token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        leader_perms = response.json()["leader"]
        
        # Leader should have all access
        assert leader_perms["can_view_own_data"] == True
        assert leader_perms["can_view_team_data"] == True
        assert leader_perms["can_access_financials"] == True
        assert leader_perms["can_manage_team"] == True
        
    def test_admin_can_update_level_permissions(self):
        """Admin should be able to update level permissions"""
        token = TestSetup.get_admin_token()
        
        # Get current permissions
        get_response = requests.get(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        original_perms = get_response.json()["executive"]
        
        # Update executive permissions
        new_perms = original_perms.copy()
        new_perms["can_access_reports"] = not original_perms["can_access_reports"]
        
        response = requests.put(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "level": "executive",
                "permissions": new_perms
            }
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verify update
        verify_response = requests.get(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert verify_response.json()["executive"]["can_access_reports"] == new_perms["can_access_reports"]
        
        # Restore original
        restore_response = requests.put(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "level": "executive",
                "permissions": original_perms
            }
        )
        assert restore_response.status_code == 200
        
    def test_hr_cannot_update_permissions(self):
        """HR manager should not be able to update level permissions (admin only)"""
        token = TestSetup.get_hr_token()
        
        response = requests.put(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "level": "executive",
                "permissions": {"can_view_own_data": True}
            }
        )
        
        assert response.status_code == 403
        
    def test_invalid_level_returns_error(self):
        """Updating invalid level should return error"""
        token = TestSetup.get_admin_token()
        
        response = requests.put(
            f"{BASE_URL}/api/role-management/level-permissions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "level": "invalid_level",
                "permissions": {"can_view_own_data": True}
            }
        )
        
        assert response.status_code == 400


# ============== Role Requests Tests ==============

class TestRoleRequests:
    """Tests for role creation request workflow"""
    
    def test_hr_can_create_role_request(self):
        """HR manager can submit a role creation request"""
        token = TestSetup.get_hr_token()
        
        role_id = f"test_role_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "role_id": role_id,
                "role_name": "Test Custom Role",
                "role_description": "A test role for testing",
                "reason": "Testing role creation workflow"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "request_id" in data
        
        return data["request_id"]
        
    def test_admin_sees_pending_requests(self):
        """Admin should see pending role requests"""
        # First create a request as HR
        hr_token = TestSetup.get_hr_token()
        role_id = f"test_role_pending_{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "role_id": role_id,
                "role_name": "Pending Test Role",
                "role_description": "For pending test",
                "reason": "Testing pending visibility"
            }
        )
        assert create_response.status_code == 200
        request_id = create_response.json()["request_id"]
        
        # Now check as admin
        admin_token = TestSetup.get_admin_token()
        response = requests.get(
            f"{BASE_URL}/api/role-management/role-requests/pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        pending_list = response.json()
        assert isinstance(pending_list, list)
        
        # Find our request
        found = any(r["id"] == request_id for r in pending_list)
        assert found, "Created request not found in pending list"
        
    def test_admin_can_approve_request(self):
        """Admin can approve a role request"""
        # Create request as HR
        hr_token = TestSetup.get_hr_token()
        role_id = f"test_approve_{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "role_id": role_id,
                "role_name": "Approve Test Role",
                "role_description": "For approval test"
            }
        )
        request_id = create_response.json()["request_id"]
        
        # Approve as admin
        admin_token = TestSetup.get_admin_token()
        response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests/{request_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={
                "approved": True,
                "comments": "Approved for testing"
            }
        )
        
        assert response.status_code == 200
        assert "approved" in response.json()["message"].lower()
        
    def test_admin_can_reject_request(self):
        """Admin can reject a role request"""
        # Create request as HR
        hr_token = TestSetup.get_hr_token()
        role_id = f"test_reject_{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "role_id": role_id,
                "role_name": "Reject Test Role",
                "role_description": "For rejection test"
            }
        )
        request_id = create_response.json()["request_id"]
        
        # Reject as admin
        admin_token = TestSetup.get_admin_token()
        response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests/{request_id}/approve",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={
                "approved": False,
                "comments": "Rejected for testing"
            }
        )
        
        assert response.status_code == 200
        assert "rejected" in response.json()["message"].lower()
        
    def test_hr_cannot_approve_requests(self):
        """HR manager should not be able to approve/reject"""
        hr_token = TestSetup.get_hr_token()
        
        response = requests.post(
            f"{BASE_URL}/api/role-management/role-requests/fake-id/approve",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={"approved": True}
        )
        
        assert response.status_code == 403
        
    def test_duplicate_role_request_fails(self):
        """Cannot create duplicate pending request for same role_id"""
        hr_token = TestSetup.get_hr_token()
        role_id = f"test_dup_{uuid.uuid4().hex[:8]}"
        
        # First request
        response1 = requests.post(
            f"{BASE_URL}/api/role-management/role-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "role_id": role_id,
                "role_name": "First Request"
            }
        )
        assert response1.status_code == 200
        
        # Duplicate request
        response2 = requests.post(
            f"{BASE_URL}/api/role-management/role-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "role_id": role_id,
                "role_name": "Duplicate Request"
            }
        )
        assert response2.status_code == 400


# ============== Assignment Requests Tests ==============

class TestAssignmentRequests:
    """Tests for role assignment request workflow"""
    
    def test_admin_cannot_create_assignment_request(self):
        """Admin (non-HR) cannot create assignment requests - only HR can"""
        admin_token = TestSetup.get_admin_token()
        
        response = requests.post(
            f"{BASE_URL}/api/role-management/assignment-requests",
            headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            json={
                "employee_id": "fake-employee",
                "role_id": "fake-role",
                "level": "executive"
            }
        )
        
        # Admin role is not in hr_manager/hr_executive, so should be 403
        assert response.status_code == 403
        
    def test_assignment_request_validates_employee(self):
        """Assignment request should validate employee exists"""
        hr_token = TestSetup.get_hr_token()
        
        response = requests.post(
            f"{BASE_URL}/api/role-management/assignment-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "employee_id": "non-existent-employee-id",
                "role_id": "consultant",
                "level": "executive"
            }
        )
        
        assert response.status_code == 404
        assert "employee" in response.json()["detail"].lower()
        
    def test_assignment_request_validates_level(self):
        """Assignment request should validate level is valid"""
        hr_token = TestSetup.get_hr_token()
        
        response = requests.post(
            f"{BASE_URL}/api/role-management/assignment-requests",
            headers={"Authorization": f"Bearer {hr_token}", "Content-Type": "application/json"},
            json={
                "employee_id": "some-id",
                "role_id": "consultant",
                "level": "invalid_level"  # Not executive/manager/leader
            }
        )
        
        # Should fail validation (400 or 404 for employee first)
        assert response.status_code in [400, 404, 422]


# ============== Stats Tests ==============

class TestRoleManagementStats:
    """Tests for GET /api/role-management/stats"""
    
    def test_admin_can_get_stats(self):
        """Admin can access stats endpoint"""
        token = TestSetup.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/role-management/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "requests" in data
        assert "employees_by_level" in data
        assert "roles" in data
        
    def test_stats_has_request_counts(self):
        """Stats should have pending/approved/rejected counts"""
        token = TestSetup.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/role-management/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        requests_data = response.json()["requests"]
        
        assert "pending" in requests_data
        assert "approved" in requests_data
        assert "rejected" in requests_data
        assert isinstance(requests_data["pending"], int)
        
    def test_stats_has_level_counts(self):
        """Stats should have employee counts by level"""
        token = TestSetup.get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/role-management/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        level_data = response.json()["employees_by_level"]
        
        assert "executive" in level_data
        assert "manager" in level_data
        assert "leader" in level_data
        assert "unassigned" in level_data
        
    def test_hr_can_access_stats(self):
        """HR manager can also access stats"""
        token = TestSetup.get_hr_token()
        
        response = requests.get(
            f"{BASE_URL}/api/role-management/stats",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
    def test_stats_requires_auth(self):
        """Stats endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/role-management/stats")
        assert response.status_code == 401
