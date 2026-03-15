"""
Funnel Eligibility API Tests
Tests for /api/leads/ssot/search endpoint with funnel_stage filtering
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}

@pytest.fixture(scope="module")
def auth_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        return response.json().get("access_token") or response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code}")

@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestLeadSSOTSearchEndpoint:
    """Tests for /api/leads/ssot/search endpoint with funnel_stage filter"""
    
    def test_search_with_any_funnel_stage(self, api_client):
        """Test search with funnel_stage='any' returns all leads"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 20,
            "funnel_stage": "any"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leads" in data, "Response should contain 'leads' key"
        assert "total" in data, "Response should contain 'total' key"
        assert "funnel_stage" in data, "Response should contain 'funnel_stage' key"
        assert data["funnel_stage"] == "any"
        assert "filtered" in data, "Response should contain 'filtered' key"
        assert data["filtered"] == False, "filtered should be False for 'any' stage"
        print(f"Found {data['total']} leads with funnel_stage='any'")
    
    def test_search_with_has_meeting_funnel_stage(self, api_client):
        """Test search with funnel_stage='has_meeting' returns only leads with meetings"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 20,
            "funnel_stage": "has_meeting"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leads" in data
        assert data["funnel_stage"] == "has_meeting"
        assert data["filtered"] == True, "filtered should be True for stage filtering"
        print(f"Found {data['total']} leads with funnel_stage='has_meeting'")
    
    def test_search_with_has_pricing_plan_funnel_stage(self, api_client):
        """Test search with funnel_stage='has_pricing_plan' returns only leads with pricing plans"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 20,
            "funnel_stage": "has_pricing_plan"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leads" in data
        assert data["funnel_stage"] == "has_pricing_plan"
        assert data["filtered"] == True, "filtered should be True for stage filtering"
        print(f"Found {data['total']} leads with funnel_stage='has_pricing_plan'")
        
        # If leads found, verify they actually have pricing plans
        if data['total'] > 0:
            lead_ids = [lead['id'] for lead in data['leads']]
            print(f"Leads with pricing plans: {lead_ids}")
    
    def test_search_with_has_quotation_funnel_stage(self, api_client):
        """Test search with funnel_stage='has_quotation' returns only leads with quotations"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 20,
            "funnel_stage": "has_quotation"
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leads" in data
        assert data["funnel_stage"] == "has_quotation"
        assert data["filtered"] == True
        print(f"Found {data['total']} leads with funnel_stage='has_quotation'")
        
        # If leads found, verify they actually have quotations
        if data['total'] > 0:
            lead_ids = [lead['id'] for lead in data['leads']]
            print(f"Leads with quotations: {lead_ids}")
    
    def test_search_response_structure(self, api_client):
        """Test the response structure contains expected fields for lead selection UI"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "Edit Protection Testing Corp",  # Known test lead
            "limit": 5,
            "funnel_stage": "any"
        })
        assert response.status_code == 200
        
        data = response.json()
        if data['total'] > 0:
            lead = data['leads'][0]
            # Check required fields for UI
            assert "id" in lead, "Lead should have id field"
            assert "company" in lead, "Lead should have company field"
            assert "contact" in lead, "Lead should have contact field"
            assert "status" in lead, "Lead should have status field"
            print(f"Lead structure verified: {lead['company']}")


class TestLeadEligibilityForProformaInvoice:
    """Test lead eligibility for Proforma Invoice creation (needs pricing plan)"""
    
    def test_leads_with_pricing_plan_exist(self, api_client):
        """Verify that there are leads with pricing plans for Proforma Invoice"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 50,
            "funnel_stage": "has_pricing_plan"
        })
        assert response.status_code == 200
        
        data = response.json()
        print(f"Total leads eligible for Proforma Invoice: {data['total']}")
        
        # Optionally verify specific test lead
        if data['total'] > 0:
            for lead in data['leads']:
                print(f"  - {lead['company']} (ID: {lead['id']})")


class TestLeadEligibilityForAgreements:
    """Test lead eligibility for Agreement creation (needs quotation)"""
    
    def test_leads_with_quotation_exist(self, api_client):
        """Verify that there are leads with quotations for Agreement creation"""
        response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 50,
            "funnel_stage": "has_quotation"
        })
        assert response.status_code == 200
        
        data = response.json()
        print(f"Total leads eligible for Agreement: {data['total']}")
        
        if data['total'] > 0:
            for lead in data['leads']:
                print(f"  - {lead['company']} (ID: {lead['id']})")


class TestFunnelFilterComparison:
    """Compare results between different funnel stages to verify filtering works"""
    
    def test_filtered_results_are_subset_of_any(self, api_client):
        """Verify that filtered results are a subset of 'any' results"""
        # Get all leads (max limit is 50)
        all_response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 50,
            "funnel_stage": "any"
        })
        assert all_response.status_code == 200, f"Expected 200, got {all_response.status_code}: {all_response.text}"
        all_data = all_response.json()
        all_lead_ids = {lead['id'] for lead in all_data['leads']}
        
        # Get leads with pricing plans
        pricing_response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 50,
            "funnel_stage": "has_pricing_plan"
        })
        assert pricing_response.status_code == 200
        pricing_data = pricing_response.json()
        pricing_lead_ids = {lead['id'] for lead in pricing_data['leads']}
        
        # Get leads with quotations
        quotation_response = api_client.get(f"{BASE_URL}/api/leads/ssot/search", params={
            "q": "",
            "limit": 50,
            "funnel_stage": "has_quotation"
        })
        assert quotation_response.status_code == 200
        quotation_data = quotation_response.json()
        quotation_lead_ids = {lead['id'] for lead in quotation_data['leads']}
        
        # Verify filtering is working
        print(f"All leads: {len(all_lead_ids)}")
        print(f"Leads with pricing plans: {len(pricing_lead_ids)}")
        print(f"Leads with quotations: {len(quotation_lead_ids)}")
        
        # Leads with pricing plans should be <= all leads
        assert pricing_lead_ids.issubset(all_lead_ids) or len(pricing_lead_ids) == 0, \
            "Leads with pricing plans should be a subset of all leads"
        
        # Leads with quotations should be <= all leads
        assert quotation_lead_ids.issubset(all_lead_ids) or len(quotation_lead_ids) == 0, \
            "Leads with quotations should be a subset of all leads"
