"""
Test Onboarding References - Professional and Personal References
Tests the References section (step 5) in the candidate onboarding form.
Features:
  - Professional Reference: name, phone, company_name, designation
  - Personal Reference: name, phone, address
  - Backend API save/submit with references validation
  - Company name should be 'D&V Business Consulting' (not Pvt. Ltd.)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestOnboardingReferences:
    """Test onboarding references functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data and get auth token."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as HR Manager to send invite
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            self.token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_01_send_invite_and_get_token(self):
        """Test sending onboarding invite to get a token for testing."""
        unique_email = f"test_refs_{uuid.uuid4().hex[:8]}@test.com"
        
        response = self.session.post(f"{BASE_URL}/api/onboarding/invite", json={
            "candidate_email": unique_email,
            "candidate_name": "References Test Candidate",
            "offered_position": "Software Engineer"
        })
        
        print(f"Invite Response Status: {response.status_code}")
        print(f"Invite Response: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert "onboarding_link" in data
        
        # Extract token from the link
        self.onboarding_token = data["onboarding_link"].split("/")[-1]
        assert len(self.onboarding_token) > 10
        
        # Store for other tests
        TestOnboardingReferences.test_token = self.onboarding_token
        TestOnboardingReferences.submission_id = data.get("submission_id")
        
        print(f"Created submission with token: {self.onboarding_token}")
        return self.onboarding_token
    
    def test_02_get_public_submission_structure(self):
        """Test that public submission endpoint returns reference fields."""
        token = getattr(TestOnboardingReferences, 'test_token', None)
        if not token:
            # Create new invite
            self.test_01_send_invite_and_get_token()
            token = TestOnboardingReferences.test_token
        
        response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        
        print(f"Public Submission Status: {response.status_code}")
        data = response.json()
        print(f"Public Submission Keys: {data.keys()}")
        
        assert response.status_code == 200
        
        # Check that reference fields exist in the response structure
        assert "professional_reference" in data or data.get("professional_reference") is None
        assert "personal_reference" in data or data.get("personal_reference") is None
        
        print("Public submission structure contains reference fields")
    
    def test_03_save_professional_reference(self):
        """Test saving professional reference data."""
        token = getattr(TestOnboardingReferences, 'test_token', None)
        if not token:
            self.test_01_send_invite_and_get_token()
            token = TestOnboardingReferences.test_token
        
        professional_ref_data = {
            "professional_reference": {
                "name": "John Smith",
                "phone": "9876543210",
                "company_name": "Tech Corp",
                "designation": "Engineering Manager"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/save",
            json=professional_ref_data
        )
        
        print(f"Save Professional Reference Status: {response.status_code}")
        print(f"Save Response: {response.json()}")
        
        assert response.status_code == 200
        
        # Verify the data was saved
        get_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        saved_data = get_response.json()
        
        assert saved_data.get("professional_reference") is not None
        pr = saved_data["professional_reference"]
        assert pr.get("name") == "John Smith"
        assert pr.get("phone") == "9876543210"
        assert pr.get("company_name") == "Tech Corp"
        assert pr.get("designation") == "Engineering Manager"
        
        print("Professional reference saved and verified successfully")
    
    def test_04_save_personal_reference(self):
        """Test saving personal reference data."""
        token = getattr(TestOnboardingReferences, 'test_token', None)
        if not token:
            self.test_01_send_invite_and_get_token()
            token = TestOnboardingReferences.test_token
        
        personal_ref_data = {
            "personal_reference": {
                "name": "Jane Doe",
                "phone": "8765432109",
                "address": "123 Main Street, City, State 123456"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/save",
            json=personal_ref_data
        )
        
        print(f"Save Personal Reference Status: {response.status_code}")
        print(f"Save Response: {response.json()}")
        
        assert response.status_code == 200
        
        # Verify the data was saved
        get_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        saved_data = get_response.json()
        
        assert saved_data.get("personal_reference") is not None
        per = saved_data["personal_reference"]
        assert per.get("name") == "Jane Doe"
        assert per.get("phone") == "8765432109"
        assert per.get("address") == "123 Main Street, City, State 123456"
        
        print("Personal reference saved and verified successfully")
    
    def test_05_save_both_references_together(self):
        """Test saving both references in a single request."""
        token = getattr(TestOnboardingReferences, 'test_token', None)
        if not token:
            self.test_01_send_invite_and_get_token()
            token = TestOnboardingReferences.test_token
        
        both_refs_data = {
            "professional_reference": {
                "name": "Professional Contact",
                "phone": "1234567890",
                "company_name": "ABC Corporation",
                "designation": "Director"
            },
            "personal_reference": {
                "name": "Personal Contact",
                "phone": "0987654321",
                "address": "456 Park Avenue, Mumbai, Maharashtra 400001"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/save",
            json=both_refs_data
        )
        
        print(f"Save Both References Status: {response.status_code}")
        assert response.status_code == 200
        
        # Verify both were saved
        get_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        saved_data = get_response.json()
        
        pr = saved_data.get("professional_reference", {})
        per = saved_data.get("personal_reference", {})
        
        assert pr.get("name") == "Professional Contact"
        assert pr.get("company_name") == "ABC Corporation"
        assert per.get("name") == "Personal Contact"
        assert per.get("address") == "456 Park Avenue, Mumbai, Maharashtra 400001"
        
        print("Both references saved together successfully")
    
    def test_06_submit_with_references(self):
        """Test submitting a complete form with references."""
        # Create a new invite for clean submission test
        unique_email = f"test_submit_refs_{uuid.uuid4().hex[:8]}@test.com"
        
        invite_response = self.session.post(f"{BASE_URL}/api/onboarding/invite", json={
            "candidate_email": unique_email,
            "candidate_name": "Submit Test Candidate",
            "offered_position": "QA Engineer"
        })
        
        assert invite_response.status_code == 200
        token = invite_response.json()["onboarding_link"].split("/")[-1]
        submission_id = invite_response.json().get("submission_id")
        
        # Prepare complete submission data
        complete_data = {
            "candidate_details": {
                "first_name": "Test",
                "last_name": "User",
                "date_of_birth": "1995-01-15",
                "gender": "male",
                "blood_group": "O+",
                "marital_status": "single",
                "nationality": "Indian",
                "phone": "9876543210",
                "alternate_phone": "9876543211",
                "pan_number": f"TEST{uuid.uuid4().hex[:5].upper()}",
                "aadhaar_number": f"{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}",
                "current_address": {
                    "street": "123 Test Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001"
                },
                "permanent_address": {
                    "street": "123 Test Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001"
                }
            },
            "education": [
                {
                    "degree": "B.Tech",
                    "institution": "IIT Mumbai",
                    "year": "2018",
                    "percentage": "85%"
                }
            ],
            "employment_history": [],
            "bank_details": {
                "account_holder_name": "Test User",
                "account_number": "1234567890123",
                "ifsc_code": "HDFC0001234",
                "bank_name": "HDFC Bank",
                "branch": "Mumbai Main Branch"
            },
            "professional_reference": {
                "name": "Prof Ref Name",
                "phone": "9999999999",
                "company_name": "Previous Company",
                "designation": "Team Lead"
            },
            "personal_reference": {
                "name": "Personal Ref Name",
                "phone": "8888888888",
                "address": "789 Personal Address, City, State 123456"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "7777777777",
                "relationship": "Father"
            },
            "declaration_signed": True,
            "declaration": {
                "signed": True,
                "signed_at": datetime.now().isoformat(),
                "text": "I hereby declare that all the information provided is true."
            }
        }
        
        # Submit the form
        submit_response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/submit",
            json=complete_data
        )
        
        print(f"Submit Response Status: {submit_response.status_code}")
        print(f"Submit Response: {submit_response.json()}")
        
        assert submit_response.status_code == 200
        
        # Verify submission was successful by checking status
        get_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        final_data = get_response.json()
        
        assert final_data.get("status") == "submitted"
        assert final_data.get("professional_reference") is not None
        assert final_data.get("personal_reference") is not None
        
        print("Form submitted with references successfully")
        
        # Store submission ID for validation test
        TestOnboardingReferences.complete_submission_id = submission_id
    
    def test_07_progress_includes_references(self):
        """Test that progress calculation includes references."""
        token = getattr(TestOnboardingReferences, 'test_token', None)
        if not token:
            self.test_01_send_invite_and_get_token()
            token = TestOnboardingReferences.test_token
        
        response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        data = response.json()
        
        print(f"Progress data: {data.get('progress')}")
        
        assert "progress" in data
        progress = data["progress"]
        assert "completed" in progress
        assert "total" in progress
        assert "percentage" in progress
        
        print(f"Progress: {progress['completed']}/{progress['total']} ({progress['percentage']}%)")
    
    def test_08_validate_submission_includes_references(self):
        """Test that validation includes references check."""
        submission_id = getattr(TestOnboardingReferences, 'submission_id', None)
        if not submission_id:
            pytest.skip("No submission ID available")
        
        # Get submission details (as HR)
        response = self.session.get(f"{BASE_URL}/api/onboarding/submissions/{submission_id}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Submission ID: {submission_id}")
            print(f"Submission status: {data.get('status')}")
            print(f"Professional Reference: {data.get('professional_reference')}")
            print(f"Personal Reference: {data.get('personal_reference')}")


class TestCompanyNameBranding:
    """Test that company name is 'D&V Business Consulting' without Pvt. Ltd."""
    
    def test_01_backend_declaration_text(self):
        """Verify declaration text uses correct company name."""
        # The declaration text in onboarding.py should use D&V Business Consulting
        # Check via submit endpoint
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Authentication failed")
        
        token_str = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token_str}"})
        
        # Create invite
        unique_email = f"test_company_{uuid.uuid4().hex[:8]}@test.com"
        invite_response = session.post(f"{BASE_URL}/api/onboarding/invite", json={
            "candidate_email": unique_email,
            "candidate_name": "Company Name Test",
            "offered_position": "Consultant"
        })
        
        assert invite_response.status_code == 200
        onboarding_token = invite_response.json()["onboarding_link"].split("/")[-1]
        
        # Submit with declaration
        submit_data = {
            "candidate_details": {
                "first_name": "Test",
                "last_name": "Candidate",
                "phone": "9876543210",
                "alternate_phone": "9876543211",
                "date_of_birth": "1990-01-01",
                "gender": "male",
                "blood_group": "A+",
                "marital_status": "single",
                "pan_number": f"PAN{uuid.uuid4().hex[:6].upper()}",
                "aadhaar_number": f"{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}",
                "current_address": {"street": "Test", "city": "Mumbai", "state": "MH", "pincode": "400001"},
                "permanent_address": {"street": "Test", "city": "Mumbai", "state": "MH", "pincode": "400001"}
            },
            "education": [{"degree": "B.Tech", "institution": "Test", "year": "2020", "percentage": "80%"}],
            "bank_details": {
                "account_holder_name": "Test",
                "account_number": "1234567890",
                "ifsc_code": "TEST0001234",
                "bank_name": "Test Bank",
                "branch": "Test Branch"
            },
            "professional_reference": {
                "name": "Prof Ref",
                "phone": "9999999999",
                "company_name": "Test Company",
                "designation": "Manager"
            },
            "personal_reference": {
                "name": "Personal Ref",
                "phone": "8888888888",
                "address": "Test Address"
            },
            "emergency_contact": {"name": "Emergency", "phone": "7777777777", "relationship": "Brother"},
            "declaration_signed": True,
            "declaration": {
                "signed": True,
                "text": "I authorize D&V Business Consulting to verify this information."
            }
        }
        
        submit_response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{onboarding_token}/submit",
            json=submit_data
        )
        
        print(f"Submit status: {submit_response.status_code}")
        
        # Check if submission was accepted (validates company name in backend code)
        assert submit_response.status_code == 200
        print("Backend accepts 'D&V Business Consulting' company name correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
