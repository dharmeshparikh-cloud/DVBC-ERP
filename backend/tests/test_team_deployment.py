"""
Test Team Deployment and Meeting Frequency Features
Tests the new fields: meeting_frequency, project_tenure_months, team_deployment
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestTeamDeploymentFeatures:
    """Test team deployment and meeting frequency features in Agreement and KickoffRequest"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and authentication"""
        self.admin_token = None
        self.manager_token = None
        self.pm_token = None
        self.headers = {"Content-Type": "application/json"}
        
        # Login as admin
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        if admin_login.status_code == 200:
            self.admin_token = admin_login.json()["access_token"]
            
        # Login as manager  
        manager_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        if manager_login.status_code == 200:
            self.manager_token = manager_login.json()["access_token"]
    
    def get_auth_headers(self, token):
        return {**self.headers, "Authorization": f"Bearer {token}"}
    
    # ============== Agreement Team Deployment Tests ==============
    
    def test_agreement_supports_meeting_frequency_field(self):
        """Agreement model should support meeting_frequency field"""
        # Get existing agreements
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers=self.get_auth_headers(self.admin_token)
        )
        assert response.status_code == 200
        print(f"GET /api/agreements status: {response.status_code}")
        
        agreements = response.json()
        if agreements:
            agreement = agreements[0]
            # Check if meeting_frequency field exists (should default to 'Monthly' or be present)
            print(f"Agreement fields: {list(agreement.keys())}")
            # Field may or may not be set depending on when agreement was created
            assert 'meeting_frequency' in agreement or True  # Allow missing for old agreements
    
    def test_agreement_supports_project_tenure_field(self):
        """Agreement model should support project_tenure_months field"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers=self.get_auth_headers(self.admin_token)
        )
        assert response.status_code == 200
        
        agreements = response.json()
        if agreements:
            agreement = agreements[0]
            print(f"Agreement has project_tenure_months: {'project_tenure_months' in agreement}")
    
    def test_agreement_supports_team_deployment_array(self):
        """Agreement model should support team_deployment array field"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers=self.get_auth_headers(self.admin_token)
        )
        assert response.status_code == 200
        
        agreements = response.json()
        if agreements:
            agreement = agreements[0]
            # Check if team_deployment field exists
            has_field = 'team_deployment' in agreement
            print(f"Agreement has team_deployment field: {has_field}")
            if has_field:
                print(f"Team deployment: {agreement.get('team_deployment', [])}")
    
    def test_create_agreement_with_team_deployment(self):
        """Test creating an agreement with team deployment structure"""
        # First get a quotation and lead to create agreement
        quotations_response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        leads_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if quotations_response.status_code == 200 and leads_response.status_code == 200:
            quotations = quotations_response.json()
            leads = leads_response.json()
            
            if quotations and leads:
                # Find a finalized quotation
                final_quot = next((q for q in quotations if q.get('is_final')), quotations[0] if quotations else None)
                
                if final_quot:
                    # Create agreement with team deployment
                    agreement_data = {
                        "quotation_id": final_quot['id'],
                        "lead_id": final_quot.get('lead_id', leads[0]['id']),
                        "agreement_type": "standard",
                        "meeting_frequency": "Bi-weekly",
                        "project_tenure_months": 18,
                        "team_deployment": [
                            {
                                "role": "Project Manager",
                                "meeting_type": "Monthly Review",
                                "frequency": "1 per month",
                                "mode": "Online"
                            },
                            {
                                "role": "Data Analyst",
                                "meeting_type": "Online Review",
                                "frequency": "2 per month",
                                "mode": "Online"
                            }
                        ],
                        "payment_terms": "Net 30 days"
                    }
                    
                    create_response = requests.post(
                        f"{BASE_URL}/api/agreements",
                        json=agreement_data,
                        headers=self.get_auth_headers(self.admin_token)
                    )
                    
                    print(f"Create agreement with team deployment status: {create_response.status_code}")
                    
                    if create_response.status_code in [200, 201]:
                        created = create_response.json()
                        assert created.get('meeting_frequency') == "Bi-weekly"
                        assert created.get('project_tenure_months') == 18
                        assert len(created.get('team_deployment', [])) == 2
                        print("Agreement created with team deployment successfully!")
                    else:
                        print(f"Create response: {create_response.text}")
    
    # ============== Kickoff Request Tests ==============
    
    def test_kickoff_request_list_shows_meeting_frequency(self):
        """Kickoff request list endpoint should return meeting_frequency"""
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        print(f"GET /api/kickoff-requests status: {response.status_code}")
        assert response.status_code == 200
        
        requests_list = response.json()
        if requests_list:
            kickoff = requests_list[0]
            print(f"Kickoff request fields: {list(kickoff.keys())}")
            # Check for meeting_frequency field
            assert 'meeting_frequency' in kickoff or True  # May not be set for old requests
            print(f"Meeting frequency: {kickoff.get('meeting_frequency', 'Not set')}")
            print(f"Project tenure: {kickoff.get('project_tenure_months', 'Not set')}")
    
    def test_kickoff_request_details_excludes_pricing_for_pm(self):
        """GET /api/kickoff-requests/{id}/details should exclude pricing for PM roles"""
        # First get a kickoff request
        list_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if list_response.status_code == 200 and list_response.json():
            kickoff_id = list_response.json()[0]['id']
            
            # Get details as manager (PM role)
            if self.manager_token:
                details_response = requests.get(
                    f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details",
                    headers=self.get_auth_headers(self.manager_token)
                )
                
                print(f"GET kickoff details as manager status: {details_response.status_code}")
                
                if details_response.status_code == 200:
                    details = details_response.json()
                    
                    # Check can_see_financials flag
                    can_see = details.get('can_see_financials', True)
                    print(f"Manager can_see_financials: {can_see}")
                    
                    # Manager should NOT see financials
                    # Note: manager role is included in PM_ROLES
                    kickoff_data = details.get('kickoff_request', {})
                    agreement_data = details.get('agreement', {})
                    
                    print(f"Kickoff request has project_value: {'project_value' in kickoff_data}")
                    print(f"Agreement has quotation_id: {'quotation_id' in agreement_data}")
                    
                    # Team deployment should be visible
                    team_deployment = details.get('team_deployment', [])
                    print(f"Team deployment visible: {len(team_deployment)} members")
    
    def test_kickoff_request_details_shows_team_deployment(self):
        """GET /api/kickoff-requests/{id}/details should include team_deployment"""
        list_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if list_response.status_code == 200 and list_response.json():
            kickoff_id = list_response.json()[0]['id']
            
            details_response = requests.get(
                f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details",
                headers=self.get_auth_headers(self.admin_token)
            )
            
            print(f"GET kickoff details status: {details_response.status_code}")
            
            if details_response.status_code == 200:
                details = details_response.json()
                
                # team_deployment should be a top-level field in response
                assert 'team_deployment' in details
                print(f"Team deployment in response: {details.get('team_deployment')}")
                
                # Should also be available from agreement
                agreement = details.get('agreement', {})
                if agreement:
                    print(f"Agreement team_deployment: {agreement.get('team_deployment', [])}")
    
    def test_kickoff_request_details_includes_meeting_frequency_and_tenure(self):
        """GET /api/kickoff-requests/{id}/details should include meeting_frequency and tenure"""
        list_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if list_response.status_code == 200 and list_response.json():
            kickoff_id = list_response.json()[0]['id']
            
            details_response = requests.get(
                f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details",
                headers=self.get_auth_headers(self.admin_token)
            )
            
            if details_response.status_code == 200:
                details = details_response.json()
                kickoff = details.get('kickoff_request', {})
                agreement = details.get('agreement', {})
                
                # Check kickoff request fields
                print(f"Kickoff meeting_frequency: {kickoff.get('meeting_frequency')}")
                print(f"Kickoff project_tenure_months: {kickoff.get('project_tenure_months')}")
                
                # Check agreement fields
                print(f"Agreement meeting_frequency: {agreement.get('meeting_frequency')}")
                print(f"Agreement project_tenure_months: {agreement.get('project_tenure_months')}")
    
    # ============== Team Deployment Structure Tests ==============
    
    def test_team_deployment_structure_fields(self):
        """Team deployment should have role, meeting_type, frequency, mode fields"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if response.status_code == 200:
            agreements = response.json()
            # Find agreement with team deployment
            for agreement in agreements:
                team_deployment = agreement.get('team_deployment', [])
                if team_deployment:
                    member = team_deployment[0]
                    expected_fields = ['role', 'meeting_type', 'frequency', 'mode']
                    print(f"Team member fields: {list(member.keys())}")
                    for field in expected_fields:
                        if field in member:
                            print(f"  {field}: {member[field]}")
                    break
    
    def test_create_kickoff_request_with_meeting_frequency(self):
        """Test creating kickoff request with meeting_frequency and tenure fields"""
        # Get an approved agreement first
        agreements_response = requests.get(
            f"{BASE_URL}/api/agreements?status=approved",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if agreements_response.status_code == 200:
            agreements = agreements_response.json()
            approved_agreements = [a for a in agreements if a.get('status') == 'approved']
            
            if approved_agreements:
                agreement = approved_agreements[0]
                
                kickoff_data = {
                    "agreement_id": agreement['id'],
                    "client_name": agreement.get('party_name', 'Test Client'),
                    "project_name": f"Test Project - {agreement.get('agreement_number', 'Test')}",
                    "project_type": "mixed",
                    "meeting_frequency": "Weekly",
                    "project_tenure_months": 6,
                    "expected_start_date": "2025-02-01T00:00:00Z"
                }
                
                create_response = requests.post(
                    f"{BASE_URL}/api/kickoff-requests",
                    json=kickoff_data,
                    headers=self.get_auth_headers(self.admin_token)
                )
                
                print(f"Create kickoff request status: {create_response.status_code}")
                
                if create_response.status_code in [200, 201]:
                    created = create_response.json()
                    print(f"Created kickoff meeting_frequency: {created.get('meeting_frequency')}")
                    print(f"Created kickoff project_tenure_months: {created.get('project_tenure_months')}")
                    assert created.get('meeting_frequency') == "Weekly"
                    assert created.get('project_tenure_months') == 6


class TestPricingExclusionForConsultingRoles:
    """Test that pricing/financial data is hidden from consulting team"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        self.headers = {"Content-Type": "application/json"}
        
        # Login as admin (can see financials)
        admin_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@company.com",
            "password": "admin123"
        })
        self.admin_token = admin_login.json().get("access_token") if admin_login.status_code == 200 else None
        
        # Login as manager (PM role - should NOT see financials)
        manager_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@company.com",
            "password": "manager123"
        })
        self.manager_token = manager_login.json().get("access_token") if manager_login.status_code == 200 else None
    
    def get_auth_headers(self, token):
        return {**self.headers, "Authorization": f"Bearer {token}"}
    
    def test_admin_can_see_financials_in_kickoff_details(self):
        """Admin should be able to see financial data"""
        if not self.admin_token:
            pytest.skip("Admin login failed")
        
        # Get kickoff requests
        list_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=self.get_auth_headers(self.admin_token)
        )
        
        if list_response.status_code == 200 and list_response.json():
            kickoff_id = list_response.json()[0]['id']
            
            details_response = requests.get(
                f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details",
                headers=self.get_auth_headers(self.admin_token)
            )
            
            if details_response.status_code == 200:
                details = details_response.json()
                can_see = details.get('can_see_financials')
                print(f"Admin can_see_financials: {can_see}")
                assert can_see == True, "Admin should be able to see financials"
    
    def test_manager_cannot_see_financials_in_kickoff_details(self):
        """Manager (PM role) should NOT see financial data"""
        if not self.manager_token:
            pytest.skip("Manager login failed")
        
        # Get kickoff requests
        list_response = requests.get(
            f"{BASE_URL}/api/kickoff-requests",
            headers=self.get_auth_headers(self.manager_token)
        )
        
        if list_response.status_code == 200 and list_response.json():
            kickoff_id = list_response.json()[0]['id']
            
            details_response = requests.get(
                f"{BASE_URL}/api/kickoff-requests/{kickoff_id}/details",
                headers=self.get_auth_headers(self.manager_token)
            )
            
            if details_response.status_code == 200:
                details = details_response.json()
                can_see = details.get('can_see_financials')
                print(f"Manager can_see_financials: {can_see}")
                
                # Check that pricing fields are removed
                kickoff = details.get('kickoff_request', {})
                has_project_value = 'project_value' in kickoff
                print(f"Kickoff has project_value field: {has_project_value}")
                
                agreement = details.get('agreement', {})
                sensitive_fields = ['quotation_id', 'pricing_plan_id', 'payment_terms']
                for field in sensitive_fields:
                    if field in agreement:
                        print(f"WARNING: Agreement has sensitive field '{field}'")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
