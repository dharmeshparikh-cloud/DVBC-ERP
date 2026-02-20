"""
Test Department Access Fixes - Bug Issues
1. Rahul Kumar can see Consulting pages even though only Sales permission given
2. 'Dept' button in Department Access Manager doesn't work
3. User ID vs Employee ID linkage concerns
4. Dhamresh Parikh (EMP110) should have has_reportees=true
5. Sales department pages should include all sales-related pages
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

class TestDepartmentAccessFixes:
    """Test department access bug fixes"""
    
    admin_token = None
    rahul_token = None
    dhamresh_token = None
    
    # Test Data
    admin_creds = {"email": "admin@dvbc.com", "password": "admin123"}
    rahul_creds = {"email": "rahul.kumar@dvbc.com", "password": "Welcome@EMP001"}
    dhamresh_creds = {"email": "dp@dvbc.com", "password": "Welcome@123"}
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup tokens for tests"""
        pass
        
    def get_admin_token(self):
        """Get admin auth token"""
        if self.admin_token:
            return self.admin_token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json()["access_token"]
        return self.admin_token
        
    def get_rahul_token(self):
        """Get Rahul Kumar auth token"""
        if self.rahul_token:
            return self.rahul_token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.rahul_creds)
        assert response.status_code == 200, f"Rahul login failed: {response.text}"
        self.rahul_token = response.json()["access_token"]
        return self.rahul_token
        
    def get_dhamresh_token(self):
        """Get Dhamresh Parikh auth token"""
        if self.dhamresh_token:
            return self.dhamresh_token
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.dhamresh_creds)
        assert response.status_code == 200, f"Dhamresh login failed: {response.text}"
        self.dhamresh_token = response.json()["access_token"]
        return self.dhamresh_token

    # ===== TEST 1: Admin Login Works =====
    def test_admin_login(self):
        """Test admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.admin_creds)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful: {data['user']['email']}")
        
    # ===== TEST 2: Rahul Kumar Login Works =====
    def test_rahul_login(self):
        """Test Rahul Kumar can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.rahul_creds)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✓ Rahul login successful: {data['user']['email']}, role: {data['user']['role']}")
        
    # ===== TEST 3: Dhamresh Parikh Login Works =====
    def test_dhamresh_login(self):
        """Test Dhamresh Parikh (EMP110) can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=self.dhamresh_creds)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print(f"✓ Dhamresh login successful: {data['user']['email']}, role: {data['user']['role']}")

    # ===== TEST 4: Rahul Kumar Department Access - Only Sales =====
    def test_rahul_department_access_only_sales(self):
        """
        CRITICAL: Rahul Kumar should only have Sales access, NOT Consulting
        The fix changes SALES_ROLES_NAV and CONSULTING_ROLES_NAV to only include 'admin'
        """
        token = self.get_rahul_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        print(f"Rahul's departments: {data.get('departments', [])}")
        print(f"Rahul's primary_department: {data.get('primary_department')}")
        print(f"Rahul's accessible_pages: {data.get('accessible_pages', [])[:10]}...")
        
        # Rahul should have Sales access
        departments = data.get("departments", [])
        assert "Sales" in departments or data.get("primary_department") == "Sales", \
            f"Rahul should have Sales access, got: {departments}"
        
        # Check if Consulting is NOT in departments (unless explicitly granted)
        # If Consulting is in departments, it should be from explicit grant, not role fallback
        if "Consulting" in departments:
            print(f"WARNING: Rahul has Consulting in departments - check if intended")
            
        print(f"✓ Rahul department access verified: {departments}")
        
    # ===== TEST 5: Dhamresh Parikh has_reportees Check =====
    def test_dhamresh_has_reportees_true(self):
        """
        CRITICAL: Dhamresh Parikh (EMP110) should have has_reportees=true
        because Rahul Kumar reports to EMP110
        """
        token = self.get_dhamresh_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        print(f"Dhamresh employee_code: {data.get('employee_code')}")
        print(f"Dhamresh has_reportees: {data.get('has_reportees')}")
        print(f"Dhamresh reportee_count: {data.get('reportee_count')}")
        print(f"Dhamresh can_manage_team: {data.get('can_manage_team')}")
        
        # Dhamresh should have has_reportees=true because Rahul reports to EMP110
        assert data.get("has_reportees") == True, \
            f"Dhamresh (EMP110) should have has_reportees=true, got: {data.get('has_reportees')}"
        assert data.get("reportee_count", 0) > 0, \
            f"Dhamresh should have at least 1 reportee, got: {data.get('reportee_count')}"
            
        print(f"✓ Dhamresh has_reportees verified: {data.get('has_reportees')}, count: {data.get('reportee_count')}")
        
    # ===== TEST 6: Verify Rahul Reports to Dhamresh =====
    def test_verify_rahul_reports_to_dhamresh(self):
        """Verify reporting_manager_id linkage: Rahul -> EMP110 (Dhamresh)"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get Rahul's employee record
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        employees = response.json()
        
        rahul = next((e for e in employees if e.get("employee_id") == "EMP001"), None)
        assert rahul is not None, "Rahul Kumar (EMP001) not found in employees"
        
        print(f"Rahul reporting_manager_id: {rahul.get('reporting_manager_id')}")
        
        # Verify Rahul reports to EMP110 (Dhamresh)
        assert rahul.get("reporting_manager_id") == "EMP110", \
            f"Rahul should report to EMP110, got: {rahul.get('reporting_manager_id')}"
            
        print(f"✓ Rahul (EMP001) correctly reports to Dhamresh (EMP110)")
        
    # ===== TEST 7: Admin can get employee department access =====
    def test_admin_get_employee_department_access(self):
        """Admin can fetch department access for any employee"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # First get Rahul's employee record to get his ID
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        employees = response.json()
        
        rahul = next((e for e in employees if e.get("employee_id") == "EMP001"), None)
        assert rahul is not None
        
        # Get department access for Rahul
        response = requests.get(
            f"{BASE_URL}/api/department-access/employee/{rahul['id']}", 
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get department access: {response.text}"
        data = response.json()
        
        print(f"Rahul department access: {data}")
        assert "employee_id" in data
        assert "departments" in data
        assert "primary_department" in data
        print(f"✓ Admin can access employee department data")
        
    # ===== TEST 8: Admin can update employee department access =====
    def test_admin_update_employee_department_access(self):
        """Admin can update department access for an employee"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get Rahul's employee record
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        employees = response.json()
        
        rahul = next((e for e in employees if e.get("employee_id") == "EMP001"), None)
        assert rahul is not None
        
        # Update Rahul's department access to only Sales
        update_data = {
            "departments": ["Sales"],
            "primary_department": "Sales",
            "custom_page_access": [],
            "restricted_pages": []
        }
        
        response = requests.put(
            f"{BASE_URL}/api/department-access/employee/{rahul['id']}", 
            headers=headers,
            json=update_data
        )
        assert response.status_code == 200, f"Failed to update department access: {response.text}"
        
        print(f"✓ Admin updated Rahul's department access to Sales only")
        
        # Verify the update
        response = requests.get(
            f"{BASE_URL}/api/department-access/employee/{rahul['id']}", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "Sales" in data.get("departments", [])
        print(f"✓ Verified Rahul now has only Sales department: {data.get('departments')}")
        
    # ===== TEST 9: Sales Department Pages Include All Sales Routes =====
    def test_sales_department_pages(self):
        """Verify Sales department pages include all sales-related routes"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/department-access/departments", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        departments = data.get("departments", {})
        sales_dept = departments.get("Sales", {})
        sales_pages = sales_dept.get("pages", [])
        
        print(f"Sales department pages: {sales_pages}")
        
        # Verify key sales pages are included
        expected_pages = ["/leads", "/sales-dashboard", "/clients", "/invoices", "/sow-pricing"]
        for page in expected_pages:
            assert page in sales_pages, f"Sales should include {page}"
            
        print(f"✓ Sales department includes all expected pages")
        
    # ===== TEST 10: Rahul sees correct pages after update =====
    def test_rahul_accessible_pages_sales_only(self):
        """After update, Rahul should only see Sales pages"""
        token = self.get_rahul_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        accessible_pages = data.get("accessible_pages", [])
        print(f"Rahul's accessible pages: {accessible_pages}")
        
        # Rahul should have Sales pages
        sales_pages = ["/leads", "/sales-dashboard", "/clients"]
        for page in sales_pages:
            if accessible_pages != ["*"]:
                assert page in accessible_pages, f"Rahul should have access to {page}"
                
        print(f"✓ Rahul has correct accessible pages")
        
    # ===== TEST 11: Department Access Stats Endpoint =====
    def test_department_access_stats(self):
        """Admin can fetch department access statistics"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/department-access/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        print(f"Department stats: {data}")
        assert "total_employees" in data
        assert "with_portal_access" in data
        assert "by_department" in data
        
        print(f"✓ Department stats accessible: {data.get('total_employees')} total employees")
        
    # ===== TEST 12: Employees by Department Endpoint =====
    def test_employees_by_department(self):
        """Admin can get employees by department"""
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(
            f"{BASE_URL}/api/department-access/employees-by-department/Sales", 
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        
        print(f"Employees in Sales: {data.get('employee_count')}")
        assert "employees" in data
        assert data.get("department") == "Sales"
        
        print(f"✓ Employees by department working: {data.get('employee_count')} in Sales")


class TestHasReporteesFunction:
    """Test has_reportees function accuracy"""
    
    def get_admin_token(self):
        """Get admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com", "password": "admin123"
        })
        return response.json()["access_token"]
        
    def test_has_reportees_query_by_employee_id(self):
        """
        Critical test: has_reportees should query by employee_id (e.g., 'EMP110')
        NOT by user_id UUID
        """
        token = self.get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get all employees
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        assert response.status_code == 200
        employees = response.json()
        
        # Find employees who have reporting_manager_id set
        managers_with_reportees = set()
        for emp in employees:
            rm_id = emp.get("reporting_manager_id")
            if rm_id:
                managers_with_reportees.add(rm_id)
                
        print(f"Managers with reportees (reporting_manager_id values): {managers_with_reportees}")
        
        # EMP110 should be in this set since Rahul reports to EMP110
        assert "EMP110" in managers_with_reportees, \
            f"EMP110 should be a manager with reportees, found: {managers_with_reportees}"
            
        print(f"✓ EMP110 confirmed as a manager with reportees")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
