"""
SSOT (Single Source of Truth) Integration Tests
Tests for LeadSelector integration in Quotations and Agreements forms

Tests:
1. SSOT search endpoint (/api/leads/ssot/search)
2. SSOT master data endpoint (/api/leads/ssot/master-data/{lead_id})
3. SSOT lead sources endpoint (/api/leads/ssot/lead-sources)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSSOTBackendEndpoints:
    """Test SSOT backend API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                self.logged_in = True
                self.user_data = login_response.json().get("user", {})
            else:
                self.logged_in = False
        else:
            print(f"Login failed: {login_response.status_code} - {login_response.text}")
            self.logged_in = False
    
    def test_login_success(self):
        """Verify login works with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "Response should contain access_token"
        print(f"PASS - Login successful for EMP001")
    
    def test_ssot_search_endpoint_exists(self):
        """Test that SSOT search endpoint exists and responds"""
        if not self.logged_in:
            pytest.skip("Login failed - cannot test authenticated endpoints")
        
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "test",
            "limit": 10
        })
        
        # Should return 200 even with no results
        assert response.status_code == 200, f"SSOT search endpoint failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "leads" in data, "Response should contain 'leads' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS - SSOT search endpoint working. Found {data['total']} leads")
    
    def test_ssot_search_returns_results_with_empty_query(self):
        """Test that SSOT search returns recent leads when query is short"""
        if not self.logged_in:
            pytest.skip("Login failed")
        
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 20
        })
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "leads" in data
        print(f"PASS - SSOT search with empty query returns {data['total']} leads")
    
    def test_ssot_search_with_company_query(self):
        """Test SSOT search with company name query"""
        if not self.logged_in:
            pytest.skip("Login failed")
        
        # Search for 'Browser Test Corp' mentioned in test data
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "Browser",
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "leads" in data
        
        if data["total"] > 0:
            # Verify lead structure
            lead = data["leads"][0]
            assert "id" in lead, "Lead should have 'id'"
            assert "company" in lead, "Lead should have 'company'"
            assert "contact" in lead, "Lead should have 'contact'"
            print(f"PASS - Found lead: {lead.get('company')} - {lead.get('contact')}")
        else:
            print("PASS - SSOT search working (no matching leads found)")
    
    def test_ssot_lead_sources_endpoint(self):
        """Test that SSOT lead sources endpoint returns dropdown options"""
        # This endpoint should work without auth
        response = requests.get(f"{BASE_URL}/api/leads/ssot/lead-sources")
        
        assert response.status_code == 200, f"Lead sources failed: {response.text}"
        data = response.json()
        assert "sources" in data, "Response should contain 'sources'"
        assert isinstance(data["sources"], list), "Sources should be a list"
        
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "id" in source, "Source should have 'id'"
            assert "label" in source, "Source should have 'label'"
            print(f"PASS - Lead sources returns {len(data['sources'])} options")
    
    def test_ssot_master_data_requires_auth(self):
        """Test that master data endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leads/ssot/master-data/test-lead-id")
        
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS - Master data endpoint requires authentication")
    
    def test_ssot_master_data_returns_404_for_invalid_lead(self):
        """Test that master data returns 404 for non-existent lead"""
        if not self.logged_in:
            pytest.skip("Login failed")
        
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/master-data/nonexistent-lead-id-12345")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS - Master data returns 404 for invalid lead")


class TestSSOTWithRealLead:
    """Test SSOT master data with a real lead"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and find a real lead"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                self.logged_in = True
            else:
                self.logged_in = False
        else:
            self.logged_in = False
        
        # Find a real lead ID
        self.lead_id = None
        if self.logged_in:
            search_response = self.session.get(f"{BASE_URL}/api/leads/ssot/search", params={
                "q": "",
                "limit": 1
            })
            if search_response.status_code == 200:
                data = search_response.json()
                if data.get("leads") and len(data["leads"]) > 0:
                    self.lead_id = data["leads"][0]["id"]
                    self.lead_company = data["leads"][0].get("company", "Unknown")
    
    def test_ssot_master_data_returns_correct_fields(self):
        """Test that master data returns all required SSOT fields"""
        if not self.logged_in:
            pytest.skip("Login failed")
        if not self.lead_id:
            pytest.skip("No leads found in database")
        
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/master-data/{self.lead_id}")
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify master_data object exists
        assert "master_data" in data, "Response should contain 'master_data'"
        
        master_data = data["master_data"]
        
        # Verify required SSOT fields
        assert "company" in master_data, "Master data should contain 'company'"
        assert "contact_person" in master_data, "Master data should contain 'contact_person'"
        assert "email" in master_data, "Master data should contain 'email'"
        assert "phone" in master_data, "Master data should contain 'phone'"
        
        # Verify locked_fields info
        assert "locked_fields" in data, "Response should contain 'locked_fields'"
        
        print(f"PASS - Master data for {self.lead_company}")
        print(f"  - Company: {master_data.get('company')}")
        print(f"  - Contact: {master_data.get('contact_person')}")
        print(f"  - Email: {master_data.get('email')}")
        print(f"  - Phone: {master_data.get('phone')}")
    
    def test_ssot_master_data_includes_locked_fields_info(self):
        """Test that master data response includes info about locked fields"""
        if not self.logged_in or not self.lead_id:
            pytest.skip("Prerequisites not met")
        
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/master-data/{self.lead_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify locked_fields list
        assert "locked_fields" in data
        locked_fields = data["locked_fields"]
        
        assert "company" in locked_fields, "company should be in locked fields"
        assert "email" in locked_fields, "email should be in locked fields"
        assert "phone" in locked_fields, "phone should be in locked fields"
        
        print(f"PASS - Locked fields: {locked_fields}")


class TestSSOTSalesUserAccess:
    """Test SSOT access with sales user credentials"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as sales user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as sales user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                self.logged_in = True
            else:
                self.logged_in = False
        else:
            print(f"Sales login failed: {login_response.status_code}")
            self.logged_in = False
    
    def test_sales_user_can_search_leads(self):
        """Test that sales user can use SSOT search"""
        if not self.logged_in:
            pytest.skip("Sales user login failed")
        
        response = self.session.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 5
        })
        
        assert response.status_code == 200, f"Sales user search failed: {response.text}"
        data = response.json()
        assert "leads" in data
        print(f"PASS - Sales user can search leads. Found {data['total']} leads")
    
    def test_sales_user_can_access_master_data(self):
        """Test that sales user can access master data for accessible leads"""
        if not self.logged_in:
            pytest.skip("Sales user login failed")
        
        # First get a lead ID
        search_response = self.session.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 1
        })
        
        if search_response.status_code != 200:
            pytest.skip("Could not search leads")
        
        data = search_response.json()
        if not data.get("leads") or len(data["leads"]) == 0:
            pytest.skip("No leads found")
        
        lead_id = data["leads"][0]["id"]
        
        # Try to get master data
        master_response = self.session.get(f"{BASE_URL}/api/leads/ssot/master-data/{lead_id}")
        
        # Should either succeed (200) or deny access (403)
        assert master_response.status_code in [200, 403], f"Unexpected status: {master_response.status_code}"
        
        if master_response.status_code == 200:
            print(f"PASS - Sales user can access master data for lead {lead_id}")
        else:
            print(f"PASS - Sales user access correctly restricted for lead {lead_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
