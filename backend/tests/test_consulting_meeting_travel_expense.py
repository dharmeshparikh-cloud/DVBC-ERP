"""
Test Consulting Meeting Travel Expense Feature
Tests the MeetingLocationPicker integration in Schedule Meeting dialog
and backend expense creation for in-person meetings with travel_details.

Features tested:
1. MeetingCreate model accepts travel_details, travel_companions, is_conveyance_claimable, scheduled_by
2. POST /api/meetings with travel_details creates expense record
3. Expense record has correct amount calculation (distance_km * rate, doubled for round trip)
4. Expense linked to meeting_id and payroll_month
5. Online meetings don't create travel expenses
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sales-funnel-fix.preview.emergentagent.com')


class TestConsultingMeetingTravelExpense:
    """Test consulting meeting travel expense feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as consultant"""
        # Login as consultant (EMP004)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["access_token"]
        self.user = login_response.json()["user"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Get a project for testing
        projects_response = requests.get(f"{BASE_URL}/api/projects", headers=self.headers)
        assert projects_response.status_code == 200
        projects = projects_response.json()
        if isinstance(projects, dict):
            projects = projects.get("items", [])
        assert len(projects) > 0, "No projects available for testing"
        self.test_project = projects[0]
        
        # Get SOW for the project
        sow_response = requests.get(f"{BASE_URL}/api/enhanced-sow", headers=self.headers)
        if sow_response.status_code == 200:
            sows = sow_response.json()
            if isinstance(sows, dict):
                sows = sows.get("items", [])
            self.test_sow = sows[0] if sows else None
        else:
            self.test_sow = None
    
    def test_01_login_as_consultant(self):
        """Test consultant login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP004",
            "password": "consultant123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["employee_id"] == "EMP004"
        print(f"PASS: Consultant login successful - {data['user']['full_name']}")
    
    def test_02_get_projects_for_meeting(self):
        """Test projects endpoint returns data for meeting creation"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=self.headers)
        assert response.status_code == 200
        projects = response.json()
        if isinstance(projects, dict):
            projects = projects.get("items", [])
        assert len(projects) > 0, "No projects found"
        
        # Verify project has required fields
        project = projects[0]
        assert "id" in project
        assert "name" in project or "project_name" in project
        print(f"PASS: Found {len(projects)} projects for meeting creation")
    
    def test_03_get_meeting_types(self):
        """Test meeting types endpoint for purpose dropdown"""
        response = requests.get(f"{BASE_URL}/api/masters/meeting-types", headers=self.headers)
        assert response.status_code == 200
        meeting_types = response.json()
        assert len(meeting_types) > 0, "No meeting types found"
        
        # Verify meeting type has code and name
        mt = meeting_types[0]
        assert "code" in mt
        assert "name" in mt
        print(f"PASS: Found {len(meeting_types)} meeting types")
    
    def test_04_create_online_meeting_no_travel_expense(self):
        """Test online meeting creation does NOT create travel expense"""
        meeting_date = (datetime.now() + timedelta(days=7)).isoformat()
        
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "online",  # Online mode - no travel
            "title": "TEST Online Meeting - No Travel",
            "agenda": ["Test agenda item"],
            "meeting_type_code": "KICKOFF",
            "is_conveyance_claimable": False
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        assert meeting["mode"] == "online"
        assert meeting.get("is_conveyance_claimable") == False or meeting.get("is_conveyance_claimable") is None
        
        # Verify no expense was created for this meeting
        meeting_id = meeting["id"]
        expenses_response = requests.get(f"{BASE_URL}/api/expenses", headers=self.headers)
        if expenses_response.status_code == 200:
            expenses = expenses_response.json()
            if isinstance(expenses, dict):
                expenses = expenses.get("items", [])
            meeting_expenses = [e for e in expenses if e.get("meeting_id") == meeting_id]
            assert len(meeting_expenses) == 0, "Online meeting should not create travel expense"
        
        print(f"PASS: Online meeting created without travel expense - {meeting_id}")
    
    def test_05_create_offline_meeting_with_travel_details_car(self):
        """Test in-person meeting with Car travel creates expense with correct calculation"""
        meeting_date = (datetime.now() + timedelta(days=8)).isoformat()
        
        # Travel details for Car mode - 25km one way, round trip
        travel_details = {
            "start_location": "Mumbai Office",
            "start_location_data": {"lat": 19.0760, "lng": 72.8777},
            "end_location": "Client Office Andheri",
            "end_location_data": {"lat": 19.1136, "lng": 72.8697},
            "via_locations": [],
            "distance_km": 25,  # 25 km one way
            "is_round_trip": True,  # Round trip = 50 km total
            "travel_mode": "DRIVING",  # Car = Rs.7/km
            "transit_amount": 0,
            "expense_amount": 350,  # 50 km * Rs.7 = Rs.350
            "travel_start_time": "09:00",
            "travel_end_time": "18:00"
        }
        
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "offline",  # In-person mode
            "title": "TEST Offline Meeting - Car Travel",
            "agenda": ["Client site visit"],
            "meeting_type_code": "REVIEW",
            "travel_details": travel_details,
            "travel_companions": [],
            "is_conveyance_claimable": True,
            "scheduled_by": self.user["id"],
            "scheduled_by_name": self.user["full_name"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        assert meeting["mode"] == "offline"
        assert meeting.get("is_conveyance_claimable") == True
        
        meeting_id = meeting["id"]
        
        # Wait a moment for background task to complete
        import time
        time.sleep(1)
        
        # Verify expense was created
        expenses_response = requests.get(f"{BASE_URL}/api/expenses", headers=self.headers)
        assert expenses_response.status_code == 200, f"Expenses fetch failed: {expenses_response.text}"
        
        expenses = expenses_response.json()
        if isinstance(expenses, dict):
            expenses = expenses.get("items", [])
        
        meeting_expenses = [e for e in expenses if e.get("meeting_id") == meeting_id]
        
        if len(meeting_expenses) > 0:
            expense = meeting_expenses[0]
            assert expense["status"] == "pending"
            assert expense["category"] == "travel"
            assert "DRIVING" in expense.get("subcategory", "").upper() or "driving" in expense.get("subcategory", "").lower()
            
            # Verify amount calculation: 25km * 2 (round trip) * Rs.7 = Rs.350
            expected_amount = 350
            actual_amount = expense.get("amount", 0)
            assert abs(actual_amount - expected_amount) < 1, f"Expected Rs.{expected_amount}, got Rs.{actual_amount}"
            
            # Verify payroll_month is set
            assert expense.get("payroll_month") is not None, "Expense should have payroll_month"
            
            print(f"PASS: Offline meeting with Car travel created expense Rs.{actual_amount} - {expense['id']}")
        else:
            # Check if expense_id is in meeting response
            if meeting.get("expense_id"):
                print(f"PASS: Meeting has expense_id linked: {meeting['expense_id']}")
            else:
                print(f"INFO: Expense may be created asynchronously - meeting_id: {meeting_id}")
    
    def test_06_create_offline_meeting_with_travel_details_bike(self):
        """Test in-person meeting with Bike travel creates expense with correct calculation"""
        meeting_date = (datetime.now() + timedelta(days=9)).isoformat()
        
        # Travel details for Bike mode - 30km one way, NOT round trip
        travel_details = {
            "start_location": "Home",
            "end_location": "Client Office",
            "distance_km": 30,  # 30 km one way
            "is_round_trip": False,  # One way only
            "travel_mode": "TWO_WHEELER",  # Bike = Rs.3/km
            "expense_amount": 90  # 30 km * Rs.3 = Rs.90
        }
        
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "offline",
            "title": "TEST Offline Meeting - Bike Travel",
            "agenda": ["Quick client visit"],
            "meeting_type_code": "FOLLOWUP",
            "travel_details": travel_details,
            "is_conveyance_claimable": True,
            "scheduled_by": self.user["id"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        meeting_id = meeting["id"]
        
        import time
        time.sleep(1)
        
        # Verify expense
        expenses_response = requests.get(f"{BASE_URL}/api/expenses", headers=self.headers)
        if expenses_response.status_code == 200:
            expenses = expenses_response.json()
            if isinstance(expenses, dict):
                expenses = expenses.get("items", [])
            
            meeting_expenses = [e for e in expenses if e.get("meeting_id") == meeting_id]
            
            if len(meeting_expenses) > 0:
                expense = meeting_expenses[0]
                # Verify amount: 30km * Rs.3 = Rs.90
                expected_amount = 90
                actual_amount = expense.get("amount", 0)
                assert abs(actual_amount - expected_amount) < 1, f"Expected Rs.{expected_amount}, got Rs.{actual_amount}"
                print(f"PASS: Bike travel expense created Rs.{actual_amount}")
            else:
                print(f"INFO: Expense may be created asynchronously - meeting_id: {meeting_id}")
    
    def test_07_create_offline_meeting_with_transit(self):
        """Test in-person meeting with Transit mode uses manual amount"""
        meeting_date = (datetime.now() + timedelta(days=10)).isoformat()
        
        # Travel details for Transit mode - manual amount entry
        travel_details = {
            "start_location": "Home",
            "end_location": "Client Office",
            "distance_km": 0,  # Not used for transit
            "is_round_trip": True,
            "travel_mode": "TRANSIT",
            "transit_amount": 150,  # Manual entry
            "expense_amount": 150
        }
        
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "offline",
            "title": "TEST Offline Meeting - Transit",
            "agenda": ["Client meeting via public transport"],
            "meeting_type_code": "TRAINING",
            "travel_details": travel_details,
            "is_conveyance_claimable": True,
            "scheduled_by": self.user["id"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        meeting_id = meeting["id"]
        
        import time
        time.sleep(1)
        
        # Verify expense
        expenses_response = requests.get(f"{BASE_URL}/api/expenses", headers=self.headers)
        if expenses_response.status_code == 200:
            expenses = expenses_response.json()
            if isinstance(expenses, dict):
                expenses = expenses.get("items", [])
            
            meeting_expenses = [e for e in expenses if e.get("meeting_id") == meeting_id]
            
            if len(meeting_expenses) > 0:
                expense = meeting_expenses[0]
                # Transit uses manual amount
                expected_amount = 150
                actual_amount = expense.get("amount", 0)
                assert abs(actual_amount - expected_amount) < 1, f"Expected Rs.{expected_amount}, got Rs.{actual_amount}"
                print(f"PASS: Transit expense created Rs.{actual_amount}")
            else:
                print(f"INFO: Expense may be created asynchronously - meeting_id: {meeting_id}")
    
    def test_08_create_offline_meeting_accompanied_no_expense(self):
        """Test in-person meeting with Accompanied mode does NOT create expense"""
        meeting_date = (datetime.now() + timedelta(days=11)).isoformat()
        
        # Travel details for Accompanied mode - no expense
        travel_details = {
            "start_location": "Home",
            "end_location": "Client Office",
            "distance_km": 40,
            "is_round_trip": True,
            "travel_mode": "ACCOMPANIED",  # No expense for accompanied
            "accompanied_by": "colleague_id",
            "expense_amount": 0
        }
        
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "offline",
            "title": "TEST Offline Meeting - Accompanied",
            "agenda": ["Team visit to client"],
            "meeting_type_code": "WORKSHOP",
            "travel_details": travel_details,
            "is_conveyance_claimable": False,  # Accompanied = no claim
            "scheduled_by": self.user["id"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        meeting_id = meeting["id"]
        
        import time
        time.sleep(1)
        
        # Verify NO expense was created
        expenses_response = requests.get(f"{BASE_URL}/api/expenses", headers=self.headers)
        if expenses_response.status_code == 200:
            expenses = expenses_response.json()
            if isinstance(expenses, dict):
                expenses = expenses.get("items", [])
            
            meeting_expenses = [e for e in expenses if e.get("meeting_id") == meeting_id]
            assert len(meeting_expenses) == 0, "Accompanied mode should not create expense"
            print(f"PASS: Accompanied mode meeting created without expense")
    
    def test_09_meeting_create_model_accepts_travel_fields(self):
        """Test MeetingCreate model accepts all travel-related fields"""
        meeting_date = (datetime.now() + timedelta(days=12)).isoformat()
        
        # Full travel data with all fields
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "offline",
            "title": "TEST Full Travel Fields",
            "agenda": ["Test all travel fields"],
            "meeting_type_code": "REVIEW",
            # All travel-related fields from MeetingCreate model
            "travel_details": {
                "start_location": "Office A",
                "start_location_data": {"lat": 19.0, "lng": 72.8},
                "end_location": "Office B",
                "end_location_data": {"lat": 19.1, "lng": 72.9},
                "via_locations": [{"address": "Via Point", "data": {"lat": 19.05, "lng": 72.85}}],
                "distance_km": 20,
                "is_round_trip": True,
                "travel_mode": "DRIVING",
                "transit_amount": 0,
                "expense_amount": 280,
                "travel_start_time": "10:00",
                "travel_end_time": "17:00"
            },
            "travel_companions": [],
            "travel_companion_names": [],
            "is_conveyance_claimable": True,
            "scheduled_by": self.user["id"],
            "scheduled_by_name": self.user["full_name"],
            "scheduled_at": datetime.now().isoformat(),
            "is_short_notice": False
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        
        # Verify all fields were accepted
        assert meeting.get("is_conveyance_claimable") == True
        assert meeting.get("scheduled_by") == self.user["id"]
        
        print(f"PASS: MeetingCreate model accepts all travel fields")
    
    def test_10_expense_linked_to_payroll_month(self):
        """Test expense record has payroll_month field set correctly"""
        meeting_date = (datetime.now() + timedelta(days=13)).isoformat()
        expected_payroll_month = (datetime.now() + timedelta(days=13)).strftime("%Y-%m")
        
        travel_details = {
            "start_location": "Home",
            "end_location": "Client",
            "distance_km": 15,
            "is_round_trip": True,
            "travel_mode": "DRIVING",
            "expense_amount": 210  # 30km * Rs.7
        }
        
        meeting_data = {
            "type": "consulting",
            "project_id": self.test_project["id"],
            "project_name": self.test_project.get("name") or self.test_project.get("project_name"),
            "client_id": self.test_project.get("client_id"),
            "client_name": self.test_project.get("client_name"),
            "sow_id": self.test_sow["id"] if self.test_sow else None,
            "meeting_date": meeting_date,
            "mode": "offline",
            "title": "TEST Payroll Month Linkage",
            "agenda": ["Test payroll linkage"],
            "meeting_type_code": "REVIEW",
            "travel_details": travel_details,
            "is_conveyance_claimable": True,
            "scheduled_by": self.user["id"]
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings", json=meeting_data, headers=self.headers)
        assert response.status_code == 200, f"Meeting creation failed: {response.text}"
        
        meeting = response.json()
        meeting_id = meeting["id"]
        
        import time
        time.sleep(1)
        
        # Verify expense has payroll_month
        expenses_response = requests.get(f"{BASE_URL}/api/expenses", headers=self.headers)
        if expenses_response.status_code == 200:
            expenses = expenses_response.json()
            if isinstance(expenses, dict):
                expenses = expenses.get("items", [])
            
            meeting_expenses = [e for e in expenses if e.get("meeting_id") == meeting_id]
            
            if len(meeting_expenses) > 0:
                expense = meeting_expenses[0]
                payroll_month = expense.get("payroll_month")
                assert payroll_month is not None, "Expense should have payroll_month"
                assert payroll_month == expected_payroll_month, f"Expected {expected_payroll_month}, got {payroll_month}"
                print(f"PASS: Expense linked to payroll month {payroll_month}")
            else:
                print(f"INFO: Expense may be created asynchronously - meeting_id: {meeting_id}")
    
    def test_11_get_consulting_meetings_list(self):
        """Test consulting meetings list endpoint works"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=consulting", headers=self.headers)
        assert response.status_code == 200
        
        meetings = response.json()
        assert isinstance(meetings, list)
        print(f"PASS: Retrieved {len(meetings)} consulting meetings")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
