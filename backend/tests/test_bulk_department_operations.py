"""
Bulk Department Operations Test Suite
Tests for POST /api/department-access/bulk-update endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employee IDs
EMP001_ID = "e184e61e-ef93-431c-86d2-d78954c5512c"  # Rahul Kumar
EMP002_ID = "09de26c6-43f1-43bc-9775-4b4863f1adc6"  # Test Deploy


class TestBulkDepartmentOperations:
    """Bulk Department Access Update Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin auth token"""
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@dvbc.com", "password": "admin123"}
        )
        assert login_resp.status_code == 200, "Admin login failed"
        self.token = login_resp.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
    def test_admin_login(self):
        """Test admin can login"""
        assert self.token is not None
        print("✓ Admin login successful")
        
    def test_bulk_add_department(self):
        """Test bulk adding department to multiple employees"""
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID, EMP002_ID],
                "add_departments": ["Finance"],
                "remove_departments": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2
        assert data["errors"] == []
        print(f"✓ Bulk add department: updated {data['updated_count']} employees")
        
        # Verify Finance was added to EMP001
        verify_resp = requests.get(
            f"{BASE_URL}/api/department-access/employee/{EMP001_ID}",
            headers=self.headers
        )
        assert verify_resp.status_code == 200
        emp_data = verify_resp.json()
        assert "Finance" in emp_data["departments"], f"Finance not in {emp_data['departments']}"
        print(f"✓ EMP001 departments: {emp_data['departments']}")
        
    def test_bulk_remove_department(self):
        """Test bulk removing department from multiple employees"""
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID, EMP002_ID],
                "add_departments": [],
                "remove_departments": ["Finance"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2
        assert data["errors"] == []
        print(f"✓ Bulk remove department: updated {data['updated_count']} employees")
        
        # Verify Finance was removed from EMP001
        verify_resp = requests.get(
            f"{BASE_URL}/api/department-access/employee/{EMP001_ID}",
            headers=self.headers
        )
        assert verify_resp.status_code == 200
        emp_data = verify_resp.json()
        assert "Finance" not in emp_data["departments"]
        print(f"✓ EMP001 departments after removal: {emp_data['departments']}")
        
    def test_bulk_add_and_remove_simultaneously(self):
        """Test adding and removing different departments in same request"""
        # First add HR
        requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID],
                "add_departments": ["HR"],
                "remove_departments": []
            }
        )
        
        # Now add Finance and remove HR in same request
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID],
                "add_departments": ["Finance"],
                "remove_departments": ["HR"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 1
        
        # Verify
        verify_resp = requests.get(
            f"{BASE_URL}/api/department-access/employee/{EMP001_ID}",
            headers=self.headers
        )
        emp_data = verify_resp.json()
        assert "Finance" in emp_data["departments"]
        assert "HR" not in emp_data["departments"]
        print(f"✓ Add Finance and remove HR: {emp_data['departments']}")
        
        # Clean up - remove Finance
        requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID],
                "add_departments": [],
                "remove_departments": ["Finance"]
            }
        )
        
    def test_empty_employee_list(self):
        """Test bulk update with empty employee list"""
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [],
                "add_departments": ["HR"],
                "remove_departments": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert data["errors"] == []
        print("✓ Empty employee list handled correctly")
        
    def test_invalid_employee_id(self):
        """Test bulk update with non-existent employee ID"""
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": ["invalid-uuid-12345"],
                "add_departments": ["HR"],
                "remove_departments": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert len(data["errors"]) == 1
        assert data["errors"][0]["error"] == "Not found"
        print("✓ Invalid employee ID handled correctly")
        
    def test_cannot_remove_all_departments(self):
        """Test that removing all departments fails gracefully"""
        # EMP001 has only Sales
        verify_resp = requests.get(
            f"{BASE_URL}/api/department-access/employee/{EMP001_ID}",
            headers=self.headers
        )
        current_depts = verify_resp.json()["departments"]
        
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID],
                "add_departments": [],
                "remove_departments": current_depts  # Try to remove all
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 0
        assert len(data["errors"]) == 1
        assert "Cannot remove all departments" in data["errors"][0]["error"]
        print("✓ Cannot remove all departments - validated")
        
    def test_invalid_department_silently_ignored(self):
        """Test that invalid department names are silently ignored"""
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=self.headers,
            json={
                "employee_ids": [EMP001_ID],
                "add_departments": ["InvalidDeptXYZ"],  # Not a valid department
                "remove_departments": []
            }
        )
        assert response.status_code == 200
        data = response.json()
        # Should succeed but department won't be added since it's invalid
        assert data["updated_count"] == 1
        
        # Verify InvalidDeptXYZ was not added
        verify_resp = requests.get(
            f"{BASE_URL}/api/department-access/employee/{EMP001_ID}",
            headers=self.headers
        )
        emp_data = verify_resp.json()
        assert "InvalidDeptXYZ" not in emp_data["departments"]
        print(f"✓ Invalid department ignored: {emp_data['departments']}")
        
    def test_non_admin_cannot_bulk_update(self):
        """Test that non-admin users cannot perform bulk updates"""
        # Login as regular user
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "rahul.kumar@dvbc.com", "password": "Welcome@EMP001"}
        )
        if login_resp.status_code != 200:
            pytest.skip("Regular user login not available")
            
        user_token = login_resp.json()["access_token"]
        user_headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/department-access/bulk-update",
            headers=user_headers,
            json={
                "employee_ids": [EMP002_ID],
                "add_departments": ["HR"],
                "remove_departments": []
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-admin user blocked from bulk update")
        
    def test_get_department_stats(self):
        """Test getting department access statistics"""
        response = requests.get(
            f"{BASE_URL}/api/department-access/stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_employees" in data
        assert "by_department" in data
        assert "departments_available" in data
        print(f"✓ Stats: {data['total_employees']} total employees, departments: {list(data['by_department'].keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
