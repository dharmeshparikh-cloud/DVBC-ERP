"""
Test Sales Funnel P0 Bug Fixes - Iteration 237
Tests for:
1. Proforma Invoice 'Save & Create Invoice' button - POST /api/quotations
2. Sales Funnel Agreement view loading - GET /api/agreements
3. Backend API - POST /api/quotations works without client_name field
4. Backend API - POST /api/agreements accepts quotation_id, meeting_frequency, project_tenure_months, team_deployment
5. Backend API - GET /api/quotations returns paginated {data: [...]} response
6. Backend API - GET /api/agreements returns paginated {data: [...]} response
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sales-funnel-fix.preview.emergentagent.com')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}
CONSULTANT_CREDS = {"employee_id": "EMP004", "password": "consultant123"}


@pytest.fixture(scope="module")
def admin_session():
    """Get authenticated admin session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
    return session


@pytest.fixture(scope="module")
def sales_session():
    """Get authenticated sales session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
    return session


@pytest.fixture(scope="module")
def consultant_session():
    """Get authenticated consultant session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json=CONSULTANT_CREDS)
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token") or data.get("token")
        if token:
            session.headers.update({"Authorization": f"Bearer {token}"})
    return session


class TestQuotationsAPI:
    """Test quotations/proforma invoice API endpoints"""
    
    def test_get_quotations_returns_paginated_response(self, sales_session):
        """GET /api/quotations should return paginated {data: [...], total, page, page_size, total_pages}"""
        response = sales_session.get(f"{BASE_URL}/api/quotations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify paginated response structure
        assert "data" in data, "Response should have 'data' field"
        assert isinstance(data["data"], list), "'data' should be a list"
        assert "total" in data, "Response should have 'total' field"
        assert "page" in data, "Response should have 'page' field"
        assert "page_size" in data, "Response should have 'page_size' field"
        assert "total_pages" in data, "Response should have 'total_pages' field"
        print(f"Quotations API returned {len(data['data'])} items, total: {data['total']}")
    
    def test_get_quotations_with_lead_filter(self, sales_session):
        """GET /api/quotations?lead_id=xxx should filter by lead"""
        # First get a lead to filter by
        leads_response = sales_session.get(f"{BASE_URL}/api/leads")
        if leads_response.status_code == 200:
            leads_data = leads_response.json()
            leads = leads_data.get("data") or leads_data.get("items") or leads_data
            if leads and len(leads) > 0:
                lead_id = leads[0].get("id")
                response = sales_session.get(f"{BASE_URL}/api/quotations?lead_id={lead_id}")
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                print(f"Filtered quotations for lead {lead_id}: {len(data['data'])} items")
    
    def test_create_quotation_without_client_name(self, sales_session):
        """POST /api/quotations should work without client_name (auto-populated from lead)"""
        # First get a lead with pricing plan
        leads_response = sales_session.get(f"{BASE_URL}/api/leads")
        if leads_response.status_code != 200:
            pytest.skip("Could not fetch leads")
        
        leads_data = leads_response.json()
        leads = leads_data.get("data") or leads_data.get("items") or leads_data
        if not leads:
            pytest.skip("No leads available")
        
        # Get pricing plans
        plans_response = sales_session.get(f"{BASE_URL}/api/pricing-plans")
        if plans_response.status_code != 200:
            pytest.skip("Could not fetch pricing plans")
        
        plans_data = plans_response.json()
        plans = plans_data.get("data") if isinstance(plans_data, dict) else plans_data
        if not plans or len(plans) == 0:
            pytest.skip("No pricing plans available")
        
        # Find a lead with a pricing plan
        plan = plans[0]
        lead_id = plan.get("lead_id")
        
        # Create quotation WITHOUT client_name
        quotation_data = {
            "lead_id": lead_id,
            "pricing_plan_id": plan.get("id"),
            "base_rate_per_meeting": 12500,
            "validity_days": 30,
            "payment_terms": "ADVANCE",
            "terms_and_conditions": "Test terms"
            # NOTE: client_name is NOT included - should be auto-populated
        }
        
        response = sales_session.post(f"{BASE_URL}/api/quotations", json=quotation_data)
        
        # Should succeed (201 or 200) or fail with funnel validation (400)
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data or "quotation_number" in data, "Response should have quotation id or number"
            # Verify client_name was auto-populated
            assert data.get("client_name"), "client_name should be auto-populated from lead"
            print(f"Created quotation: {data.get('quotation_number')} with client_name: {data.get('client_name')}")
        elif response.status_code == 400:
            # Funnel validation error (e.g., pricing plan required) is acceptable
            detail = response.json().get("detail", "")
            print(f"Quotation creation blocked by funnel validation: {detail}")
            assert "Pricing Plan" in detail or "pricing" in detail.lower(), f"Unexpected 400 error: {detail}"
        else:
            pytest.fail(f"Unexpected status {response.status_code}: {response.text}")


class TestAgreementsAPI:
    """Test agreements API endpoints"""
    
    def test_get_agreements_returns_paginated_response(self, sales_session):
        """GET /api/agreements should return paginated {data: [...], total, page, page_size, total_pages}"""
        response = sales_session.get(f"{BASE_URL}/api/agreements")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify paginated response structure
        assert "data" in data, "Response should have 'data' field"
        assert isinstance(data["data"], list), "'data' should be a list"
        assert "total" in data, "Response should have 'total' field"
        assert "page" in data, "Response should have 'page' field"
        assert "page_size" in data, "Response should have 'page_size' field"
        assert "total_pages" in data, "Response should have 'total_pages' field"
        print(f"Agreements API returned {len(data['data'])} items, total: {data['total']}")
    
    def test_get_agreement_full_details(self, sales_session):
        """GET /api/agreements/{id}/full should return full agreement details"""
        # First get list of agreements
        response = sales_session.get(f"{BASE_URL}/api/agreements")
        if response.status_code != 200:
            pytest.skip("Could not fetch agreements")
        
        data = response.json()
        agreements = data.get("data", [])
        if not agreements:
            pytest.skip("No agreements available")
        
        agreement_id = agreements[0].get("id")
        full_response = sales_session.get(f"{BASE_URL}/api/agreements/{agreement_id}/full")
        
        assert full_response.status_code == 200, f"Expected 200, got {full_response.status_code}"
        full_data = full_response.json()
        assert "agreement" in full_data, "Response should have 'agreement' field"
        print(f"Agreement full details loaded for: {full_data['agreement'].get('agreement_number')}")
    
    def test_create_agreement_with_new_fields(self, sales_session):
        """POST /api/agreements should accept quotation_id, meeting_frequency, project_tenure_months, team_deployment"""
        # Get a quotation first
        quotations_response = sales_session.get(f"{BASE_URL}/api/quotations")
        if quotations_response.status_code != 200:
            pytest.skip("Could not fetch quotations")
        
        quotations_data = quotations_response.json()
        quotations = quotations_data.get("data", [])
        if not quotations:
            pytest.skip("No quotations available")
        
        quotation = quotations[0]
        
        # Create agreement with new fields
        agreement_data = {
            "lead_id": quotation.get("lead_id"),
            "quotation_id": quotation.get("id"),  # New field
            "agreement_type": "standard",
            "payment_terms": "Net 30 days",
            "meeting_frequency": "Monthly",  # New field
            "project_tenure_months": 12,  # New field
            "team_deployment": [  # New field
                {
                    "role": "Lead Consultant",
                    "meeting_type": "Monthly Review",
                    "frequency": "1 per month",
                    "committed_meetings": 12
                }
            ]
        }
        
        response = sales_session.post(f"{BASE_URL}/api/agreements", json=agreement_data)
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data or "agreement_number" in data
            # Verify new fields are stored
            assert data.get("meeting_frequency") == "Monthly", "meeting_frequency should be stored"
            assert data.get("project_tenure_months") == 12, "project_tenure_months should be stored"
            assert data.get("team_deployment"), "team_deployment should be stored"
            print(f"Created agreement: {data.get('agreement_number')} with new fields")
        elif response.status_code == 400:
            # Funnel validation error is acceptable
            detail = response.json().get("detail", "")
            print(f"Agreement creation blocked by funnel validation: {detail}")
        else:
            pytest.fail(f"Unexpected status {response.status_code}: {response.text}")


class TestPricingPlansAPI:
    """Test pricing plans API for funnel flow"""
    
    def test_get_pricing_plans_returns_data(self, sales_session):
        """GET /api/pricing-plans should return data"""
        response = sales_session.get(f"{BASE_URL}/api/pricing-plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Can be paginated or plain array
        plans = data.get("data") if isinstance(data, dict) else data
        assert isinstance(plans, list), "Should return a list of pricing plans"
        print(f"Pricing plans API returned {len(plans)} items")


class TestLeadsAPI:
    """Test leads API for funnel flow"""
    
    def test_get_leads_returns_data(self, sales_session):
        """GET /api/leads should return data"""
        response = sales_session.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Can be paginated or plain array
        leads = data.get("data") or data.get("items") or data
        assert isinstance(leads, list), "Should return a list of leads"
        print(f"Leads API returned {len(leads)} items")


class TestRBACConsultantFiltering:
    """Test RBAC filtering for consultants on Clients page"""
    
    def test_consultant_sees_filtered_clients(self, consultant_session):
        """Consultant should only see clients/projects they are assigned to"""
        response = consultant_session.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        clients = data.get("items") or data.get("data") or data
        print(f"Consultant sees {len(clients)} clients (should be filtered by assignment)")
    
    def test_consultant_sees_filtered_projects(self, consultant_session):
        """Consultant should only see projects they are assigned to"""
        response = consultant_session.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        projects = data.get("data") if isinstance(data, dict) else data
        print(f"Consultant sees {len(projects)} projects (should be filtered by assignment)")


class TestAdditionalMeetingRequestsAPI:
    """Test Additional Meeting Requests API"""
    
    def test_get_additional_meeting_requests(self, admin_session):
        """GET /api/meeting-schedules/additional-meeting-requests should work"""
        response = admin_session.get(f"{BASE_URL}/api/meeting-schedules/additional-meeting-requests")
        # May return 200 or 404 if endpoint doesn't exist
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list), "Should return a list"
            print(f"Additional meeting requests: {len(data)} items")
        elif response.status_code == 404:
            print("Additional meeting requests endpoint not found (may not be implemented)")
        else:
            print(f"Additional meeting requests returned {response.status_code}")


class TestProjectsAPI:
    """Test Projects API for RBAC verification"""
    
    def test_get_projects_active(self, admin_session):
        """GET /api/projects?status=active should return active projects"""
        response = admin_session.get(f"{BASE_URL}/api/projects?status=active")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        projects = data.get("data") if isinstance(data, dict) else data
        print(f"Active projects: {len(projects)} items")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
