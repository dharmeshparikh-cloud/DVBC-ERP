"""
Test Employee Scorecards and Permission Fixes - Iteration 59
Tests:
1. Employee stats/summary endpoint returns correct fields (with_portal_access, without_portal_access)
2. /api/department-access/my-access returns simplified permission fields
3. Employees list endpoint works correctly
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestEmployeeScorecardsAndPermissions:
    """Test employee scorecards and permission endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dvbc.com", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_employees_stats_summary_returns_correct_fields(self):
        """Test /api/employees/stats/summary returns portal access counts"""
        response = requests.get(
            f"{BASE_URL}/api/employees/stats/summary",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Stats endpoint failed: {response.text}"
        data = response.json()
        
        # Check required fields exist
        assert "total" in data, "Missing 'total' field"
        assert "active" in data, "Missing 'active' field"
        assert "with_portal_access" in data, "Missing 'with_portal_access' field - scorecard fix"
        assert "without_portal_access" in data, "Missing 'without_portal_access' field - scorecard fix"
        assert "by_department" in data, "Missing 'by_department' field"
        
        # Verify values are numeric
        assert isinstance(data["total"], int), "total should be an integer"
        assert isinstance(data["with_portal_access"], int), "with_portal_access should be an integer"
        assert isinstance(data["without_portal_access"], int), "without_portal_access should be an integer"
        
        # Verify math adds up (active = with_access + without_access)
        assert data["active"] == data["with_portal_access"] + data["without_portal_access"], \
            f"Access counts don't add up: active={data['active']}, with={data['with_portal_access']}, without={data['without_portal_access']}"
        
        print(f"✅ Stats: total={data['total']}, with_access={data['with_portal_access']}, without_access={data['without_portal_access']}")
    
    def test_my_access_returns_simplified_permissions(self):
        """Test /api/department-access/my-access returns new simplified fields"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/my-access",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"My-access endpoint failed: {response.text}"
        data = response.json()
        
        # Check new simplified permission fields
        required_fields = [
            "user_id",
            "full_name",
            "departments",
            "primary_department",
            "accessible_pages",
            # NEW SIMPLIFIED FIELDS
            "has_reportees",
            "reportee_count",
            "is_view_only",
            "can_edit",
            "can_manage_team"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify types
        assert isinstance(data["has_reportees"], bool), "has_reportees should be boolean"
        assert isinstance(data["reportee_count"], int), "reportee_count should be integer"
        assert isinstance(data["is_view_only"], bool), "is_view_only should be boolean"
        assert isinstance(data["can_edit"], bool), "can_edit should be boolean"
        assert isinstance(data["can_manage_team"], bool), "can_manage_team should be boolean"
        
        # Verify logical consistency
        assert data["can_edit"] == (not data["is_view_only"]), "can_edit should be inverse of is_view_only"
        assert data["can_manage_team"] == data["has_reportees"], "can_manage_team should equal has_reportees"
        
        print(f"✅ My-access: has_reportees={data['has_reportees']}, can_edit={data['can_edit']}, departments={data['departments']}")
    
    def test_employees_list_endpoint(self):
        """Test /api/employees returns list of employees"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Employees list failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Employees should return a list"
        assert len(data) > 0, "Should have at least one employee"
        
        # Check first employee has expected fields
        emp = data[0]
        expected_fields = ["id", "first_name", "last_name", "email", "employee_id"]
        for field in expected_fields:
            assert field in emp, f"Employee missing field: {field}"
        
        print(f"✅ Employees list: {len(data)} employees returned")
    
    def test_departments_list_endpoint(self):
        """Test /api/employees/departments/list returns unique departments"""
        response = requests.get(
            f"{BASE_URL}/api/employees/departments/list",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Departments list failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Departments should return a list"
        # Can be empty if no departments set
        
        print(f"✅ Departments list: {len(data)} departments - {data}")
    
    def test_department_access_departments_endpoint(self):
        """Test /api/department-access/departments returns config"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/departments",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Department access config failed: {response.text}"
        data = response.json()
        
        assert "departments" in data, "Missing departments config"
        assert "universal_pages" in data, "Missing universal_pages config"
        
        # Check default departments exist
        depts = data["departments"]
        expected_depts = ["Sales", "HR", "Consulting", "Finance", "Admin"]
        for dept in expected_depts:
            assert dept in depts, f"Missing default department: {dept}"
        
        print(f"✅ Department config: {len(depts)} departments configured")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
