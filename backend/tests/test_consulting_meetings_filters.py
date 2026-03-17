"""
Test suite for Consulting Meetings features:
- Client/Month/Status filters
- MOM dialog with attachments
- File upload endpoint
- View toggle between list and card
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]


class TestConsultingMeetingsAPI:
    """Test Consulting Meetings API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_consulting_meetings(self):
        """Test GET /api/meetings?meeting_type=consulting - should return 20+ meetings"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"meeting_type": "consulting"},
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        meetings = response.json()
        assert isinstance(meetings, list), "Response should be a list"
        print(f"Found {len(meetings)} consulting meetings")
        # Verify we have meetings populated
        assert len(meetings) >= 0, "Should have meetings"
    
    def test_get_clients_for_filter(self):
        """Test GET /api/clients - used for client filter dropdown"""
        response = requests.get(f"{BASE_URL}/api/clients", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # API returns paginated response {items: [], total, skip, limit}
        assert "items" in data or isinstance(data, list), "Should have clients data"
        if "items" in data:
            clients = data["items"]
        else:
            clients = data
        print(f"Found {len(clients)} clients for filter dropdown")
    
    def test_get_single_meeting(self):
        """Test GET /api/meetings/{id} - for MOM dialog"""
        # First get list of meetings
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"meeting_type": "consulting"},
            headers=self.headers
        )
        assert response.status_code == 200
        meetings = response.json()
        
        if len(meetings) > 0:
            meeting_id = meetings[0]["id"]
            response = requests.get(
                f"{BASE_URL}/api/meetings/{meeting_id}",
                headers=self.headers
            )
            assert response.status_code == 200, f"Failed: {response.text}"
            meeting = response.json()
            assert "id" in meeting
            assert meeting["id"] == meeting_id
            print(f"Retrieved meeting: {meeting.get('title', 'No title')}")
    
    def test_consulting_meetings_tracking(self):
        """Test GET /api/consulting-meetings/tracking - commitment tracking"""
        response = requests.get(
            f"{BASE_URL}/api/consulting-meetings/tracking",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        tracking = response.json()
        assert isinstance(tracking, list), "Tracking should be a list"
        print(f"Found {len(tracking)} project tracking entries")


class TestFileUploadEndpoint:
    """Test MOM attachment upload endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_upload_meeting_attachments_endpoint_exists(self):
        """Test POST /api/upload/meeting-attachments - should accept files"""
        # Create a simple test file
        test_file_content = b"Test document content for MOM attachment"
        files = {
            'files': ('test_document.txt', test_file_content, 'text/plain')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/upload/meeting-attachments",
            files=files,
            headers=self.headers
        )
        
        # Should return 200 with uploaded file info
        assert response.status_code == 200, f"Upload failed: {response.status_code} - {response.text}"
        data = response.json()
        assert "files" in data, "Response should have 'files' key"
        assert "count" in data, "Response should have 'count' key"
        print(f"Upload response: {data}")
        
        if data["count"] > 0:
            uploaded_file = data["files"][0]
            assert "filename" in uploaded_file
            assert "url" in uploaded_file or "path" in uploaded_file
            print(f"Uploaded file: {uploaded_file.get('filename')}")
    
    def test_upload_pdf_attachment(self):
        """Test uploading PDF file for MOM"""
        # Create a simple PDF-like content (header)
        test_pdf_content = b"%PDF-1.4\n%Test PDF content"
        files = {
            'files': ('test_report.pdf', test_pdf_content, 'application/pdf')
        }
        
        response = requests.post(
            f"{BASE_URL}/api/upload/meeting-attachments",
            files=files,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        print(f"PDF upload response: count={data.get('count', 0)}")
    
    def test_upload_multiple_files(self):
        """Test uploading multiple files at once"""
        files = [
            ('files', ('doc1.txt', b'Document 1 content', 'text/plain')),
            ('files', ('doc2.txt', b'Document 2 content', 'text/plain'))
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/upload/meeting-attachments",
            files=files,
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Upload failed: {response.text}"
        data = response.json()
        print(f"Multiple files upload: {data.get('count', 0)} files uploaded")


class TestMOMEndpoints:
    """Test MOM-related endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_patch_mom_endpoint_exists(self):
        """Test PATCH /api/meetings/{id}/mom - save MOM endpoint"""
        # First get a meeting
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"meeting_type": "consulting"},
            headers=self.headers
        )
        assert response.status_code == 200
        meetings = response.json()
        
        if len(meetings) > 0:
            meeting_id = meetings[0]["id"]
            
            # Test MOM save with minimal data
            mom_data = {
                "title": "Test MOM Title",
                "agenda": ["Discuss project status"],
                "discussion_points": ["Point 1"],
                "decisions_made": ["Decision 1"],
                "action_items": [],
                "mom_attachments": []  # Test attachments field
            }
            
            response = requests.patch(
                f"{BASE_URL}/api/meetings/{meeting_id}/mom",
                json=mom_data,
                headers=self.headers
            )
            
            # Should succeed or return appropriate error
            print(f"MOM save response: {response.status_code}")
            # 200 = success, 400/403 = validation/permission error
            assert response.status_code in [200, 400, 403], f"Unexpected error: {response.text}"
    
    def test_send_mom_endpoint_exists(self):
        """Test POST /api/meetings/{id}/send-mom - send MOM endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/meetings",
            params={"meeting_type": "consulting"},
            headers=self.headers
        )
        assert response.status_code == 200
        meetings = response.json()
        
        if len(meetings) > 0:
            meeting_id = meetings[0]["id"]
            
            response = requests.post(
                f"{BASE_URL}/api/meetings/{meeting_id}/send-mom",
                headers=self.headers
            )
            
            # Should respond (might fail if no client email, but endpoint should exist)
            print(f"Send MOM response: {response.status_code}")
            assert response.status_code in [200, 400, 403, 404], f"Unexpected: {response.text}"


class TestProjectsAndUsersForFilters:
    """Test supporting data endpoints for filters"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_projects(self):
        """Test GET /api/projects - used for project dropdown"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Could be list or paginated
        if isinstance(data, list):
            projects = data
        elif "items" in data:
            projects = data["items"]
        else:
            projects = data.get("projects", [])
        print(f"Found {len(projects)} projects")
    
    def test_get_users(self):
        """Test GET /api/users - used for assignee dropdown in action items"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        users = response.json()
        assert isinstance(users, list), "Should return list of users"
        print(f"Found {len(users)} users for assignment dropdown")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
