"""
Test Suite: Kickoff Approval Workflow
Tests the complete E2E flow: Sales creates kickoff request -> Admin approves/rejects

Endpoints tested:
- GET /api/sales-funnel/consulting-team - Returns only senior/principal consultants
- POST /api/sales-funnel/request-kickoff - Creates pending kickoff request
- GET /api/sales-funnel/pending-kickoff-approvals - Admin sees pending requests
- POST /api/sales-funnel/approve-kickoff/{id} - Admin approves request
- POST /api/sales-funnel/reject-kickoff/{id} - Admin rejects request
- GET /api/sales-funnel/stage-status/{lead_id} - Returns stage info
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "ADMIN001", "password": "test123"}
SALES_EXEC_CREDS = {"employee_id": "SE001", "password": "test123"}
SALES_MANAGER_CREDS = {"employee_id": "SM001", "password": "test123"}
CONSULTANT_CREDS = {"employee_id": "CON001", "password": "test123"}


class TestKickoffApprovalWorkflow:
    """Complete E2E test for kickoff approval workflow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.sales_token = None
        self.test_request_id = None
        self.test_lead_id = None
    
    def get_token(self, credentials):
        """Login and get token"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json=credentials
        )
        if response.status_code == 200:
            data = response.json()
            # API returns access_token, not token
            return data.get("access_token") or data.get("token")
        return None
    
    # ============ Test 1: Admin Login ============
    def test_01_admin_login(self):
        """Test admin can login"""
        self.admin_token = self.get_token(ADMIN_CREDS)
        assert self.admin_token is not None, "Admin login failed"
        print(f"✓ Admin login successful")
    
    # ============ Test 2: Sales Executive Login ============
    def test_02_sales_exec_login(self):
        """Test sales executive can login"""
        self.sales_token = self.get_token(SALES_EXEC_CREDS)
        assert self.sales_token is not None, "Sales executive login failed"
        print(f"✓ Sales executive login successful")
    
    # ============ Test 3: Consulting Team Endpoint ============
    def test_03_consulting_team_returns_only_senior_principal(self):
        """Test /consulting-team returns only senior_consultant and principal_consultant roles"""
        token = self.get_token(SALES_EXEC_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "consultants" in data, "Response missing 'consultants' field"
        consultants = data["consultants"]
        
        # Verify each consultant has allowed role
        allowed_roles = ["senior_consultant", "principal_consultant"]
        for consultant in consultants:
            assert consultant.get("role") in allowed_roles, \
                f"Invalid role '{consultant.get('role')}' - only senior_consultant/principal_consultant allowed"
            assert "id" in consultant, "Consultant missing 'id' field"
            assert "full_name" in consultant, "Consultant missing 'full_name' field"
        
        print(f"✓ Consulting team endpoint returns {len(consultants)} consultants (all senior/principal)")
    
    # ============ Test 4: Get Valid Lead for Testing ============
    def test_04_get_lead_for_testing(self):
        """Get a lead to use for kickoff request testing"""
        token = self.get_token(ADMIN_CREDS)
        response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        data = response.json()
        
        leads = data.get("leads", data) if isinstance(data, dict) else data
        assert len(leads) > 0, "No leads found in the system"
        
        # Use first lead
        self.test_lead_id = leads[0].get("id")
        assert self.test_lead_id is not None, "Lead missing ID"
        print(f"✓ Using lead ID: {self.test_lead_id}")
    
    # ============ Test 5: Stage Status Endpoint ============
    def test_05_stage_status_endpoint(self):
        """Test /stage-status/{lead_id} returns correct info"""
        token = self.get_token(SALES_EXEC_CREDS)
        
        # Get a lead first
        leads_response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = leads_response.json()
        lead_list = leads.get("leads", leads) if isinstance(leads, dict) else leads
        
        if len(lead_list) == 0:
            pytest.skip("No leads to test stage status")
        
        lead_id = lead_list[0].get("id")
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/stage-status/{lead_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify stage status fields
        assert "current_stage" in data, "Missing 'current_stage' field"
        print(f"✓ Stage status endpoint working - current stage: {data.get('current_stage')}")
    
    # ============ Test 6: Request Kickoff (Sales Role) ============
    def test_06_sales_can_request_kickoff(self):
        """Test sales user can create a kickoff request"""
        token = self.get_token(SALES_EXEC_CREDS)
        
        # Get a consultant first
        consultants_response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {token}"}
        )
        consultants = consultants_response.json().get("consultants", [])
        
        if len(consultants) == 0:
            pytest.skip("No consultants available to assign")
        
        consultant_id = consultants[0].get("id")
        
        # Get a lead
        leads_response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = leads_response.json()
        lead_list = leads.get("leads", leads) if isinstance(leads, dict) else leads
        
        if len(lead_list) == 0:
            pytest.skip("No leads available for kickoff")
        
        lead_id = lead_list[0].get("id")
        
        # Create kickoff request
        kickoff_payload = {
            "lead_id": lead_id,
            "agreement_id": f"test-agreement-{uuid.uuid4().hex[:8]}",
            "assigned_consultant_id": consultant_id,
            "notes": f"Test kickoff request {uuid.uuid4().hex[:8]}"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/request-kickoff",
            headers={"Authorization": f"Bearer {token}"},
            json=kickoff_payload
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data.get("status") == "success", f"Expected success status: {data}"
        assert "request" in data, "Response missing 'request' field"
        
        request_data = data["request"]
        assert request_data.get("status") == "pending", "Request should be pending"
        self.test_request_id = request_data.get("id")
        
        print(f"✓ Kickoff request created successfully - ID: {self.test_request_id}")
    
    # ============ Test 7: Admin Sees Pending Requests ============
    def test_07_admin_sees_pending_approvals(self):
        """Test admin can see pending kickoff approvals"""
        token = self.get_token(ADMIN_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "requests" in data, "Response missing 'requests' field"
        print(f"✓ Admin can see {len(data['requests'])} pending kickoff requests")
    
    # ============ Test 8: Non-Admin Cannot See Pending Approvals ============
    def test_08_non_admin_denied_pending_approvals(self):
        """Test non-admin users cannot access pending approvals"""
        token = self.get_token(SALES_EXEC_CREDS)
        
        response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ Non-admin correctly denied access to pending approvals (403)")
    
    # ============ Test 9: Cannot Assign Non-Senior Consultant ============
    def test_09_cannot_assign_non_senior_consultant(self):
        """Test that non-senior/principal consultants cannot be assigned"""
        token = self.get_token(SALES_EXEC_CREDS)
        
        # Get a lead
        leads_response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        leads = leads_response.json()
        lead_list = leads.get("leads", leads) if isinstance(leads, dict) else leads
        
        if len(lead_list) == 0:
            pytest.skip("No leads available")
        
        lead_id = lead_list[0].get("id")
        
        # Try to assign a non-consultant user (use a fake ID or known non-consultant)
        # This should fail with 400 or 404
        kickoff_payload = {
            "lead_id": lead_id,
            "agreement_id": f"test-agreement-{uuid.uuid4().hex[:8]}",
            "assigned_consultant_id": "invalid-consultant-id",
            "notes": "Test invalid assignment"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/request-kickoff",
            headers={"Authorization": f"Bearer {token}"},
            json=kickoff_payload
        )
        
        # Should return 400 or 404
        assert response.status_code in [400, 404], \
            f"Expected 400 or 404 for invalid consultant, got {response.status_code}"
        print(f"✓ Invalid consultant assignment correctly rejected ({response.status_code})")
    
    # ============ Test 10: Create and Approve Kickoff Flow ============
    def test_10_complete_approval_flow(self):
        """Test complete flow: Sales creates -> Admin approves"""
        sales_token = self.get_token(SALES_EXEC_CREDS)
        admin_token = self.get_token(ADMIN_CREDS)
        
        # Get consultant
        consultants_response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        consultants = consultants_response.json().get("consultants", [])
        
        if len(consultants) == 0:
            pytest.skip("No consultants available")
        
        consultant_id = consultants[0].get("id")
        
        # Get lead
        leads_response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        leads = leads_response.json()
        lead_list = leads.get("leads", leads) if isinstance(leads, dict) else leads
        
        if len(lead_list) == 0:
            pytest.skip("No leads available")
        
        lead_id = lead_list[0].get("id")
        
        # Step 1: Sales creates kickoff request
        kickoff_payload = {
            "lead_id": lead_id,
            "agreement_id": f"test-agmt-{uuid.uuid4().hex[:8]}",
            "assigned_consultant_id": consultant_id,
            "notes": f"E2E test approval flow {uuid.uuid4().hex[:8]}"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/request-kickoff",
            headers={"Authorization": f"Bearer {sales_token}"},
            json=kickoff_payload
        )
        
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        request_id = create_response.json()["request"]["id"]
        print(f"  Step 1: Created kickoff request {request_id}")
        
        # Step 2: Admin sees it in pending list
        pending_response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert pending_response.status_code == 200
        pending_ids = [r["id"] for r in pending_response.json()["requests"]]
        assert request_id in pending_ids, "Request not in pending list"
        print(f"  Step 2: Admin sees request in pending list")
        
        # Step 3: Admin approves
        approve_response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/approve-kickoff/{request_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert approve_response.status_code == 200, f"Approval failed: {approve_response.text}"
        assert approve_response.json().get("status") == "success"
        print(f"  Step 3: Admin approved request successfully")
        
        # Step 4: Verify it's no longer in pending list
        pending_response2 = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        pending_ids2 = [r["id"] for r in pending_response2.json()["requests"]]
        assert request_id not in pending_ids2, "Approved request still in pending list"
        print(f"  Step 4: Request removed from pending list")
        
        print(f"✓ Complete approval flow works correctly!")
    
    # ============ Test 11: Create and Reject Kickoff Flow ============
    def test_11_complete_rejection_flow(self):
        """Test complete flow: Sales creates -> Admin rejects"""
        sales_token = self.get_token(SALES_EXEC_CREDS)
        admin_token = self.get_token(ADMIN_CREDS)
        
        # Get consultant
        consultants_response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/consulting-team",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        consultants = consultants_response.json().get("consultants", [])
        
        if len(consultants) == 0:
            pytest.skip("No consultants available")
        
        consultant_id = consultants[0].get("id")
        
        # Get lead
        leads_response = self.session.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        leads = leads_response.json()
        lead_list = leads.get("leads", leads) if isinstance(leads, dict) else leads
        
        if len(lead_list) == 0:
            pytest.skip("No leads available")
        
        lead_id = lead_list[0].get("id")
        
        # Step 1: Sales creates kickoff request
        kickoff_payload = {
            "lead_id": lead_id,
            "agreement_id": f"test-reject-{uuid.uuid4().hex[:8]}",
            "assigned_consultant_id": consultant_id,
            "notes": f"E2E test rejection flow {uuid.uuid4().hex[:8]}"
        }
        
        create_response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/request-kickoff",
            headers={"Authorization": f"Bearer {sales_token}"},
            json=kickoff_payload
        )
        
        assert create_response.status_code == 200
        request_id = create_response.json()["request"]["id"]
        print(f"  Step 1: Created kickoff request {request_id}")
        
        # Step 2: Admin rejects with reason
        reject_response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/reject-kickoff/{request_id}?reason=Test%20rejection%20reason",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert reject_response.status_code == 200, f"Rejection failed: {reject_response.text}"
        assert reject_response.json().get("status") == "success"
        print(f"  Step 2: Admin rejected request successfully")
        
        # Step 3: Verify it's no longer in pending list
        pending_response = self.session.get(
            f"{BASE_URL}/api/sales-funnel/pending-kickoff-approvals",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        pending_ids = [r["id"] for r in pending_response.json()["requests"]]
        assert request_id not in pending_ids, "Rejected request still in pending list"
        print(f"  Step 3: Request removed from pending list")
        
        print(f"✓ Complete rejection flow works correctly!")
    
    # ============ Test 12: Non-Admin Cannot Approve ============
    def test_12_non_admin_cannot_approve(self):
        """Test non-admin users cannot approve kickoff requests"""
        sales_token = self.get_token(SALES_EXEC_CREDS)
        
        # Try to approve a fake request
        response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/approve-kickoff/fake-request-id",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ Non-admin correctly denied approval access (403)")
    
    # ============ Test 13: Non-Admin Cannot Reject ============
    def test_13_non_admin_cannot_reject(self):
        """Test non-admin users cannot reject kickoff requests"""
        sales_token = self.get_token(SALES_EXEC_CREDS)
        
        response = self.session.post(
            f"{BASE_URL}/api/sales-funnel/reject-kickoff/fake-request-id",
            headers={"Authorization": f"Bearer {sales_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ Non-admin correctly denied rejection access (403)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
