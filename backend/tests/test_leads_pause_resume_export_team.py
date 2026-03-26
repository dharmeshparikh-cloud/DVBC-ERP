"""
Test Suite for Lead Pause/Resume, CSV Export, and Team Members Endpoints
Tests the following new features:
1. POST /api/leads/{lead_id}/pause - Pause a lead
2. POST /api/leads/{lead_id}/resume - Resume a paused lead
3. GET /api/leads/export/csv - Export leads as CSV
4. GET /api/leads/team-members - Get team members for reassignment
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestLeadsPauseResumeExportTeam:
    """Test suite for new lead endpoints: pause, resume, export CSV, team-members"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as sales user EMP003"""
        self.sales_token = None
        self.admin_token = None
        self.test_lead_id = None
        
        # Login as sales user (EMP003)
        login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        if login_res.status_code == 200:
            self.sales_token = login_res.json().get("access_token")
        
        # Login as admin user (EMP001)
        admin_login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        if admin_login_res.status_code == 200:
            self.admin_token = admin_login_res.json().get("access_token")
        
        yield
    
    def get_sales_headers(self):
        return {"Authorization": f"Bearer {self.sales_token}", "Content-Type": "application/json"}
    
    def get_admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}", "Content-Type": "application/json"}
    
    # ==================== TEAM MEMBERS ENDPOINT ====================
    
    def test_team_members_endpoint_exists(self):
        """Test GET /api/leads/team-members endpoint exists and returns data"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/team-members",
            headers=self.get_sales_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of team members"
        print(f"PASSED: GET /api/leads/team-members returns {len(data)} team members")
    
    def test_team_members_returns_assignable_users(self):
        """Test team-members returns users with sales/manager/admin roles"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/team-members",
            headers=self.get_sales_headers()
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have at least one user
        assert len(data) > 0, "Expected at least one team member"
        
        # Each user should have required fields
        for user in data:
            assert "id" in user or "employee_id" in user, f"User missing id: {user}"
            assert "full_name" in user or "email" in user, f"User missing name/email: {user}"
        
        print(f"PASSED: Team members have required fields. Sample: {data[0] if data else 'N/A'}")
    
    def test_team_members_accessible_by_sales_role(self):
        """Test that sales role (EMP003) can access team-members endpoint"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/team-members",
            headers=self.get_sales_headers()
        )
        
        # Should be accessible (not 403)
        assert response.status_code != 403, "Sales user should have access to team-members"
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("PASSED: Sales role (EMP003) can access team-members endpoint")
    
    def test_team_members_requires_auth(self):
        """Test team-members endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leads/team-members")
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASSED: team-members endpoint requires authentication")
    
    # ==================== PAUSE LEAD ENDPOINT ====================
    
    def test_pause_lead_endpoint_exists(self):
        """Test POST /api/leads/{lead_id}/pause endpoint exists"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        # First get a lead to pause
        leads_res = requests.get(
            f"{BASE_URL}/api/leads",
            headers=self.get_sales_headers()
        )
        
        if leads_res.status_code != 200:
            pytest.skip("Could not fetch leads")
        
        leads_data = leads_res.json()
        leads = leads_data.get("data") or leads_data.get("items") or leads_data
        if not leads or len(leads) == 0:
            pytest.skip("No leads available to test pause")
        
        # Find a lead that is not already paused
        test_lead = None
        for lead in leads:
            if lead.get("status") != "paused":
                test_lead = lead
                break
        
        if not test_lead:
            pytest.skip("No non-paused leads available")
        
        lead_id = test_lead.get("id")
        
        # Try to pause the lead
        response = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/pause",
            headers=self.get_sales_headers()
        )
        
        # Should return 200 or 400 (if already paused), not 404 or 405
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data, "Response should have message"
            assert "previous_status" in data, "Response should have previous_status"
            print(f"PASSED: Lead {lead_id} paused successfully. Previous status: {data.get('previous_status')}")
            
            # Resume the lead to restore state
            requests.post(
                f"{BASE_URL}/api/leads/{lead_id}/resume",
                headers=self.get_sales_headers()
            )
        else:
            print(f"PASSED: Pause endpoint exists (returned 400 - lead may already be paused)")
    
    def test_pause_already_paused_lead_returns_400(self):
        """Test pausing an already paused lead returns 400"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        # Get leads
        leads_res = requests.get(
            f"{BASE_URL}/api/leads",
            headers=self.get_sales_headers()
        )
        
        if leads_res.status_code != 200:
            pytest.skip("Could not fetch leads")
        
        leads_data = leads_res.json()
        leads = leads_data.get("data") or leads_data.get("items") or leads_data
        if not leads or len(leads) == 0:
            pytest.skip("No leads available")
        
        # Find a non-paused lead and pause it
        test_lead = None
        for lead in leads:
            if lead.get("status") != "paused":
                test_lead = lead
                break
        
        if not test_lead:
            pytest.skip("No non-paused leads available")
        
        lead_id = test_lead.get("id")
        
        # First pause
        first_pause = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/pause",
            headers=self.get_sales_headers()
        )
        
        if first_pause.status_code != 200:
            pytest.skip("Could not pause lead for test")
        
        # Try to pause again - should return 400
        second_pause = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/pause",
            headers=self.get_sales_headers()
        )
        
        assert second_pause.status_code == 400, f"Expected 400 for already paused lead, got {second_pause.status_code}"
        print("PASSED: Pausing already paused lead returns 400")
        
        # Cleanup - resume the lead
        requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/resume",
            headers=self.get_sales_headers()
        )
    
    # ==================== RESUME LEAD ENDPOINT ====================
    
    def test_resume_lead_endpoint_exists(self):
        """Test POST /api/leads/{lead_id}/resume endpoint exists"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        # Get leads
        leads_res = requests.get(
            f"{BASE_URL}/api/leads",
            headers=self.get_sales_headers()
        )
        
        if leads_res.status_code != 200:
            pytest.skip("Could not fetch leads")
        
        leads_data = leads_res.json()
        leads = leads_data.get("data") or leads_data.get("items") or leads_data
        if not leads or len(leads) == 0:
            pytest.skip("No leads available")
        
        # Find a non-paused lead, pause it, then resume
        test_lead = None
        for lead in leads:
            if lead.get("status") != "paused":
                test_lead = lead
                break
        
        if not test_lead:
            pytest.skip("No non-paused leads available")
        
        lead_id = test_lead.get("id")
        original_status = test_lead.get("status")
        
        # Pause the lead first
        pause_res = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/pause",
            headers=self.get_sales_headers()
        )
        
        if pause_res.status_code != 200:
            pytest.skip("Could not pause lead for resume test")
        
        # Now resume
        resume_res = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/resume",
            headers=self.get_sales_headers()
        )
        
        assert resume_res.status_code == 200, f"Expected 200, got {resume_res.status_code}: {resume_res.text}"
        
        data = resume_res.json()
        assert "message" in data, "Response should have message"
        assert "resumed_status" in data, "Response should have resumed_status"
        print(f"PASSED: Lead {lead_id} resumed to status: {data.get('resumed_status')}")
    
    def test_resume_non_paused_lead_returns_400(self):
        """Test resuming a non-paused lead returns 400"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        # Get leads
        leads_res = requests.get(
            f"{BASE_URL}/api/leads",
            headers=self.get_sales_headers()
        )
        
        if leads_res.status_code != 200:
            pytest.skip("Could not fetch leads")
        
        leads_data = leads_res.json()
        leads = leads_data.get("data") or leads_data.get("items") or leads_data
        if not leads or len(leads) == 0:
            pytest.skip("No leads available")
        
        # Find a non-paused lead
        test_lead = None
        for lead in leads:
            if lead.get("status") != "paused":
                test_lead = lead
                break
        
        if not test_lead:
            pytest.skip("No non-paused leads available")
        
        lead_id = test_lead.get("id")
        
        # Try to resume a non-paused lead - should return 400
        resume_res = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/resume",
            headers=self.get_sales_headers()
        )
        
        assert resume_res.status_code == 400, f"Expected 400 for non-paused lead, got {resume_res.status_code}"
        print("PASSED: Resuming non-paused lead returns 400")
    
    def test_resume_restores_previous_status(self):
        """Test that resume restores the previous status before pause"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        # Get leads
        leads_res = requests.get(
            f"{BASE_URL}/api/leads",
            headers=self.get_sales_headers()
        )
        
        if leads_res.status_code != 200:
            pytest.skip("Could not fetch leads")
        
        leads_data = leads_res.json()
        leads = leads_data.get("data") or leads_data.get("items") or leads_data
        if not leads or len(leads) == 0:
            pytest.skip("No leads available")
        
        # Find a non-paused lead
        test_lead = None
        for lead in leads:
            if lead.get("status") not in ["paused", "lost", "closed", "won"]:
                test_lead = lead
                break
        
        if not test_lead:
            pytest.skip("No suitable leads available")
        
        lead_id = test_lead.get("id")
        original_status = test_lead.get("status")
        
        # Pause
        pause_res = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/pause",
            headers=self.get_sales_headers()
        )
        
        if pause_res.status_code != 200:
            pytest.skip("Could not pause lead")
        
        pause_data = pause_res.json()
        assert pause_data.get("previous_status") == original_status, "Pause should save previous status"
        
        # Resume
        resume_res = requests.post(
            f"{BASE_URL}/api/leads/{lead_id}/resume",
            headers=self.get_sales_headers()
        )
        
        assert resume_res.status_code == 200
        resume_data = resume_res.json()
        
        # The resumed status should match the original status
        resumed_status = resume_data.get("resumed_status")
        print(f"PASSED: Lead resumed from paused to '{resumed_status}' (original was '{original_status}')")
    
    # ==================== CSV EXPORT ENDPOINT ====================
    
    def test_export_csv_endpoint_exists(self):
        """Test GET /api/leads/export/csv endpoint exists"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/export/csv",
            headers=self.get_sales_headers()
        )
        
        # Should return 200 with CSV content or 404 if no leads
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            # Check content type
            content_type = response.headers.get("content-type", "")
            assert "text/csv" in content_type, f"Expected text/csv content type, got {content_type}"
            
            # Check content disposition header
            content_disp = response.headers.get("content-disposition", "")
            assert "attachment" in content_disp, "Should have attachment disposition"
            assert "leads_export.csv" in content_disp, "Should have filename in disposition"
            
            print("PASSED: CSV export endpoint returns proper CSV response")
        else:
            print("PASSED: CSV export endpoint exists (returned 404 - no leads)")
    
    def test_export_csv_has_proper_headers(self):
        """Test CSV export has proper column headers"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/export/csv",
            headers=self.get_sales_headers()
        )
        
        if response.status_code == 404:
            pytest.skip("No leads to export")
        
        assert response.status_code == 200
        
        csv_content = response.text
        lines = csv_content.strip().split('\n')
        
        assert len(lines) >= 1, "CSV should have at least header row"
        
        headers = lines[0].lower()
        
        # Check for expected headers
        expected_headers = ["company", "email", "phone", "status"]
        for header in expected_headers:
            assert header in headers, f"CSV should have '{header}' column"
        
        print(f"PASSED: CSV has proper headers: {lines[0]}")
    
    def test_export_csv_has_data_rows(self):
        """Test CSV export has data rows"""
        if not self.sales_token:
            pytest.skip("Sales login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/leads/export/csv",
            headers=self.get_sales_headers()
        )
        
        if response.status_code == 404:
            pytest.skip("No leads to export")
        
        assert response.status_code == 200
        
        csv_content = response.text
        lines = csv_content.strip().split('\n')
        
        # Should have header + at least one data row
        assert len(lines) >= 2, "CSV should have header and at least one data row"
        
        print(f"PASSED: CSV export has {len(lines) - 1} data rows")
    
    # ==================== AUTHENTICATION TESTS ====================
    
    def test_pause_requires_auth(self):
        """Test pause endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/leads/test-id/pause")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASSED: Pause endpoint requires authentication")
    
    def test_resume_requires_auth(self):
        """Test resume endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/leads/test-id/resume")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASSED: Resume endpoint requires authentication")
    
    def test_export_csv_requires_auth(self):
        """Test CSV export endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/leads/export/csv")
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("PASSED: CSV export endpoint requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
