"""
Meeting Expense Claim Feature Tests
Tests the expense calculation for offline meetings with various travel modes:
- DRIVING: Rs.7/km
- TWO_WHEELER: Rs.3/km  
- TRANSIT: Manual entry with proof
- ACCOMPANIED: No expense created

Features tested:
1. POST /api/meetings/record creates expense automatically for travel modes
2. Expense amount calculated correctly for DRIVING (distance * 2 (if round trip) * 7)
3. Expense amount calculated correctly for TWO_WHEELER (distance * 2 (if round trip) * 3)
4. Transit mode uses manual transit_amount field
5. Accompanied mode does NOT create expense
6. Expense record linked to meeting and lead
7. Expense status is 'pending' for approval workflow
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SALES_CREDENTIALS = {
    "employee_id": "EMP003",
    "password": "Sales@123"
}

ADMIN_CREDENTIALS = {
    "employee_id": "ADMIN001", 
    "password": "Admin@2026"
}

# Test lead ID provided
TEST_LEAD_ID = "2e8724b1-b9b7-4983-b3cc-6c47e5de4851"


class TestMeetingExpenseClaim:
    """Test meeting expense claim feature for offline meetings"""
    
    @pytest.fixture(scope="class")
    def sales_token(self):
        """Authenticate as Sales Executive"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate as Sales Executive: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Authenticate as Admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate as Admin: {response.status_code} - {response.text}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def headers(self, sales_token):
        """Headers with auth token"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {sales_token}"
        }
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Admin headers with auth token"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {admin_token}"
        }
    
    def get_expense_for_meeting(self, meeting_id, headers):
        """Helper to get expense linked to a meeting by checking the meeting's expense_id"""
        # First get the meeting to find expense_id
        response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        if response.status_code != 200:
            return None
        
        meeting = response.json()
        expense_id = meeting.get("expense_id")
        
        if not expense_id:
            return None
        
        # Fetch the expense directly by ID
        expense_response = requests.get(f"{BASE_URL}/api/expenses/{expense_id}", headers=headers)
        if expense_response.status_code == 200:
            return expense_response.json()
        return None
    
    # ========== DRIVING MODE TESTS ==========
    
    def test_driving_one_way_expense_calculation(self, headers):
        """
        Test DRIVING mode with one-way trip.
        Distance: 100km one-way, Rate: Rs.7/km
        Expected expense: 100 * 7 = Rs.700
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "10:00",
            "meeting_type": "Offline",
            "title": f"TEST Driving OneWay Meeting {unique_id}",
            "attendees": ["Test Client"],
            "mom": "Test meeting for expense calculation - driving one way",
            "travel_details": {
                "start_location": "Test Office, Mumbai",
                "end_location": "Client Office, Pune",
                "is_round_trip": False,
                "travel_mode": "DRIVING",
                "distance_km": 100,  # One-way 100km
                "travel_start_time": "08:00",
                "travel_end_time": "10:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        data = response.json()
        meeting_id = data.get("meeting_id")
        assert meeting_id, "Meeting ID not returned"
        
        # Wait for background task to complete
        time.sleep(2)
        
        # Verify expense was created
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created"
        
        expected_amount = 100 * 7  # 100km * Rs.7/km = Rs.700
        
        assert expense["amount"] == expected_amount, f"Expected Rs.{expected_amount}, got Rs.{expense['amount']}"
        assert expense["status"] == "pending", f"Expected 'pending' status, got '{expense['status']}'"
        assert expense.get("meeting_id") == meeting_id, "Expense not linked to meeting"
        assert expense.get("lead_id") == TEST_LEAD_ID, "Expense not linked to lead"
        
        print(f"✓ DRIVING one-way: 100km × Rs.7/km = Rs.{expected_amount} (Actual: Rs.{expense['amount']})")
    
    def test_driving_round_trip_expense_calculation(self, headers):
        """
        Test DRIVING mode with round trip.
        Distance: 150km one-way, Round trip doubles it, Rate: Rs.7/km
        Expected expense: 150 * 2 * 7 = Rs.2100
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "11:00",
            "meeting_type": "Offline",
            "title": f"TEST Driving RoundTrip Meeting {unique_id}",
            "attendees": ["Test Client"],
            "mom": "Test meeting for expense calculation - driving round trip",
            "travel_details": {
                "start_location": "Office, Ahmedabad",
                "end_location": "Client Site, Vadodara",
                "is_round_trip": True,
                "travel_mode": "DRIVING",
                "distance_km": 150,  # One-way 150km (backend doubles it)
                "travel_start_time": "07:00",
                "travel_end_time": "18:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify expense
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created"
        
        expected_amount = 150 * 2 * 7  # 150km * 2 (round trip) * Rs.7/km = Rs.2100
        
        assert expense["amount"] == expected_amount, f"Expected Rs.{expected_amount}, got Rs.{expense['amount']}"
        assert expense["travel_details"]["is_round_trip"] == True, "Round trip flag not set"
        assert expense["travel_details"]["total_km"] == 300, "Total km should be 300 for round trip"
        
        print(f"✓ DRIVING round-trip: 150km × 2 × Rs.7/km = Rs.{expected_amount} (Actual: Rs.{expense['amount']})")
    
    # ========== TWO_WHEELER MODE TESTS ==========
    
    def test_two_wheeler_one_way_expense_calculation(self, headers):
        """
        Test TWO_WHEELER (Bike) mode with one-way trip.
        Distance: 20km one-way, Rate: Rs.3/km
        Expected expense: 20 * 3 = Rs.60
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "14:00",
            "meeting_type": "Offline",
            "title": f"TEST Bike OneWay Meeting {unique_id}",
            "attendees": ["Local Client"],
            "mom": "Test meeting for expense calculation - bike one way",
            "travel_details": {
                "start_location": "Office, Andheri",
                "end_location": "Client Office, Bandra",
                "is_round_trip": False,
                "travel_mode": "TWO_WHEELER",
                "distance_km": 20,
                "travel_start_time": "13:30",
                "travel_end_time": "14:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify expense
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created"
        
        expected_amount = 20 * 3  # 20km * Rs.3/km = Rs.60
        
        assert expense["amount"] == expected_amount, f"Expected Rs.{expected_amount}, got Rs.{expense['amount']}"
        
        print(f"✓ TWO_WHEELER one-way: 20km × Rs.3/km = Rs.{expected_amount} (Actual: Rs.{expense['amount']})")
    
    def test_two_wheeler_round_trip_expense_calculation(self, headers):
        """
        Test TWO_WHEELER (Bike) mode with round trip.
        Distance: 15km one-way, Round trip doubles it, Rate: Rs.3/km
        Expected expense: 15 * 2 * 3 = Rs.90
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "15:00",
            "meeting_type": "Offline",
            "title": f"TEST Bike RoundTrip Meeting {unique_id}",
            "attendees": ["Nearby Client"],
            "mom": "Test meeting for expense calculation - bike round trip",
            "travel_details": {
                "start_location": "Home Office",
                "end_location": "Client Location Nearby",
                "is_round_trip": True,
                "travel_mode": "TWO_WHEELER",
                "distance_km": 15,
                "travel_start_time": "14:30",
                "travel_end_time": "17:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify expense
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created"
        
        expected_amount = 15 * 2 * 3  # 15km * 2 * Rs.3/km = Rs.90
        
        assert expense["amount"] == expected_amount, f"Expected Rs.{expected_amount}, got Rs.{expense['amount']}"
        
        print(f"✓ TWO_WHEELER round-trip: 15km × 2 × Rs.3/km = Rs.{expected_amount} (Actual: Rs.{expense['amount']})")
    
    # ========== TRANSIT MODE TESTS ==========
    
    def test_transit_manual_amount_expense(self, headers):
        """
        Test TRANSIT mode with manual transit amount entry.
        Manual amount: Rs.350 (bus/train fare)
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "09:00",
            "meeting_type": "Offline",
            "title": f"TEST Transit Meeting {unique_id}",
            "attendees": ["Remote Client"],
            "mom": "Test meeting for expense calculation - transit manual entry",
            "travel_details": {
                "start_location": "Mumbai Central Station",
                "end_location": "Surat Railway Station",
                "is_round_trip": False,
                "travel_mode": "TRANSIT",
                "distance_km": 0,  # Not used for transit
                "transit_amount": 350,  # Manual entry
                "travel_start_time": "06:00",
                "travel_end_time": "09:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify expense
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created for transit"
        
        expected_amount = 350  # Manual transit amount
        
        assert expense["amount"] == expected_amount, f"Expected Rs.{expected_amount}, got Rs.{expense['amount']}"
        
        print(f"✓ TRANSIT manual entry: Rs.{expected_amount} (Actual: Rs.{expense['amount']})")
    
    # ========== ACCOMPANIED MODE TESTS ==========
    
    def test_accompanied_no_expense_created(self, headers):
        """
        Test ACCOMPANIED mode - NO expense should be created.
        When accompanied by another employee, they claim the expense.
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "16:00",
            "meeting_type": "Offline",
            "title": f"TEST Accompanied Meeting {unique_id}",
            "attendees": ["Important Client"],
            "mom": "Test meeting - accompanied by manager, no expense",
            "travel_details": {
                "start_location": "Head Office",
                "end_location": "Client Corporate Office",
                "is_round_trip": True,
                "travel_mode": "ACCOMPANIED",
                "distance_km": 50,
                "accompanied_by": "some-employee-id",  # Accompanied by another employee
                "travel_start_time": "15:00",
                "travel_end_time": "19:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200, f"Failed to create meeting: {response.text}"
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify NO expense was created
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is None, f"Expected no expense for ACCOMPANIED mode, but got one"
        
        print(f"✓ ACCOMPANIED mode: No expense created (as expected)")
    
    # ========== EXPENSE LINKING TESTS ==========
    
    def test_expense_linked_to_meeting_and_lead(self, headers):
        """
        Verify expense record is properly linked to both meeting and lead.
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "10:30",
            "meeting_type": "Offline",
            "title": f"TEST Link Verification Meeting {unique_id}",
            "attendees": ["Test Client"],
            "mom": "Test meeting to verify expense linking",
            "travel_details": {
                "start_location": "Office A",
                "end_location": "Client Site B",
                "is_round_trip": False,
                "travel_mode": "DRIVING",
                "distance_km": 50,
                "travel_start_time": "10:00",
                "travel_end_time": "10:30"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        meeting_id = data.get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify expense links
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created"
        
        # Verify meeting link
        assert expense.get("meeting_id") == meeting_id, "Expense not linked to meeting"
        
        # Verify lead link
        assert expense.get("lead_id") == TEST_LEAD_ID, "Expense not linked to lead"
        
        # Verify expense type
        assert expense.get("expense_type") == "meeting_expense", f"Wrong expense type: {expense.get('expense_type')}"
        
        # Verify travel details are stored
        travel_details = expense.get("travel_details", {})
        assert travel_details.get("travel_mode") == "DRIVING"
        assert travel_details.get("rate_per_km") == 7
        
        print(f"✓ Expense properly linked: meeting_id={meeting_id}, lead_id={TEST_LEAD_ID}")
    
    def test_expense_status_pending_for_approval(self, headers):
        """
        Verify expense status is 'pending' for approval workflow integration.
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "11:30",
            "meeting_type": "Offline",
            "title": f"TEST Status Check Meeting {unique_id}",
            "attendees": ["Test Client"],
            "mom": "Test meeting to verify expense approval status",
            "travel_details": {
                "start_location": "Office",
                "end_location": "Client",
                "is_round_trip": False,
                "travel_mode": "DRIVING",
                "distance_km": 30,
                "travel_start_time": "11:00",
                "travel_end_time": "11:30"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for background task
        time.sleep(2)
        
        # Verify expense status
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is not None, "Expected expense to be created"
        
        assert expense["status"] == "pending", f"Expected 'pending' status, got '{expense['status']}'"
        
        print(f"✓ Expense status is 'pending' for approval workflow")
    
    # ========== ONLINE MEETING TESTS ==========
    
    def test_online_meeting_no_travel_expense(self, headers):
        """
        Verify online meetings don't create travel expenses.
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "12:00",
            "meeting_type": "Online",  # Online meeting
            "title": f"TEST Online Meeting {unique_id}",
            "attendees": ["Remote Client"],
            "mom": "Online meeting - no travel expense expected"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200
        
        meeting_id = response.json().get("meeting_id")
        
        # Wait for any background task
        time.sleep(2)
        
        # Verify NO expense was created
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is None, f"Expected no expense for online meeting, but got one"
        
        print(f"✓ Online meeting: No travel expense created (as expected)")


class TestMeetingExpenseEdgeCases:
    """Test edge cases for meeting expense calculation"""
    
    @pytest.fixture(scope="class")
    def sales_token(self):
        """Authenticate as Sales Executive"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=SALES_CREDENTIALS)
        if response.status_code != 200:
            pytest.skip(f"Could not authenticate: {response.status_code}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def headers(self, sales_token):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {sales_token}"
        }
    
    def get_expense_for_meeting(self, meeting_id, headers):
        """Helper to get expense linked to a meeting by checking the meeting's expense_id"""
        response = requests.get(f"{BASE_URL}/api/meetings/{meeting_id}", headers=headers)
        if response.status_code != 200:
            return None
        
        meeting = response.json()
        expense_id = meeting.get("expense_id")
        
        if not expense_id:
            return None
        
        expense_response = requests.get(f"{BASE_URL}/api/expenses/{expense_id}", headers=headers)
        if expense_response.status_code == 200:
            return expense_response.json()
        return None
    
    def test_zero_distance_no_expense(self, headers):
        """
        Test that zero distance doesn't create an expense.
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "13:00",
            "meeting_type": "Offline",
            "title": f"TEST Zero Distance Meeting {unique_id}",
            "attendees": ["Client"],
            "mom": "Test with zero distance",
            "travel_details": {
                "start_location": "Same Building",
                "end_location": "Same Building",
                "is_round_trip": False,
                "travel_mode": "DRIVING",
                "distance_km": 0,  # Zero distance
                "travel_start_time": "13:00",
                "travel_end_time": "13:05"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200
        
        meeting_id = response.json().get("meeting_id")
        
        time.sleep(2)
        
        # Check - no expense should be created for zero distance
        expense = self.get_expense_for_meeting(meeting_id, headers)
        # Zero distance should not create expense (expense_amount would be 0)
        assert expense is None, "Should not create expense for zero distance"
        
        print(f"✓ Zero distance: No expense created")
    
    def test_transit_zero_amount_no_expense(self, headers):
        """
        Test that transit with zero amount doesn't create an expense.
        """
        unique_id = str(uuid.uuid4())[:8]
        meeting_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "lead_id": TEST_LEAD_ID,
            "meeting_date": meeting_date,
            "meeting_time": "14:00",
            "meeting_type": "Offline",
            "title": f"TEST Transit Zero Amount {unique_id}",
            "attendees": ["Client"],
            "mom": "Test transit with zero amount",
            "travel_details": {
                "start_location": "Station A",
                "end_location": "Station B",
                "is_round_trip": False,
                "travel_mode": "TRANSIT",
                "distance_km": 0,
                "transit_amount": 0,  # Zero amount
                "travel_start_time": "14:00",
                "travel_end_time": "15:00"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings/record", json=payload, headers=headers)
        assert response.status_code == 200
        
        meeting_id = response.json().get("meeting_id")
        
        time.sleep(2)
        
        # Verify no expense created for zero transit amount
        expense = self.get_expense_for_meeting(meeting_id, headers)
        assert expense is None, "Should not create expense for zero transit amount"
        
        print(f"✓ Transit zero amount: No expense created")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
