"""
E2E Test Suite for Sales Flow: Lead → Meeting → MOM → Pricing Plan → SOW → Agreement → Kickoff
Tests the complete sales workflow as defined in the ERP system
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://payroll-fix-10.preview.emergentagent.com"

class TestSalesFlowE2E:
    """Complete E2E test of the sales workflow"""
    
    # Shared test data
    admin_token = None
    test_lead_id = None
    test_meeting_id = None
    test_pricing_plan_id = None
    test_sow_id = None
    test_quotation_id = None
    test_agreement_id = None
    test_kickoff_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for all tests"""
        if not TestSalesFlowE2E.admin_token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@company.com",
                "password": "admin123"
            })
            assert response.status_code == 200, f"Login failed: {response.text}"
            TestSalesFlowE2E.admin_token = response.json()["access_token"]
    
    def get_headers(self):
        return {
            "Authorization": f"Bearer {TestSalesFlowE2E.admin_token}",
            "Content-Type": "application/json"
        }
    
    # ============== PHASE 1: LEAD MANAGEMENT ==============
    
    def test_01_create_lead(self):
        """Create a new lead to start the sales flow"""
        payload = {
            "first_name": "TEST_E2E",
            "last_name": f"Lead_{datetime.now().strftime('%H%M%S')}",
            "company": "TEST_E2E Corp",
            "job_title": "CEO",
            "email": f"test_e2e_{datetime.now().strftime('%H%M%S')}@example.com",
            "phone": "+91-9876543210",
            "source": "E2E Test",
            "notes": "Created by E2E test for sales flow testing"
        }
        
        response = requests.post(f"{BASE_URL}/api/leads", 
                                json=payload, 
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create lead failed: {response.text}"
        data = response.json()
        
        # Verify lead data
        assert data["first_name"] == payload["first_name"]
        assert data["company"] == payload["company"]
        assert "id" in data
        assert data["status"] == "new"
        assert data["lead_score"] >= 0  # Score should be calculated
        
        TestSalesFlowE2E.test_lead_id = data["id"]
        print(f"Created lead: {data['id']} with score: {data['lead_score']}")
    
    def test_02_get_lead(self):
        """Verify lead was persisted"""
        assert TestSalesFlowE2E.test_lead_id, "No lead ID from previous test"
        
        response = requests.get(
            f"{BASE_URL}/api/leads/{TestSalesFlowE2E.test_lead_id}",
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Get lead failed: {response.text}"
        data = response.json()
        assert data["id"] == TestSalesFlowE2E.test_lead_id
        assert data["first_name"] == "TEST_E2E"
    
    def test_03_update_lead_status_to_qualified(self):
        """Update lead status to qualified (simulating sales process)"""
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        response = requests.put(
            f"{BASE_URL}/api/leads/{TestSalesFlowE2E.test_lead_id}",
            json={"status": "qualified"},
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Update lead failed: {response.text}"
        data = response.json()
        assert data["status"] == "qualified"
        print(f"Lead status updated to: {data['status']}")
    
    def test_04_list_leads(self):
        """List all leads to verify our test lead exists"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=self.get_headers())
        
        assert response.status_code == 200, f"List leads failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        # Find our test lead
        test_leads = [l for l in data if l.get("first_name") == "TEST_E2E"]
        assert len(test_leads) > 0, "Test lead not found in list"
        print(f"Total leads: {len(data)}, test leads: {len(test_leads)}")
    
    # ============== PHASE 2: MEETINGS & MOM ==============
    
    def test_05_create_project_for_meeting(self):
        """Create a project to link meetings (required for consulting meetings)"""
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        payload = {
            "name": f"TEST_E2E Project {datetime.now().strftime('%H%M%S')}",
            "client_name": "TEST_E2E Corp",
            "lead_id": TestSalesFlowE2E.test_lead_id,
            "project_type": "mixed",
            "start_date": datetime.now().isoformat(),
            "total_meetings_committed": 12,
            "notes": "Test project for E2E sales flow"
        }
        
        response = requests.post(f"{BASE_URL}/api/projects",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create project failed: {response.text}"
        data = response.json()
        assert "id" in data
        TestSalesFlowE2E.test_project_id = data["id"]
        print(f"Created project: {data['id']}")
    
    def test_06_create_sales_meeting(self):
        """Create a sales meeting linked to the lead"""
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        meeting_date = (datetime.now() + timedelta(days=1)).isoformat()
        
        payload = {
            "type": "sales",
            "lead_id": TestSalesFlowE2E.test_lead_id,
            "meeting_date": meeting_date,
            "mode": "online",
            "duration_minutes": 60,
            "title": "TEST_E2E Sales Discovery Call",
            "agenda": ["Discuss requirements", "Present solutions", "Define scope"],
            "notes": "E2E test meeting"
        }
        
        response = requests.post(f"{BASE_URL}/api/meetings",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create meeting failed: {response.text}"
        data = response.json()
        assert data["type"] == "sales"
        assert data["lead_id"] == TestSalesFlowE2E.test_lead_id
        
        TestSalesFlowE2E.test_meeting_id = data["id"]
        print(f"Created meeting: {data['id']}")
    
    def test_07_add_mom_to_meeting(self):
        """Add Minutes of Meeting to the meeting"""
        assert TestSalesFlowE2E.test_meeting_id, "No meeting ID"
        
        payload = {
            "title": "Sales Discovery Call - TEST_E2E",
            "agenda": ["Requirements discussion", "Solution presentation"],
            "discussion_points": ["Client needs consulting for operations", "12-month engagement preferred"],
            "decisions_made": ["Proceed with pricing proposal", "Schedule follow-up"],
            "action_items": [
                {
                    "description": "Prepare pricing proposal",
                    "priority": "high",
                    "status": "pending"
                }
            ],
            "next_meeting_date": (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = requests.patch(
            f"{BASE_URL}/api/meetings/{TestSalesFlowE2E.test_meeting_id}/mom",
            json=payload,
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Add MOM failed: {response.text}"
        data = response.json()
        assert "meeting_id" in data
        print(f"MOM added to meeting: {data['meeting_id']}")
    
    def test_08_get_meeting_with_mom(self):
        """Verify MOM was saved correctly"""
        assert TestSalesFlowE2E.test_meeting_id, "No meeting ID"
        
        response = requests.get(
            f"{BASE_URL}/api/meetings/{TestSalesFlowE2E.test_meeting_id}",
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Get meeting failed: {response.text}"
        data = response.json()
        assert data["mom_generated"] == True
        assert len(data["discussion_points"]) > 0
        print(f"Meeting MOM verified, decisions: {len(data.get('decisions_made', []))}")
    
    # ============== PHASE 3: PRICING PLAN ==============
    
    def test_09_create_pricing_plan(self):
        """Create a pricing plan for the hot lead"""
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        # First update lead to proposal status
        requests.put(
            f"{BASE_URL}/api/leads/{TestSalesFlowE2E.test_lead_id}",
            json={"status": "proposal"},
            headers=self.get_headers()
        )
        
        payload = {
            "lead_id": TestSalesFlowE2E.test_lead_id,
            "project_duration_type": "yearly",  # Required field
            "total_investment": 1200000,  # 12 lakhs
            "project_duration_months": 12,
            "payment_schedule": "monthly",
            "discount_percentage": 5,
            "consultants": [],  # Required field
            "team_deployment": [
                {
                    "role": "Lead Consultant",
                    "tenure_type_code": "monthly",
                    "meeting_type": "Monthly Review",
                    "mode": "Online",
                    "count": 1,
                    "rate_per_meeting": 25000,
                    "meetings": 12
                },
                {
                    "role": "Senior Consultant",
                    "tenure_type_code": "weekly",
                    "meeting_type": "Weekly Review",
                    "mode": "Mixed",
                    "count": 1,
                    "rate_per_meeting": 12500,
                    "meetings": 48
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/pricing-plans",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create pricing plan failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["lead_id"] == TestSalesFlowE2E.test_lead_id
        assert data["total_investment"] == 1200000
        
        TestSalesFlowE2E.test_pricing_plan_id = data["id"]
        print(f"Created pricing plan: {data['id']}, value: {data['total_investment']}")
    
    def test_10_get_pricing_plans(self):
        """List pricing plans to verify persistence"""
        response = requests.get(f"{BASE_URL}/api/pricing-plans", headers=self.get_headers())
        
        assert response.status_code == 200, f"List pricing plans failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        # Find our test plan
        test_plans = [p for p in data if p.get("id") == TestSalesFlowE2E.test_pricing_plan_id]
        assert len(test_plans) > 0, "Test pricing plan not found"
        print(f"Total pricing plans: {len(data)}")
    
    # ============== PHASE 4: SOW (Statement of Work) ==============
    
    def test_11_create_sow(self):
        """Create SOW from the pricing plan"""
        assert TestSalesFlowE2E.test_pricing_plan_id, "No pricing plan ID"
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        payload = {
            "pricing_plan_id": TestSalesFlowE2E.test_pricing_plan_id,
            "lead_id": TestSalesFlowE2E.test_lead_id,
            "title": f"TEST_E2E Statement of Work {datetime.now().strftime('%H%M%S')}",
            "description": "Comprehensive consulting engagement for operational excellence",
            "scope_of_work": "Full operational audit, process optimization, team training",
            "deliverables": "Monthly reports, process documentation, training materials",
            "timeline": "12 months starting from agreement signing",
            "assumptions": "Client will provide necessary data access",
            "status": "draft"
        }
        
        response = requests.post(f"{BASE_URL}/api/sow",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create SOW failed: {response.text}"
        data = response.json()
        # API returns sow_id in response
        assert "sow_id" in data or "id" in data, f"No sow_id in response: {data}"
        
        TestSalesFlowE2E.test_sow_id = data.get("sow_id") or data.get("id")
        print(f"Created SOW: {TestSalesFlowE2E.test_sow_id}")
    
    def test_12_get_sow(self):
        """Verify SOW was created correctly"""
        assert TestSalesFlowE2E.test_sow_id, "No SOW ID"
        
        response = requests.get(
            f"{BASE_URL}/api/sow/{TestSalesFlowE2E.test_sow_id}",
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Get SOW failed: {response.text}"
        data = response.json()
        assert data["id"] == TestSalesFlowE2E.test_sow_id
        print(f"SOW status: {data.get('status', 'unknown')}")
    
    def test_13_add_sow_item(self):
        """Add line item to SOW"""
        assert TestSalesFlowE2E.test_sow_id, "No SOW ID"
        
        payload = {
            "category": "Consulting",
            "title": "Monthly Review Meeting",  # Required field
            "item_name": "Monthly Review Meeting",
            "description": "Monthly operational review with leadership team",
            "quantity": 12,
            "unit": "meetings",
            "unit_price": 25000,
            "status": "pending"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sow/{TestSalesFlowE2E.test_sow_id}/items",
            json=payload,
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Add SOW item failed: {response.text}"
        data = response.json()
        item_id = data.get("id") or data.get("item_id")
        assert item_id, f"No item ID in response: {data}"
        print(f"Added SOW item: {item_id}")
    
    # ============== PHASE 5: QUOTATION (Proforma Invoice) ==============
    
    def test_14_create_quotation(self):
        """Create quotation/proforma invoice"""
        assert TestSalesFlowE2E.test_pricing_plan_id, "No pricing plan ID"
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        payload = {
            "pricing_plan_id": TestSalesFlowE2E.test_pricing_plan_id,
            "lead_id": TestSalesFlowE2E.test_lead_id,
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "notes": "E2E test quotation"
        }
        
        response = requests.post(f"{BASE_URL}/api/quotations",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create quotation failed: {response.text}"
        data = response.json()
        assert "id" in data
        
        TestSalesFlowE2E.test_quotation_id = data["id"]
        print(f"Created quotation: {data['id']}")
    
    def test_15_finalize_quotation(self):
        """Finalize the quotation"""
        assert TestSalesFlowE2E.test_quotation_id, "No quotation ID"
        
        response = requests.patch(
            f"{BASE_URL}/api/quotations/{TestSalesFlowE2E.test_quotation_id}/finalize",
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Finalize quotation failed: {response.text}"
        data = response.json()
        # API returns message on success
        assert "message" in data or data.get("is_final") == True
        print(f"Quotation finalized, response: {data}")
    
    # ============== PHASE 6: AGREEMENT ==============
    
    def test_16_create_agreement(self):
        """Create agreement from finalized quotation"""
        assert TestSalesFlowE2E.test_quotation_id, "No quotation ID"
        assert TestSalesFlowE2E.test_lead_id, "No lead ID"
        
        start_date = datetime.now().isoformat()
        end_date = (datetime.now() + timedelta(days=365)).isoformat()
        
        payload = {
            "quotation_id": TestSalesFlowE2E.test_quotation_id,
            "lead_id": TestSalesFlowE2E.test_lead_id,
            "agreement_type": "standard",
            "payment_terms": "Net 30 days from invoice date",
            "start_date": start_date,
            "end_date": end_date,
            "meeting_frequency": "Monthly",
            "project_tenure_months": 12,
            "team_deployment": [
                {
                    "role": "Lead Consultant",
                    "meeting_type": "Monthly Review",
                    "frequency": "1 per month",
                    "mode": "Online",
                    "committed_meetings": 12
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/agreements",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create agreement failed: {response.text}"
        data = response.json()
        assert "id" in data
        
        TestSalesFlowE2E.test_agreement_id = data["id"]
        print(f"Created agreement: {data['id']}")
    
    def test_17_approve_agreement(self):
        """Approve the agreement (simulating manager approval)"""
        assert TestSalesFlowE2E.test_agreement_id, "No agreement ID"
        
        response = requests.patch(
            f"{BASE_URL}/api/agreements/{TestSalesFlowE2E.test_agreement_id}/approve",
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Approve agreement failed: {response.text}"
        data = response.json()
        # API returns message on success
        assert "message" in data or data.get("status") == "approved" or data.get("approval_status") == "approved"
        print(f"Agreement approved, response: {data}")
    
    def test_18_get_agreements_list(self):
        """List agreements to verify persistence"""
        response = requests.get(f"{BASE_URL}/api/agreements", headers=self.get_headers())
        
        assert response.status_code == 200, f"List agreements failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Total agreements: {len(data)}")
    
    # ============== PHASE 7: KICKOFF REQUEST ==============
    
    def test_19_create_kickoff_request(self):
        """Create kickoff request to hand off to consulting"""
        assert TestSalesFlowE2E.test_agreement_id, "No agreement ID"
        
        payload = {
            "agreement_id": TestSalesFlowE2E.test_agreement_id,
            "client_name": "TEST_E2E Corp",
            "project_name": "TEST_E2E Consulting Engagement",
            "project_type": "mixed",
            "total_meetings": 60,
            "meeting_frequency": "Monthly",
            "project_tenure_months": 12,
            "expected_start_date": (datetime.now() + timedelta(days=15)).isoformat(),
            "notes": "E2E test kickoff request - ready for consulting handoff"
        }
        
        response = requests.post(f"{BASE_URL}/api/kickoff-requests",
                                json=payload,
                                headers=self.get_headers())
        
        assert response.status_code == 200, f"Create kickoff failed: {response.text}"
        data = response.json()
        # API may return kickoff_id or id
        kickoff_id = data.get("id") or data.get("kickoff_id")
        assert kickoff_id, f"No kickoff ID in response: {data}"
        
        TestSalesFlowE2E.test_kickoff_id = kickoff_id
        print(f"Created kickoff request: {kickoff_id}, response: {data}")
    
    def test_20_get_kickoff_requests(self):
        """List kickoff requests"""
        response = requests.get(f"{BASE_URL}/api/kickoff-requests", headers=self.get_headers())
        
        assert response.status_code == 200, f"List kickoff requests failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        
        # Find our test kickoff
        test_kickoffs = [k for k in data if k.get("id") == TestSalesFlowE2E.test_kickoff_id]
        assert len(test_kickoffs) > 0, "Test kickoff not found"
        print(f"Total kickoff requests: {len(data)}")
    
    def test_21_get_kickoff_details(self):
        """Get detailed kickoff request info"""
        assert TestSalesFlowE2E.test_kickoff_id, "No kickoff ID"
        
        response = requests.get(
            f"{BASE_URL}/api/kickoff-requests/{TestSalesFlowE2E.test_kickoff_id}/details",
            headers=self.get_headers()
        )
        
        assert response.status_code == 200, f"Get kickoff details failed: {response.text}"
        data = response.json()
        # API returns kickoff_request not kickoff
        assert "kickoff_request" in data or "kickoff" in data
        print(f"Kickoff details retrieved, has agreement: {'agreement' in data}")
    
    # ============== CLEANUP ==============
    
    def test_99_cleanup(self):
        """Cleanup test data (optional - runs last)"""
        print("\n=== Test Data Summary ===")
        print(f"Lead ID: {TestSalesFlowE2E.test_lead_id}")
        print(f"Meeting ID: {TestSalesFlowE2E.test_meeting_id}")
        print(f"Pricing Plan ID: {TestSalesFlowE2E.test_pricing_plan_id}")
        print(f"SOW ID: {TestSalesFlowE2E.test_sow_id}")
        print(f"Quotation ID: {TestSalesFlowE2E.test_quotation_id}")
        print(f"Agreement ID: {TestSalesFlowE2E.test_agreement_id}")
        print(f"Kickoff ID: {TestSalesFlowE2E.test_kickoff_id}")
        
        # Note: Not deleting to allow manual verification
        # In production, would clean up TEST_ prefixed items


class TestMeetingsAPI:
    """Additional tests for Meetings & MOM functionality"""
    
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestMeetingsAPI.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@company.com",
                "password": "admin123"
            })
            TestMeetingsAPI.token = response.json()["access_token"]
    
    def get_headers(self):
        return {"Authorization": f"Bearer {TestMeetingsAPI.token}", "Content-Type": "application/json"}
    
    def test_list_meetings(self):
        """List all meetings"""
        response = requests.get(f"{BASE_URL}/api/meetings", headers=self.get_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Total meetings: {len(data)}")
    
    def test_list_sales_meetings(self):
        """List only sales meetings"""
        response = requests.get(f"{BASE_URL}/api/meetings?meeting_type=sales", headers=self.get_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Sales meetings: {len(data)}")


class TestAgreementSignature:
    """Test agreement signature flow"""
    
    token = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        if not TestAgreementSignature.token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@company.com",
                "password": "admin123"
            })
            TestAgreementSignature.token = response.json()["access_token"]
    
    def get_headers(self):
        return {"Authorization": f"Bearer {TestAgreementSignature.token}", "Content-Type": "application/json"}
    
    def test_pending_approvals(self):
        """Get agreements pending approval"""
        response = requests.get(f"{BASE_URL}/api/agreements/pending-approval", headers=self.get_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Pending approvals: {len(data)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
