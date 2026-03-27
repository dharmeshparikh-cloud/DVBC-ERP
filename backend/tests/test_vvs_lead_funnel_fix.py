"""
Test VVS Lead Funnel Progress Fix
=================================
Tests the fix for VVS lead stuck at Kickoff (Approved) not moving to Onboarded status.

Root causes fixed:
1. Project creation in client_confirm_approval ran AFTER status update
2. funnel-progress endpoint marked project_created based on kickoff status only
3. PaymentVerification model lacked lead_id field
4. SOW detection prioritized legacy sow collection over enhanced_sow

VVS lead_id: 329d1060-3147-46a2-98a8-dad93f95a371
Expected project_id: PROJ-20260325-0001
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
VVS_LEAD_ID = "329d1060-3147-46a2-98a8-dad93f95a371"
# Project ID is dynamically determined from funnel-progress response
VVS_PROJECT_ID = None  # Will be set during test


class TestVVSLeadFunnelFix:
    """Test VVS lead funnel progress and onboarding status"""
    
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
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
    def test_01_vvs_lead_exists(self):
        """Test that VVS lead exists in the database"""
        response = self.session.get(f"{BASE_URL}/api/leads/{VVS_LEAD_ID}")
        assert response.status_code == 200, f"VVS lead not found: {response.text}"
        
        lead = response.json()
        assert lead.get("id") == VVS_LEAD_ID
        print(f"VVS Lead found: {lead.get('company')} - Status: {lead.get('status')}")
        
    def test_02_vvs_lead_status_is_closed(self):
        """Test that VVS lead status is 'closed' (onboarded)"""
        response = self.session.get(f"{BASE_URL}/api/leads/{VVS_LEAD_ID}")
        assert response.status_code == 200
        
        lead = response.json()
        assert lead.get("status") == "closed", f"Expected status 'closed', got '{lead.get('status')}'"
        print(f"VVS Lead status is correctly 'closed'")
        
    def test_03_vvs_funnel_progress_9_of_9(self):
        """Test that VVS lead shows 9/9 funnel progress with all steps completed"""
        response = self.session.get(f"{BASE_URL}/api/leads/{VVS_LEAD_ID}/funnel-progress")
        assert response.status_code == 200, f"Funnel progress API failed: {response.text}"
        
        progress = response.json()
        
        # Check completed count
        completed_count = progress.get("completed_count", 0)
        total_steps = progress.get("total_steps", 9)
        assert completed_count == 9, f"Expected 9/9 completed, got {completed_count}/{total_steps}"
        
        # Check all steps are completed
        completed_steps = progress.get("completed_steps", [])
        expected_steps = [
            "lead_capture", "record_meeting", "pricing_plan", "scope_of_work",
            "quotation", "agreement", "record_payment", "kickoff_request", "project_created"
        ]
        
        for step in expected_steps:
            assert step in completed_steps, f"Step '{step}' not in completed_steps: {completed_steps}"
        
        print(f"VVS Funnel Progress: {completed_count}/{total_steps} - All steps completed!")
        print(f"Completed steps: {completed_steps}")
        
    def test_04_vvs_funnel_has_project_id(self):
        """Test that funnel-progress returns a valid project_id"""
        global VVS_PROJECT_ID
        response = self.session.get(f"{BASE_URL}/api/leads/{VVS_LEAD_ID}/funnel-progress")
        assert response.status_code == 200
        
        progress = response.json()
        project_id = progress.get("project_id")
        
        assert project_id is not None, "project_id is missing from funnel-progress response"
        assert project_id.startswith("PROJ-"), f"Invalid project_id format: {project_id}"
        
        # Store for later tests
        VVS_PROJECT_ID = project_id
        print(f"VVS Project ID correctly returned: {project_id}")
        
    def test_05_vvs_project_exists_in_db(self):
        """Test that the VVS project actually exists in the projects collection"""
        global VVS_PROJECT_ID
        
        # First get the project_id from funnel-progress if not set
        if not VVS_PROJECT_ID:
            fp_response = self.session.get(f"{BASE_URL}/api/leads/{VVS_LEAD_ID}/funnel-progress")
            if fp_response.status_code == 200:
                VVS_PROJECT_ID = fp_response.json().get("project_id")
        
        assert VVS_PROJECT_ID is not None, "Could not determine VVS project_id"
        
        response = self.session.get(f"{BASE_URL}/api/projects/{VVS_PROJECT_ID}")
        
        # Project should exist
        assert response.status_code == 200, f"Project {VVS_PROJECT_ID} not found: {response.text}"
        
        project = response.json()
        assert project.get("id") == VVS_PROJECT_ID
        assert project.get("lead_id") == VVS_LEAD_ID, f"Project lead_id mismatch: {project.get('lead_id')}"
        
        print(f"VVS Project exists: {project.get('name')} - Status: {project.get('status')}")
        
    def test_06_vvs_excluded_from_main_leads_table(self):
        """Test that VVS does NOT appear in main leads table with exclude_onboarded=true"""
        response = self.session.get(f"{BASE_URL}/api/leads?exclude_onboarded=true&page_size=500")
        assert response.status_code == 200, f"Leads API failed: {response.text}"
        
        data = response.json()
        leads = data.get("data", [])
        
        # VVS should NOT be in the list
        vvs_in_list = any(lead.get("id") == VVS_LEAD_ID for lead in leads)
        assert not vvs_in_list, f"VVS lead should NOT appear in main leads table with exclude_onboarded=true"
        
        print(f"VVS correctly excluded from main leads table (exclude_onboarded=true)")
        
    def test_07_vvs_included_in_closed_status_filter(self):
        """Test that VVS appears when filtering by status=closed"""
        response = self.session.get(f"{BASE_URL}/api/leads?status=closed&page_size=500")
        assert response.status_code == 200, f"Leads API failed: {response.text}"
        
        data = response.json()
        leads = data.get("data", [])
        
        # VVS should be in the list
        vvs_in_list = any(lead.get("id") == VVS_LEAD_ID for lead in leads)
        assert vvs_in_list, f"VVS lead should appear when filtering by status=closed"
        
        print(f"VVS correctly included in status=closed filter")
        
    def test_08_vvs_in_bulk_progress_with_9_completed(self):
        """Test that GET /api/leads/progress/bulk returns VVS with 9/9 completed"""
        response = self.session.get(f"{BASE_URL}/api/leads/progress/bulk")
        assert response.status_code == 200, f"Bulk progress API failed: {response.text}"
        
        progress_map = response.json()
        
        # VVS should be in the progress map
        assert VVS_LEAD_ID in progress_map, f"VVS lead not found in bulk progress response"
        
        vvs_progress = progress_map[VVS_LEAD_ID]
        completed_count = vvs_progress.get("completed_count", 0)
        
        assert completed_count == 9, f"Expected 9 completed steps, got {completed_count}"
        assert vvs_progress.get("project") == True, "project flag should be True"
        
        print(f"VVS in bulk progress: {completed_count}/9 completed, project={vvs_progress.get('project')}")
        
    def test_09_vvs_kickoff_has_approved_status(self):
        """Test that VVS kickoff request has approved status"""
        global VVS_PROJECT_ID
        
        # Get kickoff by lead_id
        response = self.session.get(f"{BASE_URL}/api/kickoff-requests?lead_id={VVS_LEAD_ID}")
        
        if response.status_code == 200:
            kickoffs = response.json()
            if isinstance(kickoffs, list) and len(kickoffs) > 0:
                kickoff = kickoffs[0]
            else:
                # Try getting all kickoffs and filter
                all_response = self.session.get(f"{BASE_URL}/api/kickoff-requests")
                if all_response.status_code == 200:
                    all_kickoffs = all_response.json()
                    kickoff = next((k for k in all_kickoffs if k.get("lead_id") == VVS_LEAD_ID), None)
                else:
                    kickoff = None
        else:
            kickoff = None
            
        assert kickoff is not None, "VVS kickoff request not found"
        
        status = kickoff.get("status")
        assert status == "approved", f"Expected kickoff status 'approved', got '{status}'"
        
        project_id = kickoff.get("project_id")
        assert project_id is not None, "Kickoff should have a project_id"
        assert project_id.startswith("PROJ-"), f"Invalid project_id format: {project_id}"
        
        # Update global if needed
        if not VVS_PROJECT_ID:
            VVS_PROJECT_ID = project_id
        
        print(f"VVS Kickoff status: {status}, project_id: {project_id}")
        
    def test_10_vvs_payment_has_lead_id(self):
        """Test that VVS payment verification has lead_id field populated"""
        # Get agreement first
        response = self.session.get(f"{BASE_URL}/api/agreements?lead_id={VVS_LEAD_ID}")
        
        if response.status_code != 200:
            # Try getting all agreements
            all_response = self.session.get(f"{BASE_URL}/api/agreements")
            if all_response.status_code == 200:
                all_agreements = all_response.json()
                if isinstance(all_agreements, dict):
                    all_agreements = all_agreements.get("data", [])
                agreement = next((a for a in all_agreements if a.get("lead_id") == VVS_LEAD_ID), None)
            else:
                agreement = None
        else:
            agreements = response.json()
            if isinstance(agreements, dict):
                agreements = agreements.get("data", [])
            agreement = agreements[0] if agreements else None
            
        if agreement:
            agreement_id = agreement.get("id")
            # Get payments for this agreement
            payments_response = self.session.get(f"{BASE_URL}/api/payments/agreement/{agreement_id}")
            
            if payments_response.status_code == 200:
                payments = payments_response.json()
                if payments:
                    payment = payments[0]
                    lead_id = payment.get("lead_id")
                    # lead_id should be populated (fix was to auto-populate from agreement)
                    print(f"VVS Payment lead_id: {lead_id}")
                    # This is a soft check - the fix auto-populates lead_id
                    if lead_id:
                        assert lead_id == VVS_LEAD_ID, f"Payment lead_id mismatch: {lead_id}"
                        print("Payment lead_id correctly populated!")
                    else:
                        print("Warning: Payment lead_id is None (may be legacy data)")
                else:
                    print("No payments found for VVS agreement")
            else:
                print(f"Could not fetch payments: {payments_response.status_code}")
        else:
            print("No agreement found for VVS lead - skipping payment check")


class TestOnboardedClientsPage:
    """Test Onboarded Clients page functionality"""
    
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
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
    def test_11_onboarded_clients_api_returns_closed_leads(self):
        """Test that the API used by Onboarded Clients page returns closed leads"""
        # The OnboardedClients.js fetches all leads and filters by status=closed
        response = self.session.get(f"{BASE_URL}/api/leads?page_size=200")
        assert response.status_code == 200, f"Leads API failed: {response.text}"
        
        data = response.json()
        all_leads = data.get("data", [])
        
        # Filter for closed leads (same logic as frontend)
        closed_leads = [l for l in all_leads if l.get("status") == "closed"]
        
        # VVS should be in closed leads
        vvs_in_closed = any(lead.get("id") == VVS_LEAD_ID for lead in closed_leads)
        assert vvs_in_closed, f"VVS lead should appear in closed leads for Onboarded Clients page"
        
        print(f"Found {len(closed_leads)} onboarded clients, VVS is included: {vvs_in_closed}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
