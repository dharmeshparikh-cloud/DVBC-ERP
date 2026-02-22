"""
Backend tests for Sales Funnel functionality:
- Pricing Plans, Quotations, Agreements, Manager Approvals
- Authentication with Manager role
- Currency in INR (₹)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://stability-checkpoint-1.preview.emergentagent.com').rstrip('/')

# Test credentials
MANAGER_EMAIL = "manager@company.com"
MANAGER_PASSWORD = "manager123"
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
EXECUTIVE_EMAIL = "executive@company.com"
EXECUTIVE_PASSWORD = "executive123"


@pytest.fixture(scope="module")
def manager_token():
    """Get manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        assert data["user"]["role"] == "manager", "Expected manager role"
        return data["access_token"]
    pytest.skip("Manager authentication failed")


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def executive_token():
    """Get executive authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EXECUTIVE_EMAIL,
        "password": EXECUTIVE_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Executive authentication failed")


class TestAuthentication:
    """Authentication endpoint tests"""
    
    def test_manager_login_success(self):
        """Test manager can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": MANAGER_EMAIL,
            "password": MANAGER_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == MANAGER_EMAIL
        assert data["user"]["role"] == "manager"
        print(f"✓ Manager login successful - role: {data['user']['role']}")

    def test_admin_login_success(self):
        """Test admin can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "admin"
        print(f"✓ Admin login successful - role: {data['user']['role']}")

    def test_executive_login_success(self):
        """Test executive can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EXECUTIVE_EMAIL,
            "password": EXECUTIVE_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "executive"
        print(f"✓ Executive login successful - role: {data['user']['role']}")

    def test_invalid_login(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@company.com",
            "password": "wrong"
        })
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


class TestPricingPlans:
    """Pricing Plans endpoint tests"""
    
    def test_get_pricing_plans(self, manager_token):
        """Test manager can view pricing plans"""
        response = requests.get(
            f"{BASE_URL}/api/pricing-plans",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} pricing plans")
        
        # Verify structure if plans exist
        if data:
            plan = data[0]
            assert "id" in plan
            assert "consultants" in plan
            print(f"✓ Pricing plan structure valid: {plan.get('id')[:8]}...")


class TestQuotations:
    """Quotations endpoint tests"""
    
    def test_get_quotations(self, manager_token):
        """Test manager can view quotations"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} quotations")
        
        # Verify INR amounts if quotations exist
        if data:
            quotation = data[0]
            assert "quotation_number" in quotation
            assert "grand_total" in quotation
            assert "subtotal" in quotation
            assert "gst_amount" in quotation
            assert quotation["grand_total"] > 0, "Grand total should be positive"
            print(f"✓ Quotation {quotation['quotation_number']}: ₹{quotation['grand_total']:,.2f}")

    def test_quotation_has_finalized_status(self, manager_token):
        """Test quotations have is_final field"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        data = response.json()
        finalized = [q for q in data if q.get("is_final")]
        print(f"✓ Found {len(finalized)} finalized quotations out of {len(data)}")
        
        if finalized:
            q = finalized[0]
            assert q["status"] == "sent", "Finalized quotation should have 'sent' status"


class TestAgreements:
    """Agreements endpoint tests"""
    
    def test_get_agreements(self, manager_token):
        """Test manager can view agreements"""
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} agreements")
        
        if data:
            agreement = data[0]
            assert "agreement_number" in agreement
            assert "status" in agreement
            assert agreement["status"] in ["draft", "pending_approval", "approved", "rejected", "sent", "signed"]
            print(f"✓ Agreement {agreement['agreement_number']}: status={agreement['status']}")


class TestManagerApprovals:
    """Manager Approvals endpoint tests"""
    
    def test_get_pending_approvals_as_manager(self, manager_token):
        """Test manager can view pending approvals"""
        response = requests.get(
            f"{BASE_URL}/api/agreements/pending-approval",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Manager can view {len(data)} pending approvals")
        
        if data:
            item = data[0]
            assert "agreement" in item
            assert "quotation" in item
            assert item["agreement"]["status"] == "pending_approval"
            print(f"✓ Pending approval: {item['agreement']['agreement_number']}")

    def test_pending_approvals_denied_for_executive(self, executive_token):
        """Test executive cannot access pending approvals"""
        response = requests.get(
            f"{BASE_URL}/api/agreements/pending-approval",
            headers={"Authorization": f"Bearer {executive_token}"}
        )
        assert response.status_code == 403
        print("✓ Executive correctly denied access to approvals")

    def test_approve_agreement_as_manager(self, manager_token):
        """Test manager can approve agreement"""
        # Get pending approvals
        response = requests.get(
            f"{BASE_URL}/api/agreements/pending-approval",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending approvals to test")
        
        agreement_id = pending[0]["agreement"]["id"]
        agreement_number = pending[0]["agreement"]["agreement_number"]
        
        # Approve the agreement
        response = requests.patch(
            f"{BASE_URL}/api/agreements/{agreement_id}/approve",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        print(f"✓ Agreement {agreement_number} approved by manager")
        
        # Verify status changed to approved
        response = requests.get(
            f"{BASE_URL}/api/agreements",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        agreements = response.json()
        approved = next((a for a in agreements if a["id"] == agreement_id), None)
        assert approved is not None
        assert approved["status"] == "approved"
        print(f"✓ Agreement status verified: {approved['status']}")

    def test_executive_cannot_approve(self, executive_token, manager_token):
        """Test executive cannot approve agreements"""
        # First check if there are pending approvals
        response = requests.get(
            f"{BASE_URL}/api/agreements/pending-approval",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        pending = response.json()
        
        if not pending:
            pytest.skip("No pending approvals to test")
        
        agreement_id = pending[0]["agreement"]["id"]
        
        # Try to approve as executive
        response = requests.patch(
            f"{BASE_URL}/api/agreements/{agreement_id}/approve",
            headers={"Authorization": f"Bearer {executive_token}"}
        )
        assert response.status_code == 403
        print("✓ Executive correctly denied approval permission")


class TestLeads:
    """Leads endpoint tests"""
    
    def test_get_leads(self, manager_token):
        """Test manager can view leads"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} leads")


class TestDashboardStats:
    """Dashboard stats endpoint tests"""
    
    def test_get_dashboard_stats(self, manager_token):
        """Test dashboard stats endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/stats/dashboard",
            headers={"Authorization": f"Bearer {manager_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "active_projects" in data
        print(f"✓ Dashboard stats: {data['total_leads']} leads, {data['active_projects']} projects")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
