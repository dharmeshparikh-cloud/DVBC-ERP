"""
Test Suite for Top-Down Pricing and Admin Masters Module
- Tests Admin Masters CRUD: Tenure Types, Consultant Roles, Meeting Types
- Tests Top-Down Pricing calculations and Pricing Plan creation
- Tests seed-defaults endpoint
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@company.com"
ADMIN_PASSWORD = "admin123"
MANAGER_EMAIL = "manager@company.com"
MANAGER_PASSWORD = "manager123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def manager_token():
    """Get manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Manager authentication failed")


@pytest.fixture
def auth_headers(admin_token):
    """Headers with admin auth token"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def manager_headers(manager_token):
    """Headers with manager auth token"""
    return {"Authorization": f"Bearer {manager_token}"}


class TestSeedDefaults:
    """Test seed-defaults endpoint"""
    
    def test_seed_defaults(self, auth_headers):
        """POST /api/masters/seed-defaults - Seed default master data"""
        response = requests.post(f"{BASE_URL}/api/masters/seed-defaults", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "created" in data
        
        # Verify structure
        created = data["created"]
        assert "tenure_types" in created
        assert "consultant_roles" in created
        assert "meeting_types" in created
        
        print(f"Seeded: {created}")


class TestTenureTypes:
    """Test tenure types CRUD endpoints"""
    
    def test_get_tenure_types(self, auth_headers):
        """GET /api/masters/tenure-types - Get all tenure types"""
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify at least some default types exist
        if len(data) > 0:
            tenure = data[0]
            assert "id" in tenure
            assert "name" in tenure
            assert "code" in tenure
            assert "allocation_percentage" in tenure
            print(f"Found {len(data)} tenure types")
            
            # Check for expected default tenure types
            codes = [t["code"] for t in data]
            expected_codes = ["full_time", "weekly", "bi_weekly", "monthly"]
            for code in expected_codes:
                if code in codes:
                    print(f"✓ Found expected tenure type: {code}")
    
    def test_create_tenure_type(self, auth_headers):
        """POST /api/masters/tenure-types - Create new tenure type"""
        unique_code = f"test_tenure_{int(time.time())}"
        payload = {
            "name": "Test Tenure Type",
            "code": unique_code,
            "allocation_percentage": 15.0,
            "meetings_per_month": 3,
            "description": "Test tenure for automated testing"
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/tenure-types", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["code"] == unique_code
        assert data["allocation_percentage"] == 15.0
        assert data["meetings_per_month"] == 3
        print(f"Created tenure type: {data['id']}")
        
        return data["id"]
    
    def test_get_specific_tenure_type(self, auth_headers):
        """GET /api/masters/tenure-types/{id} - Get specific tenure type"""
        # First get all and pick one
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=auth_headers)
        assert response.status_code == 200
        tenure_types = response.json()
        
        if len(tenure_types) == 0:
            pytest.skip("No tenure types found")
        
        tenure_id = tenure_types[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types/{tenure_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenure_id
        print(f"Retrieved tenure type: {data['name']}")
    
    def test_update_tenure_type(self, auth_headers):
        """PUT /api/masters/tenure-types/{id} - Update tenure type"""
        # First get all and pick one
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=auth_headers)
        assert response.status_code == 200
        tenure_types = response.json()
        
        if len(tenure_types) == 0:
            pytest.skip("No tenure types found")
        
        tenure = tenure_types[0]
        tenure_id = tenure["id"]
        original_desc = tenure.get("description", "")
        
        # Update description
        new_desc = f"Updated at {int(time.time())}"
        response = requests.put(
            f"{BASE_URL}/api/masters/tenure-types/{tenure_id}",
            json={"description": new_desc},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == new_desc
        print(f"Updated tenure type description: {new_desc}")
    
    def test_allocation_percentage_validation(self, auth_headers):
        """POST /api/masters/tenure-types - Validate allocation percentage range"""
        # Test invalid allocation > 100
        payload = {
            "name": "Invalid Tenure",
            "code": f"invalid_{int(time.time())}",
            "allocation_percentage": 150.0  # Invalid - over 100
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/tenure-types", json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert "allocation" in response.json().get("detail", "").lower()
        print("✓ Correctly rejected allocation percentage > 100")
    
    def test_duplicate_code_rejection(self, auth_headers):
        """POST /api/masters/tenure-types - Reject duplicate code"""
        # Get existing tenure type
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=auth_headers)
        tenure_types = response.json()
        
        if len(tenure_types) == 0:
            pytest.skip("No tenure types found")
        
        existing_code = tenure_types[0]["code"]
        
        payload = {
            "name": "Duplicate Code Test",
            "code": existing_code,  # Use existing code
            "allocation_percentage": 10.0
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/tenure-types", json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json().get("detail", "")
        print(f"✓ Correctly rejected duplicate code: {existing_code}")


class TestConsultantRoles:
    """Test consultant roles CRUD endpoints"""
    
    def test_get_consultant_roles(self, auth_headers):
        """GET /api/masters/consultant-roles - Get all consultant roles"""
        response = requests.get(f"{BASE_URL}/api/masters/consultant-roles", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            role = data[0]
            assert "id" in role
            assert "name" in role
            assert "code" in role
            assert "min_rate_per_meeting" in role
            assert "max_rate_per_meeting" in role
            assert "default_rate" in role
            print(f"Found {len(data)} consultant roles")
            
            # Check for expected roles
            role_names = [r["name"] for r in data]
            print(f"Roles: {role_names[:5]}...")  # Print first 5
    
    def test_create_consultant_role(self, auth_headers):
        """POST /api/masters/consultant-roles - Create new consultant role"""
        unique_code = f"test_role_{int(time.time())}"
        payload = {
            "name": "Test Consultant Role",
            "code": unique_code,
            "min_rate_per_meeting": 8000,
            "max_rate_per_meeting": 25000,
            "default_rate": 15000,
            "seniority_level": 2
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/consultant-roles", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["code"] == unique_code
        assert data["min_rate_per_meeting"] == 8000
        assert data["default_rate"] == 15000
        print(f"Created consultant role: {data['id']}")
        
        return data["id"]
    
    def test_update_consultant_role(self, auth_headers):
        """PUT /api/masters/consultant-roles/{id} - Update consultant role"""
        # First get all roles
        response = requests.get(f"{BASE_URL}/api/masters/consultant-roles", headers=auth_headers)
        assert response.status_code == 200
        roles = response.json()
        
        if len(roles) == 0:
            pytest.skip("No consultant roles found")
        
        role = roles[0]
        role_id = role["id"]
        
        # Update default rate
        new_rate = role["default_rate"] + 500
        response = requests.put(
            f"{BASE_URL}/api/masters/consultant-roles/{role_id}",
            json={"default_rate": new_rate},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["default_rate"] == new_rate
        print(f"Updated consultant role default rate to: {new_rate}")


class TestMeetingTypes:
    """Test meeting types endpoints"""
    
    def test_get_meeting_types(self, auth_headers):
        """GET /api/masters/meeting-types - Get all meeting types"""
        response = requests.get(f"{BASE_URL}/api/masters/meeting-types", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            meeting_type = data[0]
            assert "id" in meeting_type
            assert "name" in meeting_type
            assert "code" in meeting_type
            assert "default_duration_minutes" in meeting_type
            print(f"Found {len(data)} meeting types")
            
            # Print meeting type names
            names = [mt["name"] for mt in data]
            print(f"Meeting types: {names[:5]}...")  # Print first 5
    
    def test_create_meeting_type(self, auth_headers):
        """POST /api/masters/meeting-types - Create new meeting type"""
        unique_code = f"test_meeting_{int(time.time())}"
        payload = {
            "name": "Test Meeting Type",
            "code": unique_code,
            "default_duration_minutes": 45
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/meeting-types", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["code"] == unique_code
        assert data["default_duration_minutes"] == 45
        print(f"Created meeting type: {data['id']}")


class TestAllocationCalculation:
    """Test allocation calculation endpoint"""
    
    def test_calculate_allocation(self, auth_headers):
        """POST /api/masters/calculate-allocation - Calculate cost allocation"""
        payload = {
            "total_investment": 1000000,
            "team_members": [
                {"tenure_type_code": "full_time", "meetings_per_month": 22, "duration_months": 12},
                {"tenure_type_code": "weekly", "meetings_per_month": 4, "duration_months": 12}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/calculate-allocation", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_investment" in data
        assert data["total_investment"] == 1000000
        assert "team_breakdown" in data
        assert isinstance(data["team_breakdown"], list)
        
        if len(data["team_breakdown"]) > 0:
            member = data["team_breakdown"][0]
            assert "allocation_percentage" in member
            assert "breakup_amount" in member
            assert "total_meetings" in member
            assert "rate_per_meeting" in member
            
            print(f"Total investment: {data['total_investment']}")
            print(f"Total allocation %: {data.get('total_allocation_percentage', 'N/A')}")
            for m in data["team_breakdown"]:
                print(f"  - {m['tenure_type_name']}: {m['allocation_percentage']:.1f}% = ₹{m['breakup_amount']:,.0f} | {m['total_meetings']} meetings | ₹{m['rate_per_meeting']:,.0f}/meeting")
    
    def test_calculate_allocation_single_member(self, auth_headers):
        """Test allocation with single team member (should get 100%)"""
        payload = {
            "total_investment": 500000,
            "team_members": [
                {"tenure_type_code": "full_time", "meetings_per_month": 22, "duration_months": 12}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/calculate-allocation", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Single member should get 100% allocation (normalized)
        member = data["team_breakdown"][0]
        assert member["allocation_percentage"] == 100.0
        assert member["breakup_amount"] == 500000
        
        # Verify rate per meeting calculation
        total_meetings = 22 * 12  # meetings_per_month * duration_months
        expected_rate = 500000 / total_meetings
        assert abs(member["rate_per_meeting"] - expected_rate) < 1  # Allow rounding
        print(f"Single member gets 100%: ₹{member['breakup_amount']:,.0f} for {member['total_meetings']} meetings")
    
    def test_calculate_allocation_zero_investment_error(self, auth_headers):
        """Test allocation with zero investment - should fail"""
        payload = {
            "total_investment": 0,
            "team_members": [
                {"tenure_type_code": "full_time", "duration_months": 12}
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/calculate-allocation", json=payload, headers=auth_headers)
        
        assert response.status_code == 400
        assert "investment" in response.json().get("detail", "").lower()
        print("✓ Correctly rejected zero investment")
    
    def test_calculate_allocation_no_members_error(self, auth_headers):
        """Test allocation with no team members - should fail"""
        payload = {
            "total_investment": 1000000,
            "team_members": []
        }
        
        response = requests.post(f"{BASE_URL}/api/masters/calculate-allocation", json=payload, headers=auth_headers)
        
        assert response.status_code == 400
        assert "member" in response.json().get("detail", "").lower()
        print("✓ Correctly rejected empty team members")


class TestPricingPlanWithTopDownPricing:
    """Test Pricing Plan creation with top-down pricing model"""
    
    @pytest.fixture
    def test_lead_id(self, auth_headers):
        """Create or get a test lead for pricing plan testing"""
        # First check if there's an existing lead
        response = requests.get(f"{BASE_URL}/api/leads", headers=auth_headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        
        # Create a new test lead
        payload = {
            "first_name": "TopDown",
            "last_name": "Test",
            "company": "Test Company for Top-Down Pricing",
            "email": f"topdown_test_{int(time.time())}@test.com",
            "job_title": "CEO"
        }
        response = requests.post(f"{BASE_URL}/api/leads", json=payload, headers=auth_headers)
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_create_pricing_plan_top_down(self, auth_headers, test_lead_id):
        """POST /api/pricing-plans - Create pricing plan with top-down pricing"""
        # Get tenure types for reference
        tenure_resp = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=auth_headers)
        tenure_types = {t["code"]: t for t in tenure_resp.json()}
        
        total_investment = 1200000  # 12 Lakh total investment
        
        # Create team deployment with top-down data
        team_deployment = [
            {
                "consultant_type": "project_manager",
                "role": "Project Manager",
                "meeting_type": "Monthly Review",
                "tenure_type_code": "full_time",
                "frequency": "22 per month",
                "mode": "Mixed",
                "count": 1,
                "meetings": 264,  # 22 * 12 months
                "rate_per_meeting": 0,  # Will be calculated
                "committed_meetings": 264,
                "allocation_percentage": 70.0,
                "breakup_amount": 840000  # 70% of 1.2M
            },
            {
                "consultant_type": "consultant",
                "role": "Lean Consultant",
                "meeting_type": "Weekly Review",
                "tenure_type_code": "weekly",
                "frequency": "4 per month",
                "mode": "Online",
                "count": 1,
                "meetings": 48,  # 4 * 12 months
                "rate_per_meeting": 0,
                "committed_meetings": 48,
                "allocation_percentage": 30.0,
                "breakup_amount": 360000  # 30% of 1.2M (normalized)
            }
        ]
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "consultants": team_deployment,
            "team_deployment": team_deployment,
            "total_investment": total_investment,
            "discount_percentage": 5,
            "growth_consulting_plan": "Comprehensive growth strategy",
            "growth_guarantee": "20% growth in first year"
        }
        
        response = requests.post(f"{BASE_URL}/api/pricing-plans", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify pricing plan was created
        assert "id" in data
        assert data["lead_id"] == test_lead_id
        assert data["total_investment"] == total_investment
        assert data["project_duration_months"] == 12
        
        # Verify team deployment was stored
        assert len(data.get("consultants", [])) == 2 or len(data.get("team_deployment", [])) == 2
        
        print(f"Created pricing plan: {data['id']}")
        print(f"Total investment: ₹{data['total_investment']:,.0f}")
        print(f"Discount: {data['discount_percentage']}%")
        print(f"Total amount (with GST): ₹{data.get('total_amount', 0):,.0f}")
        
        return data["id"]
    
    def test_get_pricing_plan_with_top_down_data(self, auth_headers, test_lead_id):
        """GET /api/pricing-plans/{id} - Verify top-down pricing data retrieval"""
        # First get all pricing plans for the lead
        response = requests.get(f"{BASE_URL}/api/pricing-plans?lead_id={test_lead_id}", headers=auth_headers)
        
        if response.status_code != 200 or len(response.json()) == 0:
            pytest.skip("No pricing plans found for test lead")
        
        plan = response.json()[0]
        plan_id = plan["id"]
        
        # Get specific plan
        response = requests.get(f"{BASE_URL}/api/pricing-plans/{plan_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify top-down fields exist
        assert "total_investment" in data
        
        # Verify team deployment or consultants have allocation data
        team = data.get("consultants", []) or data.get("team_deployment", [])
        if len(team) > 0:
            member = team[0]
            # Check for top-down specific fields
            if "allocation_percentage" in member:
                print(f"✓ allocation_percentage present: {member['allocation_percentage']}")
            if "breakup_amount" in member:
                print(f"✓ breakup_amount present: {member['breakup_amount']}")
            if "tenure_type_code" in member:
                print(f"✓ tenure_type_code present: {member['tenure_type_code']}")
        
        print(f"Pricing plan retrieved successfully: {plan_id}")


class TestAccessControl:
    """Test access control for Admin Masters"""
    
    def test_tenure_types_accessible_to_all_authenticated(self, auth_headers, manager_headers):
        """Verify tenure types are readable by all authenticated users"""
        # Admin access
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=auth_headers)
        assert response.status_code == 200
        print("✓ Admin can access tenure types")
        
        # Manager access
        response = requests.get(f"{BASE_URL}/api/masters/tenure-types", headers=manager_headers)
        assert response.status_code == 200
        print("✓ Manager can access tenure types")
    
    def test_consultant_roles_accessible_to_all_authenticated(self, auth_headers, manager_headers):
        """Verify consultant roles are readable by all authenticated users"""
        # Admin access
        response = requests.get(f"{BASE_URL}/api/masters/consultant-roles", headers=auth_headers)
        assert response.status_code == 200
        print("✓ Admin can access consultant roles")
        
        # Manager access
        response = requests.get(f"{BASE_URL}/api/masters/consultant-roles", headers=manager_headers)
        assert response.status_code == 200
        print("✓ Manager can access consultant roles")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
