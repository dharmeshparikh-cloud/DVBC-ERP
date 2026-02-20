"""
Test Suite: Simplified Permission System & Sales Meetings
Tests:
1. /api/department-access/my-access returns has_reportees, is_view_only, can_edit flags
2. /sales-meetings endpoint works correctly
3. MOM recording for sales meetings
4. HR Onboarding Employee ID auto-generation with EMP prefix
"""
import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leave-manager-93.preview.emergentagent.com')

class TestSimplifiedPermissions:
    """Test simplified permission model with new fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Login as admin
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        self.admin_token = login_resp.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Login as HR Manager
        hr_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        if hr_login.status_code == 200:
            self.hr_token = hr_login.json()["access_token"]
            self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        else:
            self.hr_token = None
            self.hr_headers = None
    
    def test_my_access_returns_has_reportees_field(self):
        """Verify /my-access returns has_reportees field (NEW simplified model)"""
        resp = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=self.admin_headers)
        assert resp.status_code == 200, f"Failed to get my-access: {resp.text}"
        
        data = resp.json()
        # NEW SIMPLIFIED FIELDS - must be present
        assert "has_reportees" in data, "has_reportees field missing from my-access response"
        assert isinstance(data["has_reportees"], bool), "has_reportees should be boolean"
        print(f"✓ has_reportees field present: {data['has_reportees']}")
    
    def test_my_access_returns_is_view_only_field(self):
        """Verify /my-access returns is_view_only field (NEW simplified model)"""
        resp = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=self.admin_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "is_view_only" in data, "is_view_only field missing from my-access response"
        assert isinstance(data["is_view_only"], bool), "is_view_only should be boolean"
        print(f"✓ is_view_only field present: {data['is_view_only']}")
    
    def test_my_access_returns_can_edit_field(self):
        """Verify /my-access returns can_edit field (NEW simplified model)"""
        resp = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=self.admin_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "can_edit" in data, "can_edit field missing from my-access response"
        assert isinstance(data["can_edit"], bool), "can_edit should be boolean"
        # can_edit should be inverse of is_view_only
        assert data["can_edit"] == (not data["is_view_only"]), "can_edit should be inverse of is_view_only"
        print(f"✓ can_edit field present: {data['can_edit']}")
    
    def test_my_access_returns_can_manage_team_field(self):
        """Verify /my-access returns can_manage_team field (NEW simplified model)"""
        resp = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=self.admin_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "can_manage_team" in data, "can_manage_team field missing from my-access response"
        assert isinstance(data["can_manage_team"], bool), "can_manage_team should be boolean"
        # can_manage_team should equal has_reportees
        assert data["can_manage_team"] == data["has_reportees"], "can_manage_team should equal has_reportees"
        print(f"✓ can_manage_team field present: {data['can_manage_team']}")
    
    def test_my_access_returns_reportee_count(self):
        """Verify /my-access returns reportee_count field"""
        resp = requests.get(f"{BASE_URL}/api/department-access/my-access", headers=self.admin_headers)
        assert resp.status_code == 200
        
        data = resp.json()
        assert "reportee_count" in data, "reportee_count field missing"
        assert isinstance(data["reportee_count"], int), "reportee_count should be integer"
        print(f"✓ reportee_count field present: {data['reportee_count']}")


class TestSalesMeetings:
    """Test sales meetings page and MOM recording"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        # Login as admin (has sales access)
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_sales_meetings_endpoint_returns_data(self):
        """Verify /sales-meetings returns list of meetings"""
        resp = requests.get(f"{BASE_URL}/api/sales-meetings", headers=self.headers)
        assert resp.status_code == 200, f"Failed to get sales meetings: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Sales meetings endpoint returns {len(data)} meetings")
    
    def test_sales_meeting_has_required_fields(self):
        """Verify sales meeting structure"""
        resp = requests.get(f"{BASE_URL}/api/sales-meetings", headers=self.headers)
        assert resp.status_code == 200
        
        data = resp.json()
        if len(data) > 0:
            meeting = data[0]
            required_fields = ["id", "lead_id", "title", "scheduled_date", "status"]
            for field in required_fields:
                assert field in meeting, f"Field {field} missing from meeting"
            print(f"✓ Sales meeting has required fields: {list(meeting.keys())[:8]}...")
        else:
            print("⚠ No sales meetings found to validate structure")
    
    def test_leads_endpoint_for_meeting_creation(self):
        """Verify /leads endpoint works for meeting creation dropdown"""
        resp = requests.get(f"{BASE_URL}/api/leads", headers=self.headers)
        assert resp.status_code == 200, f"Failed to get leads: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Leads endpoint returns {len(data)} leads for meeting creation")
    
    def test_users_endpoint_for_attendees_selection(self):
        """Verify /users endpoint works for attendees selection"""
        resp = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert resp.status_code == 200, f"Failed to get users: {resp.text}"
        
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        if len(data) > 0:
            user = data[0]
            assert "id" in user, "User should have id field"
            assert "full_name" in user, "User should have full_name field"
        print(f"✓ Users endpoint returns {len(data)} users for attendees selection")
    
    def test_get_sales_meeting_mom(self):
        """Test retrieving MOM for a meeting"""
        # First get a meeting with MOM
        meetings_resp = requests.get(f"{BASE_URL}/api/sales-meetings", headers=self.headers)
        assert meetings_resp.status_code == 200
        
        meetings = meetings_resp.json()
        meeting_with_mom = None
        for m in meetings:
            if m.get("mom_id"):
                meeting_with_mom = m
                break
        
        if meeting_with_mom:
            resp = requests.get(f"{BASE_URL}/api/sales-meetings/{meeting_with_mom['id']}/mom", headers=self.headers)
            assert resp.status_code == 200, f"Failed to get MOM: {resp.text}"
            
            mom = resp.json()
            assert "summary" in mom or "discussion_points" in mom, "MOM should have content"
            print(f"✓ MOM retrieval works for meeting {meeting_with_mom['id'][:8]}...")
        else:
            print("⚠ No meeting with MOM found to test retrieval")


class TestHROnboardingEmployeeID:
    """Test Employee ID auto-generation with EMP prefix"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_employees_endpoint_returns_emp_prefix_ids(self):
        """Verify existing employees have EMP prefix IDs"""
        resp = requests.get(f"{BASE_URL}/api/employees", headers=self.headers)
        assert resp.status_code == 200, f"Failed to get employees: {resp.text}"
        
        data = resp.json()
        emp_prefix_count = 0
        for emp in data:
            emp_id = emp.get("employee_id", "")
            if emp_id and emp_id.upper().startswith("EMP"):
                emp_prefix_count += 1
        
        print(f"✓ {emp_prefix_count}/{len(data)} employees have EMP prefix IDs")
        # At least some employees should have EMP prefix
        if len(data) > 0:
            assert emp_prefix_count > 0, "At least some employees should have EMP prefix IDs"


class TestUsersEndpoint:
    """Test users endpoint for simplified permissions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert login_resp.status_code == 200
        self.token = login_resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_users_returns_department_field(self):
        """Verify users have department field (for page access)"""
        resp = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert resp.status_code == 200
        
        data = resp.json()
        if len(data) > 0:
            for user in data[:5]:  # Check first 5 users
                # Department can be null for some users
                assert "department" in user or "departments" in user, f"User should have department field"
            print(f"✓ Users have department field for page access control")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
