"""
Backend Tests for Consulting Efforts Summary
Tests the efforts-summary API and meeting attendance APIs
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"employee_id": "EMP001", "password": "admin123"}


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_login_success(self):
        """Test admin login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        print("PASS: Login successful")


class TestEffortsSummaryAPI:
    """Tests for /api/stats/consulting/efforts-summary endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for API calls"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_efforts_summary_api_exists(self, auth_headers):
        """Test that efforts-summary API endpoint exists and returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting/efforts-summary",
            headers=auth_headers
        )
        assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
        print("PASS: Efforts summary API exists and returns 200")
    
    def test_efforts_summary_response_structure(self, auth_headers):
        """Test response structure contains all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting/efforts-summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Check summary section
        assert "summary" in data, "Missing 'summary' field"
        summary = data["summary"]
        assert "total_meetings" in summary, "Missing total_meetings"
        assert "delivered_meetings" in summary, "Missing delivered_meetings"
        assert "meetings_with_mom" in summary, "Missing meetings_with_mom"
        assert "meetings_with_attendance" in summary, "Missing meetings_with_attendance"
        assert "attendance_compliance_rate" in summary, "Missing attendance_compliance_rate"
        print(f"Summary: {summary}")
        
        # Check duration section
        assert "duration" in data, "Missing 'duration' field"
        assert "total_hours" in data["duration"], "Missing total_hours in duration"
        assert "average_minutes" in data["duration"], "Missing average_minutes in duration"
        print(f"Duration: {data['duration']}")
        
        # Check tasks section
        assert "tasks" in data, "Missing 'tasks' field"
        assert "completed" in data["tasks"], "Missing completed in tasks"
        assert "timely_delivery_rate" in data["tasks"], "Missing timely_delivery_rate in tasks"
        print(f"Tasks: {data['tasks']}")
        
        # Check by_consultant section
        assert "by_consultant" in data, "Missing 'by_consultant' field"
        print(f"By Consultant count: {len(data['by_consultant'])}")
        
        # Check by_project section
        assert "by_project" in data, "Missing 'by_project' field"
        print(f"By Project count: {len(data['by_project'])}")
        
        # Check by_client section
        assert "by_client" in data, "Missing 'by_client' field"
        print(f"By Client count: {len(data['by_client'])}")
        
        # Check expenses section
        assert "expenses" in data, "Missing 'expenses' field"
        assert "total" in data["expenses"], "Missing total in expenses"
        assert "approved" in data["expenses"], "Missing approved in expenses"
        assert "pending" in data["expenses"], "Missing pending in expenses"
        print(f"Expenses: {data['expenses']}")
        
        # Check payments section
        assert "payments" in data, "Missing 'payments' field"
        assert "total_invoiced" in data["payments"], "Missing total_invoiced in payments"
        assert "received" in data["payments"], "Missing received in payments"
        assert "overdue" in data["payments"], "Missing overdue in payments"
        assert "collection_rate" in data["payments"], "Missing collection_rate in payments"
        print(f"Payments: {data['payments']}")
        
        print("PASS: Response structure is correct")
    
    def test_efforts_summary_data_values(self, auth_headers):
        """Test that data values are reasonable"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting/efforts-summary",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        
        # Total meetings should be >= delivered + pending
        assert summary["total_meetings"] >= 0, "Total meetings should be >= 0"
        assert summary["delivered_meetings"] >= 0, "Delivered meetings should be >= 0"
        assert summary["delivered_meetings"] <= summary["total_meetings"], "Delivered <= Total"
        
        # Attendance compliance rate should be 0-100
        assert 0 <= summary["attendance_compliance_rate"] <= 100, "Compliance rate should be 0-100"
        
        # Collection rate should be 0-100
        assert 0 <= data["payments"]["collection_rate"] <= 100, "Collection rate should be 0-100"
        
        print("PASS: Data values are reasonable")
    
    def test_efforts_summary_with_project_filter(self, auth_headers):
        """Test filtering by project_id"""
        # First get list of projects
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting/efforts-summary",
            headers=auth_headers
        )
        data = response.json()
        
        if data["by_project"] and len(data["by_project"]) > 0:
            project_id = data["by_project"][0]["id"]
            
            # Now filter by this project
            filtered_response = requests.get(
                f"{BASE_URL}/api/stats/consulting/efforts-summary",
                headers=auth_headers,
                params={"project_id": project_id}
            )
            assert filtered_response.status_code == 200
            filtered_data = filtered_response.json()
            
            # Verify filter is applied
            assert "filters_applied" in filtered_data
            assert filtered_data["filters_applied"]["project_id"] == project_id
            print(f"PASS: Project filter works for project {project_id}")
        else:
            print("SKIP: No projects to filter")
    
    def test_efforts_summary_with_date_filter(self, auth_headers):
        """Test filtering by date range"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting/efforts-summary",
            headers=auth_headers,
            params={
                "date_from": "2026-01-01",
                "date_to": "2026-12-31"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify filter is applied
        assert "filters_applied" in data
        assert data["filters_applied"]["date_from"] == "2026-01-01"
        assert data["filters_applied"]["date_to"] == "2026-12-31"
        print("PASS: Date filter works")
    
    def test_efforts_summary_unauthorized(self):
        """Test that unauthorized access is rejected"""
        response = requests.get(
            f"{BASE_URL}/api/stats/consulting/efforts-summary"
        )
        assert response.status_code == 401 or response.status_code == 403, \
            f"Expected 401/403, got {response.status_code}"
        print("PASS: Unauthorized access rejected")


class TestMeetingAttendanceAPI:
    """Tests for /api/attendance/meeting/{meeting_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for API calls"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_meeting_attendance_get_nonexistent(self, auth_headers):
        """Test GET for meeting without attendance returns attendance_marked=false"""
        # Use a random meeting ID that likely has no attendance
        response = requests.get(
            f"{BASE_URL}/api/attendance/meeting/nonexistent-meeting-id",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "attendance_marked" in data
        assert data["attendance_marked"] == False
        print("PASS: GET meeting attendance returns attendance_marked=false for no attendance")
    
    def test_meeting_attendance_get_existing(self, auth_headers):
        """Test GET for a meeting that exists"""
        # First get a meeting ID from the meetings endpoint
        meetings_response = requests.get(
            f"{BASE_URL}/api/meetings",
            headers=auth_headers,
            params={"type": "consulting", "limit": 1}
        )
        
        if meetings_response.status_code == 200:
            meetings = meetings_response.json()
            if isinstance(meetings, list) and len(meetings) > 0:
                meeting_id = meetings[0]["id"]
                
                # Get attendance for this meeting
                response = requests.get(
                    f"{BASE_URL}/api/attendance/meeting/{meeting_id}",
                    headers=auth_headers
                )
                assert response.status_code == 200
                data = response.json()
                assert "attendance_marked" in data
                print(f"PASS: GET meeting attendance returns attendance_marked={data['attendance_marked']}")
            else:
                print("SKIP: No consulting meetings found")
        else:
            print(f"SKIP: Could not get meetings list: {meetings_response.status_code}")
    
    def test_meeting_attendance_post_validation(self, auth_headers):
        """Test POST validation for meeting attendance"""
        # Try to post attendance without required fields
        response = requests.post(
            f"{BASE_URL}/api/attendance/meeting/test-meeting-id",
            headers=auth_headers,
            json={}  # Missing required fields
        )
        assert response.status_code == 400 or response.status_code == 404, \
            f"Expected 400/404, got {response.status_code}"
        print("PASS: POST attendance validates required fields")
    
    def test_meeting_attendance_unauthorized(self):
        """Test that unauthorized access is rejected"""
        response = requests.get(
            f"{BASE_URL}/api/attendance/meeting/test-meeting-id"
        )
        assert response.status_code == 401 or response.status_code == 403, \
            f"Expected 401/403, got {response.status_code}"
        print("PASS: Meeting attendance API rejects unauthorized access")


class TestFilterAPIs:
    """Tests for filter data APIs (projects, consultants, clients)"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for API calls"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=ADMIN_CREDENTIALS
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_projects_api_exists(self, auth_headers):
        """Test that projects API exists for filter dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Projects API should return a list"
        print(f"PASS: Projects API returns {len(data)} projects")
    
    def test_clients_api_exists(self, auth_headers):
        """Test that clients API exists for filter dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/clients",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Could be list or object with items
        if isinstance(data, dict):
            assert "items" in data or len(data) > 0
            print(f"PASS: Clients API returns data")
        else:
            print(f"PASS: Clients API returns {len(data)} clients")
    
    def test_employees_api_exists(self, auth_headers):
        """Test that employees API exists for consultant filter dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/employees/all",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Employees API should return a list"
        print(f"PASS: Employees API returns {len(data)} employees")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
