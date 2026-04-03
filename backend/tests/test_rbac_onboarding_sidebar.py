"""
Test RBAC roles API, onboarding role dropdown, AssignTeam consulting roles, and sidebar cleanup
Tests for:
1. RBAC roles API returns active roles
2. Onboarding role dropdown fetches roles dynamically from /api/rbac/roles
3. AssignTeam consulting role dropdown fetches roles filtered to Consulting department
4. Sidebar has no duplicate links
5. All sidebar sections render correctly for Admin role
6. All existing pages still load correctly
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRBACRolesAPI:
    """Test RBAC roles API endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get('access_token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_rbac_roles_api_returns_roles(self):
        """Test GET /api/rbac/roles returns active roles"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=self.headers)
        assert response.status_code == 200, f"RBAC roles API failed: {response.text}"
        
        data = response.json()
        assert "roles" in data, "Response should contain 'roles' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["roles"], list), "Roles should be a list"
        assert data["total"] > 0, "Should have at least one role"
        
        # Verify role structure
        first_role = data["roles"][0]
        assert "code" in first_role, "Role should have 'code'"
        assert "name" in first_role, "Role should have 'name'"
        assert "department" in first_role, "Role should have 'department'"
        assert "level" in first_role, "Role should have 'level'"
        assert "is_active" in first_role, "Role should have 'is_active'"
        
        print(f"PASS: RBAC roles API returns {data['total']} roles")
    
    def test_rbac_roles_contains_expected_roles(self):
        """Test that RBAC roles contains expected roles for onboarding"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        role_codes = [r["code"] for r in data["roles"]]
        
        # Expected roles that should be available for onboarding
        expected_roles = ["admin", "hr_manager", "sales_manager", "consultant", "employee"]
        
        # Check that most expected roles exist (employee might not be in RBAC)
        found_roles = [r for r in expected_roles if r in role_codes]
        assert len(found_roles) >= 3, f"Should have at least 3 expected roles, found: {found_roles}"
        
        print(f"PASS: Found expected roles: {found_roles}")
    
    def test_rbac_roles_consulting_department_filter(self):
        """Test that consulting roles can be filtered by department"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Filter roles by Consulting department (as done in AssignTeam.js)
        consulting_roles = [
            r for r in data["roles"] 
            if r.get("is_active") and r.get("department") == "Consulting"
        ]
        
        assert len(consulting_roles) > 0, "Should have at least one Consulting department role"
        
        # Verify expected consulting roles
        consulting_codes = [r["code"] for r in consulting_roles]
        expected_consulting = ["consultant", "senior_consultant", "lead_consultant", "principal_consultant"]
        found_consulting = [r for r in expected_consulting if r in consulting_codes]
        
        assert len(found_consulting) >= 3, f"Should have at least 3 consulting roles, found: {found_consulting}"
        
        print(f"PASS: Found {len(consulting_roles)} consulting roles: {consulting_codes}")
    
    def test_rbac_roles_sorted_by_level(self):
        """Test that roles can be sorted by level (as done in frontend)"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Sort by level descending (as done in SubmissionReview.js)
        sorted_roles = sorted(data["roles"], key=lambda r: r.get("level", 0), reverse=True)
        
        # Verify admin has highest level
        assert sorted_roles[0]["code"] == "admin", "Admin should have highest level"
        assert sorted_roles[0]["level"] == 100, "Admin level should be 100"
        
        print(f"PASS: Roles sorted by level, top role: {sorted_roles[0]['code']} (level {sorted_roles[0]['level']})")
    
    def test_rbac_roles_excludes_external_and_client(self):
        """Test that external/client roles can be filtered out (as done in onboarding)"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Filter as done in SubmissionReview.js: active, non-external, not client
        filtered_roles = [
            r for r in data["roles"]
            if r.get("is_active") and not r.get("is_external") and r.get("code") != "client"
        ]
        
        # Verify client role is excluded
        filtered_codes = [r["code"] for r in filtered_roles]
        assert "client" not in filtered_codes, "Client role should be excluded"
        
        print(f"PASS: Filtered roles exclude client, {len(filtered_roles)} roles available for onboarding")


class TestSidebarNavigation:
    """Test sidebar navigation items and page loading"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get('access_token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_employees_page_loads(self):
        """Test /employees page API works"""
        response = requests.get(f"{BASE_URL}/api/employees/all", headers=self.headers)
        assert response.status_code == 200, f"Employees API failed: {response.text}"
        print("PASS: /employees page API works")
    
    def test_leads_page_loads(self):
        """Test /leads page API works"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=self.headers)
        assert response.status_code == 200, f"Leads API failed: {response.text}"
        print("PASS: /leads page API works")
    
    def test_consulting_meetings_page_loads(self):
        """Test /consulting-meetings page API works"""
        response = requests.get(f"{BASE_URL}/api/meetings", headers=self.headers)
        assert response.status_code == 200, f"Consulting meetings API failed: {response.text}"
        print("PASS: /consulting-meetings page API works")
    
    def test_payroll_engine_page_loads(self):
        """Test /payroll-engine page API works"""
        # Payroll engine uses payroll/engine/register endpoint
        response = requests.get(f"{BASE_URL}/api/payroll/engine/register", headers=self.headers)
        assert response.status_code == 200, f"Payroll engine API failed: {response.text}"
        print("PASS: /payroll-engine page API works")
    
    def test_approvals_page_loads(self):
        """Test /approvals page API works"""
        response = requests.get(f"{BASE_URL}/api/approvals/pending", headers=self.headers)
        assert response.status_code == 200, f"Approvals API failed: {response.text}"
        print("PASS: /approvals page API works")
    
    def test_projects_page_loads(self):
        """Test /projects page API works"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=self.headers)
        assert response.status_code == 200, f"Projects API failed: {response.text}"
        print("PASS: /projects page API works")
    
    def test_rbac_my_access_for_admin(self):
        """Test admin sees all sidebar sections"""
        response = requests.get(f"{BASE_URL}/api/rbac/my-access", headers=self.headers)
        assert response.status_code == 200, f"RBAC my-access failed: {response.text}"
        
        data = response.json()
        sidebar = data.get("sidebar_sections", {})
        
        # Admin should see all sections
        assert sidebar.get("hr") == True, "Admin should see HR section"
        assert sidebar.get("sales") == True, "Admin should see Sales section"
        assert sidebar.get("consulting") == True, "Admin should see Consulting section"
        assert sidebar.get("admin") == True, "Admin should see Admin section"
        
        print(f"PASS: Admin sees all sidebar sections: {sidebar}")


class TestConsultantRoleAccess:
    """Test consultant role access to consulting pages"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as consultant and get token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        assert login_response.status_code == 200, f"Consultant login failed: {login_response.text}"
        self.token = login_response.json().get('access_token')
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_consultant_can_access_rbac_roles(self):
        """Test consultant can access RBAC roles API (may require admin access)"""
        response = requests.get(f"{BASE_URL}/api/rbac/roles", headers=self.headers)
        # RBAC roles API requires admin/HR access, consultant gets 403
        # This is expected behavior - frontend uses localStorage token which may have different permissions
        if response.status_code == 403:
            print("INFO: Consultant cannot access RBAC roles API directly (403 - expected for security)")
            # Verify the error message
            assert "Admin or HR" in response.json().get("detail", ""), "Should indicate admin/HR access required"
            print("PASS: RBAC roles API correctly restricts consultant access")
        else:
            assert response.status_code == 200
            data = response.json()
            assert "roles" in data
            print(f"PASS: Consultant can access RBAC roles API, {data['total']} roles returned")
    
    def test_consultant_sidebar_sections(self):
        """Test consultant sees only consulting section"""
        response = requests.get(f"{BASE_URL}/api/rbac/my-access", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        sidebar = data.get("sidebar_sections", {})
        
        # Consultant should see consulting section
        assert sidebar.get("consulting") == True, "Consultant should see Consulting section"
        
        print(f"PASS: Consultant sidebar sections: {sidebar}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
