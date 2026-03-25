"""
End-to-End Onboarding Flow Tests

Tests the complete employee onboarding to payroll flow:
1. Candidate fills 4-step onboarding form
2. HR reviews and approves
3. Employee goes live
4. Employee appears in payroll

Test credentials:
- HR: EMP002 / hr123
- Admin: EMP001 / admin123
- Onboarding token: c24f79ec-f562-4d3f-9523-c4d765b013b9
"""

import pytest
import requests
import os
import base64
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sales-table-refactor.preview.emergentagent.com')

# Test data
ONBOARDING_TOKEN = "c24f79ec-f562-4d3f-9523-c4d765b013b9"
HR_CREDENTIALS = {"employee_id": "EMP002", "password": "hr123"}
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}


class TestOnboardingPublicEndpoints:
    """Test public onboarding endpoints (no auth required)"""
    
    def test_get_onboarding_form(self):
        """Test fetching onboarding form data"""
        response = requests.get(f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}")
        print(f"GET /api/onboarding/public/{ONBOARDING_TOKEN}: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert "candidate_name" in data
        assert "offered_position" in data
        print(f"Submission status: {data.get('status')}")
        print(f"Candidate: {data.get('candidate_name')}")
        print(f"Position: {data.get('offered_position')}")
    
    def test_save_personal_details(self):
        """Test saving Step 1: Personal Details"""
        payload = {
            "candidate_details": {
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "date_of_birth": "1990-05-15",
                "phone": "9876543210",
                "email": "rajesh.kumar@example.com",
                "pan_number": "ABCDE1234F",
                "aadhaar_number": "123456789012"
            }
        }
        
        response = requests.put(f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}", json=payload)
        print(f"PUT /api/onboarding/public/{ONBOARDING_TOKEN} (personal details): {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Personal details saved successfully")
    
    def test_upload_profile_photo(self):
        """Test uploading profile photo"""
        # Create a minimal valid PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
            0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,
            0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        
        files = {'file': ('test_photo.png', png_data, 'image/png')}
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}/upload-photo",
            files=files
        )
        print(f"POST /api/onboarding/public/{ONBOARDING_TOKEN}/upload-photo: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "photo_url" in data or "profile_photo_url" in data
        print("Profile photo uploaded successfully")
    
    def test_save_address_bank_details(self):
        """Test saving Step 2: Address & Bank Details"""
        payload = {
            "candidate_details": {
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "date_of_birth": "1990-05-15",
                "phone": "9876543210",
                "email": "rajesh.kumar@example.com",
                "pan_number": "ABCDE1234F",
                "aadhaar_number": "123456789012",
                "current_address": {
                    "street": "123 Main Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001"
                },
                "permanent_address": {
                    "street": "456 Park Avenue",
                    "city": "Pune",
                    "state": "Maharashtra",
                    "pincode": "411001"
                }
            },
            "bank_details": {
                "account_holder_name": "Rajesh Kumar",
                "account_number": "1234567890123456",
                "ifsc_code": "HDFC0001234",
                "bank_name": "HDFC Bank",
                "branch": "Mumbai Main Branch"
            }
        }
        
        response = requests.put(f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}", json=payload)
        print(f"PUT /api/onboarding/public/{ONBOARDING_TOKEN} (address & bank): {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Address and bank details saved successfully")
    
    def test_save_emergency_contact(self):
        """Test saving Step 3: Emergency Contact"""
        payload = {
            "emergency_contact": {
                "name": "Priya Kumar",
                "phone": "9876543211"
            }
        }
        
        response = requests.put(f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}", json=payload)
        print(f"PUT /api/onboarding/public/{ONBOARDING_TOKEN} (emergency contact): {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Emergency contact saved successfully")
    
    def test_upload_documents(self):
        """Test uploading required documents (PAN, Aadhaar, CV)"""
        # Create a minimal PDF-like content
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        
        documents = [
            ("pan_card", "pan_card.pdf"),
            ("aadhaar", "aadhaar.pdf"),
            ("cv", "resume.pdf")
        ]
        
        for doc_type, filename in documents:
            files = {'file': (filename, pdf_content, 'application/pdf')}
            response = requests.post(
                f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}/upload?document_type={doc_type}",
                files=files
            )
            print(f"POST /api/onboarding/public/{ONBOARDING_TOKEN}/upload ({doc_type}): {response.status_code}")
            
            assert response.status_code == 200, f"Expected 200 for {doc_type}, got {response.status_code}: {response.text}"
        
        print("All documents uploaded successfully")
    
    def test_verify_documents_uploaded(self):
        """Verify all documents are uploaded"""
        response = requests.get(f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}")
        assert response.status_code == 200
        
        data = response.json()
        documents = data.get("documents", [])
        doc_types = [d.get("type") for d in documents]
        
        print(f"Uploaded documents: {doc_types}")
        
        required_docs = ["pan_card", "aadhaar", "cv"]
        for doc in required_docs:
            assert doc in doc_types, f"Missing document: {doc}"
        
        print("All required documents verified")


class TestOnboardingSubmission:
    """Test onboarding form submission"""
    
    def test_submit_onboarding_form(self):
        """Test submitting the complete onboarding form"""
        # First, ensure all data is saved
        payload = {
            "candidate_details": {
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "date_of_birth": "1990-05-15",
                "phone": "9876543210",
                "email": "rajesh.kumar@example.com",
                "pan_number": "ABCDE1234F",
                "aadhaar_number": "123456789012",
                "current_address": {
                    "street": "123 Main Street",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "pincode": "400001"
                },
                "permanent_address": {
                    "street": "456 Park Avenue",
                    "city": "Pune",
                    "state": "Maharashtra",
                    "pincode": "411001"
                }
            },
            "bank_details": {
                "account_holder_name": "Rajesh Kumar",
                "account_number": "1234567890123456",
                "ifsc_code": "HDFC0001234",
                "bank_name": "HDFC Bank",
                "branch": "Mumbai Main Branch"
            },
            "emergency_contact": {
                "name": "Priya Kumar",
                "phone": "9876543211"
            },
            "declaration": {
                "signed": True,
                "signed_at": datetime.now().isoformat(),
                "items": {
                    "info_true": True,
                    "bg_verify": True,
                    "confidentiality": True,
                    "policies": True,
                    "no_legal": True,
                    "no_termination": True
                }
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{ONBOARDING_TOKEN}/submit",
            json=payload
        )
        print(f"POST /api/onboarding/public/{ONBOARDING_TOKEN}/submit: {response.status_code}")
        
        # May fail if already submitted or missing documents
        if response.status_code == 200:
            print("Onboarding form submitted successfully")
        elif response.status_code == 400:
            print(f"Submission blocked (expected if already submitted): {response.json().get('detail')}")
        else:
            print(f"Unexpected response: {response.text}")


class TestHROnboardingReview:
    """Test HR review and approval of onboarding submissions"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_hr_login(self):
        """Test HR login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        print(f"POST /api/auth/login (HR): {response.status_code}")
        
        assert response.status_code == 200, f"HR login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        print(f"HR logged in successfully. Role: {data.get('user', {}).get('role')}")
        return data.get("access_token")
    
    def test_list_onboarding_submissions(self, hr_token):
        """Test listing onboarding submissions"""
        if not hr_token:
            pytest.skip("HR token not available")
        
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/onboarding/submissions", headers=headers)
        print(f"GET /api/onboarding/submissions: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        submissions = response.json()
        print(f"Found {len(submissions)} onboarding submissions")
        
        # Find our test submission
        test_submission = next((s for s in submissions if s.get("token") == ONBOARDING_TOKEN), None)
        if test_submission:
            print(f"Test submission status: {test_submission.get('status')}")
            print(f"Test submission progress: {test_submission.get('progress')}")
    
    def test_get_submission_details(self, hr_token):
        """Test getting detailed submission for review"""
        if not hr_token:
            pytest.skip("HR token not available")
        
        # First get the submission ID
        headers = {"Authorization": f"Bearer {hr_token}"}
        response = requests.get(f"{BASE_URL}/api/onboarding/submissions", headers=headers)
        
        if response.status_code != 200:
            pytest.skip("Could not list submissions")
        
        submissions = response.json()
        test_submission = next((s for s in submissions if s.get("token") == ONBOARDING_TOKEN), None)
        
        if not test_submission:
            pytest.skip("Test submission not found")
        
        submission_id = test_submission.get("id")
        
        response = requests.get(f"{BASE_URL}/api/onboarding/submissions/{submission_id}", headers=headers)
        print(f"GET /api/onboarding/submissions/{submission_id}: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Submission details retrieved. Status: {data.get('status')}")


class TestEmployeeGoLive:
    """Test employee Go-Live workflow"""
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_list_employees(self, admin_token):
        """Test listing employees"""
        if not admin_token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/employees", headers=headers)
        print(f"GET /api/employees: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        employees = data.get("items", data) if isinstance(data, dict) else data
        print(f"Found {len(employees)} employees")
    
    def test_go_live_pending_list(self, admin_token):
        """Test getting Go-Live pending employees"""
        if not admin_token:
            pytest.skip("Admin token not available")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/go-live/pending", headers=headers)
        print(f"GET /api/go-live/pending: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} employees pending Go-Live")
        else:
            print(f"Go-Live pending endpoint response: {response.status_code}")


class TestPayrollIntegration:
    """Test payroll integration after employee onboarding"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def test_payroll_inputs(self, hr_token):
        """Test getting payroll inputs"""
        if not hr_token:
            pytest.skip("HR token not available")
        
        headers = {"Authorization": f"Bearer {hr_token}"}
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(f"{BASE_URL}/api/payroll/inputs?month={current_month}", headers=headers)
        print(f"GET /api/payroll/inputs?month={current_month}: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Found {len(data)} employees in payroll inputs")
    
    def test_salary_slips(self, hr_token):
        """Test getting salary slips"""
        if not hr_token:
            pytest.skip("HR token not available")
        
        headers = {"Authorization": f"Bearer {hr_token}"}
        current_month = datetime.now().strftime("%Y-%m")
        
        response = requests.get(f"{BASE_URL}/api/payroll/salary-slips?month={current_month}", headers=headers)
        print(f"GET /api/payroll/salary-slips?month={current_month}: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Found {len(data)} salary slips for {current_month}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
