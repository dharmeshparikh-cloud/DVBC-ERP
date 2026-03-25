"""
Sales DataTable API Tests - Sales Module Governance
Tests pagination, filtering, sorting, and standardized response format for:
- GET /api/leads
- GET /api/meetings
- GET /api/follow-ups
- GET /api/quotations

All APIs should return standardized response: {data: [], total: N, page: N, page_size: N, total_pages: N}
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}


class TestAuthentication:
    """Authentication helper tests"""
    
    def test_admin_login(self):
        """Test admin login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"✓ Admin login successful")
        return data["access_token"]
    
    def test_sales_login(self):
        """Test sales executive login and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
        assert response.status_code == 200, f"Sales login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"✓ Sales executive login successful")
        return data["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def sales_token():
    """Get sales executive auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
    if response.status_code != 200:
        pytest.skip(f"Sales login failed: {response.text}")
    return response.json().get("access_token")


@pytest.fixture
def admin_headers(admin_token):
    """Admin auth headers"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def sales_headers(sales_token):
    """Sales auth headers"""
    return {"Authorization": f"Bearer {sales_token}", "Content-Type": "application/json"}


def validate_standardized_response(data, endpoint_name):
    """Validate standardized response format for SalesDataTable APIs"""
    assert "data" in data, f"{endpoint_name}: Missing 'data' field"
    assert "total" in data, f"{endpoint_name}: Missing 'total' field"
    assert "page" in data, f"{endpoint_name}: Missing 'page' field"
    assert "page_size" in data, f"{endpoint_name}: Missing 'page_size' field"
    assert "total_pages" in data, f"{endpoint_name}: Missing 'total_pages' field"
    
    assert isinstance(data["data"], list), f"{endpoint_name}: 'data' should be a list"
    assert isinstance(data["total"], int), f"{endpoint_name}: 'total' should be int"
    assert isinstance(data["page"], int), f"{endpoint_name}: 'page' should be int"
    assert isinstance(data["page_size"], int), f"{endpoint_name}: 'page_size' should be int"
    assert isinstance(data["total_pages"], int), f"{endpoint_name}: 'total_pages' should be int"
    
    # Validate pagination math
    if data["total"] > 0:
        expected_pages = (data["total"] + data["page_size"] - 1) // data["page_size"]
        assert data["total_pages"] == expected_pages, f"{endpoint_name}: total_pages calculation incorrect"
    
    print(f"✓ {endpoint_name}: Standardized response format validated")


# ==================== LEADS API TESTS ====================

class TestLeadsAPI:
    """Tests for GET /api/leads with pagination, filtering, and sorting"""
    
    def test_leads_basic_pagination(self, admin_headers):
        """Test basic pagination with page and page_size"""
        # Test page 1 with page_size 10
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"page": 1, "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Leads API failed: {response.text}"
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads")
        assert data["page"] == 1, "Page should be 1"
        assert data["page_size"] == 10, "Page size should be 10"
        assert len(data["data"]) <= 10, "Should return at most 10 items"
        print(f"✓ Leads basic pagination: {len(data['data'])} items, total: {data['total']}")
    
    def test_leads_pagination_page_2(self, admin_headers):
        """Test pagination page 2"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"page": 2, "page_size": 5},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads page 2")
        assert data["page"] == 2, "Page should be 2"
        assert data["page_size"] == 5, "Page size should be 5"
        print(f"✓ Leads pagination page 2: {len(data['data'])} items")
    
    def test_leads_sorting_asc(self, admin_headers):
        """Test sorting by created_at ascending"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"sort_field": "created_at", "sort_direction": "asc", "page_size": 5},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads sort asc")
        
        # Verify ascending order if we have multiple items
        if len(data["data"]) >= 2:
            dates = [item.get("created_at", "") for item in data["data"]]
            assert dates == sorted(dates), "Items should be sorted ascending by created_at"
        print(f"✓ Leads sorting ascending verified")
    
    def test_leads_sorting_desc(self, admin_headers):
        """Test sorting by created_at descending"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"sort_field": "created_at", "sort_direction": "desc", "page_size": 5},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads sort desc")
        
        # Verify descending order if we have multiple items
        if len(data["data"]) >= 2:
            dates = [item.get("created_at", "") for item in data["data"]]
            assert dates == sorted(dates, reverse=True), "Items should be sorted descending by created_at"
        print(f"✓ Leads sorting descending verified")
    
    def test_leads_search_filter(self, admin_headers):
        """Test search filter (searches in name, company, email)"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"search": "test", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads search")
        print(f"✓ Leads search filter: {data['total']} results for 'test'")
    
    def test_leads_status_filter(self, admin_headers):
        """Test status filter"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"status": "new", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads status filter")
        
        # Verify all returned items have the correct status
        for item in data["data"]:
            assert item.get("status") == "new", f"Item should have status 'new', got {item.get('status')}"
        print(f"✓ Leads status filter: {data['total']} leads with status 'new'")
    
    def test_leads_deal_value_range_filter(self, admin_headers):
        """Test deal_value_min and deal_value_max range filter"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"deal_value_min": 10000, "deal_value_max": 100000, "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads deal_value range")
        
        # Verify deal values are within range
        for item in data["data"]:
            deal_value = item.get("deal_value")
            if deal_value is not None:
                assert 10000 <= deal_value <= 100000, f"Deal value {deal_value} outside range"
        print(f"✓ Leads deal_value range filter: {data['total']} leads in range 10000-100000")
    
    def test_leads_combined_filters(self, admin_headers):
        """Test combining multiple filters"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={
                "page": 1,
                "page_size": 20,
                "sort_field": "company",
                "sort_direction": "asc"
            },
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads combined filters")
        print(f"✓ Leads combined filters: {data['total']} total, {len(data['data'])} returned")


# ==================== MEETINGS API TESTS ====================

class TestMeetingsAPI:
    """Tests for GET /api/meetings with pagination, filtering, and sorting"""
    
    def test_meetings_basic_pagination(self, admin_headers):
        """Test basic pagination"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"page": 1, "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Meetings API failed: {response.text}"
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings")
        assert data["page"] == 1
        assert data["page_size"] == 10
        print(f"✓ Meetings basic pagination: {len(data['data'])} items, total: {data['total']}")
    
    def test_meetings_sorting(self, admin_headers):
        """Test sorting by meeting_date"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"sort_field": "meeting_date", "sort_direction": "desc", "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings sort")
        print(f"✓ Meetings sorting by meeting_date desc verified")
    
    def test_meetings_date_from_filter(self, admin_headers):
        """Test date_from filter"""
        # Filter meetings from 30 days ago
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"date_from": date_from, "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings date_from")
        print(f"✓ Meetings date_from filter: {data['total']} meetings from {date_from}")
    
    def test_meetings_date_to_filter(self, admin_headers):
        """Test date_to filter"""
        date_to = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"date_to": date_to, "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings date_to")
        print(f"✓ Meetings date_to filter: {data['total']} meetings until {date_to}")
    
    def test_meetings_date_range_filter(self, admin_headers):
        """Test date_from and date_to combined"""
        date_from = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        date_to = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"date_from": date_from, "date_to": date_to, "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings date range")
        print(f"✓ Meetings date range filter: {data['total']} meetings in range")
    
    def test_meetings_search_filter(self, admin_headers):
        """Test search filter"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"search": "client", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings search")
        print(f"✓ Meetings search filter: {data['total']} results for 'client'")


# ==================== FOLLOW-UPS API TESTS ====================

class TestFollowUpsAPI:
    """Tests for GET /api/follow-ups with pagination, filtering, and sorting"""
    
    def test_followups_basic_pagination(self, admin_headers):
        """Test basic pagination"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"page": 1, "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Follow-ups API failed: {response.text}"
        data = response.json()
        
        validate_standardized_response(data, "GET /api/follow-ups")
        assert data["page"] == 1
        assert data["page_size"] == 10
        print(f"✓ Follow-ups basic pagination: {len(data['data'])} items, total: {data['total']}")
    
    def test_followups_sorting(self, admin_headers):
        """Test sorting by due_date"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"sort_field": "due_date", "sort_direction": "asc", "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/follow-ups sort")
        print(f"✓ Follow-ups sorting by due_date asc verified")
    
    def test_followups_due_date_today_filter(self, admin_headers):
        """Test due_date=TODAY filter"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"due_date": "TODAY", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/follow-ups due_date=TODAY")
        print(f"✓ Follow-ups due_date=TODAY filter: {data['total']} follow-ups due today")
    
    def test_followups_priority_filter(self, admin_headers):
        """Test priority filter"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"priority": "high", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/follow-ups priority")
        
        # Verify all returned items have high priority
        for item in data["data"]:
            assert item.get("priority") == "high", f"Item should have priority 'high'"
        print(f"✓ Follow-ups priority filter: {data['total']} high priority follow-ups")
    
    def test_followups_status_filter(self, admin_headers):
        """Test status filter"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"status": "open", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/follow-ups status")
        
        # Verify all returned items have open status
        for item in data["data"]:
            assert item.get("status") == "open", f"Item should have status 'open'"
        print(f"✓ Follow-ups status filter: {data['total']} open follow-ups")
    
    def test_followups_entity_type_filter(self, admin_headers):
        """Test entity_type filter"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"entity_type": "lead", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/follow-ups entity_type")
        
        # Verify all returned items have entity_type lead
        for item in data["data"]:
            assert item.get("entity_type") == "lead", f"Item should have entity_type 'lead'"
        print(f"✓ Follow-ups entity_type filter: {data['total']} lead follow-ups")


# ==================== QUOTATIONS API TESTS ====================

class TestQuotationsAPI:
    """Tests for GET /api/quotations with pagination, filtering, and sorting"""
    
    def test_quotations_basic_pagination(self, admin_headers):
        """Test basic pagination"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            params={"page": 1, "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Quotations API failed: {response.text}"
        data = response.json()
        
        validate_standardized_response(data, "GET /api/quotations")
        assert data["page"] == 1
        assert data["page_size"] == 10
        print(f"✓ Quotations basic pagination: {len(data['data'])} items, total: {data['total']}")
    
    def test_quotations_sorting(self, admin_headers):
        """Test sorting by created_at"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            params={"sort_field": "created_at", "sort_direction": "desc", "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/quotations sort")
        print(f"✓ Quotations sorting by created_at desc verified")
    
    def test_quotations_value_range_filter(self, admin_headers):
        """Test value_min and value_max range filter"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            params={"value_min": 1000, "value_max": 500000, "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/quotations value range")
        print(f"✓ Quotations value range filter: {data['total']} quotations in range 1000-500000")
    
    def test_quotations_status_filter(self, admin_headers):
        """Test status filter"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            params={"status": "draft", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/quotations status")
        
        # Verify all returned items have draft status
        for item in data["data"]:
            assert item.get("status") == "draft", f"Item should have status 'draft'"
        print(f"✓ Quotations status filter: {data['total']} draft quotations")
    
    def test_quotations_search_filter(self, admin_headers):
        """Test search filter"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            params={"search": "consulting", "page_size": 50},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/quotations search")
        print(f"✓ Quotations search filter: {data['total']} results for 'consulting'")


# ==================== SALES EXECUTIVE ACCESS TESTS ====================

class TestSalesExecutiveAccess:
    """Test that sales executive can access all sales module APIs"""
    
    def test_sales_exec_leads_access(self, sales_headers):
        """Sales executive should be able to access leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"page": 1, "page_size": 10},
            headers=sales_headers
        )
        assert response.status_code == 200, f"Sales exec leads access failed: {response.text}"
        data = response.json()
        validate_standardized_response(data, "Sales exec GET /api/leads")
        print(f"✓ Sales executive can access leads API")
    
    def test_sales_exec_meetings_access(self, sales_headers):
        """Sales executive should be able to access meetings"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"page": 1, "page_size": 10},
            headers=sales_headers
        )
        assert response.status_code == 200, f"Sales exec meetings access failed: {response.text}"
        data = response.json()
        validate_standardized_response(data, "Sales exec GET /api/meetings")
        print(f"✓ Sales executive can access meetings API")
    
    def test_sales_exec_followups_access(self, sales_headers):
        """Sales executive should be able to access follow-ups"""
        response = requests.get(
            f"{BASE_URL}/api/follow-ups",
            params={"page": 1, "page_size": 10},
            headers=sales_headers
        )
        assert response.status_code == 200, f"Sales exec follow-ups access failed: {response.text}"
        data = response.json()
        validate_standardized_response(data, "Sales exec GET /api/follow-ups")
        print(f"✓ Sales executive can access follow-ups API")
    
    def test_sales_exec_quotations_access(self, sales_headers):
        """Sales executive should be able to access quotations"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            params={"page": 1, "page_size": 10},
            headers=sales_headers
        )
        assert response.status_code == 200, f"Sales exec quotations access failed: {response.text}"
        data = response.json()
        validate_standardized_response(data, "Sales exec GET /api/quotations")
        print(f"✓ Sales executive can access quotations API")


# ==================== EDGE CASES ====================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_leads_empty_page(self, admin_headers):
        """Test requesting a page beyond available data"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"page": 9999, "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads empty page")
        assert len(data["data"]) == 0, "Should return empty data for page beyond range"
        print(f"✓ Empty page returns empty data array")
    
    def test_leads_max_page_size(self, admin_headers):
        """Test maximum page size limit"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"page": 1, "page_size": 1000},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads max page_size")
        assert data["page_size"] <= 1000, "Page size should be capped at max"
        print(f"✓ Max page size handled correctly")
    
    def test_leads_invalid_sort_field(self, admin_headers):
        """Test invalid sort field falls back to default"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            params={"sort_field": "invalid_field", "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/leads invalid sort")
        print(f"✓ Invalid sort field handled gracefully")
    
    def test_meetings_empty_search(self, admin_headers):
        """Test search with no results"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"search": "xyznonexistent12345", "page_size": 10},
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        validate_standardized_response(data, "GET /api/meetings empty search")
        assert data["total"] == 0, "Should return 0 total for non-matching search"
        assert len(data["data"]) == 0, "Should return empty data for non-matching search"
        print(f"✓ Empty search results handled correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
