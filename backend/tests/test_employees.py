"""
Backend API tests for Employees module
Tests: CRUD operations, link/unlink user, sync from users, org chart, stats
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "admin123"}
HR_MANAGER_CREDS = {"email": "hr_manager@company.com", "password": "manager123"}

# Track test data for cleanup
TEST_EMPLOYEE_IDS = []


class TestEmployeesSetup:
    """Setup: Get auth tokens"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if response.status_code != 200:
            pytest.skip("Admin login failed - skipping employee tests")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Admin auth headers"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }


class TestEmployeeAPIs(TestEmployeesSetup):
    """Employee CRUD and related API tests"""
    
    def test_get_employees_list(self, admin_headers):
        """Test GET /api/employees - List all employees"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Found {len(data)} employees")
    
    def test_get_employee_stats(self, admin_headers):
        """Test GET /api/employees/stats/summary - Get employee statistics"""
        response = requests.get(f"{BASE_URL}/api/employees/stats/summary", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_employees" in data, "Should have total_employees field"
        assert "with_user_access" in data, "Should have with_user_access field"
        assert "without_user_access" in data, "Should have without_user_access field"
        assert "by_department" in data, "Should have by_department field"
        print(f"✓ Stats: {data['total_employees']} total, {data['with_user_access']} with access, {data['without_user_access']} without")
    
    def test_get_departments_list(self, admin_headers):
        """Test GET /api/employees/departments/list - Get all departments"""
        response = requests.get(f"{BASE_URL}/api/employees/departments/list", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Found {len(data)} departments: {data}")
    
    def test_get_org_chart(self, admin_headers):
        """Test GET /api/employees/org-chart/hierarchy - Get org chart"""
        response = requests.get(f"{BASE_URL}/api/employees/org-chart/hierarchy", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Org chart has {len(data)} root nodes")
    
    def test_create_employee(self, admin_headers):
        """Test POST /api/employees - Create new employee"""
        emp_id = f"TEST{str(uuid.uuid4())[:8].upper()}"
        test_email = f"test_employee_{uuid.uuid4().hex[:8]}@test.com"
        
        payload = {
            "employee_id": emp_id,
            "first_name": "TEST",
            "last_name": "Employee",
            "email": test_email,
            "phone": "+91 9876543210",
            "department": "Testing",
            "designation": "Test Engineer",
            "employment_type": "full_time",
            "joining_date": "2024-01-15T00:00:00Z"
        }
        
        response = requests.post(f"{BASE_URL}/api/employees", json=payload, headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employee_id" in data, "Response should contain employee_id"
        assert data.get("emp_id") == emp_id, f"Employee ID should match: expected {emp_id}"
        
        TEST_EMPLOYEE_IDS.append(data['employee_id'])  # Internal ID for cleanup
        print(f"✓ Created employee: {emp_id}")
        return data['employee_id']
    
    def test_get_employee_by_id(self, admin_headers):
        """Test GET /api/employees/{id} - Get employee details"""
        # First get an employee
        list_response = requests.get(f"{BASE_URL}/api/employees", headers=admin_headers)
        employees = list_response.json()
        
        if not employees:
            pytest.skip("No employees to test")
        
        emp = employees[0]
        response = requests.get(f"{BASE_URL}/api/employees/{emp['id']}", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data['id'] == emp['id'], "Employee ID should match"
        assert 'first_name' in data, "Should have first_name"
        assert 'last_name' in data, "Should have last_name"
        assert 'email' in data, "Should have email"
        print(f"✓ Retrieved employee: {data['first_name']} {data['last_name']}")
    
    def test_update_employee(self, admin_headers):
        """Test PATCH /api/employees/{id} - Update employee"""
        # Create a test employee first
        emp_id = f"TESTUPD{str(uuid.uuid4())[:6].upper()}"
        test_email = f"test_update_{uuid.uuid4().hex[:8]}@test.com"
        
        create_payload = {
            "employee_id": emp_id,
            "first_name": "Update",
            "last_name": "Test",
            "email": test_email,
            "department": "QA",
            "employment_type": "full_time"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/employees", json=create_payload, headers=admin_headers)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        
        internal_id = create_response.json()['employee_id']
        TEST_EMPLOYEE_IDS.append(internal_id)
        
        # Now update
        update_payload = {
            "designation": "Senior QA Engineer",
            "department": "Quality Assurance",
            "salary": 1500000
        }
        
        response = requests.patch(f"{BASE_URL}/api/employees/{internal_id}", json=update_payload, headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update
        get_response = requests.get(f"{BASE_URL}/api/employees/{internal_id}", headers=admin_headers)
        updated_emp = get_response.json()
        assert updated_emp['designation'] == "Senior QA Engineer", "Designation should be updated"
        assert updated_emp['department'] == "Quality Assurance", "Department should be updated"
        print(f"✓ Updated employee: {updated_emp['first_name']} - designation and department changed")
    
    def test_sync_from_users(self, admin_headers):
        """Test POST /api/employees/sync-from-users - Sync employees from users"""
        response = requests.post(f"{BASE_URL}/api/employees/sync-from-users", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "created" in data, "Response should have 'created' count"
        assert "skipped" in data, "Response should have 'skipped' count"
        print(f"✓ Sync completed: {data['created']} created, {data['skipped']} skipped")
    
    def test_link_unlink_user(self, admin_headers):
        """Test link and unlink user from employee"""
        # Create employee without user link
        emp_id = f"TESTLINK{str(uuid.uuid4())[:5].upper()}"
        test_email = f"test_link_{uuid.uuid4().hex[:8]}@test.com"
        
        create_payload = {
            "employee_id": emp_id,
            "first_name": "Link",
            "last_name": "Test",
            "email": test_email,
            "employment_type": "contract"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/employees", json=create_payload, headers=admin_headers)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        
        internal_id = create_response.json()['employee_id']
        TEST_EMPLOYEE_IDS.append(internal_id)
        
        # Get a user to link (admin user)
        users_response = requests.get(f"{BASE_URL}/api/users-with-roles", headers=admin_headers)
        if users_response.status_code != 200:
            pytest.skip("Could not get users list")
        
        users = users_response.json()
        # Find a user not already linked
        test_user = None
        employees = requests.get(f"{BASE_URL}/api/employees", headers=admin_headers).json()
        linked_user_ids = {emp.get('user_id') for emp in employees if emp.get('user_id')}
        
        for u in users:
            if u['id'] not in linked_user_ids:
                test_user = u
                break
        
        if not test_user:
            print("✓ All users already linked - skipping link/unlink test")
            return
        
        # Test link
        link_response = requests.post(
            f"{BASE_URL}/api/employees/{internal_id}/link-user?user_id={test_user['id']}", 
            headers=admin_headers
        )
        assert link_response.status_code == 200, f"Link failed: {link_response.text}"
        print(f"✓ Linked user {test_user['email']} to employee")
        
        # Verify link
        get_response = requests.get(f"{BASE_URL}/api/employees/{internal_id}", headers=admin_headers)
        linked_emp = get_response.json()
        assert linked_emp.get('user_id') == test_user['id'], "User should be linked"
        
        # Test unlink
        unlink_response = requests.post(
            f"{BASE_URL}/api/employees/{internal_id}/unlink-user", 
            headers=admin_headers
        )
        assert unlink_response.status_code == 200, f"Unlink failed: {unlink_response.text}"
        print(f"✓ Unlinked user from employee")
        
        # Verify unlink
        get_response2 = requests.get(f"{BASE_URL}/api/employees/{internal_id}", headers=admin_headers)
        unlinked_emp = get_response2.json()
        assert unlinked_emp.get('user_id') is None, "User should be unlinked"
    
    def test_delete_employee(self, admin_headers):
        """Test DELETE /api/employees/{id} - Soft delete employee"""
        # Create employee to delete
        emp_id = f"TESTDEL{str(uuid.uuid4())[:6].upper()}"
        test_email = f"test_del_{uuid.uuid4().hex[:8]}@test.com"
        
        create_payload = {
            "employee_id": emp_id,
            "first_name": "Delete",
            "last_name": "Test",
            "email": test_email,
            "employment_type": "intern"
        }
        
        create_response = requests.post(f"{BASE_URL}/api/employees", json=create_payload, headers=admin_headers)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        
        internal_id = create_response.json()['employee_id']
        
        # Delete (soft)
        response = requests.delete(f"{BASE_URL}/api/employees/{internal_id}", headers=admin_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Employee {emp_id} deactivated (soft delete)")
        
        # Verify employee is inactive (won't show in default active list)
        list_response = requests.get(f"{BASE_URL}/api/employees?is_active=false", headers=admin_headers)
        inactive_employees = list_response.json()
        found = any(emp['id'] == internal_id for emp in inactive_employees)
        assert found, "Deleted employee should be in inactive list"
    
    def test_employee_form_validation(self, admin_headers):
        """Test that duplicate employee IDs are rejected"""
        emp_id = f"TESTDUP{str(uuid.uuid4())[:6].upper()}"
        test_email1 = f"test_dup1_{uuid.uuid4().hex[:8]}@test.com"
        test_email2 = f"test_dup2_{uuid.uuid4().hex[:8]}@test.com"
        
        # Create first employee
        create_payload1 = {
            "employee_id": emp_id,
            "first_name": "Duplicate",
            "last_name": "Test1",
            "email": test_email1,
            "employment_type": "full_time"
        }
        
        response1 = requests.post(f"{BASE_URL}/api/employees", json=create_payload1, headers=admin_headers)
        assert response1.status_code == 200, f"First create failed: {response1.text}"
        TEST_EMPLOYEE_IDS.append(response1.json()['employee_id'])
        
        # Try to create second with same employee_id
        create_payload2 = {
            "employee_id": emp_id,
            "first_name": "Duplicate",
            "last_name": "Test2",
            "email": test_email2,
            "employment_type": "full_time"
        }
        
        response2 = requests.post(f"{BASE_URL}/api/employees", json=create_payload2, headers=admin_headers)
        assert response2.status_code == 400, f"Expected 400 for duplicate ID, got {response2.status_code}"
        print(f"✓ Duplicate employee ID rejected correctly")


class TestEmployeePermissions:
    """Test permission-based access for employees"""
    
    @pytest.fixture
    def executive_token(self):
        """Try to get executive token (non-HR role)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "executive@company.com",
            "password": "executive123"
        })
        if response.status_code != 200:
            pytest.skip("Executive login failed")
        return response.json().get("access_token")
    
    def test_non_hr_cannot_create_employee(self, executive_token):
        """Test that non-HR users cannot create employees"""
        headers = {
            "Authorization": f"Bearer {executive_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "employee_id": "TESTEXEC001",
            "first_name": "Executive",
            "last_name": "Test",
            "email": "exec_test@test.com",
            "employment_type": "full_time"
        }
        
        response = requests.post(f"{BASE_URL}/api/employees", json=payload, headers=headers)
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-HR user correctly denied employee creation")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_employees(self):
        """Clean up test employees"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if login_response.status_code != 200:
            print("Could not login for cleanup")
            return
        
        token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # Delete test employees
        deleted_count = 0
        for emp_id in TEST_EMPLOYEE_IDS:
            try:
                response = requests.delete(f"{BASE_URL}/api/employees/{emp_id}", headers=headers)
                if response.status_code == 200:
                    deleted_count += 1
            except:
                pass
        
        print(f"✓ Cleanup: Deleted/deactivated {deleted_count} test employees")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
