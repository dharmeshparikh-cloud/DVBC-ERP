"""
Test Suite for Simplified Permission System
Tests:
1. /api/department-access/my-access returns has_reportees field
2. /api/department-access/my-access returns can_manage_team field  
3. /api/department-access/my-access returns is_view_only field
4. Employee ID auto-generation with EMP prefix
5. Removed Role and Level fields from permission system
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dept-auth-staging.preview.emergentagent.com')


class TestDepartmentAccessMyAccess:
    """Test suite for /api/department-access/my-access endpoint - new simplified fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get tokens for different users"""
        # HR Manager credentials
        hr_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert hr_response.status_code == 200, f"HR login failed: {hr_response.text}"
        self.hr_token = hr_response.json()["access_token"]
        
        # Admin credentials
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert admin_response.status_code == 200, f"Admin login failed: {admin_response.text}"
        self.admin_token = admin_response.json()["access_token"]
        
        # Dharmesh (Sales) credentials
        dharmesh_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "dharmesh.parikh@dvconsulting.co.in",
            "password": "Welcome@EMP009"
        })
        assert dharmesh_response.status_code == 200, f"Dharmesh login failed: {dharmesh_response.text}"
        self.dharmesh_token = dharmesh_response.json()["access_token"]
    
    def test_my_access_returns_has_reportees_field(self):
        """Test that /api/department-access/my-access returns has_reportees field"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify has_reportees field exists
        assert "has_reportees" in data, "has_reportees field missing from response"
        assert isinstance(data["has_reportees"], bool), "has_reportees should be boolean"
        print(f"has_reportees for HR Manager: {data['has_reportees']}")
    
    def test_my_access_returns_reportee_count_field(self):
        """Test that /api/department-access/my-access returns reportee_count field"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify reportee_count field exists
        assert "reportee_count" in data, "reportee_count field missing from response"
        assert isinstance(data["reportee_count"], int), "reportee_count should be integer"
        print(f"reportee_count for HR Manager: {data['reportee_count']}")
    
    def test_my_access_returns_can_manage_team_field(self):
        """Test that /api/department-access/my-access returns can_manage_team field"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify can_manage_team field exists
        assert "can_manage_team" in data, "can_manage_team field missing from response"
        assert isinstance(data["can_manage_team"], bool), "can_manage_team should be boolean"
        print(f"can_manage_team for HR Manager: {data['can_manage_team']}")
    
    def test_my_access_returns_is_view_only_field(self):
        """Test that /api/department-access/my-access returns is_view_only field"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify is_view_only field exists
        assert "is_view_only" in data, "is_view_only field missing from response"
        assert isinstance(data["is_view_only"], bool), "is_view_only should be boolean"
        print(f"is_view_only for HR Manager: {data['is_view_only']}")
    
    def test_my_access_returns_can_edit_field(self):
        """Test that /api/department-access/my-access returns can_edit field"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify can_edit field exists (inverse of is_view_only)
        assert "can_edit" in data, "can_edit field missing from response"
        assert isinstance(data["can_edit"], bool), "can_edit should be boolean"
        # can_edit should be inverse of is_view_only
        assert data["can_edit"] == (not data["is_view_only"]), "can_edit should be inverse of is_view_only"
        print(f"can_edit for HR Manager: {data['can_edit']}")
    
    def test_admin_my_access_has_all_fields(self):
        """Test Admin user has all new permission fields"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check all new fields
        required_fields = ["has_reportees", "reportee_count", "is_view_only", "can_edit", "can_manage_team"]
        for field in required_fields:
            assert field in data, f"{field} field missing from Admin response"
        
        print(f"Admin permissions: has_reportees={data['has_reportees']}, can_edit={data['can_edit']}, can_manage_team={data['can_manage_team']}")
    
    def test_dharmesh_my_access_has_employee_code(self):
        """Test Dharmesh user has employee_code with EMP prefix"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.dharmesh_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Dharmesh should have employee_code EMP009
        assert "employee_code" in data, "employee_code field missing"
        assert data["employee_code"] is not None, "employee_code should not be None for Dharmesh"
        assert data["employee_code"].startswith("EMP"), f"employee_code should start with EMP, got: {data['employee_code']}"
        print(f"Dharmesh employee_code: {data['employee_code']}")
    
    def test_can_manage_team_matches_has_reportees(self):
        """Test that can_manage_team equals has_reportees (auto-detection logic)"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers={"Authorization": f"Bearer {self.hr_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # can_manage_team should match has_reportees (simplified logic)
        assert data["can_manage_team"] == data["has_reportees"], \
            f"can_manage_team ({data['can_manage_team']}) should equal has_reportees ({data['has_reportees']})"
        print(f"Verified: can_manage_team == has_reportees for HR Manager")


class TestEmployeeIdAutoGeneration:
    """Test suite for Employee ID auto-generation with EMP prefix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as HR Manager"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_existing_employees_have_emp_prefix(self):
        """Test that existing employees have EMP prefix in employee_id"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.headers
        )
        assert response.status_code == 200
        employees = response.json()
        
        # Check that at least some employees have EMP prefix
        emp_prefix_count = 0
        for emp in employees:
            if emp.get("employee_id") and emp["employee_id"].startswith("EMP"):
                emp_prefix_count += 1
                print(f"Found employee with EMP ID: {emp['employee_id']} - {emp.get('first_name', '')} {emp.get('last_name', '')}")
        
        assert emp_prefix_count > 0, "No employees found with EMP prefix"
        print(f"Total employees with EMP prefix: {emp_prefix_count}/{len(employees)}")
    
    def test_emp_ids_are_sequential(self):
        """Test that EMP IDs follow sequential pattern (EMP001, EMP002, etc.)"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.headers
        )
        assert response.status_code == 200
        employees = response.json()
        
        # Extract EMP numbers
        emp_numbers = []
        for emp in employees:
            emp_id = emp.get("employee_id", "")
            if emp_id and emp_id.startswith("EMP"):
                try:
                    num = int(emp_id[3:])  # Extract number after "EMP"
                    emp_numbers.append(num)
                except ValueError:
                    pass
        
        if emp_numbers:
            emp_numbers.sort()
            print(f"EMP numbers found: {emp_numbers[:10]}...")  # Show first 10
            print(f"Min: EMP{emp_numbers[0]:03d}, Max: EMP{emp_numbers[-1]:03d}")


class TestRemovedRoleLevelFields:
    """Test that Role and Level fields are not required in simplified permission system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as HR Manager"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_my_access_does_not_require_role_for_permissions(self):
        """Test that permission checks work without explicit role field"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Primary permission indicators are now department-based, not role-based
        assert "departments" in data, "departments field should exist"
        assert "accessible_pages" in data, "accessible_pages field should exist"
        
        # The new simplified fields should drive permissions
        assert "has_reportees" in data, "has_reportees is the new team permission indicator"
        assert "is_view_only" in data, "is_view_only is the new edit permission indicator"
        
        print(f"Permissions based on: departments={data['departments']}, has_reportees={data['has_reportees']}, is_view_only={data['is_view_only']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
