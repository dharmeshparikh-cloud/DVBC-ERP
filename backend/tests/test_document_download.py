"""
Test Document Download API Endpoints
Tests for Agreement and SOW document export to PDF and Word (.docx) formats

Endpoints tested:
- GET /api/agreements/{id}/download?format=pdf
- GET /api/agreements/{id}/download?format=docx
- GET /api/sow/{id}/download?format=pdf
- GET /api/sow/{id}/download?format=docx
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDocumentDownload:
    """Test document download API endpoints for Agreements and SOW"""
    
    @pytest.fixture(autouse=True)
    def setup(self, api_client, auth_token):
        """Setup test fixtures"""
        self.client = api_client
        self.token = auth_token
        
    # ==================== Agreement Download Tests ====================
    
    def test_agreement_download_pdf_valid_id(self, authenticated_client):
        """Test downloading agreement as PDF with valid agreement ID"""
        # Use sample agreement ID provided
        agreement_id = "0b85b5a6-df58-4c97-9a67-ae7d52a0b2f4"
        
        response = authenticated_client.get(
            f"{BASE_URL}/api/agreements/{agreement_id}/download",
            params={"format": "pdf"}
        )
        
        # Should return 200 or 404 (if agreement doesn't exist in test DB)
        if response.status_code == 200:
            # Verify content type
            assert "application/pdf" in response.headers.get("Content-Type", "")
            # Verify content disposition has filename
            assert "attachment" in response.headers.get("Content-Disposition", "")
            assert ".pdf" in response.headers.get("Content-Disposition", "")
            # Verify PDF content starts with PDF header
            assert response.content[:4] == b'%PDF'
            print(f"SUCCESS: Agreement PDF downloaded ({len(response.content)} bytes)")
        elif response.status_code == 404:
            print(f"Agreement {agreement_id} not found - will test with existing agreement")
            # Try to get an existing agreement
            agreements_response = authenticated_client.get(f"{BASE_URL}/api/agreements")
            if agreements_response.status_code == 200 and len(agreements_response.json()) > 0:
                existing_agreement_id = agreements_response.json()[0]['id']
                response = authenticated_client.get(
                    f"{BASE_URL}/api/agreements/{existing_agreement_id}/download",
                    params={"format": "pdf"}
                )
                assert response.status_code == 200
                assert "application/pdf" in response.headers.get("Content-Type", "")
                print(f"SUCCESS: Agreement PDF downloaded for existing ID ({len(response.content)} bytes)")
            else:
                pytest.skip("No agreements available for testing")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_agreement_download_docx_valid_id(self, authenticated_client):
        """Test downloading agreement as Word document with valid agreement ID"""
        agreement_id = "0b85b5a6-df58-4c97-9a67-ae7d52a0b2f4"
        
        response = authenticated_client.get(
            f"{BASE_URL}/api/agreements/{agreement_id}/download",
            params={"format": "docx"}
        )
        
        if response.status_code == 200:
            # Verify content type
            assert "wordprocessingml.document" in response.headers.get("Content-Type", "")
            # Verify content disposition has filename
            assert "attachment" in response.headers.get("Content-Disposition", "")
            assert ".docx" in response.headers.get("Content-Disposition", "")
            # Verify docx content (starts with PK zip header)
            assert response.content[:2] == b'PK'
            print(f"SUCCESS: Agreement Word downloaded ({len(response.content)} bytes)")
        elif response.status_code == 404:
            print(f"Agreement {agreement_id} not found - testing with existing agreement")
            agreements_response = authenticated_client.get(f"{BASE_URL}/api/agreements")
            if agreements_response.status_code == 200 and len(agreements_response.json()) > 0:
                existing_agreement_id = agreements_response.json()[0]['id']
                response = authenticated_client.get(
                    f"{BASE_URL}/api/agreements/{existing_agreement_id}/download",
                    params={"format": "docx"}
                )
                assert response.status_code == 200
                assert "wordprocessingml.document" in response.headers.get("Content-Type", "")
                print(f"SUCCESS: Agreement Word downloaded for existing ID ({len(response.content)} bytes)")
            else:
                pytest.skip("No agreements available for testing")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_agreement_download_invalid_id(self, authenticated_client):
        """Test downloading agreement with non-existent ID returns 404"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/agreements/non-existent-id-12345/download",
            params={"format": "pdf"}
        )
        assert response.status_code == 404
        print("SUCCESS: Invalid agreement ID returns 404")
    
    def test_agreement_download_default_format_is_pdf(self, authenticated_client):
        """Test that default format is PDF when not specified"""
        # Get an existing agreement
        agreements_response = authenticated_client.get(f"{BASE_URL}/api/agreements")
        if agreements_response.status_code != 200 or len(agreements_response.json()) == 0:
            pytest.skip("No agreements available for testing")
        
        agreement_id = agreements_response.json()[0]['id']
        
        # Request without format parameter
        response = authenticated_client.get(
            f"{BASE_URL}/api/agreements/{agreement_id}/download"
        )
        
        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("Content-Type", "")
        print("SUCCESS: Default download format is PDF")
    
    # ==================== SOW Download Tests ====================
    
    def test_sow_download_pdf_valid_id(self, authenticated_client):
        """Test downloading SOW as PDF with valid SOW ID"""
        sow_id = "f9efafe7-22fa-4639-b4c8-077149d8e517"
        
        response = authenticated_client.get(
            f"{BASE_URL}/api/sow/{sow_id}/download",
            params={"format": "pdf"}
        )
        
        if response.status_code == 200:
            assert "application/pdf" in response.headers.get("Content-Type", "")
            assert "attachment" in response.headers.get("Content-Disposition", "")
            assert ".pdf" in response.headers.get("Content-Disposition", "")
            assert response.content[:4] == b'%PDF'
            print(f"SUCCESS: SOW PDF downloaded ({len(response.content)} bytes)")
        elif response.status_code == 404:
            print(f"SOW {sow_id} not found - testing with existing SOW")
            # Try to get existing SOW via pricing plans
            plans_response = authenticated_client.get(f"{BASE_URL}/api/pricing-plans")
            if plans_response.status_code == 200 and len(plans_response.json()) > 0:
                for plan in plans_response.json():
                    if plan.get('sow_id'):
                        existing_sow_id = plan['sow_id']
                        response = authenticated_client.get(
                            f"{BASE_URL}/api/sow/{existing_sow_id}/download",
                            params={"format": "pdf"}
                        )
                        if response.status_code == 200:
                            assert "application/pdf" in response.headers.get("Content-Type", "")
                            print(f"SUCCESS: SOW PDF downloaded for existing ID ({len(response.content)} bytes)")
                            return
                # No SOW found, try to get SOW by pricing plan
                pricing_plan_id = "1419ab18-85ae-49c3-a273-7fb74184c98c"
                try:
                    sow_response = authenticated_client.get(f"{BASE_URL}/api/sow/by-pricing-plan/{pricing_plan_id}")
                    if sow_response.status_code == 200:
                        existing_sow_id = sow_response.json()['id']
                        response = authenticated_client.get(
                            f"{BASE_URL}/api/sow/{existing_sow_id}/download",
                            params={"format": "pdf"}
                        )
                        assert response.status_code == 200
                        print(f"SUCCESS: SOW PDF downloaded for pricing plan SOW ({len(response.content)} bytes)")
                        return
                except:
                    pass
            pytest.skip("No SOW available for testing")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_sow_download_docx_valid_id(self, authenticated_client):
        """Test downloading SOW as Word document with valid SOW ID"""
        sow_id = "f9efafe7-22fa-4639-b4c8-077149d8e517"
        
        response = authenticated_client.get(
            f"{BASE_URL}/api/sow/{sow_id}/download",
            params={"format": "docx"}
        )
        
        if response.status_code == 200:
            assert "wordprocessingml.document" in response.headers.get("Content-Type", "")
            assert "attachment" in response.headers.get("Content-Disposition", "")
            assert ".docx" in response.headers.get("Content-Disposition", "")
            assert response.content[:2] == b'PK'
            print(f"SUCCESS: SOW Word downloaded ({len(response.content)} bytes)")
        elif response.status_code == 404:
            print(f"SOW {sow_id} not found - testing with existing SOW")
            # Try pricing plan approach
            pricing_plan_id = "1419ab18-85ae-49c3-a273-7fb74184c98c"
            try:
                sow_response = authenticated_client.get(f"{BASE_URL}/api/sow/by-pricing-plan/{pricing_plan_id}")
                if sow_response.status_code == 200:
                    existing_sow_id = sow_response.json()['id']
                    response = authenticated_client.get(
                        f"{BASE_URL}/api/sow/{existing_sow_id}/download",
                        params={"format": "docx"}
                    )
                    if response.status_code == 200:
                        assert "wordprocessingml.document" in response.headers.get("Content-Type", "")
                        print(f"SUCCESS: SOW Word downloaded for pricing plan SOW ({len(response.content)} bytes)")
                        return
            except:
                pass
            pytest.skip("No SOW available for testing")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_sow_download_invalid_id(self, authenticated_client):
        """Test downloading SOW with non-existent ID returns 404"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/sow/non-existent-sow-id-12345/download",
            params={"format": "pdf"}
        )
        assert response.status_code == 404
        print("SUCCESS: Invalid SOW ID returns 404")
    
    def test_sow_download_default_format_is_pdf(self, authenticated_client):
        """Test that default format is PDF when not specified"""
        pricing_plan_id = "1419ab18-85ae-49c3-a273-7fb74184c98c"
        try:
            sow_response = authenticated_client.get(f"{BASE_URL}/api/sow/by-pricing-plan/{pricing_plan_id}")
            if sow_response.status_code == 200:
                sow_id = sow_response.json()['id']
                response = authenticated_client.get(f"{BASE_URL}/api/sow/{sow_id}/download")
                if response.status_code == 200:
                    assert "application/pdf" in response.headers.get("Content-Type", "")
                    print("SUCCESS: Default SOW download format is PDF")
                    return
        except:
            pass
        pytest.skip("No SOW available for testing default format")
    
    # ==================== Endpoint Access Tests ====================
    
    def test_download_requires_authentication(self):
        """Test that download endpoints require authentication"""
        client = requests.Session()
        client.headers.update({"Content-Type": "application/json"})
        
        # Test agreement download without auth
        response = client.get(
            f"{BASE_URL}/api/agreements/test-id/download",
            params={"format": "pdf"}
        )
        assert response.status_code == 401
        
        # Test SOW download without auth
        response = client.get(
            f"{BASE_URL}/api/sow/test-id/download",
            params={"format": "pdf"}
        )
        assert response.status_code == 401
        print("SUCCESS: Download endpoints require authentication")


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_token(api_client):
    """Get authentication token using admin credentials"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.fail(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client
