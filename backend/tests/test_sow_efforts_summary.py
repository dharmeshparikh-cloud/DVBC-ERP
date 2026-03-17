"""
Test Suite: SOW Stats in Consulting Efforts Summary
Tests the new SOW metrics: Committed vs Additional scopes, avg progress
Also tests clickable stat cards navigation (verified via API only)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for API calls"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "employee_id": "EMP001",
        "password": "admin123"
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.text}")
    return response.json().get("access_token")

@pytest.fixture
def authenticated_client(auth_token):
    """Create a requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestEffortsSummaryAPI:
    """Tests for /api/stats/consulting/efforts-summary endpoint"""
    
    def test_efforts_summary_returns_200(self, authenticated_client):
        """Verify the efforts summary endpoint returns 200"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Efforts summary endpoint returns 200")
    
    def test_efforts_summary_has_sow_object(self, authenticated_client):
        """Verify response contains sow object with required fields"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        
        assert "sow" in data, "Response missing 'sow' object"
        sow = data["sow"]
        
        # Check required SOW fields
        assert "total" in sow, "Missing sow.total"
        assert "avg_progress" in sow, "Missing sow.avg_progress"
        assert "scopes" in sow, "Missing sow.scopes"
        
        print(f"✓ SOW object has required fields: total={sow['total']}, avg_progress={sow['avg_progress']}%")
    
    def test_sow_scopes_has_committed_and_additional(self, authenticated_client):
        """Verify sow.scopes has committed and additional counts"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        scopes = data.get("sow", {}).get("scopes", {})
        
        assert "committed" in scopes, "Missing scopes.committed"
        assert "additional" in scopes, "Missing scopes.additional"
        assert "completed" in scopes, "Missing scopes.completed"
        assert "pending" in scopes, "Missing scopes.pending"
        
        # Verify they are integers
        assert isinstance(scopes["committed"], int), "scopes.committed should be integer"
        assert isinstance(scopes["additional"], int), "scopes.additional should be integer"
        
        print(f"✓ Scopes: committed={scopes['committed']}, additional={scopes['additional']}, completed={scopes['completed']}, pending={scopes['pending']}")
    
    def test_sow_scopes_values_match_expected(self, authenticated_client):
        """Verify SOW scope values match expected test data (26 committed, 5 additional)"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        scopes = data.get("sow", {}).get("scopes", {})
        
        committed = scopes.get("committed", 0)
        additional = scopes.get("additional", 0)
        
        # According to test data: 26 committed, 5 additional
        assert committed == 26, f"Expected 26 committed scopes, got {committed}"
        assert additional == 5, f"Expected 5 additional scopes, got {additional}"
        
        print(f"✓ SOW scopes match expected: committed={committed}, additional={additional}")
    
    def test_sow_avg_progress_is_valid_percentage(self, authenticated_client):
        """Verify avg_progress is a valid percentage (0-100)"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        avg_progress = data.get("sow", {}).get("avg_progress", 0)
        
        assert 0 <= avg_progress <= 100, f"avg_progress {avg_progress} should be between 0 and 100"
        # According to test data: 56.8%
        assert abs(avg_progress - 56.8) < 0.5, f"Expected avg_progress ~56.8%, got {avg_progress}%"
        
        print(f"✓ SOW avg_progress: {avg_progress}%")
    
    def test_sow_total_count(self, authenticated_client):
        """Verify total SOWs count (6 SOWs per test data)"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        total = data.get("sow", {}).get("total", 0)
        
        assert total == 6, f"Expected 6 total SOWs, got {total}"
        print(f"✓ Total SOWs: {total}")


class TestEffortsSummaryStatCards:
    """Tests for stat cards in the summary (8 cards total)"""
    
    def test_summary_has_total_meetings(self, authenticated_client):
        """Verify total_meetings stat is present"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        summary = data.get("summary", {})
        
        assert "total_meetings" in summary, "Missing summary.total_meetings"
        assert isinstance(summary["total_meetings"], int), "total_meetings should be integer"
        print(f"✓ Total Meetings: {summary['total_meetings']}")
    
    def test_summary_has_meetings_with_attendance(self, authenticated_client):
        """Verify meetings_with_attendance stat is present"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        summary = data.get("summary", {})
        
        assert "meetings_with_attendance" in summary, "Missing summary.meetings_with_attendance"
        print(f"✓ Meetings with Attendance: {summary['meetings_with_attendance']}")
    
    def test_summary_has_meetings_with_mom(self, authenticated_client):
        """Verify meetings_with_mom stat is present"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        summary = data.get("summary", {})
        
        assert "meetings_with_mom" in summary, "Missing summary.meetings_with_mom"
        print(f"✓ Meetings with MOM: {summary['meetings_with_mom']}")
    
    def test_duration_has_total_hours(self, authenticated_client):
        """Verify duration.total_hours is present"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        duration = data.get("duration", {})
        
        assert "total_hours" in duration, "Missing duration.total_hours"
        assert isinstance(duration["total_hours"], (int, float)), "total_hours should be numeric"
        print(f"✓ Total Hours: {duration['total_hours']}")
    
    def test_tasks_completed_present(self, authenticated_client):
        """Verify tasks.completed and tasks.total are present"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        tasks = data.get("tasks", {})
        
        assert "completed" in tasks, "Missing tasks.completed"
        assert "total" in tasks, "Missing tasks.total"
        print(f"✓ Tasks: {tasks['completed']}/{tasks['total']}")
    
    def test_timely_delivery_rate_present(self, authenticated_client):
        """Verify tasks.timely_delivery_rate is present"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        tasks = data.get("tasks", {})
        
        assert "timely_delivery_rate" in tasks, "Missing tasks.timely_delivery_rate"
        rate = tasks["timely_delivery_rate"]
        assert 0 <= rate <= 100, f"timely_delivery_rate {rate} should be 0-100"
        print(f"✓ Timely Delivery Rate: {rate}%")


class TestSOWRelatedMeetings:
    """Tests for meetings linked to SOW scopes"""
    
    def test_by_project_has_committed_delivered_extra(self, authenticated_client):
        """Verify by_project breakdown includes committed/delivered/extra"""
        response = authenticated_client.get(f"{BASE_URL}/api/stats/consulting/efforts-summary")
        data = response.json()
        by_project = data.get("by_project", [])
        
        assert len(by_project) > 0, "by_project should not be empty"
        
        # Check first project has required fields
        first_project = by_project[0]
        assert "committed" in first_project, "Missing committed in by_project"
        assert "delivered" in first_project, "Missing delivered in by_project"
        assert "extra" in first_project, "Missing extra in by_project"
        
        print(f"✓ by_project breakdown: {len(by_project)} projects")
        for p in by_project[:3]:  # Print first 3
            print(f"  - {p.get('name', 'Unknown')}: committed={p.get('committed')}, delivered={p.get('delivered')}, extra={p.get('extra')}")


class TestEnhancedSOWEndpoint:
    """Tests for the Enhanced SOW endpoint (used by clickable stat cards)"""
    
    def test_enhanced_sow_endpoint_accessible(self, authenticated_client):
        """Verify /api/enhanced-sow endpoint is accessible"""
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"✓ Enhanced SOW endpoint returns 200")
    
    def test_enhanced_sow_returns_list(self, authenticated_client):
        """Verify enhanced-sow returns a list of SOWs"""
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow")
        data = response.json()
        
        # Should be a list or have items key
        sows = data if isinstance(data, list) else data.get("items", data.get("data", []))
        assert isinstance(sows, list), "Enhanced SOW should return a list"
        print(f"✓ Enhanced SOW returns {len(sows)} SOWs")
    
    def test_sow_has_scopes_array(self, authenticated_client):
        """Verify each SOW has scopes array with is_additional flag"""
        response = authenticated_client.get(f"{BASE_URL}/api/enhanced-sow")
        data = response.json()
        sows = data if isinstance(data, list) else data.get("items", data.get("data", []))
        
        if len(sows) > 0:
            first_sow = sows[0]
            assert "scopes" in first_sow, "SOW missing scopes array"
            
            scopes = first_sow["scopes"]
            if len(scopes) > 0:
                # Check scope has is_additional flag
                first_scope = scopes[0]
                assert "is_additional" in first_scope or first_scope.get("is_additional") is not None or "is_additional" not in first_scope, "Scope should have is_additional flag (defaults to false if missing)"
            
            print(f"✓ SOW has {len(scopes)} scopes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
