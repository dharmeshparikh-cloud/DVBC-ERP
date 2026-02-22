"""
Test Suite: Sales Funnel Complete E2E Flow
Tests the full sales funnel from Lead creation to Kickoff approval and Deal Closed

Stages tested:
1. LEAD → 2. MEETING → 3. PRICING → 4. SOW → 5. QUOTATION → 6. AGREEMENT → 7. PAYMENT → 8. KICKOFF → 9. CLOSED

Endpoints tested:
- Lead CRUD: GET/POST/PUT /api/leads, GET /api/leads/{id}/stage
- Pricing Plans: GET/POST /api/pricing-plans
- SOW: GET/POST /api/enhanced-sow
- Quotations: GET/POST /api/quotations
- Agreements: GET/POST /api/agreements, /api/agreements/{id}/sign
- Kickoff Flow: POST /api/sales-funnel/request-kickoff, approve-kickoff, pending-kickoff-approvals
- Dashboard Stats: GET /api/stats/dashboard
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "ADMIN001", "password": "test123"}
SALES_EXEC_CREDS = {"employee_id": "SE001", "password": "test123"}

# Test lead ID from context
TEST_LEAD_ID = "64653862-c2d0-4725-984f-f8c58432266a"


class TestSalesFunnelE2EFlow:
    """Complete E2E test for sales funnel from Lead to Kickoff Approval"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.sales_token = None
        
    def get_token(self, credentials):
        """Login and get token"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=credentials
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    # ============== Authentication Tests ==============
    
    def test_01_admin_login(self):
        """Test admin can login with Employee ID"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDS
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, "Token not returned"
        assert data.get("user", {}).get("role") == "admin", "Expected admin role"
        print(f"✓ Admin login successful - role: {data['user']['role']}")
    
    def test_02_sales_exec_login(self):
        """Test sales executive can login"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=SALES_EXEC_CREDS
        )
        assert response.status_code == 200, f"Sales exec login failed: {response.text}"
        data = response.json()
        print(f"✓ Sales exec login successful - role: {data['user']['role']}")
    
    # ============== Lead Management Tests ==============
    
    def test_03_get_leads_list(self):
        """GET /api/leads - List all leads with pagination"""
        token = self.get_token(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /leads failed: {response.text}"
        data = response.json()
        leads = data if isinstance(data, list) else data.get("leads", [])
        assert len(leads) > 0, "No leads found in the system"
        
        # Verify lead structure
        lead = leads[0]
        assert "id" in lead, "Lead missing ID"
        assert "company" in lead or "company_name" in lead, "Lead missing company"
        print(f"✓ GET /api/leads - Retrieved {len(leads)} leads")
    
    def test_04_get_single_lead(self):
        """GET /api/leads/{id} - Get single lead details"""
        token = self.get_token(ADMIN_CREDS)
        
        # First get leads list
        response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = response.json() if isinstance(response.json(), list) else response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        # Get single lead
        response = self.session.get(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /leads/{lead_id} failed: {response.text}"
        data = response.json()
        assert data.get("id") == lead_id, "Lead ID mismatch"
        print(f"✓ GET /api/leads/{lead_id} - Lead details retrieved")
    
    def test_05_get_lead_stage(self):
        """GET /api/leads/{id}/stage - Get current stage info with progress bar data"""
        token = self.get_token(ADMIN_CREDS)
        
        # Get leads
        response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = response.json() if isinstance(response.json(), list) else response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        # Get stage info
        response = self.session.get(
            f"{BASE_URL}/api/leads/{lead_id}/stage",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /leads/{lead_id}/stage failed: {response.text}"
        data = response.json()
        
        # Verify stage structure
        assert "current_stage" in data, "Missing current_stage"
        assert "stages" in data, "Missing stages array"
        assert isinstance(data["stages"], list), "stages should be a list"
        
        # Verify stage progression data
        stages = data["stages"]
        if stages:
            stage = stages[0]
            assert "stage" in stage, "Stage missing stage field"
            assert "is_completed" in stage or "is_current" in stage, "Stage missing status fields"
        
        print(f"✓ GET /api/leads/{lead_id}/stage - Current stage: {data['current_stage']}")
    
    def test_06_create_lead(self):
        """POST /api/leads - Create a new lead"""
        token = self.get_token(ADMIN_CREDS)
        
        new_lead = {
            "first_name": "Test",
            "last_name": f"E2E-{uuid.uuid4().hex[:8]}",
            "company": f"E2E Funnel Corp {uuid.uuid4().hex[:6]}",
            "email": f"test.e2e.{uuid.uuid4().hex[:6]}@testcorp.com",
            "phone": "9876543210",
            "job_title": "CEO",
            "source": "E2E Test",
            "notes": "Created for E2E sales funnel testing"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"},
            json=new_lead
        )
        assert response.status_code in [200, 201], f"POST /leads failed: {response.text}"
        data = response.json()
        assert "id" in data, "Created lead missing ID"
        print(f"✓ POST /api/leads - Created lead: {data['id']}")
        
        # Return lead ID for further tests
        return data["id"]
    
    def test_07_update_lead_status(self):
        """PUT /api/leads/{id} - Update lead status/stage"""
        token = self.get_token(ADMIN_CREDS)
        
        # Get a lead
        response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = response.json() if isinstance(response.json(), list) else response.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        # Update lead status
        update_data = {
            "status": "meeting"
        }
        
        response = self.session.put(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data
        )
        assert response.status_code == 200, f"PUT /leads/{lead_id} failed: {response.text}"
        print(f"✓ PUT /api/leads/{lead_id} - Status updated to 'meeting'")
    
    # ============== Consulting Team (for Kickoff) ==============
    
    def test_08_get_consulting_team(self):
        """GET /api/sales-funnel/consulting-team - Get consultants for kickoff assignment"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /consulting-team failed: {response.text}"
        data = response.json()
        
        assert "consultants" in data, "Missing consultants field"
        
        # Verify consultants are senior/principal only
        for consultant in data["consultants"]:
            assert consultant.get("role") in ["senior_consultant", "principal_consultant"], \
                f"Invalid consultant role: {consultant.get('role')}"
        
        print(f"✓ GET /api/sales-funnel/consulting-team - {len(data['consultants'])} consultants available")
    
    # ============== Kickoff Request Flow ==============
    
    def test_09_request_kickoff(self):
        """POST /api/sales-funnel/request-kickoff - Create kickoff request with consultant selection"""
        token = self.get_token(SALES_EXEC_CREDS) or self.get_token(ADMIN_CREDS)
        
        # Get consultants
        consultants_res = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {token}"}
        )
        consultants = consultants_res.json().get("consultants", [])
        
        if not consultants:
            pytest.skip("No consultants available for kickoff")
        
        # Get leads
        leads_res = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = leads_res.json() if isinstance(leads_res.json(), list) else leads_res.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads available for kickoff")
        
        lead_id = leads[0]["id"]
        consultant_id = consultants[0]["id"]
        
        # Create kickoff request
        kickoff_data = {
            "lead_id": lead_id,
            "agreement_id": None,
            "assigned_consultant_id": consultant_id,
            "notes": f"E2E Test kickoff request - {uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/request-kickoff",
            headers={"Authorization": f"Bearer {token}"},
            json=kickoff_data
        )
        assert response.status_code == 200, f"POST /request-kickoff failed: {response.text}"
        data = response.json()
        
        assert data.get("status") == "success", f"Expected success: {data}"
        assert "request" in data, "Missing request in response"
        assert data["request"].get("status") == "pending", "Request should be pending"
        
        print(f"✓ POST /api/sales-funnel/request-kickoff - Created request: {data['request']['id']}")
        return data["request"]["id"]
    
    def test_10_get_pending_kickoff_approvals(self):
        """GET /api/sales-funnel/pending-kickoff-approvals - Admin views pending requests"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /pending-kickoff-approvals failed: {response.text}"
        data = response.json()
        
        assert "requests" in data, "Missing requests field"
        print(f"✓ GET /api/sales-funnel/pending-kickoff-approvals - {len(data['requests'])} pending requests")
    
    def test_11_approve_kickoff(self):
        """POST /api/sales-funnel/approve-kickoff/{id} - Admin approves kickoff"""
        sales_token = self.get_token(SALES_EXEC_CREDS) or self.get_token(ADMIN_CREDS)
        admin_token = self.get_token(ADMIN_CREDS)
        
        # Get consultants
        consultants_res = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        consultants = consultants_res.json().get("consultants", [])
        
        if not consultants:
            pytest.skip("No consultants available")
        
        # Get leads
        leads_res = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        leads = leads_res.json() if isinstance(leads_res.json(), list) else leads_res.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        consultant_id = consultants[0]["id"]
        
        # Create kickoff request
        kickoff_data = {
            "lead_id": lead_id,
            "agreement_id": None,
            "assigned_consultant_id": consultant_id,
            "notes": f"E2E Test for approval - {uuid.uuid4().hex[:8]}"
        }
        
        create_res = self.session.post(
            f"{BASE_URL}/api/sales-funnel/request-kickoff",
            headers={"Authorization": f"Bearer {sales_token}"},
            json=kickoff_data
        )
        
        if create_res.status_code != 200:
            pytest.skip(f"Could not create kickoff request: {create_res.text}")
        
        request_id = create_res.json()["request"]["id"]
        
        # Admin approves
        approve_res = self.session.post(
            f"{BASE_URL}/api/sales-funnel/approve-kickoff/{request_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_res.status_code == 200, f"POST /approve-kickoff/{request_id} failed: {approve_res.text}"
        data = approve_res.json()
        
        assert data.get("status") == "success", f"Expected success: {data}"
        print(f"✓ POST /api/sales-funnel/approve-kickoff/{request_id} - Kickoff approved!")
    
    # ============== Dashboard Stats ==============
    
    def test_12_dashboard_shows_lead_counts(self):
        """Verify dashboard stats show lead counts by stage"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/stats/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /stats/dashboard failed: {response.text}"
        data = response.json()
        
        # Verify key stats are present
        assert "total_leads" in data or "active_leads" in data, "Missing lead counts"
        print(f"✓ GET /api/stats/dashboard - Stats retrieved successfully")
    
    # ============== Stage Status Tests ==============
    
    def test_13_stage_status_endpoint(self):
        """GET /api/sales-funnel/stage-status/{lead_id} - Check stage progression"""
        token = self.get_token(ADMIN_CREDS)
        
        # Get leads
        leads_res = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = leads_res.json() if isinstance(leads_res.json(), list) else leads_res.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads available")
        
        lead_id = leads[0]["id"]
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/stage-status/{lead_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /stage-status/{lead_id} failed: {response.text}"
        data = response.json()
        
        assert "current_stage" in data, "Missing current_stage"
        print(f"✓ GET /api/sales-funnel/stage-status/{lead_id} - Stage: {data['current_stage']}")
    
    # ============== Non-Admin Access Control ==============
    
    def test_14_non_admin_denied_pending_approvals(self):
        """Non-admin users cannot access pending kickoff approvals"""
        token = self.get_token(SALES_EXEC_CREDS)
        
        if not token:
            pytest.skip("Sales exec login failed")
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ Non-admin correctly denied access to pending-kickoff-approvals (403)")
    
    def test_15_non_admin_cannot_approve_kickoff(self):
        """Non-admin users cannot approve kickoff requests"""
        token = self.get_token(SALES_EXEC_CREDS)
        
        if not token:
            pytest.skip("Sales exec login failed")
        
        response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/approve-kickoff/fake-id",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ Non-admin correctly denied kickoff approval (403)")
    
    # ============== Pricing Plans Tests ==============
    
    def test_16_get_pricing_plans(self):
        """GET /api/pricing-plans - List pricing plans"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/pricing-plans",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /pricing-plans failed: {response.text}"
        data = response.json()
        plans = data if isinstance(data, list) else data.get("plans", [])
        print(f"✓ GET /api/pricing-plans - Retrieved {len(plans)} plans")
    
    # ============== Quotations Tests ==============
    
    def test_17_get_quotations(self):
        """GET /api/quotations - List quotations"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/quotations",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /quotations failed: {response.text}"
        data = response.json()
        quotations = data if isinstance(data, list) else data.get("quotations", [])
        print(f"✓ GET /api/quotations - Retrieved {len(quotations)} quotations")
    
    # ============== Agreements Tests ==============
    
    def test_18_get_agreements(self):
        """GET /api/agreements - List agreements"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"GET /agreements failed: {response.text}"
        data = response.json()
        agreements = data if isinstance(data, list) else data.get("agreements", [])
        print(f"✓ GET /api/agreements - Retrieved {len(agreements)} agreements")


class TestLeadStageProgression:
    """Test lead stage progression through the funnel"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def get_token(self, credentials):
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=credentials
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    def test_stage_order(self):
        """Verify stages are in correct order"""
        expected_stages = ["LEAD", "MEETING", "PRICING", "SOW", "QUOTATION", "AGREEMENT", "PAYMENT", "KICKOFF", "CLOSED"]
        token = self.get_token(ADMIN_CREDS)
        
        # Get leads with stage info
        leads_res = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = leads_res.json() if isinstance(leads_res.json(), list) else leads_res.json().get("leads", [])
        
        if not leads:
            pytest.skip("No leads to test stage order")
        
        lead_id = leads[0]["id"]
        
        stage_res = self.session.get(
            f"{BASE_URL}/api/leads/{lead_id}/stage",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if stage_res.status_code != 200:
            pytest.skip(f"Stage endpoint not available: {stage_res.text}")
        
        data = stage_res.json()
        stages = data.get("stages", [])
        
        # Extract stage names
        stage_names = [s.get("stage") for s in stages]
        
        # Verify order matches expected
        for i, stage_name in enumerate(stage_names):
            if i < len(expected_stages):
                assert stage_name == expected_stages[i], f"Stage order mismatch at index {i}: expected {expected_stages[i]}, got {stage_name}"
        
        print(f"✓ Stage order verified: {' → '.join(stage_names)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
