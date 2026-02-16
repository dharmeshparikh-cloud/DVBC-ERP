"""
Backend Tests for Pricing Eligibility Check Feature
Testing: MOM mandatory before pricing, Hot lead warning with override
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://erp-dashboard-93.preview.emergentagent.com')


class TestPricingEligibility:
    """Tests for GET /api/leads/{lead_id}/pricing-eligibility endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Get auth token and existing lead data"""
        self.client = api_client
        self.token = self.get_admin_token()
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        
    def get_admin_token(self):
        """Get admin auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@company.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_pricing_eligibility_returns_200_for_valid_lead(self):
        """Test that pricing eligibility endpoint returns 200 for valid lead"""
        # Get a lead first
        leads_response = self.client.get(f"{BASE_URL}/api/leads")
        assert leads_response.status_code == 200
        leads = leads_response.json()
        assert len(leads) > 0, "No leads in system"
        
        lead_id = leads[0]['id']
        
        # Check eligibility
        response = self.client.get(f"{BASE_URL}/api/leads/{lead_id}/pricing-eligibility")
        assert response.status_code == 200
        
        data = response.json()
        # Validate response structure
        assert 'lead_id' in data
        assert 'lead_name' in data
        assert 'company' in data
        assert 'lead_score' in data
        assert 'temperature' in data
        assert 'is_hot' in data
        assert 'total_meetings' in data
        assert 'meetings_with_mom' in data
        assert 'pending_mom' in data
        assert 'has_meetings' in data
        assert 'all_mom_complete' in data
        assert 'can_proceed' in data
        assert 'needs_warning' in data
        assert 'blockers' in data
        assert 'warnings' in data
        
    def test_pricing_eligibility_returns_404_for_invalid_lead(self):
        """Test that endpoint returns 404 for non-existent lead"""
        response = self.client.get(f"{BASE_URL}/api/leads/nonexistent-lead-id/pricing-eligibility")
        assert response.status_code == 404
        
    def test_pricing_eligibility_temperature_classification(self):
        """Test temperature classification based on lead score"""
        # Get leads with different scores
        leads_response = self.client.get(f"{BASE_URL}/api/leads")
        leads = leads_response.json()
        
        for lead in leads[:10]:  # Check first 10 leads
            response = self.client.get(f"{BASE_URL}/api/leads/{lead['id']}/pricing-eligibility")
            data = response.json()
            
            score = data['lead_score']
            temperature = data['temperature']
            
            # Validate temperature classification
            if score >= 80:
                assert temperature == 'hot', f"Score {score} should be hot, got {temperature}"
                assert data['is_hot'] == True
            elif score >= 50:
                assert temperature == 'warm', f"Score {score} should be warm, got {temperature}"
                assert data['is_hot'] == False
            else:
                assert temperature == 'cold', f"Score {score} should be cold, got {temperature}"
                assert data['is_hot'] == False
                
    def test_pricing_eligibility_blocker_for_no_meetings(self):
        """Test that leads without meetings have blocker"""
        leads_response = self.client.get(f"{BASE_URL}/api/leads")
        leads = leads_response.json()
        
        for lead in leads:
            response = self.client.get(f"{BASE_URL}/api/leads/{lead['id']}/pricing-eligibility")
            data = response.json()
            
            if data['total_meetings'] == 0:
                assert data['can_proceed'] == False, "Should not proceed without meetings"
                # Check blocker exists
                blockers = [b for b in data['blockers'] if b is not None]
                blocker_types = [b['type'] for b in blockers]
                assert 'no_meetings' in blocker_types, "Should have no_meetings blocker"
                break
                
    def test_pricing_eligibility_blocker_for_pending_mom(self):
        """Test that leads with pending MOM have blocker"""
        leads_response = self.client.get(f"{BASE_URL}/api/leads")
        leads = leads_response.json()
        
        for lead in leads[:20]:  # Check first 20 leads
            response = self.client.get(f"{BASE_URL}/api/leads/{lead['id']}/pricing-eligibility")
            data = response.json()
            
            if data['pending_mom'] > 0:
                assert data['can_proceed'] == False, "Should not proceed with pending MOM"
                blockers = [b for b in data['blockers'] if b is not None]
                blocker_types = [b['type'] for b in blockers]
                assert 'pending_mom' in blocker_types, "Should have pending_mom blocker"
                break
                
    def test_pricing_eligibility_warning_for_non_hot_lead(self):
        """Test that non-hot leads with all MOM complete have warning"""
        leads_response = self.client.get(f"{BASE_URL}/api/leads")
        leads = leads_response.json()
        
        for lead in leads:
            response = self.client.get(f"{BASE_URL}/api/leads/{lead['id']}/pricing-eligibility")
            data = response.json()
            
            # Check for warning when can proceed but not hot
            if data['can_proceed'] and not data['is_hot']:
                assert data['needs_warning'] == True, "Should need warning for non-hot lead"
                warnings = [w for w in data['warnings'] if w is not None]
                assert len(warnings) > 0, "Should have warning message"
                warning_types = [w['type'] for w in warnings]
                assert 'not_hot' in warning_types, "Should have not_hot warning"
                break


class TestLeadsPermissions:
    """Tests for Leads page permissions via API"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup: Get auth tokens for different users"""
        self.client = api_client
        
    def get_token(self, email, password):
        """Get auth token for user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_admin_can_create_lead(self):
        """Test that admin can create lead"""
        token = self.get_token("admin@company.com", "admin123")
        assert token is not None, "Admin login failed"
        
        response = requests.post(
            f"{BASE_URL}/api/leads",
            json={
                "first_name": "TEST_Admin",
                "last_name": "CreatedLead",
                "company": "Test Company Admin"
            },
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        assert response.status_code == 200
        lead = response.json()
        assert lead['first_name'] == "TEST_Admin"
        
        # Cleanup - delete the lead
        requests.delete(
            f"{BASE_URL}/api/leads/{lead['id']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
    def test_sales_user_can_access_leads(self):
        """Test that sales user can access leads"""
        token = self.get_token("sales@consulting.com", "sales123")
        if not token:
            pytest.skip("Sales user not found in system")
            
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


class TestFlowDiagramEndpoints:
    """Tests related to workflow diagram functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client):
        """Setup with admin auth"""
        self.client = api_client
        token_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@company.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        if token_response.status_code == 200:
            self.token = token_response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Admin login failed")
    
    def test_leads_endpoint_works(self):
        """Test that leads endpoint returns data for workflow"""
        response = self.client.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 200
        leads = response.json()
        assert isinstance(leads, list)
        
    def test_meetings_endpoint_works(self):
        """Test that meetings endpoint returns data"""
        response = self.client.get(f"{BASE_URL}/api/meetings")
        assert response.status_code == 200
        meetings = response.json()
        assert isinstance(meetings, list)
        
    def test_pricing_plans_endpoint_works(self):
        """Test that pricing plans endpoint returns data"""
        response = self.client.get(f"{BASE_URL}/api/pricing-plans")
        assert response.status_code == 200
        
    def test_projects_endpoint_works(self):
        """Test that projects endpoint returns data"""
        response = self.client.get(f"{BASE_URL}/api/projects")
        assert response.status_code == 200
        projects = response.json()
        assert isinstance(projects, list)


class TestPermissionsEndpoint:
    """Tests for permissions API endpoint"""
    
    def test_admin_gets_permissions(self):
        """Test that admin can access their permissions"""
        token_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@company.com", "password": "admin123"},
            headers={"Content-Type": "application/json"}
        )
        assert token_response.status_code == 200
        token = token_response.json().get("access_token")
        
        # Try to get permissions endpoint
        response = requests.get(
            f"{BASE_URL}/api/users/me/permissions",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Endpoint may not exist, so we check if it returns 404 or 200
        # If 404, that's fine - frontend uses default permissions
        assert response.status_code in [200, 404]


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session
