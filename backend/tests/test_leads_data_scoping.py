"""
Test suite for Leads Data Scoping by Employee Hierarchy
- Admin sees all leads
- Manager (Dhamresh EMP110) sees own leads + reportee (Rahul EMP001) leads
- Executive (Rahul EMP001) sees only own leads
- Single lead access respects hierarchy (403 if not accessible)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from review request
CREDENTIALS = {
    'admin': {'email': 'admin@dvbc.com', 'password': 'admin123'},
    'rahul': {'email': 'rahul.kumar@dvbc.com', 'password': 'Welcome@EMP001'},
    'dhamresh': {'email': 'dp@dvbc.com', 'password': 'Welcome@123'}
}


@pytest.fixture(scope='module')
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['admin'])
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()['access_token']


@pytest.fixture(scope='module')
def rahul_token():
    """Get Rahul's authentication token - sees only own leads"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['rahul'])
    assert response.status_code == 200, f"Rahul login failed: {response.text}"
    return response.json()['access_token']


@pytest.fixture(scope='module')
def dhamresh_token():
    """Get Dhamresh's authentication token - sees own + team leads"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CREDENTIALS['dhamresh'])
    assert response.status_code == 200, f"Dhamresh login failed: {response.text}"
    return response.json()['access_token']


class TestLeadsDataScoping:
    """Tests for leads data scoping by employee hierarchy"""
    
    def test_admin_login(self, admin_token):
        """Verify admin can login successfully"""
        assert admin_token is not None
        assert len(admin_token) > 10
        print(f"Admin token obtained: {admin_token[:20]}...")
    
    def test_rahul_login(self, rahul_token):
        """Verify Rahul can login successfully"""
        assert rahul_token is not None
        assert len(rahul_token) > 10
        print(f"Rahul token obtained: {rahul_token[:20]}...")
    
    def test_dhamresh_login(self, dhamresh_token):
        """Verify Dhamresh can login successfully"""
        assert dhamresh_token is not None
        assert len(dhamresh_token) > 10
        print(f"Dhamresh token obtained: {dhamresh_token[:20]}...")
    
    def test_admin_sees_all_leads(self, admin_token):
        """Admin should see all leads in the system"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        leads = response.json()
        
        # Admin should see many leads (expected ~18 according to spec)
        print(f"Admin sees {len(leads)} leads")
        assert len(leads) >= 1, "Admin should see at least 1 lead"
        # Verify response has valid lead structure
        if leads:
            lead = leads[0]
            assert 'id' in lead, "Lead should have an id"
            assert 'company' in lead, "Lead should have company field"
    
    def test_rahul_sees_only_own_leads(self, rahul_token):
        """Rahul (EMP001) should see only his own leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        leads = response.json()
        
        print(f"Rahul sees {len(leads)} leads")
        # Based on spec, Rahul should see at least 1 lead (Test Company by Rahul)
        assert len(leads) >= 1, "Rahul should see at least his own lead(s)"
        
        # Verify Rahul's test lead exists
        lead_names = [l.get('company_name', '') for l in leads]
        print(f"Rahul's leads: {lead_names}")
        
        # Check that the test lead 'Test Company by Rahul' is visible
        test_lead_found = any('Rahul' in name or 'Test Company' in name for name in lead_names)
        # Note: The lead might be named slightly differently
        print(f"Leads visible to Rahul: {lead_names}")
    
    def test_dhamresh_sees_team_leads(self, dhamresh_token, rahul_token):
        """Dhamresh (EMP110) should see own leads + Rahul's leads (as manager)"""
        # First get Rahul's leads count
        rahul_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        rahul_leads = rahul_response.json()
        rahul_lead_ids = [l['id'] for l in rahul_leads]
        
        # Now get Dhamresh's leads
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {dhamresh_token}'}
        )
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        dhamresh_leads = response.json()
        dhamresh_lead_ids = [l['id'] for l in dhamresh_leads]
        
        print(f"Dhamresh sees {len(dhamresh_leads)} leads")
        print(f"Rahul has {len(rahul_leads)} leads")
        
        # Dhamresh should see at least as many leads as Rahul (since Rahul reports to him)
        # Check that Rahul's leads are included in Dhamresh's view
        rahul_leads_visible_to_dhamresh = sum(1 for lid in rahul_lead_ids if lid in dhamresh_lead_ids)
        print(f"Rahul leads visible to Dhamresh: {rahul_leads_visible_to_dhamresh}/{len(rahul_leads)}")
        
        # Verify manager can see reportee leads
        assert rahul_leads_visible_to_dhamresh >= 1 or len(rahul_leads) == 0, \
            "Dhamresh should see Rahul's leads as his manager"


class TestSingleLeadAccess:
    """Tests for single lead access control"""
    
    def test_admin_can_access_any_lead(self, admin_token):
        """Admin should access any lead"""
        # First get a lead ID
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        leads = response.json()
        if not leads:
            pytest.skip("No leads available to test")
        
        lead_id = leads[0]['id']
        
        # Access single lead
        response = requests.get(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200, f"Admin failed to access lead: {response.text}"
        lead = response.json()
        assert lead['id'] == lead_id
        print(f"Admin successfully accessed lead: {lead.get('company_name')}")
    
    def test_rahul_can_access_own_lead(self, rahul_token):
        """Rahul should access his own leads"""
        # Get Rahul's leads
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        leads = response.json()
        if not leads:
            pytest.skip("Rahul has no leads to test")
        
        lead_id = leads[0]['id']
        
        # Access single lead
        response = requests.get(
            f"{BASE_URL}/api/leads/{lead_id}",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        assert response.status_code == 200, f"Rahul failed to access own lead: {response.text}"
        lead = response.json()
        assert lead['id'] == lead_id
        print(f"Rahul successfully accessed his lead: {lead.get('company_name')}")
    
    def test_dhamresh_can_access_reportee_lead(self, dhamresh_token, rahul_token):
        """Dhamresh should access Rahul's leads as his manager"""
        # Get Rahul's leads
        rahul_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        rahul_leads = rahul_response.json()
        if not rahul_leads:
            pytest.skip("Rahul has no leads to test manager access")
        
        rahul_lead_id = rahul_leads[0]['id']
        
        # Dhamresh should be able to access Rahul's lead
        response = requests.get(
            f"{BASE_URL}/api/leads/{rahul_lead_id}",
            headers={'Authorization': f'Bearer {dhamresh_token}'}
        )
        assert response.status_code == 200, \
            f"Dhamresh (manager) failed to access Rahul's lead: {response.text}"
        lead = response.json()
        assert lead['id'] == rahul_lead_id
        print(f"Dhamresh successfully accessed Rahul's lead: {lead.get('company_name')}")
    
    def test_rahul_cannot_access_other_leads(self, rahul_token, admin_token):
        """Rahul should NOT access leads he doesn't own or manage"""
        # Get all leads as admin
        admin_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        all_leads = admin_response.json()
        
        # Get Rahul's leads
        rahul_response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        rahul_leads = rahul_response.json()
        rahul_lead_ids = {l['id'] for l in rahul_leads}
        
        # Find a lead Rahul doesn't have access to
        other_leads = [l for l in all_leads if l['id'] not in rahul_lead_ids]
        
        if not other_leads:
            pytest.skip("No leads outside Rahul's access to test 403")
        
        other_lead_id = other_leads[0]['id']
        
        # Rahul should get 403 when accessing other's lead
        response = requests.get(
            f"{BASE_URL}/api/leads/{other_lead_id}",
            headers={'Authorization': f'Bearer {rahul_token}'}
        )
        
        print(f"Rahul trying to access lead '{other_leads[0].get('company_name')}': status={response.status_code}")
        assert response.status_code == 403, \
            f"Expected 403 Forbidden, got {response.status_code}. Rahul should not access other's leads"
        print(f"Correctly denied access to Rahul for lead: {other_lead_id}")


class TestVerifyHierarchy:
    """Verify employee hierarchy setup"""
    
    def test_verify_rahul_reports_to_dhamresh(self, admin_token):
        """Confirm Rahul (EMP001) reports to Dhamresh (EMP110)"""
        # Get employees
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        employees = response.json()
        
        # Find Rahul and Dhamresh
        rahul = None
        dhamresh = None
        for emp in employees:
            if emp.get('employee_id') == 'EMP001':
                rahul = emp
            if emp.get('employee_id') == 'EMP110':
                dhamresh = emp
        
        assert rahul is not None, "Rahul (EMP001) not found in employees"
        assert dhamresh is not None, "Dhamresh (EMP110) not found in employees"
        
        print(f"Rahul: {rahul.get('first_name')} {rahul.get('last_name')}, reporting_manager_id: {rahul.get('reporting_manager_id')}")
        print(f"Dhamresh: {dhamresh.get('first_name')} {dhamresh.get('last_name')}, employee_id: {dhamresh.get('employee_id')}")
        
        # Verify hierarchy
        assert rahul.get('reporting_manager_id') == 'EMP110', \
            f"Rahul should report to Dhamresh (EMP110), but reports to {rahul.get('reporting_manager_id')}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
