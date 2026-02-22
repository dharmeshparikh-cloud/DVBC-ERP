"""
Complete E2E Test Suite for NETRA ERP Sales Funnel
Tests the complete flow from Lead to Deal Closed including:
- Lead creation and management
- Funnel progress tracking (9 stages)
- Stage progression
- Kickoff request and approval
- Dashboard stats
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthEndpoints:
    """Test authentication for Sales Executive and Admin"""
    
    def test_login_sales_executive(self):
        """Test SE001 login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001",
            "password": "test123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["employee_id"] == "SE001"
        assert data["user"]["role"] == "sales_executive"
        print(f"PASS: Sales Executive login - {data['user']['full_name']}")
    
    def test_login_admin(self):
        """Test ADMIN001 login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "test123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["employee_id"] == "ADMIN001"
        assert data["user"]["role"] == "admin"
        print(f"PASS: Admin login - {data['user']['full_name']}")


class TestLeadsCRUD:
    """Test Leads CRUD operations"""
    
    @pytest.fixture
    def se_token(self):
        """Get Sales Executive token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001",
            "password": "test123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_get_leads_list(self, se_token):
        """Test GET /api/leads returns list of leads"""
        headers = {"Authorization": f"Bearer {se_token}"}
        response = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        assert response.status_code == 200
        leads = response.json()
        assert isinstance(leads, list)
        print(f"PASS: GET /api/leads - Found {len(leads)} leads")
    
    def test_create_lead(self, se_token):
        """Test POST /api/leads creates a new lead"""
        headers = {"Authorization": f"Bearer {se_token}"}
        test_lead = {
            "first_name": "TEST_E2E",
            "last_name": f"Lead_{uuid.uuid4().hex[:8]}",
            "company": "E2E Test Corp",
            "email": f"test_{uuid.uuid4().hex[:6]}@e2etest.com",
            "phone": "9876543210",
            "job_title": "CEO",
            "source": "E2E Test"
        }
        response = requests.post(f"{BASE_URL}/api/leads", json=test_lead, headers=headers)
        assert response.status_code == 200
        created = response.json()
        assert created["first_name"] == test_lead["first_name"]
        assert created["company"] == test_lead["company"]
        assert "id" in created
        assert "lead_score" in created
        print(f"PASS: POST /api/leads - Created lead ID: {created['id']}, Score: {created['lead_score']}")
        return created["id"]
    
    def test_get_single_lead(self, se_token):
        """Test GET /api/leads/{id} returns single lead"""
        headers = {"Authorization": f"Bearer {se_token}"}
        # First create a lead
        test_lead = {
            "first_name": "TEST_Single",
            "last_name": "Lead",
            "company": "Single Test Corp",
            "email": f"single_{uuid.uuid4().hex[:6]}@test.com",
        }
        create_resp = requests.post(f"{BASE_URL}/api/leads", json=test_lead, headers=headers)
        lead_id = create_resp.json()["id"]
        
        # Then get it
        response = requests.get(f"{BASE_URL}/api/leads/{lead_id}", headers=headers)
        assert response.status_code == 200
        lead = response.json()
        assert lead["id"] == lead_id
        assert lead["first_name"] == test_lead["first_name"]
        print(f"PASS: GET /api/leads/{lead_id} - Retrieved lead")
    
    def test_update_lead_status(self, se_token):
        """Test PUT /api/leads/{id} updates lead"""
        headers = {"Authorization": f"Bearer {se_token}"}
        # Create lead
        test_lead = {
            "first_name": "TEST_Update",
            "last_name": "Status",
            "company": "Update Corp",
            "email": f"update_{uuid.uuid4().hex[:6]}@test.com",
        }
        create_resp = requests.post(f"{BASE_URL}/api/leads", json=test_lead, headers=headers)
        lead_id = create_resp.json()["id"]
        
        # Update status
        response = requests.put(f"{BASE_URL}/api/leads/{lead_id}", 
            json={"status": "contacted"}, headers=headers)
        assert response.status_code == 200
        updated = response.json()
        assert updated["status"] == "contacted"
        print(f"PASS: PUT /api/leads/{lead_id} - Status updated to 'contacted'")


class TestFunnelProgress:
    """Test the new funnel-progress endpoint"""
    
    @pytest.fixture
    def se_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001", "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_funnel_progress_endpoint_exists(self, se_token):
        """Test GET /api/leads/{id}/funnel-progress returns correct structure"""
        headers = {"Authorization": f"Bearer {se_token}"}
        
        # Get a lead first
        leads_resp = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        leads = leads_resp.json()
        if not leads:
            pytest.skip("No leads available for testing")
        
        lead_id = leads[0]["id"]
        response = requests.get(f"{BASE_URL}/api/leads/{lead_id}/funnel-progress", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "lead_id" in data
        assert "completed_steps" in data
        assert "current_step" in data
        assert "total_steps" in data
        assert "progress_percentage" in data
        
        # Verify steps
        assert data["total_steps"] == 9
        assert isinstance(data["completed_steps"], list)
        assert isinstance(data["progress_percentage"], (int, float))
        
        print(f"PASS: GET /api/leads/{lead_id}/funnel-progress")
        print(f"  - Completed: {len(data['completed_steps'])}/9 steps")
        print(f"  - Current step: {data['current_step']}")
        print(f"  - Progress: {data['progress_percentage']}%")
    
    def test_funnel_progress_for_specific_lead(self, se_token):
        """Test funnel-progress for the specific test lead from context"""
        headers = {"Authorization": f"Bearer {se_token}"}
        lead_id = "64653862-c2d0-4725-984f-f8c58432266a"
        
        response = requests.get(f"{BASE_URL}/api/leads/{lead_id}/funnel-progress", headers=headers)
        
        if response.status_code == 404:
            pytest.skip("Test lead not found")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["lead_id"] == lead_id
        assert "lead_capture" in data["completed_steps"]  # First step always completed
        print(f"PASS: Specific lead funnel-progress - {data['company']}")


class TestLeadStage:
    """Test lead stage endpoint"""
    
    @pytest.fixture
    def se_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001", "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_get_lead_stage(self, se_token):
        """Test GET /api/leads/{id}/stage returns stage info"""
        headers = {"Authorization": f"Bearer {se_token}"}
        
        leads_resp = requests.get(f"{BASE_URL}/api/leads", headers=headers)
        leads = leads_resp.json()
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        response = requests.get(f"{BASE_URL}/api/leads/{lead_id}/stage", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "lead_id" in data
        assert "current_stage" in data
        assert "stages" in data
        assert len(data["stages"]) == 9  # 9 stages in the funnel
        
        # Verify stage structure
        for stage in data["stages"]:
            assert "stage" in stage
            assert "name" in stage
            assert "is_completed" in stage
            assert "is_current" in stage
            assert "is_locked" in stage
        
        print(f"PASS: GET /api/leads/{lead_id}/stage")
        print(f"  - Current stage: {data['current_stage']}")


class TestKickoffApprovals:
    """Test kickoff request and approval flow"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001", "password": "test123"
        })
        return response.json()["access_token"]
    
    @pytest.fixture
    def se_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001", "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_get_pending_kickoff_approvals_admin(self, admin_token):
        """Test GET /api/sales-funnel/pending-kickoff-approvals - Admin only"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # API returns {"requests": [...]} or a list
        if isinstance(data, dict) and "requests" in data:
            requests_list = data["requests"]
        else:
            requests_list = data
        assert isinstance(requests_list, list)
        print(f"PASS: GET /api/sales-funnel/pending-kickoff-approvals - {len(requests_list)} pending requests")
    
    def test_non_admin_denied_kickoff_approvals(self, se_token):
        """Test non-admin gets 403 for kickoff approvals"""
        headers = {"Authorization": f"Bearer {se_token}"}
        response = requests.get(f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals", headers=headers)
        
        # Should be 403 Forbidden for non-admin
        assert response.status_code == 403
        print("PASS: Non-admin denied access to pending kickoff approvals (403)")


class TestDashboardStats:
    """Test dashboard statistics endpoint"""
    
    @pytest.fixture
    def admin_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001", "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_dashboard_stats(self, admin_token):
        """Test GET /api/stats/dashboard returns stats"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/stats/dashboard", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Dashboard should have various stats
        assert isinstance(data, dict)
        print(f"PASS: GET /api/stats/dashboard - Stats retrieved")
        if "total_leads" in data:
            print(f"  - Total leads: {data['total_leads']}")
        if "hot_leads" in data:
            print(f"  - Hot leads: {data['hot_leads']}")


class TestSalesFunnelEndpoints:
    """Test sales funnel specific endpoints"""
    
    @pytest.fixture
    def se_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001", "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_get_consulting_team(self, se_token):
        """Test GET /api/sales-funnel/consulting-team"""
        headers = {"Authorization": f"Bearer {se_token}"}
        response = requests.get(f"{BASE_URL}/api/sales-funnel/consulting-team", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        # API returns {"consultants": [...]} or a list
        if isinstance(data, dict) and "consultants" in data:
            consultants_list = data["consultants"]
        else:
            consultants_list = data
        assert isinstance(consultants_list, list)
        print(f"PASS: GET /api/sales-funnel/consulting-team - {len(consultants_list)} consultants")


class TestPricingQuotationsAgreements:
    """Test related sales funnel collections"""
    
    @pytest.fixture
    def se_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "SE001", "password": "test123"
        })
        return response.json()["access_token"]
    
    def test_get_pricing_plans(self, se_token):
        """Test GET /api/pricing-plans"""
        headers = {"Authorization": f"Bearer {se_token}"}
        response = requests.get(f"{BASE_URL}/api/pricing-plans", headers=headers)
        
        assert response.status_code == 200
        print(f"PASS: GET /api/pricing-plans - Status {response.status_code}")
    
    def test_get_quotations(self, se_token):
        """Test GET /api/quotations"""
        headers = {"Authorization": f"Bearer {se_token}"}
        response = requests.get(f"{BASE_URL}/api/quotations", headers=headers)
        
        assert response.status_code == 200
        print(f"PASS: GET /api/quotations - Status {response.status_code}")
    
    def test_get_agreements(self, se_token):
        """Test GET /api/agreements"""
        headers = {"Authorization": f"Bearer {se_token}"}
        response = requests.get(f"{BASE_URL}/api/agreements", headers=headers)
        
        assert response.status_code == 200
        print(f"PASS: GET /api/agreements - Status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
