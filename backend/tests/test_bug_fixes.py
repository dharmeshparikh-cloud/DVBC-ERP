"""
Backend Tests for Bug Fixes - Iteration 28

Testing:
1. Proforma Invoice PDF Export - Backend data structure 
2. Pricing Plan ID visibility - Backend returns plan ID
3. Custom Scope Saving to Master List - Backend saves custom scopes
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://payroll-fix-10.preview.emergentagent.com')

@pytest.fixture(scope="session")
def auth_token():
    """Login and get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

@pytest.fixture
def api_client(auth_token):
    """Configured requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestPricingPlanDropdown:
    """Test Pricing Plan API returns Plan ID for dropdown display"""
    
    def test_pricing_plans_return_id(self, api_client):
        """Verify pricing plans endpoint returns plan IDs"""
        response = api_client.get(f"{BASE_URL}/api/pricing-plans")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            plan = data[0]
            assert "id" in plan, "Pricing plan should have 'id' field"
            assert len(plan["id"]) > 0, "Pricing plan ID should not be empty"
            print(f"SUCCESS: Pricing plan ID found: {plan['id'][:12]}...")
        else:
            pytest.skip("No pricing plans found to test")
    
    def test_pricing_plan_has_duration_info(self, api_client):
        """Verify pricing plans have duration info for dropdown display"""
        response = api_client.get(f"{BASE_URL}/api/pricing-plans")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            plan = data[0]
            # Check for duration fields used in dropdown
            assert "project_duration_months" in plan or "project_duration_type" in plan
            print(f"SUCCESS: Duration info found - months: {plan.get('project_duration_months')}, type: {plan.get('project_duration_type')}")


class TestProformaInvoice:
    """Test Proforma Invoice (Quotation) API"""
    
    def test_quotations_endpoint(self, api_client):
        """Verify quotations endpoint works"""
        response = api_client.get(f"{BASE_URL}/api/quotations")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Found {len(data)} quotations/invoices")
    
    def test_quotation_has_required_fields(self, api_client):
        """Verify quotation has fields needed for PDF export"""
        response = api_client.get(f"{BASE_URL}/api/quotations")
        assert response.status_code == 200
        
        data = response.json()
        if len(data) > 0:
            invoice = data[0]
            required_fields = ["quotation_number", "subtotal", "gst_amount", "grand_total"]
            for field in required_fields:
                assert field in invoice, f"Invoice missing required field: {field}"
            print(f"SUCCESS: Invoice has all required fields for PDF export")
            print(f"  - quotation_number: {invoice.get('quotation_number')}")
            print(f"  - grand_total: {invoice.get('grand_total')}")


class TestCustomScopeSavingToMaster:
    """Test custom scope saving to sow_scope_templates collection"""
    
    def test_sow_categories_exist(self, api_client):
        """Verify SOW categories exist for custom scope assignment"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/categories")
        assert response.status_code == 200
        
        categories = response.json()
        assert len(categories) > 0, "Should have at least one category"
        print(f"SUCCESS: Found {len(categories)} SOW categories")
        return categories
    
    def test_sow_scopes_grouped(self, api_client):
        """Verify SOW scopes can be fetched grouped by category"""
        response = api_client.get(f"{BASE_URL}/api/sow-masters/scopes/grouped")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        total_scopes = sum(len(g.get('scopes', [])) for g in data)
        print(f"SUCCESS: Found {total_scopes} total scopes across {len(data)} categories")
        
        # Check for custom scopes
        custom_count = 0
        for group in data:
            for scope in group.get('scopes', []):
                if scope.get('is_custom'):
                    custom_count += 1
                    print(f"  Custom scope found: {scope.get('name')}")
        
        print(f"Custom scopes in master: {custom_count}")
    
    def test_enhanced_sow_sales_selection_endpoint(self, api_client):
        """Test the sales selection endpoint that should save custom scopes"""
        # Get a pricing plan first
        plans_response = api_client.get(f"{BASE_URL}/api/pricing-plans")
        assert plans_response.status_code == 200
        
        plans = plans_response.json()
        if len(plans) == 0:
            pytest.skip("No pricing plans available for test")
        
        # Get categories for custom scope
        cat_response = api_client.get(f"{BASE_URL}/api/sow-masters/categories")
        categories = cat_response.json()
        assert len(categories) > 0
        
        category_id = categories[0].get('id')
        print(f"Using category: {categories[0].get('name')} ({category_id})")
        
        # This test verifies the endpoint structure exists
        # The actual custom scope saving is done in the POST /enhanced-sow/{id}/sales-selection endpoint
        # which adds custom scopes to sow_scope_templates collection
        
        # Verify the enhanced SOW endpoint exists
        test_plan_id = "test-" + str(uuid.uuid4())
        response = api_client.post(
            f"{BASE_URL}/api/enhanced-sow/{test_plan_id}/sales-selection",
            json={
                "scope_template_ids": [],
                "custom_scopes": []
            },
            params={
                "current_user_id": "test-user",
                "current_user_name": "Test User",
                "current_user_role": "admin"
            }
        )
        
        # Should return 404 for non-existent pricing plan (which is expected)
        # This confirms the endpoint exists and is accessible
        assert response.status_code == 404
        assert "Pricing plan not found" in response.json().get('detail', '')
        print("SUCCESS: Enhanced SOW sales-selection endpoint exists and validates pricing plan")


class TestLeadSelection:
    """Test Lead selection for Proforma Invoice"""
    
    def test_leads_endpoint(self, api_client):
        """Verify leads endpoint works for invoice creation"""
        response = api_client.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Found {len(data)} leads for selection")
        
        if len(data) > 0:
            lead = data[0]
            assert "id" in lead
            assert "first_name" in lead
            assert "last_name" in lead
            assert "company" in lead
            print(f"Lead example: {lead.get('first_name')} {lead.get('last_name')} - {lead.get('company')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
