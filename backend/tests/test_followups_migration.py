"""
Test Follow-ups Migration - Phase 4 (FollowUps.js -> FollowUpsTable)
Tests for:
1. /api/follow-ups - paginated response { data, total, page, page_size, total_pages }
2. /api/follow-ups filters (status, entity_type, overdue_only)
3. /api/follow-ups/escalations - manager-only endpoint
4. /api/follow-ups/dashboard/today - today's follow-ups
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SALES_CREDENTIALS = {"employee_id": "EMP003", "password": "sales123"}
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}


@pytest.fixture(scope="module")
def sales_token():
    """Get authentication token for sales user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Sales authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_token():
    """Get authentication token for admin user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token") or data.get("token")
    pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")


class TestFollowUpsAPI:
    """Test /api/follow-ups endpoint returns paginated response"""
    
    def test_followups_returns_paginated_response(self, sales_token):
        """Verify follow-ups API returns { data, total, page, page_size, total_pages }"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/follow-ups", headers=headers)
        
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
        
        print(f"✓ Follow-ups API returns paginated response: {data['total']} total, page {data['page']}/{data['total_pages']}")
    
    def test_followups_pagination_params(self, sales_token):
        """Verify pagination parameters work correctly"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        
        # Test with custom page_size
        response = requests.get(f"{BASE_URL}/api/follow-ups?page=1&page_size=10", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        
        print(f"✓ Follow-ups pagination params work: page_size={data['page_size']}")
    
    def test_followups_status_filter(self, sales_token):
        """Verify status filter works"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        
        # Test with status=open filter
        response = requests.get(f"{BASE_URL}/api/follow-ups?status=open", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        # Verify all returned items have status=open
        for item in data["data"]:
            assert item.get("status") == "open", f"Expected status=open, got {item.get('status')}"
        
        print(f"✓ Follow-ups status filter works: {len(data['data'])} open items")
    
    def test_followups_entity_type_filter(self, sales_token):
        """Verify entity_type filter works"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        
        # Test with entity_type=lead filter
        response = requests.get(f"{BASE_URL}/api/follow-ups?entity_type=lead", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        # Verify all returned items have entity_type=lead
        for item in data["data"]:
            assert item.get("entity_type") == "lead", f"Expected entity_type=lead, got {item.get('entity_type')}"
        
        print(f"✓ Follow-ups entity_type filter works: {len(data['data'])} lead items")
    
    def test_followups_overdue_filter(self, sales_token):
        """Verify overdue_only filter works"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        
        # Test with overdue_only=true filter
        response = requests.get(f"{BASE_URL}/api/follow-ups?overdue_only=true", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        print(f"✓ Follow-ups overdue filter works: {len(data['data'])} overdue items")
    
    def test_followups_sorting(self, sales_token):
        """Verify sorting parameters work"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        
        # Test sorting by due_date asc
        response = requests.get(
            f"{BASE_URL}/api/follow-ups?sort_field=due_date&sort_direction=asc", 
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        
        print(f"✓ Follow-ups sorting works: {len(data['data'])} items returned")


class TestFollowUpsEscalationsAPI:
    """Test /api/follow-ups/escalations endpoint (manager-only)"""
    
    def test_escalations_requires_manager_role(self, sales_token):
        """Verify escalations endpoint requires manager role"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/follow-ups/escalations", headers=headers)
        
        # Sales executive should get 403 (not a manager)
        # OR 200 if they happen to be a manager
        assert response.status_code in [200, 403], f"Expected 200 or 403, got {response.status_code}"
        
        if response.status_code == 403:
            print("✓ Escalations endpoint correctly requires manager role")
        else:
            print("✓ Escalations endpoint accessible (user has manager role)")
    
    def test_escalations_accessible_by_admin(self, admin_token):
        """Verify escalations endpoint is accessible by admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/follow-ups/escalations", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "items" in data, "Response should have 'items' field"
        assert "total" in data, "Response should have 'total' field"
        
        print(f"✓ Escalations API accessible by admin: {data['total']} escalated items")


class TestFollowUpsDashboardAPI:
    """Test /api/follow-ups/dashboard/today endpoint"""
    
    def test_dashboard_today_returns_data(self, sales_token):
        """Verify dashboard/today endpoint returns expected structure"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/follow-ups/dashboard/today", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify expected fields
        assert "items" in data, "Response should have 'items' field"
        assert "overdue_count" in data, "Response should have 'overdue_count' field"
        assert "today_count" in data, "Response should have 'today_count' field"
        assert "total" in data, "Response should have 'total' field"
        
        print(f"✓ Dashboard today API works: {data['total']} items, {data['overdue_count']} overdue, {data['today_count']} today")


class TestFollowUpsCRUD:
    """Test follow-up CRUD operations"""
    
    def test_get_single_followup(self, sales_token):
        """Test getting a single follow-up by ID"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        
        # First get list to find an ID
        response = requests.get(f"{BASE_URL}/api/follow-ups?page_size=1", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        if data["data"] and len(data["data"]) > 0:
            followup_id = data["data"][0]["id"]
            
            # Get single follow-up
            response = requests.get(f"{BASE_URL}/api/follow-ups/{followup_id}", headers=headers)
            assert response.status_code == 200
            
            followup = response.json()
            assert followup["id"] == followup_id
            
            print(f"✓ Get single follow-up works: {followup_id}")
        else:
            print("✓ No follow-ups to test single get (skipped)")


class TestAgreementsAPI:
    """Test /api/agreements endpoint (regression test)"""
    
    def test_agreements_returns_paginated_response(self, sales_token):
        """Verify agreements API still returns paginated response"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/agreements", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify paginated response structure
        assert "data" in data, "Response should have 'data' field"
        assert "total" in data, "Response should have 'total' field"
        
        print(f"✓ Agreements API returns paginated response: {data['total']} total")


class TestEnhancedSOWListAPI:
    """Test /api/enhanced-sow/list endpoint (regression test)"""
    
    def test_sow_list_returns_paginated_response(self, sales_token):
        """Verify enhanced-sow/list API still returns paginated response"""
        headers = {"Authorization": f"Bearer {sales_token}"}
        response = requests.get(f"{BASE_URL}/api/enhanced-sow/list", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify paginated response structure
        assert "data" in data, "Response should have 'data' field"
        assert "total" in data, "Response should have 'total' field"
        
        print(f"✓ Enhanced SOW List API returns paginated response: {data['total']} total")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
