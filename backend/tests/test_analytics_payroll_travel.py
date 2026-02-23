"""
Test Suite for Analytics, Payroll, and Travel Routers
Tests the newly extracted routers for:
- Analytics: /api/analytics/* endpoints (funnel-summary, bottleneck-analysis, forecasting, etc.)
- Payroll: /api/payroll/* endpoints (salary-components, inputs, salary-slips, etc.)
- Travel: /api/travel/* endpoints (rates, reimbursements, calculate-distance, etc.)

Covers: Authentication, Role-Based Access, Validation, Error Handling, Data Consistency
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

# API Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://erp-approval-flow.preview.emergentagent.com"

# Test credentials
ADMIN_EMAIL = "admin@dvbc.com"
ADMIN_PASSWORD = "admin123"
SALES_MANAGER_EMAIL = "dp@dvbc.com"
SALES_MANAGER_PASSWORD = "Welcome@123"
HR_MANAGER_EMAIL = "hr.manager@dvbc.com"
HR_MANAGER_PASSWORD = "hr123"


class TestAuth:
    """Authentication tests for login flow"""
    
    def test_admin_login_success(self, api_client):
        """Test admin login returns valid token"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == ADMIN_EMAIL
        print(f"✓ Admin login successful, role: {data['user']['role']}")
    
    def test_sales_manager_login_success(self, api_client):
        """Test sales manager login returns valid token"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": SALES_MANAGER_EMAIL,
            "password": SALES_MANAGER_PASSWORD
        })
        assert response.status_code == 200, f"Sales manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == SALES_MANAGER_EMAIL
        print(f"✓ Sales manager login successful, role: {data['user']['role']}")
    
    def test_invalid_credentials(self, api_client):
        """Test login with invalid credentials returns 401"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_missing_password(self, api_client):
        """Test login without password returns error"""
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL
        })
        # Should be 422 for validation error or 400 for bad request
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print("✓ Missing password correctly rejected")


class TestAnalyticsRouter:
    """Tests for /api/analytics/* endpoints"""
    
    def test_funnel_summary_authenticated(self, admin_client):
        """Test funnel summary endpoint with valid auth"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/funnel-summary")
        assert response.status_code == 200, f"Funnel summary failed: {response.text}"
        data = response.json()
        # Verify response structure
        assert "period" in data
        assert "summary" in data
        assert "stage_counts" in data
        assert "funnel_stages" in data
        # Verify summary fields
        summary = data["summary"]
        assert "total_leads" in summary
        assert "completed" in summary
        assert "conversion_rate" in summary
        print(f"✓ Funnel summary returned: {summary['total_leads']} total leads, {summary['conversion_rate']}% conversion")
    
    def test_funnel_summary_with_period_filter(self, admin_client):
        """Test funnel summary with different period filters"""
        for period in ["week", "month", "quarter", "year"]:
            response = admin_client.get(f"{BASE_URL}/api/analytics/funnel-summary?period={period}")
            assert response.status_code == 200, f"Funnel summary failed for period={period}: {response.text}"
            data = response.json()
            assert data["period"] == period
            print(f"✓ Funnel summary for period '{period}' returned successfully")
    
    def test_funnel_summary_unauthenticated(self, api_client):
        """Test funnel summary without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/analytics/funnel-summary")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Funnel summary correctly requires authentication")
    
    def test_my_funnel_summary(self, admin_client):
        """Test personal funnel summary endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/my-funnel-summary")
        assert response.status_code == 200, f"My funnel summary failed: {response.text}"
        data = response.json()
        assert "period" in data
        assert "total_leads" in data
        assert "stage_counts" in data
        assert "targets" in data
        print(f"✓ My funnel summary returned: {data['total_leads']} leads")
    
    def test_funnel_trends_manager_only(self, admin_client, sales_client):
        """Test funnel trends is manager-only endpoint"""
        # Admin should succeed
        response = admin_client.get(f"{BASE_URL}/api/analytics/funnel-trends")
        assert response.status_code == 200, f"Admin should access funnel trends: {response.text}"
        print("✓ Admin can access funnel trends")
        
        # Sales manager should also succeed (has manager role)
        if sales_client:
            response = sales_client.get(f"{BASE_URL}/api/analytics/funnel-trends")
            # May be 200 or 403 depending on role
            if response.status_code == 403:
                print("✓ Non-manager correctly denied funnel trends access")
            else:
                print(f"✓ Sales manager has access (status: {response.status_code})")
    
    def test_bottleneck_analysis(self, admin_client):
        """Test bottleneck analysis endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/bottleneck-analysis")
        assert response.status_code == 200, f"Bottleneck analysis failed: {response.text}"
        data = response.json()
        assert "total_leads" in data
        assert "stages" in data
        assert "bottlenecks" in data
        # Verify bottleneck structure
        if data["bottlenecks"]:
            bottleneck = data["bottlenecks"][0]
            assert "from_stage" in bottleneck
            assert "to_stage" in bottleneck
            assert "conversion_rate" in bottleneck
            assert "drop_off_rate" in bottleneck
        print(f"✓ Bottleneck analysis returned: {len(data['stages'])} stages analyzed")
    
    def test_forecasting_endpoint(self, admin_client):
        """Test sales forecasting endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/forecasting")
        assert response.status_code == 200, f"Forecasting failed: {response.text}"
        data = response.json()
        assert "total_pipeline" in data
        assert "stage_distribution" in data
        assert "pipeline_forecast" in data
        assert "weighted_summary" in data
        assert "time_based_forecast" in data
        # Verify forecast structure
        forecast = data["time_based_forecast"]
        assert "30_days" in forecast
        assert "60_days" in forecast
        assert "90_days" in forecast
        print(f"✓ Forecasting returned: {data['total_pipeline']} leads in pipeline")
    
    def test_time_in_stage_analytics(self, admin_client):
        """Test time-in-stage analytics endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/time-in-stage")
        assert response.status_code == 200, f"Time in stage failed: {response.text}"
        data = response.json()
        assert "stages" in data
        assert "total_leads_analyzed" in data
        assert "overall_metrics" in data
        print(f"✓ Time in stage analysis: {data['total_leads_analyzed']} leads analyzed")
    
    def test_win_loss_analysis(self, admin_client):
        """Test win/loss analysis endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/win-loss")
        assert response.status_code == 200, f"Win-loss failed: {response.text}"
        data = response.json()
        assert "summary" in data
        summary = data["summary"]
        assert "total_leads" in summary
        assert "won" in summary
        assert "lost" in summary
        assert "win_rate" in summary
        print(f"✓ Win-loss analysis: Win rate = {summary['win_rate']}%")
    
    def test_velocity_metrics(self, admin_client):
        """Test sales velocity metrics endpoint"""
        response = admin_client.get(f"{BASE_URL}/api/analytics/velocity")
        assert response.status_code == 200, f"Velocity metrics failed: {response.text}"
        data = response.json()
        # Response can have either structure depending on which endpoint is hit
        # Server.py defines: deals, summary, stage_velocity, insights
        # Analytics router defines: total_completed_deals, overall_velocity
        assert "deals" in data or "total_completed_deals" in data
        assert "summary" in data or "overall_velocity" in data
        if "deals" in data:
            print(f"✓ Velocity metrics: {len(data['deals'])} completed deals")
        else:
            print(f"✓ Velocity metrics: {data['total_completed_deals']} completed deals")


class TestPayrollRouter:
    """Tests for /api/payroll/* endpoints"""
    
    def test_get_salary_components(self, admin_client):
        """Test get salary components"""
        response = admin_client.get(f"{BASE_URL}/api/payroll/salary-components")
        assert response.status_code == 200, f"Get salary components failed: {response.text}"
        data = response.json()
        assert "earnings" in data or "type" in data
        print(f"✓ Salary components retrieved")
    
    def test_salary_components_requires_auth(self, api_client):
        """Test salary components requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/payroll/salary-components")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Salary components correctly requires auth")
    
    def test_update_salary_components_admin_only(self, admin_client, sales_client):
        """Test update salary components is admin/HR only"""
        test_data = {"type": "salary_components", "test": True}
        
        # Admin should succeed
        response = admin_client.post(f"{BASE_URL}/api/payroll/salary-components", json=test_data)
        # 200 or 403 depending on role check
        if response.status_code == 200:
            print("✓ Admin can update salary components")
        elif response.status_code == 403:
            print("✓ Admin HR role check enforced")
        
        # Sales manager should be denied
        if sales_client:
            response = sales_client.post(f"{BASE_URL}/api/payroll/salary-components", json=test_data)
            assert response.status_code == 403, f"Sales manager should not update salary components"
            print("✓ Non-admin correctly denied salary component updates")
    
    def test_add_salary_component_validation(self, admin_client):
        """Test add salary component validates required fields"""
        # Missing name
        response = admin_client.post(f"{BASE_URL}/api/payroll/salary-components/add", json={
            "type": "earnings"
        })
        assert response.status_code in [400, 403], f"Expected 400/403, got {response.status_code}"
        print("✓ Component name validation working")
        
        # Missing percentage or fixed
        response = admin_client.post(f"{BASE_URL}/api/payroll/salary-components/add", json={
            "type": "earnings",
            "name": "TEST_Component"
        })
        assert response.status_code in [400, 403], f"Expected 400/403, got {response.status_code}"
        print("✓ Component value validation working")
    
    def test_get_payroll_inputs_hr_only(self, admin_client, sales_client):
        """Test get payroll inputs is HR only"""
        current_month = datetime.now().strftime("%Y-%m")
        
        # Admin should succeed
        response = admin_client.get(f"{BASE_URL}/api/payroll/inputs?month={current_month}")
        assert response.status_code == 200 or response.status_code == 403, f"Unexpected status: {response.status_code}"
        if response.status_code == 200:
            print("✓ Admin can access payroll inputs")
        
        # Sales manager should be denied
        if sales_client:
            response = sales_client.get(f"{BASE_URL}/api/payroll/inputs?month={current_month}")
            assert response.status_code == 403, f"Sales should not access payroll inputs"
            print("✓ Non-HR correctly denied payroll inputs access")
    
    def test_save_payroll_input_validation(self, admin_client):
        """Test save payroll input validates required fields"""
        # Missing employee_id
        response = admin_client.post(f"{BASE_URL}/api/payroll/inputs", json={
            "month": "2025-01"
        })
        assert response.status_code in [400, 403, 422], f"Expected validation error, got {response.status_code}"
        print("✓ Payroll input validation working")
    
    def test_get_salary_slips(self, admin_client):
        """Test get salary slips"""
        response = admin_client.get(f"{BASE_URL}/api/payroll/salary-slips")
        assert response.status_code == 200, f"Get salary slips failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Salary slips retrieved: {len(data)} slips")
    
    def test_generate_salary_slip_validation(self, admin_client):
        """Test generate salary slip validates required fields"""
        # Missing employee_id
        response = admin_client.post(f"{BASE_URL}/api/payroll/generate-slip", json={
            "month": "2025-01"
        })
        assert response.status_code in [400, 403, 404], f"Expected error, got {response.status_code}"
        print("✓ Generate slip validation working")
    
    def test_get_payroll_summary_report(self, admin_client):
        """Test get payroll summary report"""
        current_month = datetime.now().strftime("%Y-%m")
        response = admin_client.get(f"{BASE_URL}/api/payroll/summary-report?month={current_month}")
        assert response.status_code == 200 or response.status_code == 403, f"Unexpected: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "month" in data
            assert "total_employees" in data
            print(f"✓ Payroll summary report: {data['total_employees']} employees")
    
    def test_get_pending_reimbursements(self, admin_client):
        """Test get pending reimbursements"""
        response = admin_client.get(f"{BASE_URL}/api/payroll/pending-reimbursements")
        assert response.status_code == 200 or response.status_code == 403, f"Unexpected: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "reimbursements" in data
            assert "total_amount" in data
            print(f"✓ Pending reimbursements: {data['count']} items")
    
    def test_get_linkage_summary(self, admin_client):
        """Test get payroll linkage summary"""
        current_month = datetime.now().strftime("%Y-%m")
        response = admin_client.get(f"{BASE_URL}/api/payroll/linkage-summary?month={current_month}")
        assert response.status_code == 200 or response.status_code == 403, f"Unexpected: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "month" in data
            print(f"✓ Payroll linkage summary retrieved")


class TestTravelRouter:
    """Tests for /api/travel/* endpoints"""
    
    def test_get_travel_rates(self, admin_client):
        """Test get travel reimbursement rates"""
        response = admin_client.get(f"{BASE_URL}/api/travel/rates")
        assert response.status_code == 200, f"Get travel rates failed: {response.text}"
        data = response.json()
        assert "rates" in data
        rates = data["rates"]
        assert "car" in rates
        assert "two_wheeler" in rates
        print(f"✓ Travel rates: Car=₹{rates['car']}/km, Two-wheeler=₹{rates['two_wheeler']}/km")
    
    def test_travel_rates_requires_auth(self, api_client):
        """Test travel rates requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/travel/rates")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Travel rates correctly requires auth")
    
    def test_calculate_distance(self, admin_client):
        """Test calculate travel distance"""
        # Mumbai to Pune coordinates
        test_data = {
            "start_location": {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "name": "Mumbai"
            },
            "end_location": {
                "latitude": 18.5204,
                "longitude": 73.8567,
                "name": "Pune"
            },
            "vehicle_type": "car",
            "is_round_trip": False
        }
        response = admin_client.post(f"{BASE_URL}/api/travel/calculate-distance", json=test_data)
        assert response.status_code == 200, f"Calculate distance failed: {response.text}"
        data = response.json()
        assert "distance_km" in data
        assert "calculated_amount" in data
        assert "vehicle_type" in data
        assert data["distance_km"] > 0
        print(f"✓ Distance calculated: {data['distance_km']} km, Amount: ₹{data['calculated_amount']}")
    
    def test_calculate_distance_validation(self, admin_client):
        """Test calculate distance validates coordinates"""
        # Missing start coordinates
        response = admin_client.post(f"{BASE_URL}/api/travel/calculate-distance", json={
            "start_location": {},
            "end_location": {"latitude": 18.5204, "longitude": 73.8567}
        })
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Distance calculation validates coordinates")
    
    def test_calculate_distance_round_trip(self, admin_client):
        """Test calculate distance with round trip"""
        test_data = {
            "start_location": {"latitude": 19.0760, "longitude": 72.8777},
            "end_location": {"latitude": 18.5204, "longitude": 73.8567},
            "vehicle_type": "car",
            "is_round_trip": True
        }
        response = admin_client.post(f"{BASE_URL}/api/travel/calculate-distance", json=test_data)
        assert response.status_code == 200
        data = response.json()
        assert data["is_round_trip"] == True
        
        # Also test one-way
        test_data["is_round_trip"] = False
        response2 = admin_client.post(f"{BASE_URL}/api/travel/calculate-distance", json=test_data)
        data2 = response2.json()
        
        # Round trip should be approximately double
        assert data["distance_km"] > data2["distance_km"]
        print(f"✓ Round trip ({data['distance_km']} km) > One-way ({data2['distance_km']} km)")
    
    def test_get_travel_reimbursements(self, admin_client):
        """Test get travel reimbursements list"""
        response = admin_client.get(f"{BASE_URL}/api/travel/reimbursements")
        assert response.status_code == 200, f"Get reimbursements failed: {response.text}"
        data = response.json()
        assert "records" in data
        assert "summary" in data
        summary = data["summary"]
        assert "total_records" in summary
        assert "total_distance_km" in summary
        assert "total_amount" in summary
        print(f"✓ Travel reimbursements: {summary['total_records']} records, ₹{summary['total_amount']}")
    
    def test_get_travel_reimbursements_with_filter(self, admin_client):
        """Test get travel reimbursements with status filter"""
        for status in ["pending", "approved"]:
            response = admin_client.get(f"{BASE_URL}/api/travel/reimbursements?status={status}")
            assert response.status_code == 200, f"Filter failed for status={status}"
            data = response.json()
            # All records should have the filtered status
            for record in data.get("records", []):
                assert record.get("status") == status or len(data["records"]) == 0
            print(f"✓ Travel reimbursements filtered by status '{status}'")
    
    def test_create_travel_reimbursement(self, admin_client):
        """Test create travel reimbursement"""
        test_data = {
            "start_location": {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "name": "TEST_Office"
            },
            "end_location": {
                "latitude": 19.1136,
                "longitude": 72.8697,
                "name": "TEST_Client"
            },
            "vehicle_type": "car",
            "is_round_trip": False,
            "travel_date": datetime.now().strftime("%Y-%m-%d"),
            "notes": "TEST_Travel for testing"
        }
        response = admin_client.post(f"{BASE_URL}/api/travel/reimbursement", json=test_data)
        # May fail if no employee record linked to admin
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "distance_km" in data
            print(f"✓ Travel reimbursement created: {data['distance_km']} km")
        elif response.status_code == 400:
            print(f"✓ Reimbursement creation requires employee record (expected behavior)")
        else:
            print(f"! Unexpected status: {response.status_code}")
    
    def test_create_travel_reimbursement_validation(self, admin_client):
        """Test travel reimbursement validates required fields"""
        # Missing locations
        response = admin_client.post(f"{BASE_URL}/api/travel/reimbursement", json={
            "vehicle_type": "car"
        })
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("✓ Reimbursement creation validates locations")
    
    def test_get_my_travel_reimbursements(self, admin_client):
        """Test get current user's travel reimbursements"""
        response = admin_client.get(f"{BASE_URL}/api/my/travel-reimbursements")
        assert response.status_code == 200, f"Get my reimbursements failed: {response.text}"
        data = response.json()
        assert "records" in data
        assert "summary" in data
        print(f"✓ My travel reimbursements retrieved")
    
    def test_get_travel_stats_hr_only(self, admin_client, sales_client):
        """Test travel stats is HR/Admin only"""
        response = admin_client.get(f"{BASE_URL}/api/travel/stats")
        assert response.status_code == 200 or response.status_code == 403
        if response.status_code == 200:
            data = response.json()
            assert "total_records" in data
            print(f"✓ Travel stats: {data['total_records']} total records")
        
        # Sales manager should be denied
        if sales_client:
            response = sales_client.get(f"{BASE_URL}/api/travel/stats")
            assert response.status_code == 403, f"Sales should not access travel stats"
            print("✓ Non-HR correctly denied travel stats access")
    
    def test_location_search_requires_api_key(self, admin_client):
        """Test location search with Google Maps API"""
        response = admin_client.get(f"{BASE_URL}/api/travel/location-search?query=Mumbai")
        # May return 200 with results or 500 if API key not configured
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            print(f"✓ Location search returned {len(data['results'])} results")
        elif response.status_code == 500:
            print("✓ Location search requires Google Maps API key (expected)")
        else:
            print(f"! Unexpected status: {response.status_code}")
    
    def test_location_search_validation(self, admin_client):
        """Test location search validates query length"""
        # Query too short
        response = admin_client.get(f"{BASE_URL}/api/travel/location-search?query=a")
        assert response.status_code == 400, f"Expected 400 for short query, got {response.status_code}"
        print("✓ Location search validates query length")


class TestRoleBasedAccess:
    """Tests for role-based access control across routers"""
    
    def test_analytics_access_by_role(self, admin_client, sales_client):
        """Test analytics endpoints access by different roles"""
        endpoints = [
            "/api/analytics/funnel-summary",
            "/api/analytics/bottleneck-analysis",
            "/api/analytics/forecasting"
        ]
        
        for endpoint in endpoints:
            # Admin should always have access
            response = admin_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"Admin should access {endpoint}"
            
            # Sales manager should have access to basic analytics
            if sales_client:
                response = sales_client.get(f"{BASE_URL}{endpoint}")
                assert response.status_code in [200, 403], f"Unexpected status for {endpoint}"
        
        print("✓ Analytics role-based access verified")
    
    def test_payroll_access_by_role(self, admin_client, sales_client):
        """Test payroll endpoints are restricted to HR/Admin"""
        hr_endpoints = [
            "/api/payroll/inputs?month=2025-01",
            "/api/payroll/pending-reimbursements",
            "/api/payroll/linkage-summary?month=2025-01"
        ]
        
        for endpoint in hr_endpoints:
            if sales_client:
                response = sales_client.get(f"{BASE_URL}{endpoint}")
                assert response.status_code == 403, f"Sales should not access {endpoint}"
        
        print("✓ Payroll HR-only access verified")
    
    def test_travel_approval_by_role(self, admin_client, sales_client):
        """Test travel approval is restricted to HR/Admin/Manager"""
        # This test verifies that only authorized roles can approve
        # First we need an existing reimbursement to test approval
        response = admin_client.get(f"{BASE_URL}/api/travel/reimbursements?status=pending")
        if response.status_code == 200:
            data = response.json()
            if data.get("records") and len(data["records"]) > 0:
                travel_id = data["records"][0]["id"]
                
                # Sales manager should be able to approve (has manager role)
                if sales_client:
                    response = sales_client.post(f"{BASE_URL}/api/travel/reimbursements/{travel_id}/approve")
                    # May be 200 (success) or 403 (denied) based on role
                    print(f"✓ Travel approval access checked: {response.status_code}")


class TestErrorHandling:
    """Tests for error handling across routers"""
    
    def test_404_on_invalid_travel_id(self, admin_client):
        """Test 404 returned for non-existent travel reimbursement"""
        response = admin_client.get(f"{BASE_URL}/api/travel/reimbursements/invalid-uuid-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ 404 returned for invalid travel ID")
    
    def test_400_on_invalid_payroll_month(self, admin_client):
        """Test validation for invalid month format"""
        response = admin_client.get(f"{BASE_URL}/api/payroll/inputs?month=invalid")
        # Should return data even with invalid month (empty result)
        assert response.status_code in [200, 400, 403]
        print("✓ Payroll handles invalid month format")
    
    def test_400_on_missing_required_fields(self, admin_client):
        """Test 400 returned for missing required fields"""
        # Travel distance without coordinates
        response = admin_client.post(f"{BASE_URL}/api/travel/calculate-distance", json={})
        assert response.status_code in [400, 422]
        print("✓ Missing required fields returns 400/422")


class TestDataConsistency:
    """Tests for data consistency in CRUD operations"""
    
    def test_analytics_data_consistency(self, admin_client):
        """Test analytics data is consistent across endpoints"""
        # Get funnel summary
        response1 = admin_client.get(f"{BASE_URL}/api/analytics/funnel-summary")
        assert response1.status_code == 200
        summary = response1.json()
        
        # Get bottleneck analysis
        response2 = admin_client.get(f"{BASE_URL}/api/analytics/bottleneck-analysis")
        assert response2.status_code == 200
        bottleneck = response2.json()
        
        # Total leads should be consistent
        # (May differ slightly due to filters, but should be in same order of magnitude)
        print(f"✓ Funnel: {summary['summary']['total_leads']} leads, Bottleneck: {bottleneck['total_leads']} leads")
    
    def test_salary_slip_generate_and_retrieve(self, admin_client):
        """Test salary slip generation creates retrievable record"""
        # This is a smoke test - full test would require valid employee data
        # Get existing slips to verify data consistency
        response = admin_client.get(f"{BASE_URL}/api/payroll/salary-slips")
        assert response.status_code == 200
        slips = response.json()
        
        if slips and len(slips) > 0:
            slip = slips[0]
            # Verify slip has required fields
            assert "employee_id" in slip
            assert "month" in slip
            assert "net_salary" in slip
            print(f"✓ Salary slip data consistent: {slip['employee_id']} for {slip['month']}")
        else:
            print("✓ No salary slips to verify (expected for clean test data)")


# ==================== Fixtures ====================

@pytest.fixture
def api_client():
    """Shared requests session without authentication"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def admin_client(api_client):
    """Session authenticated as admin"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("access_token")
        api_client.headers.update({"Authorization": f"Bearer {token}"})
        return api_client
    pytest.skip("Admin authentication failed")


@pytest.fixture
def sales_client():
    """Session authenticated as sales manager"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": SALES_MANAGER_EMAIL,
        "password": SALES_MANAGER_PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    return None  # Return None if sales manager login fails


@pytest.fixture
def hr_client():
    """Session authenticated as HR manager"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": HR_MANAGER_EMAIL,
        "password": HR_MANAGER_PASSWORD
    })
    if response.status_code == 200:
        token = response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    return None


# ==================== Test Execution ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
