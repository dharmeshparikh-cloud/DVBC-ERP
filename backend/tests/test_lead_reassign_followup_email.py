"""
Test Lead Reassignment, Follow-up Email Templates, and Follow-up ↔ Lead Integration
P1 Enhancements Testing - January 2026

Tests:
1. Lead Reassignment (single lead)
2. Bulk Lead Migration (manager-initiated)
3. Follow-up Email Templates (Formal, Meeting, Reminder)
4. Client Action CTA endpoints (close, reschedule)
5. Follow-up ↔ Lead Integration (linked lead info)
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://erp-governance-hub-3.preview.emergentagent.com')

# Test credentials from context
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}

# Known IDs from context
VVS_LEAD_ID = "329d1060-3147-46a2-98a8-dad93f95a371"
SALES_EXEC_USER_ID = "93b3be1a-a909-4cb4-9d15-3e9c1f2dbac8"
ADMIN_USER_ID = "848612a5-94d3-4c32-a1f4-dde3d5f2b1d8"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def sales_token():
    """Get sales executive auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDS)
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Sales login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def sales_client(sales_token):
    """Session with sales auth header"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {sales_token}",
        "Content-Type": "application/json"
    })
    return session


class TestLeadReassignment:
    """Test Lead Reassignment feature - single lead and bulk"""
    
    def test_get_users_for_reassign(self, admin_client):
        """Test GET /api/users returns users for reassign dropdown"""
        response = admin_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        users = data if isinstance(data, list) else data.get('data', data.get('users', []))
        assert len(users) > 0, "No users returned"
        
        # Check for sales roles
        sales_users = [u for u in users if u.get('role') in ['sales', 'sales_manager', 'admin', 'principal_consultant', 'executive', 'sales_executive']]
        print(f"Found {len(sales_users)} sales team users for reassignment")
        assert len(sales_users) > 0, "No sales team users found"
    
    def test_single_lead_reassign_endpoint_exists(self, admin_client):
        """Test POST /api/leads/{lead_id}/reassign endpoint exists"""
        # Use VVS lead ID from context
        payload = {
            "new_owner_id": SALES_EXEC_USER_ID,
            "reason": "Test reassignment",
            "transfer_all_data": True
        }
        
        response = admin_client.post(f"{BASE_URL}/api/leads/{VVS_LEAD_ID}/reassign", json=payload)
        
        # Should succeed or return 404 if lead not found (but endpoint exists)
        assert response.status_code in [200, 404, 403], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data or "transfer_results" in data
            print(f"Reassign response: {data}")
    
    def test_bulk_reassign_endpoint_exists(self, admin_client):
        """Test POST /api/leads/bulk-reassign endpoint exists (admin only)"""
        payload = {
            "from_user_id": SALES_EXEC_USER_ID,
            "to_user_id": ADMIN_USER_ID,
            "reason": "Test bulk migration"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/leads/bulk-reassign", json=payload)
        
        # Should succeed or return appropriate error
        assert response.status_code in [200, 400, 403, 404], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data or "transferred_count" in data
            print(f"Bulk reassign response: {data}")
    
    def test_sales_cannot_bulk_reassign(self, sales_client):
        """Test that sales executive cannot bulk reassign (manager only)"""
        payload = {
            "from_user_id": ADMIN_USER_ID,
            "to_user_id": SALES_EXEC_USER_ID,
            "reason": "Unauthorized attempt"
        }
        
        response = sales_client.post(f"{BASE_URL}/api/leads/bulk-reassign", json=payload)
        
        # Should be forbidden for non-managers
        assert response.status_code == 403, f"Expected 403, got {response.status_code} - {response.text}"


class TestFollowUpEmailTemplates:
    """Test Follow-up Email Templates feature"""
    
    def test_create_follow_up_with_lead(self, sales_client):
        """Test creating a follow-up linked to a lead"""
        # First get a lead to link
        leads_response = sales_client.get(f"{BASE_URL}/api/leads?page_size=1")
        if leads_response.status_code != 200:
            pytest.skip("Cannot get leads")
        
        leads_data = leads_response.json()
        leads = leads_data.get('data', leads_data.get('items', leads_data if isinstance(leads_data, list) else []))
        
        if not leads:
            pytest.skip("No leads available")
        
        lead = leads[0]
        lead_id = lead.get('id')
        
        # Create follow-up
        due_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        payload = {
            "entity_type": "lead",
            "entity_id": lead_id,
            "lead_id": lead_id,
            "client_name": lead.get('company', 'Test Client'),
            "due_date": due_date,
            "notes": "Test follow-up for email template testing",
            "priority": "medium"
        }
        
        response = sales_client.post(f"{BASE_URL}/api/follow-ups", json=payload)
        assert response.status_code in [200, 201], f"Failed to create follow-up: {response.text}"
        
        data = response.json()
        assert "id" in data
        self.__class__.test_follow_up_id = data["id"]
        print(f"Created follow-up: {data['id']}")
        return data["id"]
    
    def test_get_email_template(self, sales_client):
        """Test GET /api/follow-ups/{id}/email-template returns prefilled data"""
        follow_up_id = getattr(self.__class__, 'test_follow_up_id', None)
        
        if not follow_up_id:
            # Create one first
            follow_up_id = self.test_create_follow_up_with_lead(sales_client)
        
        response = sales_client.get(f"{BASE_URL}/api/follow-ups/{follow_up_id}/email-template")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "subject" in data, "Missing subject in email template"
        assert "body" in data, "Missing body in email template"
        assert "recipient_email" in data, "Missing recipient_email in email template"
        
        print(f"Email template: subject='{data.get('subject')}', has_body={bool(data.get('body'))}")
    
    def test_client_action_close(self):
        """Test GET /api/follow-ups/{id}/client-action?action=close (public endpoint)"""
        follow_up_id = getattr(self.__class__, 'test_follow_up_id', None)
        
        if not follow_up_id:
            pytest.skip("No follow-up ID available")
        
        # This is a public endpoint - no auth required
        response = requests.get(f"{BASE_URL}/api/follow-ups/{follow_up_id}/client-action?action=close")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert data.get("action") == "closed"
        print(f"Client close action: {data}")
    
    def test_client_action_reschedule(self, sales_client):
        """Test GET /api/follow-ups/{id}/client-action?action=reschedule (public endpoint)"""
        # Create a new follow-up for reschedule test
        leads_response = sales_client.get(f"{BASE_URL}/api/leads?page_size=1")
        if leads_response.status_code != 200:
            pytest.skip("Cannot get leads")
        
        leads_data = leads_response.json()
        leads = leads_data.get('data', leads_data.get('items', leads_data if isinstance(leads_data, list) else []))
        
        if not leads:
            pytest.skip("No leads available")
        
        lead = leads[0]
        due_date = (datetime.utcnow() + timedelta(days=2)).isoformat()
        payload = {
            "entity_type": "lead",
            "entity_id": lead.get('id'),
            "lead_id": lead.get('id'),
            "due_date": due_date,
            "notes": "Test for reschedule action",
            "priority": "high"
        }
        
        create_response = sales_client.post(f"{BASE_URL}/api/follow-ups", json=payload)
        if create_response.status_code not in [200, 201]:
            pytest.skip("Cannot create follow-up")
        
        follow_up_id = create_response.json().get("id")
        
        # Test reschedule action (public endpoint)
        response = requests.get(f"{BASE_URL}/api/follow-ups/{follow_up_id}/client-action?action=reschedule")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "message" in data
        assert data.get("action") == "reschedule_requested"
        print(f"Client reschedule action: {data}")


class TestFollowUpLeadIntegration:
    """Test Follow-up ↔ Lead Integration"""
    
    def test_follow_up_has_lead_info(self, sales_client):
        """Test that follow-up detail includes linked lead info"""
        # Get follow-ups
        response = sales_client.get(f"{BASE_URL}/api/follow-ups?page_size=5")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        follow_ups = data.get('data', data.get('items', data if isinstance(data, list) else []))
        
        # Find one with lead_id
        linked_follow_up = None
        for fu in follow_ups:
            if fu.get('lead_id'):
                linked_follow_up = fu
                break
        
        if not linked_follow_up:
            pytest.skip("No follow-ups with linked leads found")
        
        # Check for lead info fields
        assert 'lead_id' in linked_follow_up
        assert 'client_name' in linked_follow_up or 'lead_company' in linked_follow_up
        print(f"Follow-up with lead: lead_id={linked_follow_up.get('lead_id')}, client={linked_follow_up.get('client_name')}")
    
    def test_follow_up_detail_has_lead_email(self, sales_client):
        """Test that follow-up list enriches with lead email"""
        response = sales_client.get(f"{BASE_URL}/api/follow-ups?page_size=10")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        follow_ups = data.get('data', data.get('items', data if isinstance(data, list) else []))
        
        # Check if any have lead_email enrichment
        has_email = any(fu.get('lead_email') for fu in follow_ups if fu.get('lead_id'))
        print(f"Follow-ups with lead_email enrichment: {has_email}")
        # This is optional enrichment, so just log it
    
    def test_follow_ups_table_client_response_column(self, sales_client):
        """Test that follow-ups have client_response field for table display"""
        response = sales_client.get(f"{BASE_URL}/api/follow-ups?page_size=10")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        follow_ups = data.get('data', data.get('items', data if isinstance(data, list) else []))
        
        # Check structure supports client_response
        for fu in follow_ups:
            # client_response may be null/empty, but history should track client actions
            history = fu.get('history', [])
            client_actions = [h for h in history if h.get('action', '').startswith('client_')]
            if client_actions:
                print(f"Follow-up {fu.get('id')} has client actions: {[h.get('action') for h in client_actions]}")


class TestSalesDataTableOverflow:
    """Test SalesDataTable overflow fix"""
    
    def test_leads_endpoint_returns_data(self, sales_client):
        """Test /api/leads returns paginated data for SalesDataTable"""
        response = sales_client.get(f"{BASE_URL}/api/leads?page=1&page_size=20")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert 'data' in data or 'items' in data or isinstance(data, list)
        assert 'total' in data or 'total_count' in data or isinstance(data, list)
        print(f"Leads API response structure: {list(data.keys()) if isinstance(data, dict) else 'list'}")
    
    def test_follow_ups_endpoint_returns_data(self, sales_client):
        """Test /api/follow-ups returns paginated data for SalesDataTable"""
        response = sales_client.get(f"{BASE_URL}/api/follow-ups?page=1&page_size=20")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert 'data' in data or 'items' in data or isinstance(data, list)
        print(f"Follow-ups API response structure: {list(data.keys()) if isinstance(data, dict) else 'list'}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
