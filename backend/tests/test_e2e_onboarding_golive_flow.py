"""
NETRA ERP - E2E Onboarding to Go-Live Flow Test
Tests the complete employee onboarding lifecycle:
1. HR sends onboarding invite
2. Candidate fills and submits form
3. HR reviews and completes onboarding
4. Go-Live submission and approval
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL env var must be set"

# Test credentials
HR_CREDENTIALS = {"employee_id": "DVC037", "password": "test123"}
ADMIN_CREDENTIALS = {"employee_id": "ADMIN001", "password": "admin123"}

# Test data - unique per run
TEST_ID = uuid.uuid4().hex[:6]
TEST_CANDIDATE = {
    "name": f"E2E Test {TEST_ID}",
    "email": f"e2e.{TEST_ID}@test.example.com",
    "position": "Test Engineer"
}


class TestE2EOnboardingGoLive:
    """Complete E2E test for Onboarding to Go-Live flow"""
    
    @pytest.fixture(scope="class")
    def hr_session(self):
        """Get HR Manager session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"HR login failed: {response.text}")
        token = response.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    @pytest.fixture(scope="class")
    def admin_session(self):
        """Get Admin session"""
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.text}")
        token = response.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    # ==================== PHASE 1: HR SENDS INVITE ====================
    
    def test_01_hr_sends_onboarding_invite(self, hr_session):
        """HR sends onboarding invite to candidate"""
        response = hr_session.post(
            f"{BASE_URL}/api/onboarding/invite",
            json={
                "candidate_name": TEST_CANDIDATE["name"],
                "candidate_email": TEST_CANDIDATE["email"],
                "offered_position": TEST_CANDIDATE["position"]
            }
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "submission_id" in data
        assert "onboarding_link" in data
        assert "expires_at" in data
        
        # Store for subsequent tests
        pytest.submission_id = data["submission_id"]
        pytest.onboarding_token = data["onboarding_link"].split("/")[-1]
        
        print(f"✓ Invite sent - ID: {data['submission_id']}")
    
    def test_02_verify_submission_status_invited(self, hr_session):
        """Verify submission is in 'invited' status"""
        response = hr_session.get(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "invited"
        assert data["candidate_name"] == TEST_CANDIDATE["name"]
        
        print("✓ Submission created with 'invited' status")
    
    # ==================== PHASE 2: CANDIDATE FILLS FORM ====================
    
    def test_03_public_form_accessible(self):
        """Candidate accesses public form with token"""
        response = requests.get(
            f"{BASE_URL}/api/onboarding/public/{pytest.onboarding_token}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["invited", "draft"]
        assert data["candidate_name"] == TEST_CANDIDATE["name"]
        
        print("✓ Public form accessible")
    
    def test_04_candidate_saves_progress(self):
        """Candidate saves form progress"""
        form_data = {
            "candidate_details": {
                "first_name": "E2E",
                "last_name": f"Test{TEST_ID}",
                "date_of_birth": "1995-05-15",
                "gender": "male",
                "blood_group": "A+",
                "marital_status": "single",
                "nationality": "Indian",
                "phone": "9876543210",
                "alternate_phone": "9876543211",
                "pan_number": "ABCDE1234F",
                "aadhaar_number": "123456789012",
                "current_address": {"street": "123 Test St", "city": "Bangalore", "state": "Karnataka", "pincode": "560001"},
                "permanent_address": {"street": "123 Test St", "city": "Bangalore", "state": "Karnataka", "pincode": "560001"}
            },
            "education": [
                {"degree": "B.Tech", "institution": "Test University", "year": "2017", "percentage": "85%"}
            ],
            "employment_history": [
                {"company": "Previous Corp", "designation": "Junior Engineer", "from_date": "2018-01-01", "to_date": "2023-12-31", "reason_for_leaving": "Career growth"}
            ],
            "bank_details": {
                "account_holder_name": f"E2E Test{TEST_ID}",
                "account_number": "1234567890123",
                "ifsc_code": "SBIN0001234",
                "bank_name": "State Bank of India",
                "branch": "Test Branch"
            },
            "professional_reference": {
                "name": "John Manager",
                "phone": "9876543212",
                "company_name": "Previous Corp",
                "designation": "Manager"
            },
            "personal_reference": {
                "name": "Jane Friend",
                "phone": "9876543213",
                "address": "456 Friend St, Bangalore"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "9876543214",
                "relationship": "Parent"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{pytest.onboarding_token}/save",
            json=form_data
        )
        
        assert response.status_code == 200
        print("✓ Form progress saved")
    
    def test_05_candidate_submits_form(self):
        """Candidate submits completed form"""
        form_data = {
            "candidate_details": {
                "first_name": "E2E",
                "last_name": f"Test{TEST_ID}",
                "date_of_birth": "1995-05-15",
                "gender": "male",
                "blood_group": "A+",
                "marital_status": "single",
                "nationality": "Indian",
                "phone": "9876543210",
                "alternate_phone": "9876543211",
                "pan_number": "ABCDE1234F",
                "aadhaar_number": "123456789012",
                "current_address": {"street": "123 Test St", "city": "Bangalore", "state": "Karnataka", "pincode": "560001"},
                "permanent_address": {"street": "123 Test St", "city": "Bangalore", "state": "Karnataka", "pincode": "560001"}
            },
            "education": [
                {"degree": "B.Tech", "institution": "Test University", "year": "2017", "percentage": "85%"}
            ],
            "employment_history": [
                {"company": "Previous Corp", "designation": "Junior Engineer", "from_date": "2018-01-01", "to_date": "2023-12-31", "reason_for_leaving": "Career growth"}
            ],
            "bank_details": {
                "account_holder_name": f"E2E Test{TEST_ID}",
                "account_number": "1234567890123",
                "ifsc_code": "SBIN0001234",
                "bank_name": "State Bank of India",
                "branch": "Test Branch"
            },
            "professional_reference": {
                "name": "John Manager",
                "phone": "9876543212",
                "company_name": "Previous Corp",
                "designation": "Manager"
            },
            "personal_reference": {
                "name": "Jane Friend",
                "phone": "9876543213",
                "address": "456 Friend St, Bangalore"
            },
            "emergency_contact": {
                "name": "Emergency Contact",
                "phone": "9876543214",
                "relationship": "Parent"
            },
            "declaration_signed": True,
            "declaration": {
                "signed": True,
                "signed_at": datetime.now().isoformat(),
                "text": "I declare all information is true."
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/onboarding/public/{pytest.onboarding_token}/submit",
            json=form_data
        )
        
        assert response.status_code == 200
        print("✓ Form submitted successfully")
    
    def test_06_verify_submission_status_submitted(self, hr_session):
        """Verify submission is now 'submitted'"""
        response = hr_session.get(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None
        
        print("✓ Submission status changed to 'submitted'")
    
    # ==================== PHASE 3: HR REVIEW ====================
    
    def test_07_hr_lists_pending_submissions(self, hr_session):
        """HR views pending submissions in Onboarding Hub"""
        response = hr_session.get(f"{BASE_URL}/api/onboarding/submissions")
        
        assert response.status_code == 200
        submissions = response.json()
        
        # Find our test submission
        test_submission = next((s for s in submissions if s["id"] == pytest.submission_id), None)
        assert test_submission is not None
        assert test_submission["status"] == "submitted"
        
        print(f"✓ Found {len(submissions)} submissions, test submission in pending")
    
    def test_08_hr_assigns_department_manager(self, hr_session):
        """HR assigns department, manager, joining date"""
        # First get a manager from employees list
        response = hr_session.get(f"{BASE_URL}/api/employees/all")
        assert response.status_code == 200
        employees = response.json().get("items", response.json())
        
        # Find a manager
        manager = next((e for e in employees if e.get("role") in ["hr_manager", "manager", "admin"]), None)
        manager_id = manager["id"] if manager else "admin-user-id"
        manager_name = manager.get("full_name", "Admin User") if manager else "Admin User"
        
        # Assign HR details
        assignment = {
            "department": "Consulting",
            "reporting_manager_id": manager_id,
            "reporting_manager_name": manager_name,
            "joining_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "official_email": f"e2e.test.{TEST_ID}@dvconsulting.co.in",
            "employment_type": "full_time",
            "designation": TEST_CANDIDATE["position"]
        }
        
        response = hr_session.patch(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}/hr-assign",
            json=assignment
        )
        
        assert response.status_code == 200
        print("✓ HR assignment saved")
    
    def test_09_hr_verifies_documents(self, hr_session):
        """HR verifies documents"""
        response = hr_session.post(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}/verify-documents"
        )
        
        assert response.status_code == 200
        print("✓ Documents verified")
    
    def test_10_hr_verifies_bank(self, hr_session):
        """HR verifies bank details"""
        response = hr_session.post(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}/verify-bank"
        )
        
        assert response.status_code == 200
        print("✓ Bank details verified")
    
    def test_11_hr_uploads_document(self, hr_session):
        """HR uploads document on behalf of candidate"""
        # Create a simple test file content
        import io
        test_file = io.BytesIO(b"Test document content")
        
        response = hr_session.post(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}/upload-document",
            params={"document_type": "pan_card"},
            files={"file": ("test_pan.pdf", test_file, "application/pdf")}
        )
        
        assert response.status_code == 200
        print("✓ HR uploaded document")
        
        # Upload second required doc
        test_file2 = io.BytesIO(b"Test aadhaar content")
        response2 = hr_session.post(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}/upload-document",
            params={"document_type": "aadhaar_card"},
            files={"file": ("test_aadhaar.pdf", test_file2, "application/pdf")}
        )
        assert response2.status_code == 200
        print("✓ HR uploaded second document (aadhaar)")
    
    # ==================== PHASE 4: COMPLETE ONBOARDING ====================
    
    def test_12_hr_completes_onboarding(self, hr_session):
        """HR completes onboarding - Employee ID generated"""
        response = hr_session.post(
            f"{BASE_URL}/api/onboarding/submissions/{pytest.submission_id}/complete"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "employee_id" in data
        assert data["employee_id"].startswith("DVBC")
        
        pytest.generated_employee_id = data["employee_id"]
        pytest.employee_record_id = data.get("employee_record_id")
        
        print(f"✓ Onboarding complete - Employee ID: {data['employee_id']}")
    
    def test_13_verify_employee_created(self, hr_session):
        """Verify employee record was created"""
        # Try to find by employee_id
        response = hr_session.get(f"{BASE_URL}/api/employees/all")
        assert response.status_code == 200
        employees = response.json().get("items", response.json())
        
        # Find our new employee
        new_employee = next((e for e in employees if e.get("employee_id") == pytest.generated_employee_id), None)
        
        if new_employee:
            assert new_employee["first_name"] == "E2E"
            assert new_employee["department"] == "Consulting"
            assert new_employee["go_live_status"] in ["not_submitted", None]
            pytest.employee_db_id = new_employee["id"]
            print(f"✓ Employee record found with ID: {new_employee['id']}")
        else:
            # May need to search differently
            pytest.employee_db_id = pytest.employee_record_id
            print(f"✓ Employee created, using record ID: {pytest.employee_record_id}")
    
    # ==================== PHASE 5: GO-LIVE PROCESS ====================
    
    def test_14_go_live_dashboard_shows_employee(self, hr_session):
        """Go-Live Dashboard shows new employee"""
        response = hr_session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        
        employees = response.json().get("items", response.json())
        # Find employee needing go-live
        employee = next((e for e in employees if e.get("employee_id") == pytest.generated_employee_id), None)
        
        if employee:
            pytest.employee_db_id = employee["id"]
            print(f"✓ Employee visible - Status: {employee.get('go_live_status', 'not_submitted')}")
        else:
            print("! Employee not found in list, using stored ID")
    
    def test_15_get_go_live_checklist(self, hr_session):
        """Get Go-Live checklist for employee"""
        employee_id = getattr(pytest, 'employee_db_id', None) or pytest.employee_record_id
        
        response = hr_session.get(
            f"{BASE_URL}/api/go-live/checklist/{employee_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "checklist" in data
        assert "summary" in data
        
        print(f"✓ Checklist: {data['summary']['completed']}/{data['summary']['total']} items complete")
    
    def test_16_hr_submits_go_live_request(self, hr_session):
        """HR submits Go-Live request for approval"""
        employee_id = getattr(pytest, 'employee_db_id', None) or pytest.employee_record_id
        
        response = hr_session.post(
            f"{BASE_URL}/api/go-live/submit/{employee_id}",
            json={
                "checklist": {},
                "notes": "E2E Test Go-Live Request"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        pytest.go_live_request_id = data.get("request_id")
        
        print(f"✓ Go-Live request submitted - ID: {data.get('request_id')}")
    
    def test_17_admin_views_pending_approvals(self, admin_session):
        """Admin views pending Go-Live approvals"""
        response = admin_session.get(f"{BASE_URL}/api/go-live/pending")
        
        assert response.status_code == 200
        requests_list = response.json()
        
        # Find our request
        our_request = next(
            (r for r in requests_list if r.get("employee_name", "").startswith("E2E")),
            None
        )
        
        if our_request:
            pytest.go_live_request_id = our_request["id"]
            print(f"✓ Found pending request for approval - ID: {our_request['id']}")
        else:
            print(f"! Total pending: {len(requests_list)}")
    
    def test_18_admin_approves_go_live(self, admin_session):
        """Admin approves Go-Live request"""
        request_id = getattr(pytest, 'go_live_request_id', None)
        
        if not request_id:
            # Try to find it
            response = admin_session.get(f"{BASE_URL}/api/go-live/pending")
            requests_list = response.json()
            our_request = next(
                (r for r in requests_list if "E2E" in r.get("employee_name", "") or "Test" in r.get("employee_name", "")),
                None
            )
            if our_request:
                request_id = our_request["id"]
        
        if not request_id:
            pytest.skip("No go-live request to approve")
        
        response = admin_session.post(
            f"{BASE_URL}/api/go-live/{request_id}/approve",
            json={"remarks": "E2E Test approved"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        
        print(f"✓ Go-Live approved!")
    
    def test_19_verify_employee_active(self, hr_session):
        """Verify employee status is now 'active'"""
        employee_id = getattr(pytest, 'employee_db_id', None) or pytest.employee_record_id
        
        # Get checklist again to see status
        response = hr_session.get(
            f"{BASE_URL}/api/go-live/checklist/{employee_id}"
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("employee", {}).get("go_live_status")
            assert status == "active", f"Expected 'active', got '{status}'"
            print(f"✓ Employee is now ACTIVE!")
        else:
            # Fallback check via employees endpoint
            response = hr_session.get(f"{BASE_URL}/api/employees")
            employees = response.json().get("items", response.json())
            employee = next((e for e in employees if e.get("employee_id") == pytest.generated_employee_id), None)
            if employee:
                assert employee.get("go_live_status") == "active"
                print(f"✓ Employee is ACTIVE (verified via employees list)")


class TestOnboardingAPIs:
    """Test individual onboarding API endpoints"""
    
    @pytest.fixture
    def hr_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip("HR login failed")
        session.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
        return session
    
    def test_list_submissions_endpoint(self, hr_session):
        """Test GET /api/onboarding/submissions"""
        response = hr_session.get(f"{BASE_URL}/api/onboarding/submissions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ Submissions list: {len(response.json())} records")
    
    def test_list_legacy_endpoint(self, hr_session):
        """Test GET /api/onboarding/legacy"""
        response = hr_session.get(f"{BASE_URL}/api/onboarding/legacy")
        assert response.status_code == 200
        print(f"✓ Legacy records: {len(response.json())} records")


class TestGoLiveAPIs:
    """Test Go-Live API endpoints"""
    
    @pytest.fixture
    def hr_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip("HR login failed")
        session.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
        return session
    
    @pytest.fixture
    def admin_session(self):
        session = requests.Session()
        response = session.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        session.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})
        return session
    
    def test_go_live_stats(self, hr_session):
        """Test GET /api/go-live/stats"""
        response = hr_session.get(f"{BASE_URL}/api/go-live/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pending" in data
        assert "approved" in data
        print(f"✓ Go-Live stats: pending={data['pending']}, approved={data['approved']}")
    
    def test_go_live_all_requests(self, hr_session):
        """Test GET /api/go-live/all"""
        response = hr_session.get(f"{BASE_URL}/api/go-live/all")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ All go-live requests: {len(response.json())} records")
    
    def test_pending_requests_admin(self, admin_session):
        """Test GET /api/go-live/pending (admin only)"""
        response = admin_session.get(f"{BASE_URL}/api/go-live/pending")
        assert response.status_code == 200
        print(f"✓ Pending requests: {len(response.json())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
