"""
Test Meeting Schedule APIs - Recurring meetings, calendar, notifications
Tests the Meeting Calendar feature: recurring schedules, calendar views, conflicts, notification preferences
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"employee_id": "ADMIN001", "password": "admin123"}


class TestMeetingScheduleAPIs:
    """Test Meeting Schedule endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for all tests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.user_id = response.json().get("user", {}).get("id")

    # ============== Stats Overview Tests ==============
    def test_stats_overview_endpoint(self):
        """Test GET /api/meeting-schedules/stats/overview returns stats"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/stats/overview",
            headers=self.headers
        )
        assert response.status_code == 200, f"Stats overview failed: {response.text}"
        data = response.json()
        
        # Verify required fields
        assert "active_schedules" in data
        assert "meetings_this_week" in data
        assert "delivered_this_week" in data
        assert "pending_mom" in data
        assert "total_conflicts" in data
        
        # Verify data types
        assert isinstance(data["active_schedules"], int)
        assert isinstance(data["meetings_this_week"], int)
        assert isinstance(data["delivered_this_week"], int)
        assert isinstance(data["pending_mom"], int)
        assert isinstance(data["total_conflicts"], int)
    
    # ============== Calendar Week Tests ==============
    def test_calendar_week_current(self):
        """Test GET /api/meeting-schedules/calendar/week for current week"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/calendar/week?week_offset=0",
            headers=self.headers
        )
        assert response.status_code == 200, f"Calendar week failed: {response.text}"
        data = response.json()
        
        # Verify week metadata
        assert "week_start" in data
        assert "week_end" in data
        assert "week_offset" in data
        assert data["week_offset"] == 0
        
        # Verify calendar structure
        assert "calendar" in data
        assert isinstance(data["calendar"], dict)
        
        # Verify weekdays list
        assert "weekdays" in data
        assert len(data["weekdays"]) == 7
        assert data["weekdays"][0] == "Monday"
    
    def test_calendar_week_previous(self):
        """Test GET /api/meeting-schedules/calendar/week for previous week"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/calendar/week?week_offset=-1",
            headers=self.headers
        )
        assert response.status_code == 200, f"Previous week failed: {response.text}"
        data = response.json()
        assert data["week_offset"] == -1
    
    def test_calendar_week_next(self):
        """Test GET /api/meeting-schedules/calendar/week for next week"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/calendar/week?week_offset=1",
            headers=self.headers
        )
        assert response.status_code == 200, f"Next week failed: {response.text}"
        data = response.json()
        assert data["week_offset"] == 1
    
    # ============== Conflicts Tests ==============
    def test_conflicts_all_endpoint(self):
        """Test GET /api/meeting-schedules/conflicts/all"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/conflicts/all",
            headers=self.headers
        )
        assert response.status_code == 200, f"Conflicts endpoint failed: {response.text}"
        data = response.json()
        
        assert "total_conflicts" in data
        assert "conflicts" in data
        assert isinstance(data["conflicts"], list)
    
    # ============== Notification Preferences Tests ==============
    def test_get_notification_preferences(self):
        """Test GET /api/meeting-schedules/notifications/preferences"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/notifications/preferences",
            headers=self.headers
        )
        assert response.status_code == 200, f"Get prefs failed: {response.text}"
        data = response.json()
        
        # Verify default structure
        assert "user_id" in data
        assert "meeting_reminders" in data
        
        reminders = data["meeting_reminders"]
        assert "enabled" in reminders
        assert "remind_24h" in reminders
        assert "remind_1h" in reminders
        assert "email" in reminders
    
    def test_update_notification_preferences(self):
        """Test PUT /api/meeting-schedules/notifications/preferences"""
        new_prefs = {
            "meeting_reminders": {
                "enabled": True,
                "remind_24h": False,
                "remind_1h": True,
                "email": True
            }
        }
        
        response = requests.put(
            f"{BASE_URL}/api/meeting-schedules/notifications/preferences",
            headers=self.headers,
            json=new_prefs
        )
        assert response.status_code == 200, f"Update prefs failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "preferences" in data
        
        # Verify update was persisted
        get_response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/notifications/preferences",
            headers=self.headers
        )
        assert get_response.status_code == 200
        updated_prefs = get_response.json()
        assert updated_prefs["meeting_reminders"]["remind_24h"] == False
    
    def test_toggle_all_reminders_off(self):
        """Test disabling all meeting reminders"""
        new_prefs = {
            "meeting_reminders": {
                "enabled": False,
                "remind_24h": False,
                "remind_1h": False,
                "email": False
            }
        }
        
        response = requests.put(
            f"{BASE_URL}/api/meeting-schedules/notifications/preferences",
            headers=self.headers,
            json=new_prefs
        )
        assert response.status_code == 200
        
        # Verify
        get_response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/notifications/preferences",
            headers=self.headers
        )
        data = get_response.json()
        assert data["meeting_reminders"]["enabled"] == False
        
        # Reset back to enabled
        reset_prefs = {
            "meeting_reminders": {
                "enabled": True,
                "remind_24h": True,
                "remind_1h": True,
                "email": True
            }
        }
        requests.put(
            f"{BASE_URL}/api/meeting-schedules/notifications/preferences",
            headers=self.headers,
            json=reset_prefs
        )
    
    # ============== Schedules List Tests ==============
    def test_list_schedules_empty(self):
        """Test GET /api/meeting-schedules returns list"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules",
            headers=self.headers
        )
        assert response.status_code == 200, f"List schedules failed: {response.text}"
        data = response.json()
        
        assert "schedules" in data
        assert "total" in data
        assert isinstance(data["schedules"], list)
    
    # ============== Weekday Options Tests ==============
    def test_weekday_options(self):
        """Test GET /api/meeting-schedules/options/weekdays"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/options/weekdays",
            headers=self.headers
        )
        assert response.status_code == 200, f"Weekday options failed: {response.text}"
        data = response.json()
        
        assert "weekdays" in data
        assert len(data["weekdays"]) == 7
        
        # Verify structure
        monday = data["weekdays"][0]
        assert "value" in monday
        assert "label" in monday
        assert monday["value"] == "monday"
        assert monday["label"] == "Monday"


class TestMeetingScheduleCreation:
    """Test creating and managing meeting schedules"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token and fetch required data"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Get a project and consultant for testing
        projects_resp = requests.get(f"{BASE_URL}/api/projects?status=active", headers=self.headers)
        self.project = None
        if projects_resp.status_code == 200:
            projects = projects_resp.json()
            if isinstance(projects, list) and len(projects) > 0:
                self.project = projects[0]
        
        users_resp = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        self.consultant = None
        if users_resp.status_code == 200:
            users = users_resp.json()
            for user in users:
                if user.get("role") in ["consultant", "principal_consultant", "senior_consultant"]:
                    self.consultant = user
                    break
    
    def test_create_schedule_validation_no_project(self):
        """Test schedule creation fails without project_id"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-schedules",
            headers=self.headers,
            json={
                "consultant_id": "some-id",
                "schedule_type": "fixed_day",
                "config": {"day": "monday", "time": "10:00"}
            }
        )
        assert response.status_code == 400
        assert "project_id" in response.json().get("detail", "").lower()
    
    def test_create_schedule_validation_invalid_type(self):
        """Test schedule creation fails with invalid schedule_type"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-schedules",
            headers=self.headers,
            json={
                "project_id": "some-project",
                "consultant_id": "some-consultant",
                "schedule_type": "invalid_type",
                "config": {}
            }
        )
        assert response.status_code == 400
        assert "schedule_type" in response.json().get("detail", "").lower()
    
    def test_create_fixed_day_schedule_validation(self):
        """Test fixed_day schedule requires day config"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-schedules",
            headers=self.headers,
            json={
                "project_id": "some-project",
                "consultant_id": "some-consultant",
                "schedule_type": "fixed_day",
                "config": {"time": "10:00"}  # Missing day
            }
        )
        assert response.status_code == 400
        assert "day" in response.json().get("detail", "").lower()
    
    def test_create_interval_schedule_validation(self):
        """Test interval schedule requires interval_days config"""
        response = requests.post(
            f"{BASE_URL}/api/meeting-schedules",
            headers=self.headers,
            json={
                "project_id": "some-project",
                "consultant_id": "some-consultant",
                "schedule_type": "interval",
                "config": {"preferred_time": "10:00"}  # Missing interval_days
            }
        )
        assert response.status_code == 400
        assert "interval_days" in response.json().get("detail", "").lower()


class TestCalendarTeamView:
    """Test team calendar endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_team_calendar_with_date_range(self):
        """Test GET /api/meeting-schedules/calendar/team with date range"""
        response = requests.get(
            f"{BASE_URL}/api/meeting-schedules/calendar/team?start_date=2026-03-01&end_date=2026-03-31",
            headers=self.headers
        )
        assert response.status_code == 200, f"Team calendar failed: {response.text}"
        data = response.json()
        
        assert "start_date" in data
        assert "end_date" in data
        assert "calendar" in data
        assert "total_meetings" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
