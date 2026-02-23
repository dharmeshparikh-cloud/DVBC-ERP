"""
Test Sales Funnel Bug Fixes - P0 Issues
1. Record Meeting button passing leadId in URL
2. Lead status auto-update when funnel progress changes
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSalesFunnelBugFixes:
    """Test cases for P0 sales funnel bug fixes"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test with authentication"""
        # Login as Sales Executive
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "SE001", "password": "password123"}
        )
        if login_resp.status_code != 200:
            pytest.skip("Authentication failed - cannot test sales funnel")
        
        self.token = login_resp.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.lead_id = "dac1da55-d96b-4401-8f8e-7ed99276822f"  # Test lead ID
    
    def test_funnel_progress_api_returns_correct_step_ids(self):
        """Verify funnel progress returns correct step IDs (record_meeting, not meeting)"""
        resp = requests.get(
            f"{BASE_URL}/api/leads/{self.lead_id}/funnel-progress",
            headers=self.headers
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        
        data = resp.json()
        
        # Verify step IDs use correct format
        completed_steps = data.get("completed_steps", [])
        current_step = data.get("current_step", "")
        
        # Step IDs should be record_meeting, pricing_plan, etc. (not meeting, pricing)
        valid_step_ids = [
            "lead_capture", "record_meeting", "pricing_plan", "scope_of_work",
            "quotation", "agreement", "record_payment", "kickoff_request", "project_created"
        ]
        
        for step in completed_steps:
            assert step in valid_step_ids, f"Invalid step ID in completed_steps: {step}"
        
        assert current_step in valid_step_ids, f"Invalid current_step: {current_step}"
        print(f"✓ Step IDs are correct: completed={completed_steps}, current={current_step}")
    
    def test_funnel_progress_api_returns_lead_id(self):
        """Verify funnel progress API returns the lead_id"""
        resp = requests.get(
            f"{BASE_URL}/api/leads/{self.lead_id}/funnel-progress",
            headers=self.headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        assert data.get("lead_id") == self.lead_id, "API should return the queried lead_id"
        print(f"✓ lead_id returned correctly: {data.get('lead_id')}")
    
    def test_lead_status_auto_updates_with_funnel_progress(self):
        """Verify lead status auto-updates when funnel progress is fetched"""
        # Get current funnel progress (triggers auto-update)
        resp = requests.get(
            f"{BASE_URL}/api/leads/{self.lead_id}/funnel-progress",
            headers=self.headers
        )
        assert resp.status_code == 200
        
        funnel_data = resp.json()
        funnel_status = funnel_data.get("status")
        completed_steps = funnel_data.get("completed_steps", [])
        
        # Now get the lead directly
        lead_resp = requests.get(
            f"{BASE_URL}/api/leads/{self.lead_id}",
            headers=self.headers
        )
        assert lead_resp.status_code == 200
        
        lead_data = lead_resp.json()
        lead_status = lead_data.get("status")
        
        # Verify both APIs return consistent status
        assert funnel_status == lead_status, (
            f"Status mismatch: funnel={funnel_status}, lead={lead_status}"
        )
        
        # Verify status matches expected based on completed steps
        status_map = {
            "lead_capture": "new",
            "record_meeting": "contacted",
            "pricing_plan": "qualified",
            "scope_of_work": "qualified",
            "quotation": "proposal",
            "agreement": "agreement",
            "record_payment": "agreement",
            "kickoff_request": "agreement",
            "project_created": "closed"
        }
        
        # Find the last completed step that has a status mapping
        expected_status = "new"
        for step in ["lead_capture", "record_meeting", "pricing_plan", "scope_of_work",
                     "quotation", "agreement", "record_payment", "kickoff_request", "project_created"]:
            if step in completed_steps:
                expected_status = status_map.get(step, expected_status)
        
        assert lead_status == expected_status, (
            f"Lead status should be '{expected_status}' based on completed steps {completed_steps}, "
            f"but got '{lead_status}'"
        )
        print(f"✓ Lead status auto-updated correctly: {lead_status} (based on {completed_steps})")
    
    def test_meeting_record_endpoint_works(self):
        """Verify meetings/record endpoint creates meeting for sales funnel"""
        meeting_data = {
            "lead_id": self.lead_id,
            "meeting_title": "Test Meeting - Pytest",
            "meeting_date": "2026-02-23",
            "meeting_time": "14:00",
            "mode": "online",
            "attendees": ["SE001"],
            "mom": "Test MOM for pytest verification"
        }
        
        resp = requests.post(
            f"{BASE_URL}/api/meetings/record",
            json=meeting_data,
            headers=self.headers
        )
        assert resp.status_code == 200, f"Meeting creation failed: {resp.text}"
        
        data = resp.json()
        assert "meeting_id" in data, "Response should contain meeting_id"
        assert data.get("meeting", {}).get("lead_id") == self.lead_id
        print(f"✓ Meeting created successfully: {data.get('meeting_id')}")
    
    def test_funnel_checklist_endpoint(self):
        """Verify funnel checklist endpoint returns correct structure"""
        resp = requests.get(
            f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist",
            headers=self.headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        
        # Check required keys exist
        expected_keys = [
            "lead_capture", "record_meeting", "pricing_plan", "scope_of_work",
            "quotation", "agreement", "record_payment", "kickoff_request", "project_created"
        ]
        
        for key in expected_keys:
            assert key in data, f"Missing checklist key: {key}"
            step_data = data[key]
            assert "title" in step_data, f"Missing 'title' in {key}"
            assert "requirements" in step_data, f"Missing 'requirements' in {key}"
        
        print(f"✓ Funnel checklist structure is correct with {len(data)} steps")


class TestLeadStatusMapping:
    """Test cases for lead status mapping based on funnel progress"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test with authentication"""
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "SE001", "password": "password123"}
        )
        if login_resp.status_code != 200:
            pytest.skip("Authentication failed")
        
        self.token = login_resp.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_lead_returns_valid_status(self):
        """Verify lead API returns valid status enum value"""
        lead_id = "dac1da55-d96b-4401-8f8e-7ed99276822f"
        
        resp = requests.get(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers=self.headers
        )
        assert resp.status_code == 200
        
        data = resp.json()
        status = data.get("status")
        
        valid_statuses = ["new", "contacted", "qualified", "proposal", "agreement", "closed", "lost"]
        assert status in valid_statuses, f"Invalid status: {status}"
        print(f"✓ Lead status is valid: {status}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
