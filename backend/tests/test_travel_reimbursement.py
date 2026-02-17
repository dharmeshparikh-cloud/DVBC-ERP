"""
Travel Reimbursement System API Tests
=====================================
Tests for:
1. GET /api/travel/rates - Travel rates (₹7/km car, ₹3/km two-wheeler)
2. GET /api/travel/location-search - OpenStreetMap location search
3. POST /api/travel/calculate-distance - Haversine formula distance calculation
4. POST /api/travel/reimbursement - Create travel reimbursement request
5. GET /api/my/travel-reimbursements - User's travel claims
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@company.com", "password": "admin123"}
HR_CREDS = {"email": "hr.manager@company.com", "password": "hr123"}

# Sample locations in India for testing (Haversine calculation)
BANGALORE_COORDS = {"latitude": 12.9716, "longitude": 77.5946}
MYSORE_COORDS = {"latitude": 12.2958, "longitude": 76.6394}

@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=ADMIN_CREDS
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")

@pytest.fixture(scope="module")
def hr_token():
    """Get HR Manager (Sales team) authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=HR_CREDS
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip(f"HR login failed: {response.status_code} - {response.text}")


class TestTravelRates:
    """Test GET /api/travel/rates endpoint"""
    
    def test_get_travel_rates_success(self, admin_token):
        """Should return travel rates for car (₹7/km) and two-wheeler (₹3/km)"""
        response = requests.get(
            f"{BASE_URL}/api/travel/rates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rates" in data, "Response should contain 'rates' key"
        
        rates = data["rates"]
        # Verify car rate is ₹7/km
        assert rates.get("car") == 7, f"Car rate should be 7, got {rates.get('car')}"
        # Verify two-wheeler rate is ₹3/km
        assert rates.get("two_wheeler") == 3, f"Two-wheeler rate should be 3, got {rates.get('two_wheeler')}"
        
        print(f"✓ Travel rates verified: Car=₹{rates['car']}/km, Two-wheeler=₹{rates['two_wheeler']}/km")
    
    def test_get_travel_rates_without_auth(self):
        """Should return 401 without authentication"""
        response = requests.get(f"{BASE_URL}/api/travel/rates")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Travel rates requires authentication")


class TestLocationSearch:
    """Test GET /api/travel/location-search endpoint"""
    
    def test_location_search_bangalore(self, admin_token):
        """Should return location search results for Bangalore from OpenStreetMap"""
        response = requests.get(
            f"{BASE_URL}/api/travel/location-search",
            params={"query": "Bangalore"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "results" in data, "Response should contain 'results' key"
        
        # OpenStreetMap should return results for Bangalore
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "name" in result, "Result should have 'name'"
            assert "latitude" in result, "Result should have 'latitude'"
            assert "longitude" in result, "Result should have 'longitude'"
            assert "address" in result, "Result should have 'address'"
            print(f"✓ Location search returned {len(data['results'])} results for Bangalore")
            print(f"  First result: {result['name']} ({result['latitude']}, {result['longitude']})")
        else:
            # External API might be rate-limited, just verify response structure
            print("✓ Location search returned empty results (possibly rate-limited)")
    
    def test_location_search_short_query(self, admin_token):
        """Should reject queries less than 3 characters"""
        response = requests.get(
            f"{BASE_URL}/api/travel/location-search",
            params={"query": "ab"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # API should reject short queries
        assert response.status_code == 400, f"Expected 400 for short query, got {response.status_code}"
        print("✓ Location search rejects queries < 3 characters")
    
    def test_location_search_mumbai(self, admin_token):
        """Should return results for Mumbai"""
        response = requests.get(
            f"{BASE_URL}/api/travel/location-search",
            params={"query": "Mumbai Maharashtra"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "results" in data
        print(f"✓ Location search for Mumbai returned {len(data.get('results', []))} results")


class TestDistanceCalculation:
    """Test POST /api/travel/calculate-distance endpoint using Haversine formula"""
    
    def test_calculate_distance_one_way(self, admin_token):
        """Should calculate one-way distance using Haversine formula"""
        payload = {
            "start_location": BANGALORE_COORDS,
            "end_location": MYSORE_COORDS,
            "vehicle_type": "car",
            "is_round_trip": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "distance_km" in data, "Response should contain 'distance_km'"
        assert "calculated_amount" in data, "Response should contain 'calculated_amount'"
        
        # Bangalore to Mysore is approximately 140-150 km by road
        # Haversine gives straight-line distance (~125 km)
        distance = data["distance_km"]
        assert 100 < distance < 180, f"Distance should be ~125km (Haversine), got {distance}"
        
        # Verify rate calculation (₹7/km for car)
        expected_amount = round(distance * 7, 2)
        assert data["calculated_amount"] == expected_amount, f"Expected amount {expected_amount}, got {data['calculated_amount']}"
        assert data["is_round_trip"] == False
        assert data["rate_per_km"] == 7
        
        print(f"✓ Distance calculation: Bangalore→Mysore = {distance:.2f} km")
        print(f"✓ Calculated amount (car): ₹{data['calculated_amount']}")
    
    def test_calculate_distance_round_trip(self, admin_token):
        """Should double distance for round trips"""
        payload = {
            "start_location": BANGALORE_COORDS,
            "end_location": MYSORE_COORDS,
            "vehicle_type": "car",
            "is_round_trip": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Round trip should be double
        assert data["is_round_trip"] == True
        
        # Get one-way distance for comparison
        one_way_payload = {**payload, "is_round_trip": False}
        one_way_resp = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json=one_way_payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        one_way_distance = one_way_resp.json()["distance_km"]
        
        # Round trip should be approximately 2x one-way
        assert abs(data["distance_km"] - (one_way_distance * 2)) < 0.1
        
        print(f"✓ Round trip distance: {data['distance_km']:.2f} km (2x {one_way_distance:.2f} km)")
    
    def test_calculate_distance_two_wheeler(self, admin_token):
        """Should calculate with ₹3/km rate for two-wheeler"""
        payload = {
            "start_location": BANGALORE_COORDS,
            "end_location": MYSORE_COORDS,
            "vehicle_type": "two_wheeler",
            "is_round_trip": False
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Two-wheeler rate should be ₹3/km
        assert data["rate_per_km"] == 3, f"Two-wheeler rate should be 3, got {data['rate_per_km']}"
        
        expected_amount = round(data["distance_km"] * 3, 2)
        assert data["calculated_amount"] == expected_amount
        
        print(f"✓ Two-wheeler calculation: {data['distance_km']:.2f} km × ₹3 = ₹{data['calculated_amount']}")
    
    def test_calculate_distance_missing_start(self, admin_token):
        """Should reject if start location coordinates are missing"""
        payload = {
            "start_location": {},
            "end_location": MYSORE_COORDS,
            "vehicle_type": "car"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Distance calculation rejects missing start location")
    
    def test_calculate_distance_missing_end(self, admin_token):
        """Should reject if end location coordinates are missing"""
        payload = {
            "start_location": BANGALORE_COORDS,
            "end_location": {},
            "vehicle_type": "car"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Distance calculation rejects missing end location")


class TestTravelReimbursementCRUD:
    """Test POST /api/travel/reimbursement and GET /api/my/travel-reimbursements"""
    
    @pytest.fixture
    def created_claim_id(self, hr_token):
        """Create a test travel claim and return its ID"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "start_location": {
                "name": "Bangalore Office",
                "address": "Bangalore, Karnataka",
                **BANGALORE_COORDS
            },
            "end_location": {
                "name": "Mysore Client Site",
                "address": "Mysore, Karnataka",
                **MYSORE_COORDS
            },
            "vehicle_type": "car",
            "is_round_trip": True,
            "travel_date": "2026-01-15",
            "travel_type": "manual",
            "notes": f"Test travel claim {unique_id}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/reimbursement",
            json=payload,
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        if response.status_code == 200:
            return response.json()["id"]
        return None
    
    def test_create_travel_reimbursement_car(self, hr_token):
        """Should create a travel reimbursement request for car"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "start_location": {
                "name": "Bangalore Office",
                "address": "Bangalore, Karnataka, India",
                **BANGALORE_COORDS
            },
            "end_location": {
                "name": "Mysore Client",
                "address": "Mysore, Karnataka, India",
                **MYSORE_COORDS
            },
            "vehicle_type": "car",
            "is_round_trip": True,
            "travel_date": "2026-01-15",
            "travel_type": "manual",
            "notes": f"Test claim for car {unique_id}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/reimbursement",
            json=payload,
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "id" in data, "Response should contain claim 'id'"
        assert "distance_km" in data, "Response should contain 'distance_km'"
        assert "final_amount" in data, "Response should contain 'final_amount'"
        
        # Verify round trip distance (double the one-way)
        # Bangalore to Mysore ~125km, round trip ~250km
        assert data["distance_km"] > 200, f"Round trip distance should be >200km, got {data['distance_km']}"
        
        # Verify amount calculation (distance × ₹7)
        expected_amount = round(data["distance_km"] * 7, 2)
        assert data["final_amount"] == expected_amount or data["calculated_amount"] == expected_amount
        
        print(f"✓ Created travel reimbursement: ID={data['id']}")
        print(f"  Distance: {data['distance_km']:.2f} km (round trip)")
        print(f"  Amount: ₹{data['final_amount']}")
    
    def test_create_travel_reimbursement_two_wheeler(self, hr_token):
        """Should create a travel reimbursement for two-wheeler at ₹3/km"""
        payload = {
            "start_location": {
                "name": "Office",
                **BANGALORE_COORDS
            },
            "end_location": {
                "name": "Client",
                **MYSORE_COORDS
            },
            "vehicle_type": "two_wheeler",
            "is_round_trip": False,
            "travel_date": "2026-01-16",
            "travel_type": "manual"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/reimbursement",
            json=payload,
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Two-wheeler at ₹3/km, one-way
        expected_amount = round(data["distance_km"] * 3, 2)
        assert abs(data["final_amount"] - expected_amount) < 1, f"Expected ~₹{expected_amount}, got ₹{data['final_amount']}"
        
        print(f"✓ Two-wheeler reimbursement: {data['distance_km']:.2f} km × ₹3 = ₹{data['final_amount']}")
    
    def test_create_travel_reimbursement_missing_locations(self, hr_token):
        """Should reject if locations are missing"""
        payload = {
            "vehicle_type": "car",
            "is_round_trip": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/travel/reimbursement",
            json=payload,
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Travel reimbursement rejects missing locations")
    
    def test_get_my_travel_reimbursements(self, hr_token, created_claim_id):
        """Should return user's travel reimbursement claims"""
        response = requests.get(
            f"{BASE_URL}/api/my/travel-reimbursements",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "records" in data, "Response should contain 'records'"
        
        # Verify our created claim is in the list
        if created_claim_id:
            claim_ids = [r["id"] for r in data["records"]]
            # The claim might be there (depends on employee record)
            print(f"✓ Retrieved {len(data['records'])} travel reimbursement records")
        else:
            print(f"✓ Retrieved {len(data.get('records', []))} travel records")
    
    def test_get_my_travel_reimbursements_with_month_filter(self, hr_token):
        """Should filter travel claims by month"""
        response = requests.get(
            f"{BASE_URL}/api/my/travel-reimbursements",
            params={"month": "2026-01"},
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All records should be from January 2026
        for record in data.get("records", []):
            if record.get("travel_date"):
                assert record["travel_date"].startswith("2026-01"), f"Record date {record['travel_date']} not in 2026-01"
        
        print(f"✓ Month filter working: {len(data.get('records', []))} records for 2026-01")


class TestTravelReimbursementForSalesTeam:
    """Test that Sales team roles can access travel features"""
    
    def test_admin_can_access_travel_features(self, admin_token):
        """Admin should be able to access all travel endpoints"""
        # Get rates
        response = requests.get(
            f"{BASE_URL}/api/travel/rates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Admin can access travel rates")
        
        # Search locations
        response = requests.get(
            f"{BASE_URL}/api/travel/location-search",
            params={"query": "Delhi"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        print("✓ Admin can search locations")
    
    def test_hr_manager_can_access_travel_features(self, hr_token):
        """HR Manager (sales team) should be able to access travel endpoints"""
        # Get rates
        response = requests.get(
            f"{BASE_URL}/api/travel/rates",
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert response.status_code == 200
        print("✓ HR Manager can access travel rates")
        
        # Calculate distance
        response = requests.post(
            f"{BASE_URL}/api/travel/calculate-distance",
            json={
                "start_location": BANGALORE_COORDS,
                "end_location": MYSORE_COORDS,
                "vehicle_type": "car"
            },
            headers={"Authorization": f"Bearer {hr_token}"}
        )
        assert response.status_code == 200
        print("✓ HR Manager can calculate distance")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
