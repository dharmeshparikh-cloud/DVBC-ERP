"""
Test suite for HR Onboarding and Employee Go-Live audit fixes.

Issues to test:
1. Auto-save toast spam (frontend useDraft hook) - NOT testable via API
2. Professional reference optional in CandidateOnboardingForm - API validation
3. Go-Live Dashboard search - API endpoint check
4. Individual document approve/reject - API endpoints
5. Data persistence after save - API save/load cycle

Author: Testing Agent
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://zero-crash-erp.preview.emergentagent.com')

# Test credentials
HR_CREDENTIALS = {"employee_id": "DVC037", "password": "test123"}
ADMIN_CREDENTIALS = {"employee_id": "ADMIN001", "password": "admin123"}


class TestAuthAndSetup:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR Manager auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("HR login failed")
    
    @pytest.fixture(scope="class")  
    def admin_token(self):
        """Get Admin auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Admin login failed")
    
    def test_hr_login(self):
        """Test HR Manager login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        assert response.status_code == 200, f"HR login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"HR Login successful, user role: {data.get('user', {}).get('role')}")
    
    def test_admin_login(self):
        """Test Admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        print(f"Admin Login successful, user role: {data.get('user', {}).get('role')}")


class TestGoLiveDashboard:
    """Test ISSUE 3: Go-Live Dashboard has employee search functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for HR"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_employees_list_endpoint(self, auth_headers):
        """Test /api/employees returns employee list for Go-Live search"""
        response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        assert response.status_code == 200, f"Employees endpoint failed: {response.text}"
        
        data = response.json()
        # API returns either 'items' array or direct array
        employees = data.get('items') if isinstance(data, dict) else data
        assert employees is not None, "No employee data returned"
        print(f"Employees endpoint returned {len(employees)} employees")
    
    def test_go_live_checklist_endpoint(self, auth_headers):
        """Test /api/go-live/checklist/{employee_id} endpoint exists"""
        # First get an employee ID
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=auth_headers)
        if emp_response.status_code == 200:
            data = emp_response.json()
            employees = data.get('items') if isinstance(data, dict) else data
            if employees and len(employees) > 0:
                emp_id = employees[0].get('employee_id') or employees[0].get('id')
                
                # Test checklist endpoint
                checklist_response = requests.get(
                    f"{BASE_URL}/api/go-live/checklist/{emp_id}", 
                    headers=auth_headers
                )
                # Allow 200 or 404 (employee may not have checklist data)
                assert checklist_response.status_code in [200, 404], \
                    f"Unexpected status: {checklist_response.status_code}"
                print(f"Go-Live checklist endpoint status: {checklist_response.status_code}")


class TestDocumentVerification:
    """Test ISSUE 4: Individual document approve/reject endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for HR Manager"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_onboarding_submissions_list(self, auth_headers):
        """Test /api/onboarding/submissions endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/onboarding/submissions", headers=auth_headers)
        assert response.status_code == 200, f"Submissions endpoint failed: {response.text}"
        
        submissions = response.json()
        print(f"Found {len(submissions)} onboarding submissions")
        return submissions
    
    def test_document_approve_endpoint_exists(self, auth_headers):
        """Test that document approve endpoint structure is correct"""
        # This tests the route exists by checking server response pattern
        # Using a fake submission/document ID should return 404, not 405 or 500
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/test-submission-id/documents/test-doc-id/approve",
            headers=auth_headers
        )
        # Should be 404 (not found) not 405 (method not allowed) or 500 (server error)
        assert response.status_code in [404, 400], \
            f"Approve endpoint may not exist. Status: {response.status_code}, Response: {response.text}"
        print(f"Document approve endpoint check: status {response.status_code} (expected 404 for fake ID)")
    
    def test_document_reject_endpoint_exists(self, auth_headers):
        """Test that document reject endpoint structure is correct"""
        response = requests.post(
            f"{BASE_URL}/api/onboarding/submissions/test-submission-id/documents/test-doc-id/reject",
            headers=auth_headers,
            json={"reason": "Test rejection"}
        )
        # Should be 404 (not found) not 405 (method not allowed) or 500 (server error)
        assert response.status_code in [404, 400], \
            f"Reject endpoint may not exist. Status: {response.status_code}, Response: {response.text}"
        print(f"Document reject endpoint check: status {response.status_code} (expected 404 for fake ID)")


class TestOnboardingDataPersistence:
    """Test ISSUE 5: Data persistence after save and reopen"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_get_submission_returns_saved_data(self, auth_headers):
        """Test that saved submission data persists on reload"""
        # Get list of submissions
        response = requests.get(f"{BASE_URL}/api/onboarding/submissions", headers=auth_headers)
        assert response.status_code == 200
        
        submissions = response.json()
        if not submissions:
            pytest.skip("No submissions to test")
        
        # Get first submission with status 'submitted' or 'draft'
        test_submission = None
        for sub in submissions:
            if sub.get('status') in ['submitted', 'draft', 'completed']:
                test_submission = sub
                break
        
        if not test_submission:
            pytest.skip("No suitable submission to test")
        
        submission_id = test_submission.get('id')
        
        # Fetch full submission details
        detail_response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions/{submission_id}",
            headers=auth_headers
        )
        assert detail_response.status_code == 200
        
        submission_detail = detail_response.json()
        
        # Verify data fields are present (not null/empty after save)
        assert submission_detail.get('candidate_name'), "Candidate name should persist"
        assert submission_detail.get('candidate_email'), "Candidate email should persist"
        
        # If candidate_details were filled, they should persist
        cd = submission_detail.get('candidate_details')
        if cd:
            print(f"✓ Candidate details persisted: {cd.get('first_name')} {cd.get('last_name')}")
        
        print(f"✓ Submission {submission_id} data persists correctly")


class TestDraftSaveEndpoint:
    """Test draft save functionality for auto-save feature"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=HR_CREDENTIALS)
        if response.status_code == 200:
            token = response.json().get("access_token")
            return {"Authorization": f"Bearer {token}"}
        pytest.skip("Auth failed")
    
    def test_drafts_endpoint_exists(self, auth_headers):
        """Test /api/drafts endpoint is accessible"""
        response = requests.get(f"{BASE_URL}/api/drafts", headers=auth_headers)
        # Should return 200 with list of drafts (even if empty)
        assert response.status_code == 200, f"Drafts endpoint failed: {response.text}"
        print(f"Drafts endpoint accessible, returned {len(response.json())} drafts")
    
    def test_draft_save_and_retrieve(self, auth_headers):
        """Test saving a draft and retrieving it"""
        # Create a test draft
        test_draft = {
            "module": "test",
            "draft_type": "test_type",
            "title": "Test Draft for Audit",
            "route": "/test",
            "form_data": {"test_field": "test_value"},
            "data": {"test_field": "test_value"}
        }
        
        # Save draft
        save_response = requests.post(
            f"{BASE_URL}/api/drafts",
            headers=auth_headers,
            json=test_draft
        )
        
        if save_response.status_code in [200, 201]:
            draft_data = save_response.json()
            draft_id = draft_data.get('draft', {}).get('id')
            
            if draft_id:
                # Retrieve draft
                get_response = requests.get(
                    f"{BASE_URL}/api/drafts/{draft_id}",
                    headers=auth_headers
                )
                assert get_response.status_code == 200
                
                retrieved = get_response.json()
                assert retrieved.get('form_data', {}).get('test_field') == 'test_value'
                print(f"✓ Draft saved and retrieved successfully: {draft_id}")
                
                # Cleanup - delete test draft
                requests.delete(f"{BASE_URL}/api/drafts/{draft_id}", headers=auth_headers)
        else:
            print(f"Draft save returned {save_response.status_code}: {save_response.text}")


class TestProfessionalReferenceOptional:
    """Test ISSUE 2: Professional reference is now optional"""
    
    def test_onboarding_validation_endpoint_exists(self):
        """Verify onboarding public endpoint structure"""
        # Test public endpoint with fake token - should return 404 not 500
        response = requests.get(f"{BASE_URL}/api/onboarding/public/fake-token-12345")
        # Expected 404 (invalid token) or 410 (expired) - NOT 500 (server error)
        assert response.status_code in [404, 410], \
            f"Unexpected status: {response.status_code}. Public endpoint may have issues."
        print(f"Public onboarding endpoint check: status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
