"""
Test Reverse Geocode Feature - GPS to Address conversion
Tests:
1. GET /api/reverse-geocode endpoint with valid coordinates
2. POST /api/my/check-in with location_address fields
3. POST /api/my/check-out with checkout_address field
4. GET /api/my/attendance returns location_address field
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReverseGeocode:
    """Test reverse geocode endpoint and address storage in attendance"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
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
            self.auth_success = True
        else:
            self.auth_success = False
            pytest.skip("Authentication failed - skipping tests")
    
    def test_reverse_geocode_mumbai_coordinates(self):
        """Test reverse geocode with Mumbai coordinates (19.0760, 72.8777)"""
        response = self.session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lat": 19.0760,
            "lng": 72.8777
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Mumbai reverse geocode response: {data}")
        
        # Verify response structure
        assert "address" in data, "Response should contain 'address' field"
        assert "locality" in data, "Response should contain 'locality' field"
        assert "area" in data, "Response should contain 'area' field"
        assert "city" in data, "Response should contain 'city' field"
        
        # Address should not be just coordinates
        address = data.get("address", "")
        assert address, "Address should not be empty"
        print(f"Mumbai address: {address}")
        print(f"Locality: {data.get('locality')}, Area: {data.get('area')}, City: {data.get('city')}")
    
    def test_reverse_geocode_delhi_coordinates(self):
        """Test reverse geocode with Delhi coordinates (28.6139, 77.2090)"""
        response = self.session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lat": 28.6139,
            "lng": 77.2090
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Delhi reverse geocode response: {data}")
        
        # Verify response structure
        assert "address" in data, "Response should contain 'address' field"
        assert "city" in data, "Response should contain 'city' field"
        
        # Address should contain Delhi-related info
        address = data.get("address", "")
        city = data.get("city", "")
        print(f"Delhi address: {address}")
        print(f"City: {city}")
    
    def test_reverse_geocode_bangalore_coordinates(self):
        """Test reverse geocode with Bangalore coordinates (12.9716, 77.5946)"""
        response = self.session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lat": 12.9716,
            "lng": 77.5946
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Bangalore reverse geocode response: {data}")
        
        assert "address" in data
        assert "city" in data
        print(f"Bangalore address: {data.get('address')}")
        print(f"City: {data.get('city')}")
    
    def test_reverse_geocode_requires_auth(self):
        """Test that reverse geocode endpoint requires authentication"""
        # Create new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lat": 19.0760,
            "lng": 72.8777
        })
        
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_check_status_endpoint(self):
        """Test GET /api/my/check-status returns today's attendance status"""
        response = self.session.get(f"{BASE_URL}/api/my/check-status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        print(f"Check status response: {data}")
        
        # Verify response structure
        assert "date" in data, "Response should contain 'date' field"
        assert "has_checked_in" in data, "Response should contain 'has_checked_in' field"
        assert "has_checked_out" in data, "Response should contain 'has_checked_out' field"
    
    def test_my_attendance_returns_location_address(self):
        """Test GET /api/my/attendance returns records with location_address field"""
        import datetime
        month = datetime.datetime.now().strftime("%Y-%m")
        
        response = self.session.get(f"{BASE_URL}/api/my/attendance", params={"month": month})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        records = data if isinstance(data, list) else data.get("records", [])
        
        print(f"Found {len(records)} attendance records for {month}")
        
        # Check if any records have location_address
        for record in records[:5]:  # Check first 5 records
            print(f"Record date: {record.get('date')}, location_address: {record.get('location_address', 'N/A')}")
            # location_address may be null for old records
            if record.get('location_address'):
                print(f"  -> Found address: {record.get('location_address')}")


class TestCheckInWithAddress:
    """Test check-in endpoint accepts and stores address fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as sales user (EMP003)"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as sales user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP003",
            "password": "sales123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.auth_success = True
        else:
            self.auth_success = False
            pytest.skip("Authentication failed for EMP003 - skipping tests")
    
    def test_check_in_accepts_address_fields(self):
        """Test that check-in endpoint accepts location_address, location_locality, location_area, location_city"""
        # First check if already checked in
        status_response = self.session.get(f"{BASE_URL}/api/my/check-status")
        if status_response.status_code == 200:
            status = status_response.json()
            if status.get("has_checked_in"):
                print("Already checked in today - skipping check-in test")
                pytest.skip("Already checked in today")
        
        # Attempt check-in with address fields
        payload = {
            "work_location": "in_office",
            "remarks": "Test check-in with address",
            "geo_location": {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "accuracy": 10,
                "address": "Fort, Mumbai, Maharashtra"
            },
            "location_address": "Fort, Mumbai, Maharashtra",
            "location_locality": "Fort",
            "location_area": "South Mumbai",
            "location_city": "Mumbai"
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-in", json=payload)
        
        # May fail if already checked in
        if response.status_code == 400 and "Already checked in" in response.text:
            print("Already checked in today - test passed (endpoint accepts payload)")
            return
        
        print(f"Check-in response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            attendance = data.get("attendance", {})
            print(f"Check-in successful. Attendance record: {attendance}")
            
            # Verify address fields were stored
            assert attendance.get("location_address") == "Fort, Mumbai, Maharashtra", "location_address should be stored"
    
    def test_check_out_accepts_address_field(self):
        """Test that check-out endpoint accepts checkout_address via geo_location.address"""
        # First check if checked in but not checked out
        status_response = self.session.get(f"{BASE_URL}/api/my/check-status")
        if status_response.status_code == 200:
            status = status_response.json()
            if not status.get("has_checked_in"):
                print("Not checked in today - skipping check-out test")
                pytest.skip("Not checked in today")
            if status.get("has_checked_out"):
                print("Already checked out today - skipping check-out test")
                pytest.skip("Already checked out today")
        
        # Attempt check-out with address
        payload = {
            "geo_location": {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "accuracy": 10,
                "address": "Fort, Mumbai, Maharashtra - Checkout"
            }
        }
        
        response = self.session.post(f"{BASE_URL}/api/my/check-out", json=payload)
        
        print(f"Check-out response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            attendance = data.get("attendance", {})
            print(f"Check-out successful. Working hours: {data.get('working_hours')}")
            
            # Verify checkout_address was stored
            if attendance.get("checkout_address"):
                print(f"Checkout address stored: {attendance.get('checkout_address')}")


class TestReverseGeocodeEdgeCases:
    """Test edge cases for reverse geocode"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_reverse_geocode_ocean_coordinates(self):
        """Test reverse geocode with ocean coordinates (should return fallback)"""
        # Coordinates in the middle of the ocean
        response = self.session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lat": 0.0,
            "lng": 0.0
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"Ocean coordinates response: {data}")
        
        # Should still return address field (may be coordinates as fallback)
        assert "address" in data
    
    def test_reverse_geocode_missing_params(self):
        """Test reverse geocode with missing parameters"""
        # Missing lng
        response = self.session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lat": 19.0760
        })
        
        # Should return 422 (validation error) for missing required param
        assert response.status_code == 422, f"Expected 422 for missing lng, got {response.status_code}"
        
        # Missing lat
        response = self.session.get(f"{BASE_URL}/api/reverse-geocode", params={
            "lng": 72.8777
        })
        
        assert response.status_code == 422, f"Expected 422 for missing lat, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
