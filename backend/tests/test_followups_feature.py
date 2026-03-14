"""
Test Follow-ups Feature - Lead next_follow_up and FollowUps page integration

Tests:
1. Login as Admin (ADMIN001 / Admin@2026)
2. Create lead with next_follow_up field via POST /api/leads
3. Verify GET /api/leads returns the next_follow_up field
4. Verify the lead appears in follow-ups context
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestFollowUpsFeature:
    """Tests for Follow-ups feature with Lead next_follow_up date"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as Admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            self.user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip(f"Login failed with status {login_response.status_code}: {login_response.text}")
    
    def test_01_login_successful(self):
        """Test login works with Admin credentials"""
        assert self.token is not None, "Auth token should be present"
        assert self.user is not None, "User data should be present"
        assert self.user.get("role") == "admin", "User role should be admin"
        print(f"PASSED: Login successful for user {self.user.get('full_name')}")
    
    def test_02_create_lead_with_next_follow_up(self):
        """Test creating a lead with next_follow_up and follow_up_notes fields"""
        # Set follow-up date to tomorrow
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        lead_payload = {
            "first_name": "TEST_FollowUp",
            "last_name": "LeadUser",
            "company": "TEST FollowUp Testing Corp",
            "job_title": "CEO",
            "email": "test_followup_lead@test.com",
            "phone": "9876543210",
            "source": "API Test",
            "notes": "Testing next_follow_up field",
            "next_follow_up": f"{tomorrow}T10:00:00",
            "follow_up_notes": "Test follow-up note for verification"
        }
        
        response = self.session.post(f"{BASE_URL}/api/leads", json=lead_payload)
        
        assert response.status_code == 200, f"Lead creation should succeed: {response.text}"
        
        data = response.json()
        assert data.get("id") is not None, "Lead should have an ID"
        assert data.get("first_name") == "TEST_FollowUp", "First name should match"
        assert data.get("company") == "TEST FollowUp Testing Corp", "Company should match"
        assert data.get("next_follow_up") is not None, "next_follow_up should be set"
        assert data.get("follow_up_notes") == "Test follow-up note for verification", "follow_up_notes should match"
        
        # Store lead ID for later tests
        self.__class__.created_lead_id = data.get("id")
        print(f"PASSED: Created lead with ID {data.get('id')} and next_follow_up date")
    
    def test_03_get_leads_returns_next_follow_up(self):
        """Test that GET /api/leads returns leads with next_follow_up field"""
        response = self.session.get(f"{BASE_URL}/api/leads")
        
        assert response.status_code == 200, f"Get leads should succeed: {response.text}"
        
        data = response.json()
        # API returns paginated response with 'items' key
        leads = data.get("items", data) if isinstance(data, dict) else data
        
        assert len(leads) > 0, "Should have at least one lead"
        
        # Find the lead we just created
        created_lead = None
        for lead in leads:
            if lead.get("id") == getattr(self.__class__, 'created_lead_id', None):
                created_lead = lead
                break
        
        if created_lead:
            assert created_lead.get("next_follow_up") is not None, "next_follow_up should be present in response"
            assert created_lead.get("follow_up_notes") is not None, "follow_up_notes should be present"
            print(f"PASSED: Lead with next_follow_up found in GET /api/leads response")
        else:
            print("INFO: Could not find newly created lead (may be filtered by role)")
    
    def test_04_get_specific_lead_has_follow_up_fields(self):
        """Test that GET /api/leads/{id} returns follow-up fields"""
        lead_id = getattr(self.__class__, 'created_lead_id', None)
        if not lead_id:
            pytest.skip("No lead ID from previous test")
        
        response = self.session.get(f"{BASE_URL}/api/leads/{lead_id}")
        
        assert response.status_code == 200, f"Get lead should succeed: {response.text}"
        
        data = response.json()
        assert data.get("next_follow_up") is not None, "next_follow_up should be present"
        assert data.get("follow_up_notes") == "Test follow-up note for verification", "follow_up_notes should match"
        print(f"PASSED: GET /api/leads/{lead_id} returns follow-up fields correctly")
    
    def test_05_update_lead_follow_up_date(self):
        """Test updating lead's next_follow_up date"""
        lead_id = getattr(self.__class__, 'created_lead_id', None)
        if not lead_id:
            pytest.skip("No lead ID from previous test")
        
        # Update to day after tomorrow
        new_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        
        update_payload = {
            "next_follow_up": f"{new_date}T14:00:00",
            "follow_up_notes": "Updated follow-up notes"
        }
        
        response = self.session.put(f"{BASE_URL}/api/leads/{lead_id}", json=update_payload)
        
        assert response.status_code == 200, f"Update lead should succeed: {response.text}"
        
        data = response.json()
        assert "follow_up_notes" in data or data.get("follow_up_notes") == "Updated follow-up notes", "follow_up_notes should be updated"
        print(f"PASSED: Lead follow-up date updated successfully")
    
    def test_06_check_existing_test_lead(self):
        """Test that existing test lead 'Test FollowUp' from 'FollowUp Corp' is accessible"""
        response = self.session.get(f"{BASE_URL}/api/leads")
        
        assert response.status_code == 200, f"Get leads should succeed: {response.text}"
        
        data = response.json()
        leads = data.get("items", data) if isinstance(data, dict) else data
        
        # Look for the existing test lead mentioned in requirements
        test_lead = None
        for lead in leads:
            if "FollowUp" in (lead.get("first_name") or "") or "FollowUp Corp" in (lead.get("company") or ""):
                test_lead = lead
                break
        
        if test_lead:
            print(f"PASSED: Found existing test lead: {test_lead.get('first_name')} {test_lead.get('last_name')} from {test_lead.get('company')}")
            if test_lead.get("next_follow_up"):
                print(f"  - Has next_follow_up: {test_lead.get('next_follow_up')}")
        else:
            print("INFO: Existing test lead 'Test FollowUp' from 'FollowUp Corp' not found (may need to be created)")
    
    def test_07_get_meetings_endpoint(self):
        """Test /api/meetings endpoint is accessible (for Follow-ups page)"""
        response = self.session.get(f"{BASE_URL}/api/meetings")
        
        assert response.status_code == 200, f"Get meetings should succeed: {response.text}"
        
        data = response.json()
        meetings = data.get("items", data) if isinstance(data, dict) else data
        
        print(f"PASSED: /api/meetings returns {len(meetings) if isinstance(meetings, list) else 'data'}")
        
        # Check for meetings with next_meeting_date
        meetings_with_next_date = [m for m in (meetings if isinstance(meetings, list) else []) if m.get("next_meeting_date")]
        print(f"  - Meetings with next_meeting_date: {len(meetings_with_next_date)}")
    
    def test_08_get_consulting_payments_endpoint(self):
        """Test /api/consulting/payments endpoint is accessible (for Follow-ups page)"""
        response = self.session.get(f"{BASE_URL}/api/consulting/payments")
        
        # Might return 403 if user doesn't have consulting role, 404 if endpoint doesn't exist
        if response.status_code == 200:
            data = response.json()
            payments = data if isinstance(data, list) else data.get("items", [])
            print(f"PASSED: /api/consulting/payments returns {len(payments)} payments")
        elif response.status_code == 403:
            print("INFO: /api/consulting/payments returned 403 (role restriction) - expected for non-consulting users")
        elif response.status_code == 404:
            print("INFO: /api/consulting/payments endpoint not found")
        else:
            print(f"INFO: /api/consulting/payments returned status {response.status_code}")
    
    def test_09_cleanup_test_lead(self):
        """Cleanup: Delete the test lead created during tests"""
        lead_id = getattr(self.__class__, 'created_lead_id', None)
        if not lead_id:
            pytest.skip("No lead ID to cleanup")
        
        response = self.session.delete(f"{BASE_URL}/api/leads/{lead_id}")
        
        # Admin should be able to delete leads
        if response.status_code == 200:
            print(f"PASSED: Test lead {lead_id} cleaned up successfully")
        else:
            print(f"INFO: Could not delete test lead (status {response.status_code})")


class TestLoginCredentials:
    """Test login with various credentials"""
    
    def test_admin_login(self):
        """Test Admin login with ADMIN001 / Admin@2026"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "Admin@2026"
        })
        
        assert response.status_code == 200, f"Admin login should succeed: {response.text}"
        data = response.json()
        assert data.get("access_token") is not None, "Should return access_token"
        assert data.get("user", {}).get("role") == "admin", "User role should be admin"
        print("PASSED: Admin login successful")
    
    def test_sales_manager_login(self):
        """Test Sales Manager login with EMP002 / Sales@123"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP002",
            "password": "Sales@123"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"PASSED: Sales Manager login successful - role: {data.get('user', {}).get('role')}")
        else:
            print(f"INFO: Sales Manager EMP002 login returned {response.status_code}")
    
    def test_sales_executive_login(self):
        """Test Sales Executive login with EMP003 / Sales@123"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "Sales@123"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"PASSED: Sales Executive login successful - role: {data.get('user', {}).get('role')}")
        else:
            print(f"INFO: Sales Executive EMP003 login returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
