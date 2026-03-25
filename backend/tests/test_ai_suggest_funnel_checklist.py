"""
Test AI Suggestion Endpoint and Updated Funnel Checklist
Features tested:
1. POST /api/ai/suggest - AI-powered text suggestion endpoint
2. GET /api/leads/{id}/funnel-checklist - Updated checklist with correct mandatory fields
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SALES_CREDENTIALS = {"employee_id": "EMP003", "password": "sales123"}
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}


class TestAISuggestionEndpoint:
    """Tests for POST /api/ai/suggest endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as sales executive
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if login_res.status_code == 200:
            token = login_res.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
        else:
            pytest.skip(f"Login failed: {login_res.status_code}")
    
    def test_ai_suggest_mom_context(self):
        """Test AI suggestion with context_type='mom'"""
        payload = {
            "context_type": "mom",
            "rough_text": "discussed pricing, client wants discount, need to follow up next week",
            "client_name": "John Doe",
            "company": "Acme Corp"
        }
        
        response = self.session.post(f"{BASE_URL}/api/ai/suggest", json=payload)
        
        # AI endpoint should return 200 with suggestion
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestion" in data, "Response should contain 'suggestion' field"
        assert len(data["suggestion"]) > 0, "Suggestion should not be empty"
        print(f"AI MOM suggestion received: {data['suggestion'][:100]}...")
    
    def test_ai_suggest_follow_up_context(self):
        """Test AI suggestion with context_type='follow_up'"""
        payload = {
            "context_type": "follow_up",
            "rough_text": "call client about proposal status",
            "client_name": "Jane Smith",
            "company": "Tech Solutions"
        }
        
        response = self.session.post(f"{BASE_URL}/api/ai/suggest", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestion" in data
        assert len(data["suggestion"]) > 0
        print(f"AI follow_up suggestion received: {data['suggestion'][:100]}...")
    
    def test_ai_suggest_next_steps_context(self):
        """Test AI suggestion with context_type='next_steps'"""
        payload = {
            "context_type": "next_steps",
            "rough_text": "send revised quote, schedule demo, prepare contract",
            "client_name": "Bob Wilson",
            "company": "Global Industries"
        }
        
        response = self.session.post(f"{BASE_URL}/api/ai/suggest", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestion" in data
        assert len(data["suggestion"]) > 0
        print(f"AI next_steps suggestion received: {data['suggestion'][:100]}...")
    
    def test_ai_suggest_empty_text_returns_400(self):
        """Test that empty rough_text AND empty additional_context returns 400"""
        payload = {
            "context_type": "mom",
            "rough_text": "",
            "additional_context": "",
            "client_name": "Test Client"
        }
        
        response = self.session.post(f"{BASE_URL}/api/ai/suggest", json=payload)
        
        assert response.status_code == 400, f"Expected 400 for empty text, got {response.status_code}: {response.text}"
        print("Correctly returned 400 for empty text")
    
    def test_ai_suggest_with_additional_context_only(self):
        """Test AI suggestion works with only additional_context (no rough_text)"""
        payload = {
            "context_type": "notes",
            "rough_text": "",
            "additional_context": "Meeting about new project requirements for Q2 2026",
            "client_name": "Test Client",
            "company": "Test Company"
        }
        
        response = self.session.post(f"{BASE_URL}/api/ai/suggest", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "suggestion" in data
        print(f"AI suggestion with additional_context only: {data['suggestion'][:100]}...")
    
    def test_ai_suggest_requires_auth(self):
        """Test that AI suggest endpoint requires authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        payload = {
            "context_type": "mom",
            "rough_text": "test text"
        }
        
        response = no_auth_session.post(f"{BASE_URL}/api/ai/suggest", json=payload)
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("Correctly requires authentication")


class TestFunnelChecklist:
    """Tests for GET /api/leads/{id}/funnel-checklist with updated requirements"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and find a lead for tests"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as sales executive
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if login_res.status_code == 200:
            token = login_res.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Login failed: {login_res.status_code}")
        
        # Get a lead ID for testing
        leads_res = self.session.get(f"{BASE_URL}/api/leads?page_size=5")
        if leads_res.status_code == 200:
            leads_data = leads_res.json()
            leads = leads_data.get("data", []) if isinstance(leads_data, dict) else leads_data
            if leads:
                self.lead_id = leads[0].get("id")
            else:
                pytest.skip("No leads found for testing")
        else:
            pytest.skip(f"Failed to get leads: {leads_res.status_code}")
    
    def test_funnel_checklist_endpoint_exists(self):
        """Test that funnel-checklist endpoint returns data"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Should have all funnel steps
        expected_steps = ["lead_capture", "record_meeting", "pricing_plan", "scope_of_work", 
                         "quotation", "agreement", "record_payment", "kickoff_request", "project_created"]
        
        for step in expected_steps:
            assert step in data, f"Missing step: {step}"
        
        print(f"Funnel checklist has all {len(expected_steps)} steps")
    
    def test_pricing_plan_checklist_requirements(self):
        """Test pricing_plan step shows correct required items"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        pricing_plan = data.get("pricing_plan", {})
        requirements = pricing_plan.get("requirements", [])
        
        # Extract requirement items
        req_items = [r.get("item", "") for r in requirements]
        
        # Check for the NEW required items (not old ones like 'project type' or 'services itemized')
        assert any("team member" in item.lower() for item in req_items), \
            f"pricing_plan should require 'At least one team member added'. Got: {req_items}"
        
        assert any("total investment" in item.lower() and "> 0" in item for item in req_items), \
            f"pricing_plan should require 'Total investment entered (> 0)'. Got: {req_items}"
        
        assert any("payment start date" in item.lower() for item in req_items), \
            f"pricing_plan should require 'Payment start date set'. Got: {req_items}"
        
        print(f"pricing_plan requirements verified: {req_items}")
    
    def test_record_meeting_checklist_requirements(self):
        """Test record_meeting step shows correct required items"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        record_meeting = data.get("record_meeting", {})
        requirements = record_meeting.get("requirements", [])
        
        req_items = [r.get("item", "") for r in requirements]
        
        # Check for required items
        assert any("meeting date" in item.lower() and "time" in item.lower() for item in req_items), \
            f"record_meeting should require 'Meeting date & time set'. Got: {req_items}"
        
        assert any("mom" in item.lower() and "summary" in item.lower() for item in req_items), \
            f"record_meeting should require 'MOM summary filled'. Got: {req_items}"
        
        print(f"record_meeting requirements verified: {req_items}")
    
    def test_agreement_checklist_requirements(self):
        """Test agreement step shows 'Milestones added with amounts' as required"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        agreement = data.get("agreement", {})
        requirements = agreement.get("requirements", [])
        
        req_items = [r.get("item", "") for r in requirements]
        
        assert any("milestone" in item.lower() and "amount" in item.lower() for item in req_items), \
            f"agreement should require 'Milestones added with amounts'. Got: {req_items}"
        
        print(f"agreement requirements verified: {req_items}")
    
    def test_scope_of_work_checklist_requirements(self):
        """Test scope_of_work step shows 'At least one scope item with title' as required"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        sow = data.get("scope_of_work", {})
        requirements = sow.get("requirements", [])
        
        req_items = [r.get("item", "") for r in requirements]
        
        assert any("scope item" in item.lower() and "title" in item.lower() for item in req_items), \
            f"scope_of_work should require 'At least one scope item with title'. Got: {req_items}"
        
        print(f"scope_of_work requirements verified: {req_items}")
    
    def test_checklist_has_tips(self):
        """Test that checklist steps include tips for guidance"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check that at least some steps have tips
        steps_with_tips = 0
        for step_name, step_data in data.items():
            if isinstance(step_data, dict) and step_data.get("tips"):
                steps_with_tips += 1
        
        assert steps_with_tips > 0, "Checklist should include tips for guidance"
        print(f"Found {steps_with_tips} steps with tips")


class TestFunnelChecklistCompletionStatus:
    """Test that checklist correctly shows completion status based on actual data"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if login_res.status_code == 200:
            token = login_res.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Login failed: {login_res.status_code}")
        
        # Get a lead with some funnel data
        leads_res = self.session.get(f"{BASE_URL}/api/leads?page_size=20")
        if leads_res.status_code == 200:
            leads_data = leads_res.json()
            leads = leads_data.get("data", []) if isinstance(leads_data, dict) else leads_data
            if leads:
                self.lead_id = leads[0].get("id")
            else:
                pytest.skip("No leads found")
        else:
            pytest.skip(f"Failed to get leads: {leads_res.status_code}")
    
    def test_lead_capture_always_completed(self):
        """Test that lead_capture step is always marked as completed for existing leads"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        lead_capture = data.get("lead_capture", {})
        
        assert lead_capture.get("completed") == True, "lead_capture should always be completed for existing leads"
        print("lead_capture correctly marked as completed")
    
    def test_checklist_requirements_have_completed_flag(self):
        """Test that each requirement has a 'completed' boolean flag"""
        response = self.session.get(f"{BASE_URL}/api/leads/{self.lead_id}/funnel-checklist")
        assert response.status_code == 200
        
        data = response.json()
        
        for step_name, step_data in data.items():
            if isinstance(step_data, dict) and "requirements" in step_data:
                for req in step_data["requirements"]:
                    assert "completed" in req, f"Requirement in {step_name} missing 'completed' flag: {req}"
                    assert isinstance(req["completed"], bool), f"'completed' should be boolean in {step_name}"
        
        print("All requirements have 'completed' boolean flag")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
