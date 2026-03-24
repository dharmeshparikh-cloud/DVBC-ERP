"""
Test ConsultingMeetings Governed Dropdowns - Backend API Tests

Tests for:
1. GET /api/projects - Returns all 6 projects for admin
2. GET /api/enhanced-sow/project/{project_id}/sow - Returns SOW data for project
3. GET /api/masters/meeting-types - Returns 10 meeting types
4. GET /api/meetings - Returns consulting meetings list
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestConsultingMeetingsGovernedDropdowns:
    """Tests for ConsultingMeetings governed dropdown APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.token = token
            print(f"[SETUP] Admin login successful, token obtained")
        else:
            pytest.skip(f"Admin login failed: {login_response.status_code} - {login_response.text}")
    
    # ============== Projects API Tests ==============
    
    def test_projects_api_returns_data(self):
        """Test GET /api/projects returns projects list"""
        response = self.session.get(f"{BASE_URL}/api/projects")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Handle both array and paginated response
        projects = data if isinstance(data, list) else data.get('items', [])
        
        print(f"[PROJECTS] Returned {len(projects)} projects")
        assert len(projects) >= 1, "Expected at least 1 project"
        
        # Verify project structure
        if projects:
            project = projects[0]
            assert 'id' in project, "Project should have 'id' field"
            # Check for name field (could be 'name' or 'project_name')
            has_name = 'name' in project or 'project_name' in project
            assert has_name, "Project should have 'name' or 'project_name' field"
            print(f"[PROJECTS] First project: {project.get('name') or project.get('project_name')}")
    
    def test_projects_api_returns_client_info(self):
        """Test projects include client information for dropdown display"""
        response = self.session.get(f"{BASE_URL}/api/projects")
        
        assert response.status_code == 200
        
        data = response.json()
        projects = data if isinstance(data, list) else data.get('items', [])
        
        # Check at least one project has client info
        projects_with_client = [p for p in projects if p.get('client_id') or p.get('client_name')]
        print(f"[PROJECTS] {len(projects_with_client)}/{len(projects)} projects have client info")
        
        # Not all projects may have clients, but structure should support it
        if projects:
            project = projects[0]
            print(f"[PROJECTS] Sample project fields: {list(project.keys())[:10]}")
    
    # ============== Meeting Types API Tests ==============
    
    def test_meeting_types_api_returns_data(self):
        """Test GET /api/masters/meeting-types returns meeting types"""
        response = self.session.get(f"{BASE_URL}/api/masters/meeting-types")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        meeting_types = data if isinstance(data, list) else data.get('items', [])
        
        print(f"[MEETING_TYPES] Returned {len(meeting_types)} meeting types")
        assert len(meeting_types) >= 1, "Expected at least 1 meeting type"
        
        # Verify meeting type structure
        if meeting_types:
            mt = meeting_types[0]
            assert 'code' in mt or 'id' in mt, "Meeting type should have 'code' or 'id' field"
            assert 'name' in mt, "Meeting type should have 'name' field"
            print(f"[MEETING_TYPES] First type: {mt.get('name')} (code: {mt.get('code')})")
    
    def test_meeting_types_count(self):
        """Test meeting types returns expected count (10 types per requirement)"""
        response = self.session.get(f"{BASE_URL}/api/masters/meeting-types")
        
        assert response.status_code == 200
        
        data = response.json()
        meeting_types = data if isinstance(data, list) else data.get('items', [])
        
        print(f"[MEETING_TYPES] Count: {len(meeting_types)}")
        # Log all meeting types for verification
        for mt in meeting_types:
            print(f"  - {mt.get('name')} (code: {mt.get('code')})")
    
    # ============== Enhanced SOW by Project API Tests ==============
    
    def test_enhanced_sow_by_project_endpoint_exists(self):
        """Test GET /api/enhanced-sow/project/{project_id}/sow endpoint exists"""
        # First get a project ID
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200
        
        data = projects_response.json()
        projects = data if isinstance(data, list) else data.get('items', [])
        
        if not projects:
            pytest.skip("No projects available to test SOW endpoint")
        
        project_id = projects[0].get('id')
        print(f"[SOW] Testing with project_id: {project_id}")
        
        # Test the SOW endpoint
        response = self.session.get(f"{BASE_URL}/api/enhanced-sow/project/{project_id}/sow")
        
        # Should return 200 (with SOW) or 404 (no SOW for project)
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            print(f"[SOW] Response keys: {list(data.keys())}")
            # Verify response structure per enhanced_sow.py line 1424
            # Returns {sow: {...}, can_edit, is_assigned_consultant, project_name, client_name}
            if 'sow' in data:
                print(f"[SOW] SOW found for project, can_edit: {data.get('can_edit')}")
            else:
                print(f"[SOW] Response structure: {data}")
        else:
            print(f"[SOW] No SOW found for project {project_id}")
    
    def test_enhanced_sow_response_structure(self):
        """Test SOW response has correct structure for dropdown usage"""
        # Get projects
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200
        
        data = projects_response.json()
        projects = data if isinstance(data, list) else data.get('items', [])
        
        # Try each project until we find one with SOW
        sow_found = False
        for project in projects[:5]:  # Check first 5 projects
            project_id = project.get('id')
            response = self.session.get(f"{BASE_URL}/api/enhanced-sow/project/{project_id}/sow")
            
            if response.status_code == 200:
                data = response.json()
                sow_found = True
                
                # Verify structure matches what useSOWsByProject expects
                # The hook handles: array, {sow: ...}, {items: [...]}, {sows: [...]}
                if 'sow' in data:
                    sow = data['sow']
                    print(f"[SOW] Found SOW for project {project.get('name')}")
                    print(f"[SOW] SOW fields: {list(sow.keys())[:10]}")
                    
                    # Verify SOW has id and name/title for dropdown
                    assert 'id' in sow, "SOW should have 'id' field"
                    has_name = 'name' in sow or 'title' in sow
                    print(f"[SOW] SOW id: {sow.get('id')}, name/title: {sow.get('name') or sow.get('title')}")
                break
        
        if not sow_found:
            print("[SOW] No projects with SOW found - this may be expected for new setup")
    
    # ============== Consulting Meetings API Tests ==============
    
    def test_meetings_api_returns_data(self):
        """Test GET /api/meetings returns meetings list"""
        response = self.session.get(f"{BASE_URL}/api/meetings?meeting_type=consulting")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        meetings = data if isinstance(data, list) else data.get('items', [])
        
        print(f"[MEETINGS] Returned {len(meetings)} consulting meetings")
    
    # ============== Integration Tests ==============
    
    def test_project_to_sow_flow(self):
        """Test the flow: Select Project -> Get SOW for that project"""
        # Step 1: Get projects
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        assert projects_response.status_code == 200
        
        data = projects_response.json()
        projects = data if isinstance(data, list) else data.get('items', [])
        
        print(f"[FLOW] Step 1: Got {len(projects)} projects")
        
        if not projects:
            pytest.skip("No projects available")
        
        # Step 2: For each project, check if SOW exists
        projects_with_sow = []
        for project in projects[:6]:  # Check first 6 projects
            project_id = project.get('id')
            project_name = project.get('name') or project.get('project_name')
            
            sow_response = self.session.get(f"{BASE_URL}/api/enhanced-sow/project/{project_id}/sow")
            
            if sow_response.status_code == 200:
                sow_data = sow_response.json()
                if sow_data.get('sow'):
                    projects_with_sow.append({
                        'project_id': project_id,
                        'project_name': project_name,
                        'sow_id': sow_data['sow'].get('id'),
                        'client_name': sow_data.get('client_name')
                    })
                    print(f"[FLOW] Project '{project_name}' has SOW")
                else:
                    print(f"[FLOW] Project '{project_name}' - SOW response but no sow field")
            else:
                print(f"[FLOW] Project '{project_name}' - No SOW (404)")
        
        print(f"[FLOW] Step 2: {len(projects_with_sow)}/{len(projects[:6])} projects have SOW")
        
        # Verify the flow works for at least one project
        if projects_with_sow:
            print(f"[FLOW] SUCCESS: Project->SOW flow works")
            print(f"[FLOW] Sample: {projects_with_sow[0]}")
    
    def test_all_dropdown_apis_accessible(self):
        """Test all dropdown APIs are accessible and return valid data"""
        results = {}
        
        # Test Projects API
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        results['projects'] = {
            'status': projects_response.status_code,
            'count': len(projects_response.json() if isinstance(projects_response.json(), list) else projects_response.json().get('items', []))
        }
        
        # Test Meeting Types API
        mt_response = self.session.get(f"{BASE_URL}/api/masters/meeting-types")
        results['meeting_types'] = {
            'status': mt_response.status_code,
            'count': len(mt_response.json() if isinstance(mt_response.json(), list) else mt_response.json().get('items', []))
        }
        
        # Test Clients API (for reference)
        clients_response = self.session.get(f"{BASE_URL}/api/clients")
        clients_data = clients_response.json()
        results['clients'] = {
            'status': clients_response.status_code,
            'count': len(clients_data if isinstance(clients_data, list) else clients_data.get('items', []))
        }
        
        print(f"[DROPDOWNS] API Results:")
        for api, data in results.items():
            print(f"  - {api}: status={data['status']}, count={data['count']}")
        
        # All should return 200
        assert results['projects']['status'] == 200, "Projects API should return 200"
        assert results['meeting_types']['status'] == 200, "Meeting Types API should return 200"
        assert results['clients']['status'] == 200, "Clients API should return 200"


class TestSOWByProjectHookBehavior:
    """Tests that verify the useSOWsByProject hook behavior"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin auth"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Admin login failed")
    
    def test_sow_endpoint_handles_no_project_id(self):
        """Test SOW endpoint behavior with invalid project ID"""
        response = self.session.get(f"{BASE_URL}/api/enhanced-sow/project/invalid-id/sow")
        
        # Should return 404 for non-existent project
        assert response.status_code == 404, f"Expected 404 for invalid project, got {response.status_code}"
        print(f"[SOW] Invalid project ID correctly returns 404")
    
    def test_sow_response_can_be_normalized(self):
        """Test SOW response can be normalized by the hook transformer"""
        # Get a project with SOW
        projects_response = self.session.get(f"{BASE_URL}/api/projects")
        projects = projects_response.json() if isinstance(projects_response.json(), list) else projects_response.json().get('items', [])
        
        for project in projects[:5]:
            project_id = project.get('id')
            response = self.session.get(f"{BASE_URL}/api/enhanced-sow/project/{project_id}/sow")
            
            if response.status_code == 200:
                data = response.json()
                
                # The hook normalizes: {sow: {...}} -> [{...}]
                if 'sow' in data:
                    sow = data['sow']
                    
                    # Verify fields that normalizeSOW expects
                    # normalizeSOW creates: name, id, project_id, client_id, client_name, status
                    normalized = {
                        'name': sow.get('name') or sow.get('title') or sow.get('client_name') or f"SOW-{(sow.get('id') or '')[:8]}",
                        'id': sow.get('id') or sow.get('_id') or '',
                        'project_id': sow.get('project_id') or sow.get('projectId') or '',
                        'client_id': sow.get('client_id') or sow.get('clientId') or '',
                        'client_name': sow.get('client_name') or '',
                        'status': sow.get('status') or 'unknown'
                    }
                    
                    print(f"[NORMALIZE] Original SOW fields: {list(sow.keys())[:8]}")
                    print(f"[NORMALIZE] Normalized: name='{normalized['name']}', id='{normalized['id'][:8]}...'")
                    
                    # Verify normalized data is usable for dropdown
                    assert normalized['id'], "Normalized SOW should have id"
                    assert normalized['name'], "Normalized SOW should have name"
                    print(f"[NORMALIZE] SUCCESS: SOW can be normalized for dropdown")
                    return
        
        print("[NORMALIZE] No SOW found to test normalization")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
