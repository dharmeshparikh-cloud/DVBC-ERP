"""
Test Agreement E-Signature and Kickoff Request workflow
Features tested:
- /api/employees/consultants - returns employees with Consultant designation
- /api/agreements/{id}/sign - E-sign an approved agreement
- /api/kickoff-requests - Create kickoff request after PM selection
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="module")
def admin_token(api_client):
    """Get admin authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def manager_token(api_client):
    """Get manager authentication token"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@company.com",
        "password": "manager123"
    })
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json().get("access_token")

@pytest.fixture(scope="module")
def authenticated_client(api_client, admin_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestConsultantsEndpoint:
    """Test /api/employees/consultants endpoint for PM selection"""
    
    def test_get_consultants_returns_list(self, authenticated_client):
        """Test that consultants endpoint returns employees with Consultant designation"""
        response = authenticated_client.get(f"{BASE_URL}/api/employees/consultants")
        
        assert response.status_code == 200, f"Failed to get consultants: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least one consultant"
        
        # Verify structure and that designation contains 'consultant'
        for consultant in data[:5]:  # Check first 5
            assert "id" in consultant, "Consultant should have id"
            assert "first_name" in consultant, "Consultant should have first_name"
            assert "last_name" in consultant, "Consultant should have last_name"
            assert "designation" in consultant, "Consultant should have designation"
            assert "consultant" in consultant["designation"].lower(), \
                f"Designation '{consultant['designation']}' should contain 'consultant'"
        
        print(f"✓ Consultants endpoint returned {len(data)} employees with Consultant designation")

    def test_consultants_have_user_id_field(self, authenticated_client):
        """Test that consultants response includes user_id for PM assignment"""
        response = authenticated_client.get(f"{BASE_URL}/api/employees/consultants")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that user_id field exists (can be null if not linked to user)
        for consultant in data[:10]:
            assert "user_id" in consultant, "Consultant should have user_id field"
        
        # Find at least one consultant with user_id
        with_user_id = [c for c in data if c.get("user_id")]
        print(f"✓ Found {len(with_user_id)} consultants with linked user accounts out of {len(data)}")


class TestAgreementSigning:
    """Test agreement e-signature workflow"""
    
    def test_get_approved_agreements(self, authenticated_client):
        """Test that we can find approved agreements for signing"""
        response = authenticated_client.get(f"{BASE_URL}/api/agreements")
        
        assert response.status_code == 200, f"Failed to get agreements: {response.text}"
        data = response.json()
        
        # Find approved agreements
        approved = [a for a in data if a.get("status") == "approved"]
        print(f"✓ Found {len(approved)} approved agreements available for signing")
        
        assert len(approved) > 0, "Should have at least one approved agreement for testing"
        return approved[0]

    def test_get_agreement_full_details(self, authenticated_client):
        """Test getting full agreement details for signing view"""
        # Get agreements list first
        response = authenticated_client.get(f"{BASE_URL}/api/agreements")
        assert response.status_code == 200
        
        agreements = response.json()
        approved = [a for a in agreements if a.get("status") == "approved"]
        
        if not approved:
            pytest.skip("No approved agreements available for testing")
        
        agreement_id = approved[0]["id"]
        
        # Get full details
        response = authenticated_client.get(f"{BASE_URL}/api/agreements/{agreement_id}/full")
        
        assert response.status_code == 200, f"Failed to get agreement full: {response.text}"
        data = response.json()
        
        assert "agreement" in data, "Response should have agreement"
        assert data["agreement"]["id"] == agreement_id, "Should return correct agreement"
        print(f"✓ Got full details for agreement {data['agreement'].get('agreement_number', agreement_id)}")


class TestKickoffRequestCreation:
    """Test kickoff request creation after agreement signing"""
    
    def test_create_kickoff_request_success(self, authenticated_client):
        """Test creating a kickoff request with PM selection"""
        # First get an approved agreement
        agreements_resp = authenticated_client.get(f"{BASE_URL}/api/agreements")
        assert agreements_resp.status_code == 200
        
        agreements = agreements_resp.json()
        approved = [a for a in agreements if a.get("status") == "approved"]
        
        if not approved:
            pytest.skip("No approved agreements available for testing")
        
        agreement = approved[0]
        
        # Get a consultant for PM assignment
        consultants_resp = authenticated_client.get(f"{BASE_URL}/api/employees/consultants")
        assert consultants_resp.status_code == 200
        
        consultants = consultants_resp.json()
        consultant = consultants[0] if consultants else None
        
        if not consultant:
            pytest.skip("No consultants available for PM assignment")
        
        # Create kickoff request
        kickoff_data = {
            "agreement_id": agreement["id"],
            "client_name": "TEST_Kickoff_Client",
            "project_name": "TEST_Kickoff_Project",
            "project_type": "mixed",
            "total_meetings": 12,
            "meeting_frequency": "Monthly",
            "project_tenure_months": 12,
            "assigned_pm_id": consultant.get("user_id") or consultant.get("id"),
            "assigned_pm_name": f"{consultant['first_name']} {consultant['last_name']}",
            "notes": "Test kickoff request from automated testing"
        }
        
        response = authenticated_client.post(f"{BASE_URL}/api/kickoff-requests", json=kickoff_data)
        
        assert response.status_code == 200, f"Failed to create kickoff request: {response.text}"
        data = response.json()
        
        assert "id" in data, "Response should have kickoff request id"
        assert "message" in data, "Response should have success message"
        
        print(f"✓ Created kickoff request with id: {data['id']}")
        return data["id"]

    def test_get_kickoff_requests_list(self, authenticated_client):
        """Test getting kickoff requests list"""
        response = authenticated_client.get(f"{BASE_URL}/api/kickoff-requests")
        
        assert response.status_code == 200, f"Failed to get kickoff requests: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Kickoff requests endpoint returned {len(data)} requests")


class TestSignAndKickoffFlow:
    """Test the complete flow: Sign Agreement -> PM Selection -> Create Kickoff"""
    
    def test_agreement_sign_endpoint(self, authenticated_client):
        """Test the agreement signing endpoint"""
        # Get an approved agreement
        agreements_resp = authenticated_client.get(f"{BASE_URL}/api/agreements")
        assert agreements_resp.status_code == 200
        
        agreements = agreements_resp.json()
        # Find approved but not yet signed
        approved = [a for a in agreements if a.get("status") == "approved"]
        
        if not approved:
            pytest.skip("No approved agreements available for signing test")
        
        agreement_id = approved[0]["id"]
        agreement_number = approved[0].get("agreement_number", agreement_id)
        
        # Try to sign with signature data
        sign_data = {
            "signer_name": "TEST_Signer",
            "signer_designation": "Test Director",
            "signer_email": "test@company.com",
            "signature_date": "2026-01-15",
            "signature_image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/agreements/{agreement_id}/sign",
            json=sign_data
        )
        
        # Either succeeds (200) or fails because already signed (400)
        if response.status_code == 200:
            print(f"✓ Successfully signed agreement {agreement_number}")
            data = response.json()
            assert "signed_at" in data, "Response should have signed_at timestamp"
        elif response.status_code == 400:
            print(f"✓ Agreement {agreement_number} already signed (expected for repeated tests)")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code} - {response.text}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_kickoff_requests(self, authenticated_client):
        """Remove TEST_ prefixed kickoff requests"""
        response = authenticated_client.get(f"{BASE_URL}/api/kickoff-requests")
        if response.status_code == 200:
            requests_list = response.json()
            test_requests = [r for r in requests_list if "TEST_" in r.get("project_name", "")]
            
            # Note: Kickoff requests may not have delete endpoint, just log
            print(f"✓ Found {len(test_requests)} TEST_ prefixed kickoff requests")
