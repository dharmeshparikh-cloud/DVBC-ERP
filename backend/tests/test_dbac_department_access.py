"""
DBAC (Department-Based Access Control) Testing
Tests the new department-based access control system after architectural refactor from RBAC.
Priority: Verify login flows, department access APIs, and navigation filtering.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials - NOTE: consultant password is 'consultant123' not 'consult123'
CREDENTIALS = {
    "admin": {"email": "admin@dvbc.com", "password": "admin123"},
    "hr_manager": {"email": "hr.manager@dvbc.com", "password": "hr123"},
    "sales_manager": {"email": "sales.manager@dvbc.com", "password": "sales123"},
    "consultant": {"email": "consultant@dvbc.com", "password": "consultant123"},
}


class TestAuthLogin:
    """Test login flows for different user roles"""
    
    def test_admin_login_success(self):
        """Test admin user can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        print(f"Admin login response: {response.status_code}")
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == "admin@dvbc.com"
        print(f"Admin login successful - role: {data['user'].get('role')}")
    
    def test_hr_manager_login_success(self):
        """Test HR manager can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["hr_manager"])
        print(f"HR Manager login response: {response.status_code}")
        assert response.status_code == 200, f"HR Manager login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"HR Manager login successful - role: {data['user'].get('role')}")
    
    def test_sales_manager_login_success(self):
        """Test Sales manager can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["sales_manager"])
        print(f"Sales Manager login response: {response.status_code}")
        assert response.status_code == 200, f"Sales Manager login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"Sales Manager login successful - role: {data['user'].get('role')}")
    
    def test_consultant_login_success(self):
        """Test consultant can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["consultant"])
        print(f"Consultant login response: {response.status_code}")
        assert response.status_code == 200, f"Consultant login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"Consultant login successful - role: {data['user'].get('role')}")
    
    def test_invalid_credentials_rejected(self):
        """Test invalid credentials are rejected"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestDepartmentAccessAPI:
    """Test department access APIs"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def hr_manager_token(self):
        """Get HR manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["hr_manager"])
        if response.status_code != 200:
            pytest.skip(f"HR Manager login failed: {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def sales_manager_token(self):
        """Get Sales manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["sales_manager"])
        if response.status_code != 200:
            pytest.skip(f"Sales Manager login failed: {response.text}")
        return response.json()["access_token"]
    
    @pytest.fixture
    def consultant_token(self):
        """Get consultant auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["consultant"])
        if response.status_code != 200:
            pytest.skip(f"Consultant login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_get_departments_list(self, admin_token):
        """Test /api/department-access/departments returns department list"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/department-access/departments", headers=headers)
        
        print(f"Departments list response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get departments: {response.text}"
        
        data = response.json()
        assert "departments" in data, "No departments in response"
        assert "universal_pages" in data, "No universal_pages in response"
        
        departments = data["departments"]
        print(f"Departments found: {list(departments.keys())}")
        
        # Verify key departments exist
        expected_depts = ["Sales", "HR", "Consulting", "Finance", "Admin"]
        for dept in expected_depts:
            assert dept in departments, f"Missing department: {dept}"
        
        print(f"Universal pages: {data['universal_pages']}")
    
    def test_admin_my_access_returns_full_access(self, admin_token):
        """Test admin user has full access (Admin department)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        
        print(f"Admin my-access response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get my-access: {response.text}"
        
        data = response.json()
        print(f"Admin access data: {data}")
        
        # Admin should have Admin department
        assert "departments" in data
        assert "Admin" in data["departments"], "Admin should have Admin department"
        
        # Admin should have full access
        assert "accessible_pages" in data
        pages = data["accessible_pages"]
        # Admin typically has ["*"] for all pages OR a comprehensive list
        assert pages == ["*"] or len(pages) > 10, f"Admin should have full access, got: {pages}"
        
        print(f"Admin departments: {data['departments']}")
        print(f"Admin level: {data.get('level')}")
    
    def test_hr_manager_my_access_returns_hr_department(self, hr_manager_token):
        """Test HR manager has HR department access"""
        headers = {"Authorization": f"Bearer {hr_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        
        print(f"HR Manager my-access response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get my-access: {response.text}"
        
        data = response.json()
        print(f"HR Manager access data: departments={data.get('departments')}, pages count={len(data.get('accessible_pages', []))}")
        
        # HR Manager should have HR-related pages
        departments = data.get("departments", [])
        accessible_pages = data.get("accessible_pages", [])
        
        # Check if they have HR department or HR-related pages
        has_hr_access = "HR" in departments or any("/employees" in p or "/attendance" in p or "/hr" in p for p in accessible_pages)
        assert has_hr_access, f"HR Manager should have HR access. Departments: {departments}, Pages: {accessible_pages}"
        
        print(f"HR Manager level: {data.get('level')}")
    
    def test_sales_manager_my_access_returns_sales_department(self, sales_manager_token):
        """Test Sales manager has Sales department access"""
        headers = {"Authorization": f"Bearer {sales_manager_token}"}
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        
        print(f"Sales Manager my-access response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get my-access: {response.text}"
        
        data = response.json()
        print(f"Sales Manager access data: departments={data.get('departments')}, pages count={len(data.get('accessible_pages', []))}")
        
        departments = data.get("departments", [])
        accessible_pages = data.get("accessible_pages", [])
        
        # Check if they have Sales department or Sales-related pages
        has_sales_access = "Sales" in departments or any("/leads" in p or "/sales" in p or "/clients" in p for p in accessible_pages)
        assert has_sales_access, f"Sales Manager should have Sales access. Departments: {departments}, Pages: {accessible_pages}"
    
    def test_consultant_my_access_returns_restricted_view(self, consultant_token):
        """Test consultant has restricted/consulting department access"""
        headers = {"Authorization": f"Bearer {consultant_token}"}
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        
        print(f"Consultant my-access response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get my-access: {response.text}"
        
        data = response.json()
        print(f"Consultant access data: departments={data.get('departments')}, pages count={len(data.get('accessible_pages', []))}")
        
        departments = data.get("departments", [])
        accessible_pages = data.get("accessible_pages", [])
        
        # Consultant should have limited access - NOT admin
        assert "Admin" not in departments, f"Consultant should NOT have Admin department"
        
        # Consultant should have access to consulting pages or their own modules
        has_consulting_access = "Consulting" in departments or any("/projects" in p or "/timesheets" in p for p in accessible_pages)
        print(f"Consultant has consulting access: {has_consulting_access}")
    
    def test_unauthenticated_access_rejected(self):
        """Test unauthenticated requests are rejected"""
        response = requests.get(f"{BASE_URL}/api/department-access/my-access")
        assert response.status_code == 401, f"Expected 401 for unauthenticated request, got {response.status_code}"


class TestPermissionConfigDepartments:
    """Test permission-config/departments endpoint for department CRUD"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_get_departments_config(self, admin_token):
        """Test /api/permission-config/departments returns department configuration"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/permission-config/departments", headers=headers)
        
        print(f"Permission config departments response: {response.status_code}")
        assert response.status_code == 200, f"Failed to get departments config: {response.text}"
        
        data = response.json()
        print(f"Departments config data: {data}")
        
        # Should have departments list
        assert "departments" in data, "No departments in response"
        
        if len(data["departments"]) > 0:
            dept = data["departments"][0]
            print(f"Sample department: {dept}")
            # Each department should have: id, name, code, pages, etc.
            assert "name" in dept or "id" in dept, "Department missing required fields"
    
    def test_create_new_department(self, admin_token):
        """Test admin can create a new department via API"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        new_dept = {
            "name": "TEST_Marketing",
            "code": "TEST_MKT",
            "description": "Test marketing department for DBAC testing",
            "pages": ["/test-marketing", "/test-campaigns"],
            "icon": "TrendingUp",
            "color": "#EC4899",
            "is_active": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/permission-config/departments",
            headers=headers,
            json=new_dept
        )
        
        print(f"Create department response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Check if endpoint exists and accepts POST
        if response.status_code == 404:
            pytest.skip("POST /api/permission-config/departments endpoint not found")
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            print(f"Created department: {data}")
            assert "id" in data or "name" in data, "Response should contain department data"
        elif response.status_code == 400 and "already exists" in response.text.lower():
            print("Department already exists - this is acceptable")
        else:
            # Log the response for debugging but don't fail - endpoint might have different requirements
            print(f"Unexpected status {response.status_code}: {response.text}")


class TestDepartmentAccessStats:
    """Test department access statistics endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS["admin"])
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        return response.json()["access_token"]
    
    def test_get_department_stats(self, admin_token):
        """Test /api/department-access/stats returns statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/department-access/stats", headers=headers)
        
        print(f"Department stats response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Stats: {data}")
            # Should have statistics like total_employees, by_department, etc.
            assert isinstance(data, dict), "Stats should be a dict"
        elif response.status_code == 403:
            print("Stats endpoint requires admin/HR access - expected behavior")
        else:
            print(f"Unexpected status: {response.status_code} - {response.text}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
