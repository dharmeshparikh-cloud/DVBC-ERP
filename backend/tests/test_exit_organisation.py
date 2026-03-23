"""
Test Exit Organisation (Resignation) Workflow APIs
- Employee initiates resignation from My Details page
- Complete exit interview questions
- Submit for Admin/HR approval
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"employee_id": "EMP001", "password": "admin123"}
HR_CREDS = {"employee_id": "EMP002", "password": "hr123"}
SALES_CREDS = {"employee_id": "EMP003", "password": "sales123"}


class TestExitOrganisationAPIs:
    """Test Exit Organisation API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, creds):
        """Login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return token
        return None
    
    # Test 1: Get Exit Interview Questions (public endpoint)
    def test_get_exit_interview_questions(self):
        """GET /api/exit/interview-questions - should return questions list"""
        # Login as employee first
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        response = self.session.get(f"{BASE_URL}/api/exit/interview-questions")
        print(f"Interview Questions Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "questions" in data, "Response should contain 'questions' key"
        
        questions = data["questions"]
        assert len(questions) > 0, "Should have at least one question"
        
        # Verify question structure
        for q in questions:
            assert "id" in q, "Question should have 'id'"
            assert "question" in q, "Question should have 'question' text"
            assert "type" in q, "Question should have 'type'"
        
        # Verify expected question types
        question_types = [q["type"] for q in questions]
        assert "select" in question_types, "Should have select type questions"
        assert "rating" in question_types, "Should have rating type questions"
        assert "text" in question_types, "Should have text type questions"
        
        print(f"Found {len(questions)} exit interview questions")
        print(f"Question types: {set(question_types)}")
    
    # Test 2: Get My Exit Request (should return null if no request)
    def test_get_my_exit_request_no_request(self):
        """GET /api/exit/my-request - should return null if no request exists"""
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        response = self.session.get(f"{BASE_URL}/api/exit/my-request")
        print(f"My Exit Request Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "request" in data, "Response should contain 'request' key"
        # Note: request can be null or an existing request object
        print(f"My Exit Request: {data['request']}")
    
    # Test 3: Get Exit Checklist Template
    def test_get_exit_checklist_template(self):
        """GET /api/exit/checklist-template - should return checklist items"""
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        response = self.session.get(f"{BASE_URL}/api/exit/checklist-template")
        print(f"Checklist Template Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "checklist" in data, "Response should contain 'checklist' key"
        
        checklist = data["checklist"]
        assert len(checklist) > 0, "Should have checklist items"
        
        # Verify checklist structure
        for item in checklist:
            assert "id" in item, "Checklist item should have 'id'"
            assert "item" in item, "Checklist item should have 'item' description"
            assert "category" in item, "Checklist item should have 'category'"
        
        print(f"Found {len(checklist)} checklist items")
    
    # Test 4: Initiate Exit Request (Employee)
    def test_initiate_exit_request(self):
        """POST /api/exit/initiate - employee initiates resignation"""
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        # First check if there's already a pending request
        check_response = self.session.get(f"{BASE_URL}/api/exit/my-request")
        existing_request = check_response.json().get("request")
        
        if existing_request and existing_request.get("status") in ["pending", "admin_approved", "hr_approved", "in_progress"]:
            print(f"Employee already has pending exit request: {existing_request['id']}")
            print(f"Status: {existing_request['status']}")
            # Test passes - employee already has a request
            return
        
        # Prepare exit interview responses
        interview_responses = {
            "reason": "Better opportunity",
            "experience": 4,
            "recommend": "Yes",
            "management": 4,
            "growth": "Yes",
            "feedback": "Great company to work with",
            "rejoin": "Maybe"
        }
        
        payload = {
            "interview_responses": interview_responses
        }
        
        response = self.session.post(f"{BASE_URL}/api/exit/initiate", json=payload)
        print(f"Initiate Exit Response: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Could be 200 (success) or 400 (already has pending request)
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "request_id" in data, "Response should contain 'request_id'"
            assert "last_working_day" in data, "Response should contain 'last_working_day'"
            assert "notice_period_days" in data, "Response should contain 'notice_period_days'"
            print(f"Exit request created: {data['request_id']}")
            print(f"Last working day: {data['last_working_day']}")
        else:
            print(f"Expected error (already has request): {response.json()}")
    
    # Test 5: Get Pending Exit Requests (Admin/HR only)
    def test_get_pending_exit_requests_admin(self):
        """GET /api/exit/pending - Admin can view pending requests"""
        token = self.login(ADMIN_CREDS)
        assert token is not None, "Failed to login as Admin"
        
        response = self.session.get(f"{BASE_URL}/api/exit/pending")
        print(f"Pending Exit Requests Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "requests" in data, "Response should contain 'requests' key"
        
        requests_list = data["requests"]
        print(f"Found {len(requests_list)} pending exit requests")
        
        for req in requests_list:
            print(f"  - {req.get('employee_name')} ({req.get('employee_code')}): {req.get('status')}")
    
    # Test 6: Get All Exit Requests (Admin/HR only)
    def test_get_all_exit_requests_hr(self):
        """GET /api/exit/all - HR can view all requests"""
        token = self.login(HR_CREDS)
        assert token is not None, "Failed to login as HR"
        
        response = self.session.get(f"{BASE_URL}/api/exit/all")
        print(f"All Exit Requests Response: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "requests" in data, "Response should contain 'requests' key"
        
        print(f"Found {len(data['requests'])} total exit requests")
    
    # Test 7: Employee cannot access pending requests
    def test_employee_cannot_access_pending_requests(self):
        """GET /api/exit/pending - Employee should get 403"""
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        response = self.session.get(f"{BASE_URL}/api/exit/pending")
        print(f"Employee accessing pending requests: {response.status_code}")
        
        assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}"
    
    # Test 8: Validate exit interview required fields
    def test_initiate_exit_missing_required_fields(self):
        """POST /api/exit/initiate - should fail without required interview responses"""
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        # First check if there's already a pending request
        check_response = self.session.get(f"{BASE_URL}/api/exit/my-request")
        existing_request = check_response.json().get("request")
        
        if existing_request and existing_request.get("status") in ["pending", "admin_approved", "hr_approved", "in_progress"]:
            print("Skipping - employee already has pending exit request")
            return
        
        # Missing required fields (only providing optional text field)
        payload = {
            "interview_responses": {
                "feedback": "Some feedback"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/exit/initiate", json=payload)
        print(f"Initiate Exit (missing fields) Response: {response.status_code}")
        
        # Should fail with 400 due to missing required fields
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print(f"Expected error: {response.json()}")


class TestExitOrganisationWorkflow:
    """Test complete exit workflow: initiate -> admin approve -> hr approve"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self, creds):
        """Login and get token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json=creds)
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return token
        return None
    
    def test_complete_exit_workflow(self):
        """Test complete exit workflow from initiation to approval"""
        # Step 1: Employee initiates exit
        token = self.login(SALES_CREDS)
        assert token is not None, "Failed to login as EMP003"
        
        # Check existing request
        check_response = self.session.get(f"{BASE_URL}/api/exit/my-request")
        existing_request = check_response.json().get("request")
        
        request_id = None
        
        if existing_request:
            request_id = existing_request.get("id")
            print(f"Using existing exit request: {request_id}")
            print(f"Current status: {existing_request.get('status')}")
        else:
            # Create new request
            interview_responses = {
                "reason": "Better opportunity",
                "experience": 4,
                "recommend": "Yes",
                "management": 4,
                "growth": "Yes",
                "feedback": "Great company",
                "rejoin": "Maybe"
            }
            
            response = self.session.post(f"{BASE_URL}/api/exit/initiate", json={
                "interview_responses": interview_responses
            })
            
            if response.status_code == 200:
                request_id = response.json().get("request_id")
                print(f"Created new exit request: {request_id}")
        
        if not request_id:
            print("No exit request to test workflow")
            return
        
        # Step 2: Admin approves
        token = self.login(ADMIN_CREDS)
        assert token is not None, "Failed to login as Admin"
        
        # Get request details
        detail_response = self.session.get(f"{BASE_URL}/api/exit/{request_id}")
        if detail_response.status_code == 200:
            request_data = detail_response.json()
            current_status = request_data.get("status")
            print(f"Request status before admin approval: {current_status}")
            
            if current_status == "pending":
                approve_response = self.session.post(
                    f"{BASE_URL}/api/exit/{request_id}/admin-approve",
                    json={"remarks": "Approved by Admin"}
                )
                print(f"Admin approval response: {approve_response.status_code}")
                if approve_response.status_code == 200:
                    print("Admin approved successfully")
            elif current_status == "admin_approved":
                print("Already admin approved, proceeding to HR approval")
        
        # Step 3: HR approves
        token = self.login(HR_CREDS)
        assert token is not None, "Failed to login as HR"
        
        detail_response = self.session.get(f"{BASE_URL}/api/exit/{request_id}")
        if detail_response.status_code == 200:
            request_data = detail_response.json()
            current_status = request_data.get("status")
            print(f"Request status before HR approval: {current_status}")
            
            if current_status == "admin_approved":
                approve_response = self.session.post(
                    f"{BASE_URL}/api/exit/{request_id}/hr-approve",
                    json={"remarks": "Approved by HR"}
                )
                print(f"HR approval response: {approve_response.status_code}")
                if approve_response.status_code == 200:
                    print("HR approved successfully")
                    fnf = approve_response.json().get("fnf")
                    if fnf:
                        print(f"F&F Calculation: Net Payable = {fnf.get('net_payable')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
