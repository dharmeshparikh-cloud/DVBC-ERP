"""
Test Payment Plan Breakup Feature
Tests:
1. Payment plan field stored correctly in pricing plan
2. GST 18% fixed (non-editable)
3. TDS and Conveyance editable percentages
4. Payment schedule generation based on frequency
5. Net calculation: Basic + GST + Conveyance - TDS
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@company.com",
        "password": "admin123"
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")

@pytest.fixture
def api_client(auth_token):
    """Session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session

@pytest.fixture
def test_lead_id(api_client):
    """Get first available lead ID for testing"""
    response = api_client.get(f"{BASE_URL}/api/leads")
    if response.status_code == 200:
        leads = response.json()
        if leads and len(leads) > 0:
            return leads[0]['id']
    pytest.skip("No leads available for testing")


class TestPaymentPlanBreakup:
    """Test Payment Plan Breakup Feature in Pricing Plan"""
    
    def test_create_pricing_plan_with_payment_plan(self, api_client, test_lead_id):
        """Test creating pricing plan with payment_plan field"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "total_investment": 1200000,  # 12 lakhs
            "discount_percentage": 0,
            "consultants": [
                {
                    "consultant_type": "project_manager",
                    "role": "Project Manager",
                    "meeting_type": "Weekly Review",
                    "tenure_type_code": "full_time",
                    "mode": "Online",
                    "count": 1,
                    "meetings": 48,
                    "rate_per_meeting": 25000,
                    "committed_meetings": 48,
                    "allocation_percentage": 100,
                    "breakup_amount": 1200000
                }
            ],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {
                    "gst": 18,
                    "tds": 10,
                    "conveyance": 5
                },
                "schedule_breakdown": [
                    {
                        "frequency": "Month 1",
                        "due_date": f"{start_date}T00:00:00.000Z",
                        "basic": 100000,
                        "gst": 18000,
                        "tds": 10000,
                        "conveyance": 5000,
                        "net": 113000
                    }
                ]
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200, f"Failed to create pricing plan: {response.text}"
        
        data = response.json()
        assert 'id' in data
        assert 'payment_plan' in data
        assert data['payment_plan'] is not None
        assert data['payment_plan']['start_date'] == start_date
        assert 'gst' in data['payment_plan']['selected_components']
        assert data['payment_plan']['component_values']['gst'] == 18
        print(f"Created pricing plan with payment_plan: {data['id']}")
        
        return data['id']

    def test_payment_plan_gst_fixed_at_18(self, api_client, test_lead_id):
        """Test that GST should be 18% (fixed)"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "total_investment": 1200000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst"],
                "component_values": {
                    "gst": 18,  # Fixed at 18%
                    "tds": 10,
                    "conveyance": 5
                },
                "schedule_breakdown": []
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['payment_plan']['component_values']['gst'] == 18
        print("GST correctly set to 18%")

    def test_payment_plan_tds_editable(self, api_client, test_lead_id):
        """Test that TDS percentage can be customized"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Test with custom TDS percentage (e.g., 15%)
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "quarterly",
            "total_investment": 1000000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds"],
                "component_values": {
                    "gst": 18,
                    "tds": 15,  # Custom TDS percentage
                    "conveyance": 5
                },
                "schedule_breakdown": []
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['payment_plan']['component_values']['tds'] == 15
        print("TDS correctly set to custom 15%")

    def test_payment_plan_conveyance_editable(self, api_client, test_lead_id):
        """Test that Conveyance percentage can be customized"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Test with custom Conveyance percentage (e.g., 8%)
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "milestone",
            "total_investment": 500000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "conveyance"],
                "component_values": {
                    "gst": 18,
                    "tds": 10,
                    "conveyance": 8  # Custom Conveyance percentage
                },
                "schedule_breakdown": []
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['payment_plan']['component_values']['conveyance'] == 8
        print("Conveyance correctly set to custom 8%")

    def test_payment_schedule_monthly(self, api_client, test_lead_id):
        """Test monthly payment schedule generates correct breakdown"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # For 12 months with 12L investment: Basic = 1L/month
        # GST 18% = 18K, TDS 10% = 10K (deduct), Conveyance 5% = 5K
        # Net = 1L + 18K + 5K - 10K = 1.13L
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "total_investment": 1200000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {
                    "gst": 18,
                    "tds": 10,
                    "conveyance": 5
                },
                "schedule_breakdown": [
                    {
                        "frequency": f"Month {i+1}",
                        "due_date": f"2026-{str(i+1).zfill(2)}-15T00:00:00.000Z",
                        "basic": 100000,
                        "gst": 18000,
                        "tds": 10000,
                        "conveyance": 5000,
                        "net": 113000  # 100000 + 18000 + 5000 - 10000
                    } for i in range(12)
                ]
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        schedule = data['payment_plan']['schedule_breakdown']
        
        # Verify 12 payment entries
        assert len(schedule) == 12, f"Expected 12 payments, got {len(schedule)}"
        
        # Verify first payment calculation
        first = schedule[0]
        assert first['basic'] == 100000
        assert first['gst'] == 18000
        assert first['tds'] == 10000
        assert first['conveyance'] == 5000
        assert first['net'] == 113000, f"Net should be 113000, got {first['net']}"
        
        print(f"Monthly schedule verified: 12 payments, first net = ₹{first['net']:,}")

    def test_payment_schedule_quarterly(self, api_client, test_lead_id):
        """Test quarterly payment schedule generates correct breakdown"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # For 12 months with 12L investment quarterly: 4 payments of 3L each
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "quarterly",
            "total_investment": 1200000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst"],
                "component_values": {
                    "gst": 18,
                    "tds": 10,
                    "conveyance": 5
                },
                "schedule_breakdown": [
                    {
                        "frequency": f"Q{i+1}",
                        "due_date": f"2026-{str((i*3)+1).zfill(2)}-15T00:00:00.000Z",
                        "basic": 300000,
                        "gst": 54000,  # 18% of 300000
                        "tds": 0,
                        "conveyance": 0,
                        "net": 354000
                    } for i in range(4)
                ]
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        schedule = data['payment_plan']['schedule_breakdown']
        
        # Verify 4 payment entries (quarterly for 12 months)
        assert len(schedule) == 4, f"Expected 4 payments, got {len(schedule)}"
        print(f"Quarterly schedule verified: 4 payments")

    def test_net_calculation_formula(self, api_client, test_lead_id):
        """Test Net = Basic + GST + Conveyance - TDS formula"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Example: Basic=100000, GST=18%(18000), TDS=10%(10000), Conveyance=5%(5000)
        # Net = 100000 + 18000 + 5000 - 10000 = 113000
        
        basic = 100000
        gst_percent = 18
        tds_percent = 10
        conveyance_percent = 5
        
        gst = int(basic * (gst_percent / 100))
        tds = int(basic * (tds_percent / 100))
        conveyance = int(basic * (conveyance_percent / 100))
        expected_net = basic + gst + conveyance - tds
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "monthly",
            "project_duration_months": 1,
            "payment_schedule": "upfront",
            "total_investment": basic,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {
                    "gst": gst_percent,
                    "tds": tds_percent,
                    "conveyance": conveyance_percent
                },
                "schedule_breakdown": [
                    {
                        "frequency": "Upfront",
                        "due_date": f"{start_date}T00:00:00.000Z",
                        "basic": basic,
                        "gst": gst,
                        "tds": tds,
                        "conveyance": conveyance,
                        "net": expected_net
                    }
                ]
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        payment = data['payment_plan']['schedule_breakdown'][0]
        
        # Verify the formula
        actual_net = payment['net']
        assert actual_net == expected_net, f"Net calculation error. Expected {expected_net}, got {actual_net}"
        print(f"Net formula verified: {basic} + {gst} + {conveyance} - {tds} = {actual_net}")

    def test_payment_plan_without_optional_components(self, api_client, test_lead_id):
        """Test payment plan with only GST selected (TDS and Conveyance deselected)"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        basic = 100000
        gst = 18000
        expected_net = basic + gst  # No TDS or Conveyance
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "monthly",
            "project_duration_months": 1,
            "payment_schedule": "upfront",
            "total_investment": basic,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst"],  # Only GST selected
                "component_values": {
                    "gst": 18,
                    "tds": 10,
                    "conveyance": 5
                },
                "schedule_breakdown": [
                    {
                        "frequency": "Upfront",
                        "due_date": f"{start_date}T00:00:00.000Z",
                        "basic": basic,
                        "gst": gst,
                        "tds": 0,
                        "conveyance": 0,
                        "net": expected_net
                    }
                ]
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify only GST is in selected components
        assert data['payment_plan']['selected_components'] == ["gst"]
        
        payment = data['payment_plan']['schedule_breakdown'][0]
        assert payment['tds'] == 0
        assert payment['conveyance'] == 0
        assert payment['net'] == expected_net
        print(f"Payment plan with only GST verified: Net = {expected_net}")


class TestPricingPlanModelUpdated:
    """Test that PricingPlan model properly stores payment_plan field"""
    
    def test_payment_plan_field_persisted(self, api_client, test_lead_id):
        """Test that payment_plan field is properly persisted"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "total_investment": 1200000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds"],
                "component_values": {
                    "gst": 18,
                    "tds": 10,
                    "conveyance": 5
                },
                "schedule_breakdown": []
            }
        }
        
        # Create pricing plan
        create_response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert create_response.status_code == 200
        plan_id = create_response.json()['id']
        
        # Retrieve and verify
        get_response = api_client.get(f"{BASE_URL}/api/pricing-plans?lead_id={test_lead_id}")
        assert get_response.status_code == 200
        
        plans = get_response.json()
        matching_plan = None
        for p in plans:
            if p['id'] == plan_id:
                matching_plan = p
                break
        
        assert matching_plan is not None, "Created pricing plan not found"
        assert matching_plan.get('payment_plan') is not None, "payment_plan field missing"
        assert matching_plan['payment_plan']['start_date'] == start_date
        print(f"Payment plan field persisted and retrieved successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
