"""
Self-Service Candidate Onboarding Module Tests
==============================================
Tests for the complete onboarding workflow:
1. HR sends invite to candidate
2. Candidate fills form via public link (no login)
3. HR reviews, assigns dept/manager, verifies
4. On completion: Employee ID generated, record created

Endpoints tested:
- POST /api/onboarding/invite - HR sends invite
- GET /api/onboarding/submissions - HR lists submissions
- GET /api/onboarding/submissions/{id} - HR views submission details
- GET /api/onboarding/public/{token} - Candidate views form (no auth)
- POST /api/onboarding/public/{token}/save - Candidate saves progress
- POST /api/onboarding/public/{token}/submit - Candidate submits form
- POST /api/onboarding/public/{token}/upload - Candidate uploads documents
- PATCH /api/onboarding/submissions/{id}/hr-assign - HR assigns dept/manager
- POST /api/onboarding/submissions/{id}/verify-documents - HR verifies docs
- POST /api/onboarding/submissions/{id}/verify-bank - HR verifies bank
- POST /api/onboarding/submissions/{id}/complete - Generate Employee ID
- POST /api/onboarding/submissions/{id}/request-revision - HR requests revision
- POST /api/onboarding/submissions/{id}/reject - HR rejects submission
- GET /api/onboarding/legacy - List legacy records
"""

import pytest
import requests
import os
import uuid
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL env var must be set"


class TestOnboardingAuth:
    """Test authentication and authorization for onboarding endpoints"""

    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200, f"HR login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture
    def admin_token(self):
        """Get Admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "ADMIN001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]

    def test_hr_manager_login(self, hr_token):
        """Verify HR Manager can login and has correct role"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert user["role"] == "hr_manager"
        print(f"PASSED: HR Manager login - {user['full_name']} ({user['role']})")
    
    def test_admin_login(self, admin_token):
        """Verify Admin can login and has correct role"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        user = response.json()
        assert user["role"] == "admin"
        print(f"PASSED: Admin login - {user['full_name']} ({user['role']})")


class TestOnboardingInvite:
    """Test POST /api/onboarding/invite - HR sends invite to candidate"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]

    def test_send_invite_success(self, hr_token):
        """HR can send onboarding invite with all required fields"""
        candidate_email = f"test.candidate.{uuid.uuid4().hex[:6]}@example.com"
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": candidate_email,
                "candidate_name": "Test Candidate",
                "offered_position": "Software Engineer"
            }
        )
        
        assert response.status_code == 200, f"Invite failed: {response.text}"
        data = response.json()
        
        assert "submission_id" in data
        assert "onboarding_link" in data
        assert "expires_at" in data
        assert data["message"] == "Onboarding invite sent successfully"
        
        print(f"PASSED: Invite sent - submission_id: {data['submission_id']}")
        return data

    def test_send_invite_missing_email(self, hr_token):
        """Invite fails when email is missing"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_name": "Test Candidate",
                "offered_position": "Software Engineer"
            }
        )
        
        assert response.status_code == 400
        assert "required" in response.json().get("detail", "").lower()
        print("PASSED: Missing email returns 400")

    def test_send_invite_missing_name(self, hr_token):
        """Invite fails when name is missing"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": "test@example.com",
                "offered_position": "Software Engineer"
            }
        )
        
        assert response.status_code == 400
        assert "required" in response.json().get("detail", "").lower()
        print("PASSED: Missing name returns 400")

    def test_send_invite_missing_position(self, hr_token):
        """Invite fails when position is missing"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": "test@example.com",
                "candidate_name": "Test Candidate"
            }
        )
        
        assert response.status_code == 400
        assert "required" in response.json().get("detail", "").lower()
        print("PASSED: Missing position returns 400")

    def test_send_invite_without_auth(self):
        """Invite fails without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            json={
                "candidate_email": "test@example.com",
                "candidate_name": "Test Candidate",
                "offered_position": "Software Engineer"
            }
        )
        
        assert response.status_code == 401 or response.status_code == 403
        print("PASSED: Unauthenticated request rejected")


class TestOnboardingSubmissions:
    """Test GET /api/onboarding/submissions - HR lists all submissions"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_list_submissions_success(self, hr_token):
        """HR can list all onboarding submissions"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASSED: List submissions - found {len(data)} submissions")
        
        if len(data) > 0:
            submission = data[0]
            # Verify submission structure
            assert "id" in submission
            assert "status" in submission
            assert "candidate_email" in submission
            assert "candidate_name" in submission
            print(f"  Sample submission: {submission['candidate_name']} - {submission['status']}")

    def test_list_submissions_filter_by_status(self, hr_token):
        """HR can filter submissions by status"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions?status=invited",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned items should have invited status
        for submission in data:
            assert submission["status"] == "invited"
        
        print(f"PASSED: Filter by status - found {len(data)} invited submissions")

    def test_list_submissions_without_auth(self):
        """Listing submissions fails without auth"""
        response = requests.get(f"{BASE_URL}/api/onboarding/submissions")
        assert response.status_code == 401 or response.status_code == 403
        print("PASSED: Unauthenticated request rejected")


class TestOnboardingSubmissionDetails:
    """Test GET /api/onboarding/submissions/{id} - HR views submission details"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def submission_id(self, hr_token):
        """Create a submission and return its ID"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": f"detail.test.{uuid.uuid4().hex[:6]}@example.com",
                "candidate_name": "Detail Test Candidate",
                "offered_position": "QA Engineer"
            }
        )
        assert response.status_code == 200
        return response.json()["submission_id"]
    
    def test_get_submission_details(self, hr_token, submission_id):
        """HR can view detailed submission info"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == submission_id
        assert "candidate_details" in data
        assert "education" in data
        assert "employment_history" in data
        assert "bank_details" in data
        assert "emergency_contact" in data
        assert "documents" in data
        assert "hr_assigned" in data
        assert "hr_verification" in data
        assert "progress" in data
        
        print(f"PASSED: Get submission details - ID: {submission_id}")

    def test_get_nonexistent_submission(self, hr_token):
        """404 for non-existent submission"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/nonexistent-id-12345",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 404
        print("PASSED: Non-existent submission returns 404")


class TestOnboardingPublicEndpoints:
    """Test public candidate-facing endpoints (no auth required)"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def submission_data(self, hr_token):
        """Create a submission and return its data including token"""
        email = f"public.test.{uuid.uuid4().hex[:6]}@example.com"
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": email,
                "candidate_name": "Public Test Candidate",
                "offered_position": "DevOps Engineer"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Extract token from the onboarding link
        link = data["onboarding_link"]
        token = link.split("/")[-1]
        
        return {
            "submission_id": data["submission_id"],
            "token": token,
            "email": email
        }
    
    def test_get_public_submission(self, submission_data):
        """Candidate can access form via public token (no auth)"""
        token = submission_data["token"]
        
        response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["candidate_name"] == "Public Test Candidate"
        assert data["offered_position"] == "DevOps Engineer"
        assert data["status"] == "invited"
        assert "progress" in data
        
        print(f"PASSED: Public form access - candidate: {data['candidate_name']}")

    def test_save_public_submission(self, submission_data):
        """Candidate can save progress (auto-save)"""
        token = submission_data["token"]
        
        candidate_details = {
            "first_name": "Public",
            "last_name": "Test",
            "phone": "9876543210",
            "date_of_birth": "1990-01-15",
            "gender": "Male",
            "nationality": "Indian"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/save",
            json={"candidate_details": candidate_details}
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Progress saved"
        
        # Verify data was saved
        verify_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        assert verify_response.status_code == 200
        saved_data = verify_response.json()
        
        assert saved_data["candidate_details"]["first_name"] == "Public"
        assert saved_data["candidate_details"]["phone"] == "9876543210"
        assert saved_data["status"] == "draft"  # Status changes from invited to draft
        
        print("PASSED: Save progress works - status changed to draft")

    def test_submit_public_submission(self, submission_data):
        """Candidate can submit completed form"""
        token = submission_data["token"]
        
        # First save complete data
        complete_data = {
            "candidate_details": {
                "first_name": "Submit",
                "last_name": "Test",
                "phone": "9876543210",
                "date_of_birth": "1990-01-15",
                "gender": "Male",
                "nationality": "Indian",
                "pan_number": f"ABCDE{uuid.uuid4().hex[:4].upper()}F",
                "current_address": "123 Test Street",
                "permanent_address": "123 Test Street"
            },
            "education": [{
                "degree": "B.Tech",
                "institution": "Test University",
                "year": "2012",
                "percentage": "80"
            }],
            "bank_details": {
                "account_number": "123456789012",
                "bank_name": "Test Bank",
                "branch": "Test Branch",
                "ifsc_code": "TEST0001234",
                "account_holder_name": "Submit Test"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "9876543211",
                "relationship": "Spouse"
            },
            "declaration_signed": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/submit",
            json=complete_data
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()
        
        # Verify status changed to submitted
        verify_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "submitted"
        
        print("PASSED: Submit form works - status changed to submitted")

    def test_invalid_token_returns_404(self):
        """Invalid token returns 404"""
        response = requests.get(f"{BASE_URL}/api/onboarding/public/invalid-token-123")
        assert response.status_code == 404
        print("PASSED: Invalid token returns 404")


class TestOnboardingHRActions:
    """Test HR actions: assign, verify, complete, request-revision, reject"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def submitted_submission(self, hr_token):
        """Create and submit a complete submission"""
        # Create invite
        email = f"hr.action.{uuid.uuid4().hex[:6]}@example.com"
        invite_response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": email,
                "candidate_name": "HR Action Test",
                "offered_position": "Test Engineer"
            }
        )
        assert invite_response.status_code == 200
        invite_data = invite_response.json()
        token = invite_data["onboarding_link"].split("/")[-1]
        submission_id = invite_data["submission_id"]
        
        # Submit complete form
        complete_data = {
            "candidate_details": {
                "first_name": "HR",
                "last_name": "Action",
                "phone": "9876543210",
                "date_of_birth": "1990-01-15",
                "gender": "Male",
                "nationality": "Indian",
                "pan_number": f"HRPAN{uuid.uuid4().hex[:4].upper()}F",
                "current_address": "123 HR Street"
            },
            "education": [{
                "degree": "B.Tech",
                "institution": "Test University",
                "year": "2012"
            }],
            "bank_details": {
                "account_number": "123456789012",
                "bank_name": "Test Bank",
                "branch": "Test Branch",
                "ifsc_code": "TEST0001234",
                "account_holder_name": "HR Action"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "9876543211",
                "relationship": "Spouse"
            },
            "declaration_signed": True
        }
        
        submit_response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/submit",
            json=complete_data
        )
        assert submit_response.status_code == 200
        
        return {
            "submission_id": submission_id,
            "token": token,
            "email": email
        }

    def test_hr_assign_details(self, hr_token, submitted_submission):
        """HR can assign department, manager, joining date"""
        submission_id = submitted_submission["submission_id"]
        
        response = requests.patch(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/hr-assign",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "department": "Engineering",
                "reporting_manager_id": "mgr-001",
                "reporting_manager_name": "Test Manager",
                "joining_date": "2026-02-15",
                "official_email": "hr.action@dvbc.com",
                "employment_type": "Full-time"
            }
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()
        
        # Verify HR assigned fields
        verify_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_response.status_code == 200
        hr_assigned = verify_response.json()["hr_assigned"]
        
        assert hr_assigned["department"] == "Engineering"
        assert hr_assigned["reporting_manager_name"] == "Test Manager"
        assert hr_assigned["official_email"] == "hr.action@dvbc.com"
        
        print("PASSED: HR assign details works")

    def test_hr_verify_documents(self, hr_token, submitted_submission):
        """HR can verify documents"""
        submission_id = submitted_submission["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/verify-documents",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()
        
        # Verify the flag is set
        verify_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_response.status_code == 200
        hr_verification = verify_response.json()["hr_verification"]
        
        assert hr_verification["documents_verified"] == True
        assert hr_verification["documents_verified_by"] is not None
        
        print("PASSED: HR verify documents works")

    def test_hr_verify_bank(self, hr_token, submitted_submission):
        """HR can verify bank details"""
        submission_id = submitted_submission["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/verify-bank",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()
        
        # Verify the flag is set
        verify_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_response.status_code == 200
        hr_verification = verify_response.json()["hr_verification"]
        
        assert hr_verification["bank_verified"] == True
        assert hr_verification["bank_verified_by"] is not None
        
        print("PASSED: HR verify bank works")

    def test_hr_request_revision(self, hr_token, submitted_submission):
        """HR can request revision from candidate"""
        submission_id = submitted_submission["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/request-revision",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"reason": "Please update your PAN card details"}
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()
        
        # Verify status changed
        verify_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "revision_requested"
        
        print("PASSED: HR request revision works")

    def test_hr_request_revision_without_reason(self, hr_token, submitted_submission):
        """Request revision fails without reason"""
        submission_id = submitted_submission["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/request-revision",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={}
        )
        
        assert response.status_code == 400
        print("PASSED: Request revision without reason returns 400")


class TestOnboardingReject:
    """Test POST /api/onboarding/submissions/{id}/reject - HR rejects submission"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def submitted_submission_for_reject(self, hr_token):
        """Create and submit a submission for rejection test"""
        email = f"reject.test.{uuid.uuid4().hex[:6]}@example.com"
        invite_response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": email,
                "candidate_name": "Reject Test",
                "offered_position": "Test Role"
            }
        )
        assert invite_response.status_code == 200
        invite_data = invite_response.json()
        token = invite_data["onboarding_link"].split("/")[-1]
        
        # Submit form
        requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/submit",
            json={
                "candidate_details": {"first_name": "Reject", "last_name": "Test", "phone": "9876543210"},
                "bank_details": {"account_number": "123", "ifsc_code": "TEST0001"},
                "emergency_contact": {"name": "Contact", "phone": "9876543211"},
                "declaration_signed": True
            }
        )
        
        return {"submission_id": invite_data["submission_id"], "token": token}

    def test_hr_reject_submission(self, hr_token, submitted_submission_for_reject):
        """HR can reject a candidate"""
        submission_id = submitted_submission_for_reject["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/reject",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"reason": "Position filled by another candidate"}
        )
        
        assert response.status_code == 200
        assert "rejected" in response.json()["message"].lower()
        
        # Verify status changed
        verify_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "rejected"
        
        print("PASSED: HR reject submission works")
    
    def test_hr_reject_without_reason(self, hr_token, submitted_submission_for_reject):
        """Reject fails without reason"""
        submission_id = submitted_submission_for_reject["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/reject",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={}
        )
        
        assert response.status_code == 400
        print("PASSED: Reject without reason returns 400")


class TestOnboardingComplete:
    """Test POST /api/onboarding/submissions/{id}/complete - Generate Employee ID"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture
    def fully_ready_submission(self, hr_token):
        """Create a fully verified submission ready for completion"""
        unique_id = uuid.uuid4().hex[:6]
        email = f"complete.test.{unique_id}@example.com"
        
        # Create invite
        invite_response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": email,
                "candidate_name": "Complete Test",
                "offered_position": "Senior Engineer"
            }
        )
        assert invite_response.status_code == 200
        invite_data = invite_response.json()
        token = invite_data["onboarding_link"].split("/")[-1]
        submission_id = invite_data["submission_id"]
        
        # Upload required documents (at least 2 documents required)
        pdf_content = b"%PDF-1.4\n%Test PDF for complete test\n"
        
        # Upload PAN card document
        files1 = {'file': ('pan_card.pdf', io.BytesIO(pdf_content), 'application/pdf')}
        upload1 = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/upload?document_type=pan_card",
            files=files1
        )
        assert upload1.status_code == 200, f"PAN upload failed: {upload1.text}"
        
        # Upload Aadhaar document
        files2 = {'file': ('aadhaar.pdf', io.BytesIO(pdf_content), 'application/pdf')}
        upload2 = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/upload?document_type=aadhaar",
            files=files2
        )
        assert upload2.status_code == 200, f"Aadhaar upload failed: {upload2.text}"
        
        # Submit complete form with all required fields
        complete_data = {
            "candidate_details": {
                "first_name": "Complete",
                "last_name": "Test",
                "phone": "9876543210",
                "date_of_birth": "1990-01-15",
                "gender": "Male",
                "nationality": "Indian",
                "pan_number": f"CMPLT{unique_id.upper()}F",
                "current_address": "123 Complete Street",
                "permanent_address": "123 Complete Street"
            },
            "education": [{
                "degree": "B.Tech",
                "institution": "Test University",
                "year": "2012",
                "percentage": "80"
            }],
            "bank_details": {
                "account_number": "123456789012",
                "bank_name": "Test Bank",
                "branch": "Test Branch",
                "ifsc_code": "TEST0001234",
                "account_holder_name": "Complete Test"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "9876543211",
                "relationship": "Spouse"
            },
            "declaration_signed": True
        }
        
        submit_response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/submit",
            json=complete_data
        )
        assert submit_response.status_code == 200
        
        # HR assigns all required fields
        assign_response = requests.patch(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/hr-assign",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "department": "Engineering",
                "reporting_manager_id": "mgr-001",
                "reporting_manager_name": "Test Manager",
                "joining_date": "2026-02-20",
                "official_email": f"complete.test.{unique_id}@dvbc.com",
                "employment_type": "Full-time"
            }
        )
        assert assign_response.status_code == 200
        
        # HR verifies documents
        verify_docs_response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/verify-documents",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_docs_response.status_code == 200
        
        # HR verifies bank
        verify_bank_response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/verify-bank",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_bank_response.status_code == 200
        
        return {"submission_id": submission_id, "token": token, "email": email}

    def test_complete_onboarding_generates_employee_id(self, hr_token, fully_ready_submission):
        """Complete onboarding generates Employee ID and creates employee record"""
        submission_id = fully_ready_submission["submission_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/complete",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200, f"Complete failed: {response.text}"
        data = response.json()
        
        assert "employee_id" in data
        assert data["employee_id"].startswith("DVBC")  # Employee ID format: DVBCxxxx
        assert "employee_record_id" in data
        assert "successfully" in data["message"].lower()
        
        print(f"PASSED: Complete onboarding - Employee ID generated: {data['employee_id']}")
        
        # Verify submission status is completed
        verify_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["status"] == "completed"
        
        return data

    def test_complete_already_completed_submission(self, hr_token, fully_ready_submission):
        """Cannot complete an already completed submission"""
        submission_id = fully_ready_submission["submission_id"]
        
        # First completion
        requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/complete",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        # Second completion attempt
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/complete",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 400
        assert "already completed" in response.json()["detail"].lower()
        print("PASSED: Cannot complete already completed submission")


class TestOnboardingLegacy:
    """Test GET /api/onboarding/legacy - List legacy records"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]

    def test_list_legacy_records(self, hr_token):
        """HR can list legacy onboarding records"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/legacy",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASSED: List legacy records - found {len(data)} records")

    def test_list_legacy_without_auth(self):
        """Legacy endpoint requires auth"""
        response = requests.get(f"{BASE_URL}/api/onboarding/legacy")
        assert response.status_code == 401 or response.status_code == 403
        print("PASSED: Legacy endpoint requires authentication")


class TestOnboardingDocumentUpload:
    """Test POST /api/onboarding/public/{token}/upload - Candidate uploads documents"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture
    def submission_token(self, hr_token):
        """Create a submission and return its token"""
        email = f"upload.test.{uuid.uuid4().hex[:6]}@example.com"
        response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": email,
                "candidate_name": "Upload Test",
                "offered_position": "Test Role"
            }
        )
        assert response.status_code == 200
        return response.json()["onboarding_link"].split("/")[-1]

    def test_upload_document_success(self, submission_token):
        """Candidate can upload a PDF document"""
        # Create a simple PDF-like content (minimal PDF header)
        pdf_content = b"%PDF-1.4\n%Test PDF content for upload test\n"
        
        files = {
            'file': ('test_document.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{submission_token}/upload?document_type=pan_card",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "document_id" in data
        assert data["document_type"] == "pan_card"
        assert "successfully" in data["message"].lower()
        
        print(f"PASSED: Document upload - document_id: {data['document_id']}")

    def test_upload_invalid_file_type(self, submission_token):
        """Upload fails for invalid file type"""
        files = {
            'file': ('test.exe', io.BytesIO(b"fake executable"), 'application/x-msdownload')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{submission_token}/upload?document_type=id_proof",
            files=files
        )
        
        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()
        print("PASSED: Invalid file type rejected")


class TestOnboardingE2EFlow:
    """Complete E2E flow test: invite -> fill -> submit -> verify -> complete"""
    
    @pytest.fixture
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "HR001",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["access_token"]

    def test_complete_e2e_onboarding_flow(self, hr_token):
        """Test the complete onboarding flow from invite to employee creation"""
        unique_id = uuid.uuid4().hex[:6]
        
        # Step 1: HR sends invite
        print("Step 1: HR sends invite...")
        email = f"e2e.flow.{unique_id}@example.com"
        invite_response = requests.post(
            f"{BASE_URL}/api/onboarding/invite",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "candidate_email": email,
                "candidate_name": "E2E Flow Test",
                "offered_position": "Full Stack Developer"
            }
        )
        assert invite_response.status_code == 200
        invite_data = invite_response.json()
        submission_id = invite_data["submission_id"]
        token = invite_data["onboarding_link"].split("/")[-1]
        print(f"  Invite sent - submission_id: {submission_id}")
        
        # Step 2: Candidate accesses form
        print("Step 2: Candidate accesses form...")
        public_response = requests.get(f"{BASE_URL}/api/onboarding/public/{token}")
        assert public_response.status_code == 200
        assert public_response.json()["status"] == "invited"
        print(f"  Form accessed - status: invited")
        
        # Step 3: Candidate saves progress
        print("Step 3: Candidate saves progress...")
        save_response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/save",
            json={
                "candidate_details": {
                    "first_name": "E2E",
                    "last_name": "Flow",
                    "phone": "9876543210"
                }
            }
        )
        assert save_response.status_code == 200
        print(f"  Progress saved - status changed to draft")
        
        # Step 4: Candidate submits complete form
        print("Step 4: Candidate submits complete form...")
        submit_response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{token}/submit",
            json={
                "candidate_details": {
                    "first_name": "E2E",
                    "last_name": "Flow",
                    "phone": "9876543210",
                    "date_of_birth": "1992-05-15",
                    "gender": "Male",
                    "nationality": "Indian",
                    "pan_number": f"E2EFL{unique_id.upper()}F",
                    "current_address": "123 E2E Street",
                    "permanent_address": "123 E2E Street"
                },
                "education": [{
                    "degree": "M.Tech",
                    "institution": "E2E University",
                    "year": "2015"
                }],
                "bank_details": {
                    "account_number": "9876543210123",
                    "bank_name": "E2E Bank",
                    "branch": "E2E Branch",
                    "ifsc_code": "E2E00001234",
                    "account_holder_name": "E2E Flow"
                },
                "emergency_contact": {
                    "name": "E2E Emergency",
                    "phone": "9876543211",
                    "relationship": "Parent"
                },
                "declaration_signed": True
            }
        )
        assert submit_response.status_code == 200
        print(f"  Form submitted - status changed to submitted")
        
        # Step 5: HR assigns department and manager
        print("Step 5: HR assigns department and manager...")
        assign_response = requests.patch(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/hr-assign",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={
                "department": "Engineering",
                "reporting_manager_id": "mgr-e2e",
                "reporting_manager_name": "E2E Manager",
                "joining_date": "2026-03-01",
                "official_email": f"e2e.flow.{unique_id}@dvbc.com",
                "employment_type": "Full-time"
            }
        )
        assert assign_response.status_code == 200
        print(f"  HR details assigned")
        
        # Step 6: HR verifies documents
        print("Step 6: HR verifies documents...")
        verify_docs_response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/verify-documents",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_docs_response.status_code == 200
        print(f"  Documents verified")
        
        # Step 7: HR verifies bank
        print("Step 7: HR verifies bank...")
        verify_bank_response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/verify-bank",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert verify_bank_response.status_code == 200
        print(f"  Bank verified")
        
        # Step 8: HR completes onboarding
        print("Step 8: HR completes onboarding...")
        complete_response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}/complete",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert complete_response.status_code == 200
        complete_data = complete_response.json()
        
        assert complete_data["employee_id"].startswith("DVBC")
        print(f"  ONBOARDING COMPLETE!")
        print(f"  Employee ID: {complete_data['employee_id']}")
        print(f"  Employee Record ID: {complete_data['employee_record_id']}")
        
        # Final verification
        final_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert final_response.status_code == 200
        final_data = final_response.json()
        
        assert final_data["status"] == "completed"
        assert final_data["employee_id_generated"] == complete_data["employee_id"]
        
        print("\n=== E2E ONBOARDING FLOW TEST PASSED ===")
        print(f"Candidate: E2E Flow Test ({email})")
        print(f"Employee ID: {complete_data['employee_id']}")
        print(f"Department: Engineering")
        print(f"Position: Full Stack Developer")
        
        return complete_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
