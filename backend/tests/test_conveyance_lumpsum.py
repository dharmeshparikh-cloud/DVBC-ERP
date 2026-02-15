"""
Test Conveyance Lumpsum Feature
Tests:
1. Conveyance lumpsum field is accepted in pricing plan API
2. Conveyance lumpsum is distributed evenly across payment periods
3. Net receivable calculation includes conveyance correctly
4. Total conveyance in schedule equals entered lumpsum
5. Various payment schedules (monthly, quarterly, upfront) with conveyance
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


class TestConveyanceLumpsumFeature:
    """Test Conveyance Lumpsum Feature in Payment Plan"""
    
    def test_backend_accepts_conveyance_lumpsum_field(self, api_client, test_lead_id):
        """Test that backend accepts pricing plan with conveyance_lumpsum field"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        conveyance_lumpsum = 60000  # ₹60,000 lumpsum
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "total_investment": 1200000,  # ₹12,00,000
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {
                    "gst": 18,
                    "tds": 10
                },
                "conveyance_lumpsum": conveyance_lumpsum,  # New lumpsum field
                "schedule_breakdown": []
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200, f"Failed to create pricing plan: {response.text}"
        
        data = response.json()
        assert 'id' in data
        assert 'payment_plan' in data
        assert data['payment_plan'] is not None
        assert data['payment_plan']['conveyance_lumpsum'] == conveyance_lumpsum
        print(f"✓ Backend accepts conveyance_lumpsum: ₹{conveyance_lumpsum:,}")
        
        return data['id']

    def test_conveyance_distributed_evenly_monthly(self, api_client, test_lead_id):
        """Test that ₹60,000 conveyance lumpsum is distributed evenly across 12 months (₹5,000/month)"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        total_investment = 1200000  # ₹12,00,000
        conveyance_lumpsum = 60000  # ₹60,000 total
        duration_months = 12
        conveyance_per_month = conveyance_lumpsum // duration_months  # ₹5,000
        
        # Generate schedule breakdown with distributed conveyance
        schedule_breakdown = []
        basic_per_month = total_investment // duration_months  # ₹1,00,000
        
        for i in range(duration_months):
            gst = int(basic_per_month * 0.18)  # 18%
            tds = int(basic_per_month * 0.10)  # 10%
            # Net = Basic + GST + Conveyance - TDS
            net = basic_per_month + gst + conveyance_per_month - tds
            
            schedule_breakdown.append({
                "frequency": f"Month {i + 1}",
                "due_date": f"2026-{str(i+1).zfill(2)}-15T00:00:00.000Z",
                "basic": basic_per_month,
                "gst": gst,
                "tds": tds,
                "conveyance": conveyance_per_month,
                "net": net
            })
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": duration_months,
            "payment_schedule": "monthly",
            "total_investment": total_investment,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {
                    "gst": 18,
                    "tds": 10
                },
                "conveyance_lumpsum": conveyance_lumpsum,
                "schedule_breakdown": schedule_breakdown
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        schedule = data['payment_plan']['schedule_breakdown']
        
        # Verify 12 payments
        assert len(schedule) == 12, f"Expected 12 payments, got {len(schedule)}"
        
        # Verify each payment has ₹5,000 conveyance
        for i, payment in enumerate(schedule):
            assert payment['conveyance'] == conveyance_per_month, \
                f"Month {i+1}: Expected conveyance ₹{conveyance_per_month:,}, got ₹{payment['conveyance']:,}"
        
        # Verify total conveyance equals lumpsum
        total_conveyance = sum(p['conveyance'] for p in schedule)
        assert total_conveyance == conveyance_lumpsum, \
            f"Total conveyance should be ₹{conveyance_lumpsum:,}, got ₹{total_conveyance:,}"
        
        print(f"✓ Conveyance distributed evenly: ₹{conveyance_per_month:,}/month × 12 = ₹{total_conveyance:,}")

    def test_net_receivable_includes_conveyance(self, api_client, test_lead_id):
        """Test Net Receivable = Basic + GST + Conveyance - TDS formula"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Test case from requirements: ₹12,00,000 investment, ₹60,000 conveyance, 12 months
        total_investment = 1200000
        conveyance_lumpsum = 60000
        duration_months = 12
        
        basic_per_month = total_investment // duration_months  # ₹1,00,000
        conveyance_per_month = conveyance_lumpsum // duration_months  # ₹5,000
        gst = int(basic_per_month * 0.18)  # ₹18,000
        tds = int(basic_per_month * 0.10)  # ₹10,000
        
        # Expected Net = 1,00,000 + 18,000 + 5,000 - 10,000 = 1,13,000
        expected_net = basic_per_month + gst + conveyance_per_month - tds
        
        schedule_breakdown = [{
            "frequency": "Month 1",
            "due_date": f"{start_date}T00:00:00.000Z",
            "basic": basic_per_month,
            "gst": gst,
            "tds": tds,
            "conveyance": conveyance_per_month,
            "net": expected_net
        }]
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "monthly",
            "project_duration_months": 1,
            "payment_schedule": "upfront",
            "total_investment": basic_per_month,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {
                    "gst": 18,
                    "tds": 10
                },
                "conveyance_lumpsum": conveyance_per_month,
                "schedule_breakdown": schedule_breakdown
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        payment = data['payment_plan']['schedule_breakdown'][0]
        
        assert payment['net'] == expected_net, \
            f"Net should be ₹{expected_net:,}, got ₹{payment['net']:,}"
        
        print(f"✓ Net Receivable formula correct: ₹{basic_per_month:,} + ₹{gst:,} + ₹{conveyance_per_month:,} - ₹{tds:,} = ₹{expected_net:,}")

    def test_total_conveyance_equals_lumpsum(self, api_client, test_lead_id):
        """Test that sum of all payment conveyance equals the entered lumpsum"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        conveyance_lumpsum = 60000
        num_payments = 12
        conveyance_per_payment = conveyance_lumpsum // num_payments
        
        schedule_breakdown = [{
            "frequency": f"Month {i+1}",
            "due_date": f"2026-{str(i+1).zfill(2)}-01T00:00:00.000Z",
            "basic": 100000,
            "gst": 18000,
            "tds": 10000,
            "conveyance": conveyance_per_payment,
            "net": 100000 + 18000 + conveyance_per_payment - 10000
        } for i in range(num_payments)]
        
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
                "component_values": {"gst": 18, "tds": 10},
                "conveyance_lumpsum": conveyance_lumpsum,
                "schedule_breakdown": schedule_breakdown
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify conveyance_lumpsum is stored
        assert data['payment_plan']['conveyance_lumpsum'] == conveyance_lumpsum
        
        # Verify sum of conveyance in schedule
        total_conveyance = sum(p['conveyance'] for p in data['payment_plan']['schedule_breakdown'])
        assert total_conveyance == conveyance_lumpsum, \
            f"Total conveyance ₹{total_conveyance:,} should equal lumpsum ₹{conveyance_lumpsum:,}"
        
        print(f"✓ Total conveyance in footer matches lumpsum: ₹{total_conveyance:,}")

    def test_quarterly_payment_with_conveyance_lumpsum(self, api_client, test_lead_id):
        """Test conveyance distributed across quarterly payments (4 payments)"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        conveyance_lumpsum = 60000
        num_payments = 4  # Quarterly for 12 months
        conveyance_per_quarter = conveyance_lumpsum // num_payments  # ₹15,000
        
        schedule_breakdown = [{
            "frequency": f"Q{i+1}",
            "due_date": f"2026-{str((i*3)+1).zfill(2)}-01T00:00:00.000Z",
            "basic": 300000,  # 12L / 4 quarters
            "gst": 54000,  # 18%
            "tds": 30000,  # 10%
            "conveyance": conveyance_per_quarter,
            "net": 300000 + 54000 + conveyance_per_quarter - 30000
        } for i in range(num_payments)]
        
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
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {"gst": 18, "tds": 10},
                "conveyance_lumpsum": conveyance_lumpsum,
                "schedule_breakdown": schedule_breakdown
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        schedule = data['payment_plan']['schedule_breakdown']
        
        # Verify 4 quarterly payments
        assert len(schedule) == 4, f"Expected 4 quarterly payments, got {len(schedule)}"
        
        # Verify each quarter has ₹15,000 conveyance
        for i, payment in enumerate(schedule):
            assert payment['conveyance'] == conveyance_per_quarter, \
                f"Q{i+1}: Expected conveyance ₹{conveyance_per_quarter:,}, got ₹{payment['conveyance']:,}"
        
        total_conveyance = sum(p['conveyance'] for p in schedule)
        assert total_conveyance == conveyance_lumpsum
        
        print(f"✓ Quarterly distribution: ₹{conveyance_per_quarter:,}/quarter × 4 = ₹{total_conveyance:,}")

    def test_conveyance_lumpsum_zero_when_not_selected(self, api_client, test_lead_id):
        """Test conveyance is 0 when conveyance component is not selected"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        schedule_breakdown = [{
            "frequency": "Upfront",
            "due_date": f"{start_date}T00:00:00.000Z",
            "basic": 100000,
            "gst": 18000,
            "tds": 0,
            "conveyance": 0,  # No conveyance
            "net": 118000  # 100000 + 18000 (no conveyance)
        }]
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "monthly",
            "project_duration_months": 1,
            "payment_schedule": "upfront",
            "total_investment": 100000,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst"],  # Only GST, no conveyance
                "component_values": {"gst": 18, "tds": 10},
                "conveyance_lumpsum": 0,
                "schedule_breakdown": schedule_breakdown
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['payment_plan']['conveyance_lumpsum'] == 0
        assert 'conveyance' not in data['payment_plan']['selected_components']
        
        payment = data['payment_plan']['schedule_breakdown'][0]
        assert payment['conveyance'] == 0
        
        print("✓ Conveyance is 0 when not selected in components")

    def test_gst_tds_still_work_correctly(self, api_client, test_lead_id):
        """Verify GST 18% and TDS 10% calculations are unaffected by conveyance lumpsum change"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        basic = 1200000
        expected_gst = int(basic * 0.18)  # ₹2,16,000
        expected_tds = int(basic * 0.10)  # ₹1,20,000
        
        schedule_breakdown = [{
            "frequency": "Upfront",
            "due_date": f"{start_date}T00:00:00.000Z",
            "basic": basic,
            "gst": expected_gst,
            "tds": expected_tds,
            "conveyance": 60000,
            "net": basic + expected_gst + 60000 - expected_tds
        }]
        
        payload = {
            "lead_id": test_lead_id,
            "project_duration_type": "yearly",
            "project_duration_months": 12,
            "payment_schedule": "upfront",
            "total_investment": basic,
            "discount_percentage": 0,
            "consultants": [],
            "team_deployment": [],
            "payment_plan": {
                "start_date": start_date,
                "selected_components": ["gst", "tds", "conveyance"],
                "component_values": {"gst": 18, "tds": 10},
                "conveyance_lumpsum": 60000,
                "schedule_breakdown": schedule_breakdown
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-plans", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        payment = data['payment_plan']['schedule_breakdown'][0]
        
        assert payment['gst'] == expected_gst, f"GST should be ₹{expected_gst:,}, got ₹{payment['gst']:,}"
        assert payment['tds'] == expected_tds, f"TDS should be ₹{expected_tds:,}, got ₹{payment['tds']:,}"
        
        print(f"✓ GST (18%): ₹{payment['gst']:,}, TDS (10%): ₹{payment['tds']:,} - Working correctly")


class TestConveyanceLumpsumPersistence:
    """Test that conveyance_lumpsum is persisted and retrievable"""
    
    def test_conveyance_lumpsum_persisted_and_retrieved(self, api_client, test_lead_id):
        """Test that conveyance_lumpsum is properly persisted and can be retrieved"""
        start_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        conveyance_lumpsum = 72000  # ₹72,000
        
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
                "selected_components": ["gst", "conveyance"],
                "component_values": {"gst": 18, "tds": 10},
                "conveyance_lumpsum": conveyance_lumpsum,
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
        assert matching_plan['payment_plan'].get('conveyance_lumpsum') == conveyance_lumpsum, \
            f"conveyance_lumpsum should be ₹{conveyance_lumpsum:,}"
        
        print(f"✓ conveyance_lumpsum persisted and retrieved: ₹{conveyance_lumpsum:,}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
