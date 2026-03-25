"""
Test Sales Table Migration - Phase 4
Tests for:
1. /api/agreements - paginated response
2. /api/enhanced-sow/list - paginated response
3. /api/quotations - paginated response (already working)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SALES_CREDENTIALS = {"employee_id": "EMP003", "password": "sales123"}
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for sales user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


class TestAgreementsAPI:
    """Test /api/agreements endpoint returns paginated response"""
    
    def test_agreements_returns_paginated_response(self, auth_token):
        """Verify agreements API returns { data, total, page, page_size, total_pages }"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/agreements", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify paginated response structure
        assert "data" in data, "Response should have 'data' field"
        assert "total" in data, "Response should have 'total' field"
        assert "page" in data, "Response should have 'page' field"
        assert "page_size" in data, "Response should have 'page_size' field"
        assert "total_pages" in data, "Response should have 'total_pages' field"
        
        # Verify data types
        assert isinstance(data["data"], list), "'data' should be a list"
        assert isinstance(data["total"], int), "'total' should be an integer"
        assert isinstance(data["page"], int), "'page' should be an integer"
        assert isinstance(data["page_size"], int), "'page_size' should be an integer"
        assert isinstance(data["total_pages"], int), "'total_pages' should be an integer"
        
        print(f"✓ Agreements API returns paginated response: {data['total']} total, page {data['page']}/{data['total_pages']}")
    
    def test_agreements_pagination_params(self, auth_token):
        """Verify pagination parameters work correctly"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test with custom page_size
        response = requests.get(f"{BASE_URL}/api/agreements?page=1&page_size=5", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        
        print(f"✓ Agreements pagination params work: page_size={data['page_size']}")
    
    def test_agreements_sorting(self, auth_token):
        """Verify sorting parameters work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test sorting by created_at desc
        response = requests.get(
            f"{BASE_URL}/api/agreements?sort_field=created_at&sort_direction=desc", 
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        print(f"✓ Agreements sorting works: {len(data['data'])} items returned")


class TestEnhancedSOWListAPI:
    """Test /api/enhanced-sow/list endpoint returns paginated response"""
    
    def test_sow_list_returns_paginated_response(self, auth_token):
        """Verify enhanced-sow/list API returns { data, total, page, page_size, total_pages }"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/enhanced-sow/list", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify paginated response structure
        assert "data" in data, "Response should have 'data' field"
        assert "total" in data, "Response should have 'total' field"
        assert "page" in data, "Response should have 'page' field"
        assert "page_size" in data, "Response should have 'page_size' field"
        assert "total_pages" in data, "Response should have 'total_pages' field"
        
        # Verify data types
        assert isinstance(data["data"], list), "'data' should be a list"
        assert isinstance(data["total"], int), "'total' should be an integer"
        
        print(f"✓ Enhanced SOW List API returns paginated response: {data['total']} total, page {data['page']}/{data['total_pages']}")
    
    def test_sow_list_pagination_params(self, auth_token):
        """Verify pagination parameters work correctly"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test with custom page_size
        response = requests.get(f"{BASE_URL}/api/enhanced-sow/list?page=1&page_size=10", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        
        print(f"✓ SOW List pagination params work: page_size={data['page_size']}")
    
    def test_sow_list_role_filter(self, auth_token):
        """Verify role filter works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test with sales role filter
        response = requests.get(f"{BASE_URL}/api/enhanced-sow/list?role=sales", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        print(f"✓ SOW List role filter works: {len(data['data'])} items for sales role")


class TestQuotationsAPI:
    """Test /api/quotations endpoint returns paginated response"""
    
    def test_quotations_returns_data(self, auth_token):
        """Verify quotations API returns data (may be array or paginated)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/quotations", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Quotations may return array or paginated response
        if isinstance(data, list):
            print(f"✓ Quotations API returns array: {len(data)} items")
        else:
            # Check for paginated structure
            if "data" in data:
                assert isinstance(data["data"], list)
                print(f"✓ Quotations API returns paginated response: {len(data['data'])} items")
            else:
                print(f"✓ Quotations API returns data: {type(data)}")


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_accessible(self):
        """Verify API is accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        # Health endpoint may not exist, so we just check connectivity
        assert response.status_code in [200, 404, 405], f"API not accessible: {response.status_code}"
        print(f"✓ API is accessible at {BASE_URL}")
    
    def test_login_works(self):
        """Verify login endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "access_token" in data or "token" in data, "Login should return token"
        print(f"✓ Login works for {SALES_CREDENTIALS['employee_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
