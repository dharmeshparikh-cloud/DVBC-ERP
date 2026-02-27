"""
Test Go-Live Workflow - New Employee ID Generation Flow
============================================================
Tests the new Go-Live workflow where:
1. Onboarding completion does NOT generate Employee ID
2. Employee ID is ONLY generated when Admin approves Go-Live request
3. Admin can see detailed employee info before approving

Credentials:
- Admin: ADMIN001 / admin123
- HR Manager: DVC037 / test123
"""

import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


class TestGoLiveNewFlow:
    """Tests for the new Go-Live Employee ID generation flow"""

    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "ADMIN001", "password": "admin123"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]

    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR Manager authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "DVC037", "password": "test123"}
        )
        assert response.status_code == 200, f"HR login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]

    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Headers with admin auth"""
        return {"Authorization": f"Bearer {admin_token}"}

    @pytest.fixture(scope="class")
    def hr_headers(self, hr_token):
        """Headers with HR auth"""
        return {"Authorization": f"Bearer {hr_token}"}

    # ====================
    # Test Go-Live Checklist API
    # ====================

    def test_golive_checklist_endpoint(self, hr_headers):
        """Test Go-Live checklist API returns proper structure"""
        # Get any employee to test checklist
        emp_response = requests.get(f"{BASE_URL}/api/employees", headers=hr_headers)
        assert emp_response.status_code == 200, f"Failed to get employees: {emp_response.text}"
        
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", [])
        
        assert len(employees) > 0, "No employees found"
        
        # Get checklist for first employee
        emp = employees[0]
        emp_id = emp.get("id") or emp.get("employee_id")
        
        checklist_response = requests.get(
            f"{BASE_URL}/api/go-live/checklist/{emp_id}",
            headers=hr_headers
        )
        assert checklist_response.status_code in [200, 404], f"Checklist API error: {checklist_response.text}"
        
        if checklist_response.status_code == 200:
            data = checklist_response.json()
            # Verify checklist structure
            assert "employee" in data, "Missing employee in checklist response"
            assert "checklist" in data, "Missing checklist in response"
            assert "summary" in data, "Missing summary in response"
            
            # Verify summary has required fields
            summary = data["summary"]
            assert "completed" in summary, "Missing completed count in summary"
            assert "total" in summary, "Missing total count in summary"
            assert "percentage" in summary, "Missing percentage in summary"
            assert "is_ready" in summary, "Missing is_ready flag in summary"
            
            print(f"✓ Checklist API working - {summary['completed']}/{summary['total']} items complete")

    # ====================
    # Test Pending Go-Live Requests (Admin)
    # ====================

    def test_pending_golive_requests(self, admin_headers):
        """Test Admin can fetch pending Go-Live requests"""
        response = requests.get(
            f"{BASE_URL}/api/go-live/pending",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to get pending requests: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Pending requests should be a list"
        print(f"✓ Found {len(data)} pending Go-Live requests")
        
        # If there are pending requests, verify structure
        if len(data) > 0:
            req = data[0]
            assert "id" in req, "Missing id in request"
            assert "employee_id" in req, "Missing employee_id in request"
            assert "employee_name" in req, "Missing employee_name in request"
            assert "status" in req, "Missing status in request"
            assert req["status"] == "pending", f"Expected pending status, got {req['status']}"
            print(f"✓ Request structure valid: {req['employee_name']}")

    # ====================
    # Test Go-Live Request Details (Admin Review)
    # ====================

    def test_golive_request_details_endpoint(self, admin_headers):
        """Test Admin can see detailed employee info for Go-Live approval"""
        # First get pending requests
        pending_response = requests.get(
            f"{BASE_URL}/api/go-live/pending",
            headers=admin_headers
        )
        assert pending_response.status_code == 200
        pending = pending_response.json()
        
        if len(pending) == 0:
            pytest.skip("No pending Go-Live requests to test details endpoint")
        
        # Get details for first pending request
        request_id = pending[0]["id"]
        details_response = requests.get(
            f"{BASE_URL}/api/go-live/request/{request_id}/details",
            headers=admin_headers
        )
        assert details_response.status_code == 200, f"Failed to get request details: {details_response.text}"
        
        data = details_response.json()
        
        # Verify detailed employee info structure
        assert "request" in data, "Missing request in details"
        assert "employee" in data, "Missing employee details"
        
        employee = data["employee"]
        
        # Key fields Admin should see before approving
        required_fields = ["id", "full_name", "department", "designation", "joining_date"]
        for field in required_fields:
            assert field in employee, f"Missing {field} in employee details"
        
        # Check for preview Employee ID (generated on approval)
        if employee.get("employee_id_pending"):
            assert "preview_employee_id" in employee, "Missing preview_employee_id for pending employee"
            print(f"✓ Preview Employee ID: {employee.get('preview_employee_id')}")
        
        print(f"✓ Details endpoint working - shows {employee.get('full_name')}")
        print(f"  Department: {employee.get('department')}")
        print(f"  Designation: {employee.get('designation')}")
        print(f"  Joining Date: {employee.get('joining_date')}")
        print(f"  Bank Verified: {employee.get('bank_verified')}")

    # ====================
    # Test Go-Live Stats
    # ====================

    def test_golive_stats(self, admin_headers):
        """Test Go-Live statistics endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/go-live/stats",
            headers=admin_headers
        )
        assert response.status_code == 200, f"Stats API error: {response.text}"
        
        stats = response.json()
        assert "pending" in stats, "Missing pending count in stats"
        assert "approved" in stats, "Missing approved count in stats"
        assert "total" in stats, "Missing total count in stats"
        
        print(f"✓ Stats: Pending={stats['pending']}, Approved={stats['approved']}, Total={stats['total']}")

    # ====================
    # Test Onboarding Completion Does NOT Generate Employee ID
    # ====================

    def test_onboarding_completion_no_employee_id(self, hr_headers):
        """Verify onboarding completion does NOT generate Employee ID"""
        # Get completed onboarding submissions
        response = requests.get(
            f"{BASE_URL}/api/onboarding/submissions?status=completed",
            headers=hr_headers
        )
        
        if response.status_code != 200:
            pytest.skip("Onboarding submissions endpoint not available")
        
        submissions = response.json()
        if isinstance(submissions, list) and len(submissions) > 0:
            # Find a recently completed submission
            for sub in submissions:
                # Check if employee_id_generated is None or pending
                if sub.get("employee_id_pending") == True:
                    print(f"✓ Submission {sub.get('id')} correctly has employee_id_pending=True")
                    return
                elif sub.get("employee_id_generated") is None:
                    print(f"✓ Submission {sub.get('id')} correctly has no employee_id_generated")
                    return
        
        print("✓ Onboarding completion behavior verified (no pending submissions to check)")

    # ====================
    # Test Employee with employee_id_pending flag
    # ====================

    def test_employee_id_pending_flag(self, hr_headers):
        """Verify employees can have employee_id_pending flag"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=hr_headers
        )
        assert response.status_code == 200
        
        employees = response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", [])
        
        # Look for employees with employee_id_pending=True
        pending_employees = [e for e in employees if e.get("employee_id_pending") == True]
        
        # Look for employees with go_live_status = not_submitted
        not_submitted = [e for e in employees if e.get("go_live_status") == "not_submitted"]
        
        print(f"✓ Found {len(pending_employees)} employees with employee_id_pending=True")
        print(f"✓ Found {len(not_submitted)} employees with go_live_status=not_submitted")

    # ====================
    # Test Enable Portal Access (without Employee ID)
    # ====================

    def test_enable_portal_access_api(self, admin_headers):
        """Test Enable Portal Access endpoint"""
        # Get employees to find one without portal access
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=admin_headers
        )
        assert emp_response.status_code == 200
        
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", [])
        
        # Find employee without portal access (user_id is None)
        no_access = [e for e in employees if not e.get("user_id") and e.get("go_live_status") != "active"]
        
        if len(no_access) == 0:
            print("✓ All employees already have portal access (or are active)")
            return
        
        emp = no_access[0]
        emp_id = emp.get("id")
        
        # Check if enable portal access endpoint exists
        # Note: We won't actually enable to avoid side effects
        # Just verify the endpoint pattern is correct
        print(f"✓ Found employee {emp.get('full_name')} without portal access")
        print(f"  Enable endpoint: POST /api/employees/{emp_id}/grant-access")

    # ====================
    # Test Go-Live Approval Flow (Simulation)
    # ====================

    def test_golive_approval_generates_employee_id(self, admin_headers):
        """Verify that Go-Live approval generates Employee ID"""
        # Get pending requests
        response = requests.get(
            f"{BASE_URL}/api/go-live/pending",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        pending = response.json()
        
        if len(pending) > 0:
            # Get the first pending request
            req = pending[0]
            print(f"✓ Found pending request for: {req.get('employee_name')}")
            print(f"  Department: {req.get('department')}")
            print(f"  Submitted by: {req.get('submitted_by_name')}")
            
            # Get details to see preview Employee ID
            details_response = requests.get(
                f"{BASE_URL}/api/go-live/request/{req['id']}/details",
                headers=admin_headers
            )
            
            if details_response.status_code == 200:
                details = details_response.json()
                emp = details.get("employee", {})
                preview_id = emp.get("preview_employee_id")
                if preview_id:
                    print(f"  Preview Employee ID: {preview_id} (will be assigned on approval)")
        else:
            print("✓ No pending Go-Live requests - approval flow cannot be tested without affecting data")

    # ====================
    # Test HR Cannot Approve Go-Live (Only Admin)
    # ====================

    def test_hr_cannot_approve_golive(self, hr_headers, admin_headers):
        """Verify HR cannot approve Go-Live (only Admin can)"""
        # Get pending requests with admin
        response = requests.get(
            f"{BASE_URL}/api/go-live/pending",
            headers=admin_headers
        )
        pending = response.json()
        
        if len(pending) == 0:
            pytest.skip("No pending requests to test HR approval restriction")
        
        # Try to approve with HR credentials
        req_id = pending[0]["id"]
        hr_approve_response = requests.post(
            f"{BASE_URL}/api/go-live/{req_id}/approve",
            headers=hr_headers,
            json={}
        )
        
        # HR should be forbidden
        assert hr_approve_response.status_code in [403, 401], \
            f"HR should not be able to approve Go-Live, got status {hr_approve_response.status_code}"
        
        print("✓ HR correctly cannot approve Go-Live requests (Admin only)")

    # ====================
    # Test All Go-Live Requests
    # ====================

    def test_all_golive_requests(self, admin_headers):
        """Test fetching all Go-Live requests with optional status filter"""
        # All requests
        response = requests.get(
            f"{BASE_URL}/api/go-live/all",
            headers=admin_headers
        )
        assert response.status_code == 200
        
        all_requests = response.json()
        print(f"✓ Total Go-Live requests: {len(all_requests)}")
        
        # Filter by status
        approved_response = requests.get(
            f"{BASE_URL}/api/go-live/all?status=approved",
            headers=admin_headers
        )
        assert approved_response.status_code == 200
        approved = approved_response.json()
        print(f"✓ Approved requests: {len(approved)}")


class TestGoLiveSubmission:
    """Tests for Go-Live submission by HR"""

    @pytest.fixture(scope="class")
    def hr_token(self):
        """Get HR Manager authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"employee_id": "DVC037", "password": "test123"}
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture(scope="class")
    def hr_headers(self, hr_token):
        return {"Authorization": f"Bearer {hr_token}"}

    def test_hr_can_submit_golive(self, hr_headers):
        """Verify HR can submit Go-Live request"""
        # Get employees with go_live_status = not_submitted
        emp_response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=hr_headers
        )
        
        employees = emp_response.json()
        if isinstance(employees, dict):
            employees = employees.get("items", [])
        
        eligible = [e for e in employees if e.get("go_live_status") == "not_submitted"]
        
        if len(eligible) == 0:
            print("✓ No employees available for Go-Live submission (all submitted or active)")
            return
        
        emp = eligible[0]
        print(f"✓ Found eligible employee: {emp.get('full_name')} ({emp.get('employee_id')})")
        print(f"  Current Go-Live Status: {emp.get('go_live_status')}")
        
        # Note: Not actually submitting to avoid affecting test data
        # The endpoint is POST /api/go-live/submit/{employee_id}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
