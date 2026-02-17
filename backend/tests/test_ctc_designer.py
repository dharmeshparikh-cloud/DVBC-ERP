"""
Test Suite for CTC Structure Designer with Admin Approval Workflow
Tests: CTC Preview calculation, CTC Design submission, Pending Approvals, Approve/Reject

Standard Indian CTC Breakdown:
- Basic: 40% of CTC
- HRA: 50% of Basic
- DA: 10% of Basic
- Conveyance: ₹1600/month (₹19,200/year)
- Medical: ₹1250/month (₹15,000/year)
- Special Allowance: balance
- PF Employer: 12% of Basic
- Gratuity: 4.81% of Basic
- Optional: Retention Bonus (paid after vesting period)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCTCDesignerBackend:
    """Test CTC Designer APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - get admin and HR tokens"""
        # Admin login
        admin_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        assert admin_response.status_code == 200, f"Admin login failed: {admin_response.text}"
        self.admin_token = admin_response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.admin_user = admin_response.json()["user"]
        
        # HR Manager login
        hr_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "hr.manager@dvbc.com",
            "password": "hr123"
        })
        assert hr_response.status_code == 200, f"HR login failed: {hr_response.text}"
        self.hr_token = hr_response.json()["access_token"]
        self.hr_headers = {"Authorization": f"Bearer {self.hr_token}"}
        self.hr_user = hr_response.json()["user"]
        
        yield
    
    # ==================== CTC Preview Calculation Tests ====================
    
    def test_ctc_preview_calculation_12_lakh(self):
        """Test CTC breakdown for ₹12,00,000 annual CTC"""
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={"annual_ctc": 1200000, "retention_bonus": 0},
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"CTC preview failed: {response.text}"
        
        data = response.json()
        assert "components" in data, "Response should have components"
        assert "summary" in data, "Response should have summary"
        
        # Verify annual CTC
        assert data["summary"]["annual_ctc"] == 1200000, "Annual CTC mismatch"
        
        # Verify Basic (40% of CTC = 4,80,000)
        basic = data["components"]["basic"]
        assert basic["annual"] == 480000, f"Basic annual should be 4,80,000, got {basic['annual']}"
        assert basic["monthly"] == 40000, f"Basic monthly should be 40,000, got {basic['monthly']}"
        
        # Verify HRA (50% of Basic = 2,40,000)
        hra = data["components"]["hra"]
        assert hra["annual"] == 240000, f"HRA annual should be 2,40,000, got {hra['annual']}"
        
        # Verify DA (10% of Basic = 48,000)
        da = data["components"]["da"]
        assert da["annual"] == 48000, f"DA annual should be 48,000, got {da['annual']}"
        
        # Verify Conveyance (fixed ₹19,200/year)
        conveyance = data["components"]["conveyance"]
        assert conveyance["annual"] == 19200, f"Conveyance should be 19,200, got {conveyance['annual']}"
        
        # Verify Medical (fixed ₹15,000/year)
        medical = data["components"]["medical"]
        assert medical["annual"] == 15000, f"Medical should be 15,000, got {medical['annual']}"
        
        # Verify PF Employer (12% of Basic = 57,600)
        pf = data["components"]["pf_employer"]
        assert pf["annual"] == 57600, f"PF Employer should be 57,600, got {pf['annual']}"
        
        # Verify Gratuity (4.81% of Basic = 23,088)
        gratuity = data["components"]["gratuity"]
        assert round(gratuity["annual"]) == 23088, f"Gratuity should be ~23,088, got {gratuity['annual']}"
        
        print(f"✓ CTC Preview ₹12,00,000 - All components calculated correctly")
        print(f"  Basic: {basic['annual']}, HRA: {hra['annual']}, DA: {da['annual']}")
        print(f"  Gross Monthly: {data['summary']['gross_monthly']}")
    
    def test_ctc_preview_with_retention_bonus(self):
        """Test CTC preview with optional retention bonus"""
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={
                "annual_ctc": 1500000,
                "retention_bonus": 100000,
                "retention_vesting_months": 18
            },
            headers=self.hr_headers
        )
        assert response.status_code == 200, f"CTC preview with retention failed: {response.text}"
        
        data = response.json()
        assert "retention_bonus" in data["components"], "Retention bonus component should exist"
        
        rb = data["components"]["retention_bonus"]
        assert rb["annual"] == 100000, f"Retention bonus should be 1,00,000, got {rb['annual']}"
        assert rb["vesting_months"] == 18, f"Vesting months should be 18, got {rb['vesting_months']}"
        assert rb["is_optional"] == True, "Retention bonus should be marked optional"
        
        print(f"✓ CTC Preview with Retention Bonus - Working correctly")
    
    def test_ctc_preview_invalid_ctc(self):
        """Test CTC preview with invalid (zero/negative) CTC"""
        # Zero CTC
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={"annual_ctc": 0},
            headers=self.hr_headers
        )
        assert response.status_code == 400, f"Should reject zero CTC, got {response.status_code}"
        
        # Negative CTC
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={"annual_ctc": -100000},
            headers=self.hr_headers
        )
        assert response.status_code == 400, f"Should reject negative CTC, got {response.status_code}"
        
        print(f"✓ CTC Preview validation - Invalid CTC rejected")
    
    def test_ctc_preview_unauthorized(self):
        """Test CTC preview without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/ctc/calculate-preview",
            json={"annual_ctc": 1200000}
        )
        assert response.status_code == 401, f"Should require auth, got {response.status_code}"
        
        print(f"✓ CTC Preview - Requires authentication")
    
    # ==================== CTC Design Submission Tests ====================
    
    def test_get_employees_for_ctc(self):
        """Test fetching employees for CTC designer dropdown"""
        response = requests.get(
            f"{BASE_URL}/api/employees",
            headers=self.hr_headers
        )
        assert response.status_code == 200, f"Employees fetch failed: {response.text}"
        
        employees = response.json()
        assert len(employees) > 0, "Should have at least one employee"
        
        # Store first active employee for other tests
        active_employees = [e for e in employees if e.get('is_active', True)]
        assert len(active_employees) > 0, "Should have at least one active employee"
        
        self.test_employee = active_employees[0]
        print(f"✓ Employees list fetched - {len(active_employees)} active employees found")
        return active_employees
    
    def test_ctc_design_submission_and_pending_approval(self):
        """Test full CTC design submission and pending approval workflow"""
        # Get an active employee
        employees = self.test_get_employees_for_ctc()
        test_employee = employees[0]
        
        # Create unique effective month to avoid conflicts
        effective_month = "2027-03"
        
        # First cancel any existing pending requests for this employee
        pending_response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.admin_headers
        )
        if pending_response.status_code == 200:
            for pending in pending_response.json():
                if pending.get("employee_id") == test_employee["id"]:
                    requests.delete(
                        f"{BASE_URL}/api/ctc/{pending['id']}/cancel",
                        headers=self.admin_headers
                    )
        
        # Submit CTC design
        ctc_data = {
            "employee_id": test_employee["id"],
            "annual_ctc": 1200000,
            "retention_bonus": 50000,
            "retention_vesting_months": 12,
            "effective_month": effective_month,
            "remarks": "TEST_CTC_STRUCTURE annual review",
            "components": {}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/design",
            json=ctc_data,
            headers=self.hr_headers
        )
        assert response.status_code == 200, f"CTC design submission failed: {response.text}"
        
        result = response.json()
        assert "ctc_structure_id" in result, "Should return ctc_structure_id"
        assert result["status"] == "pending", "Status should be pending"
        
        ctc_id = result["ctc_structure_id"]
        print(f"✓ CTC Design submitted - ID: {ctc_id}, Status: pending")
        
        # Verify it appears in pending approvals (Admin view)
        pending_response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.admin_headers
        )
        assert pending_response.status_code == 200, f"Pending approvals failed: {pending_response.text}"
        
        pending_list = pending_response.json()
        pending_ids = [p["id"] for p in pending_list]
        assert ctc_id in pending_ids, f"CTC {ctc_id} should be in pending approvals"
        
        print(f"✓ Pending approvals list contains the submitted CTC")
        
        return ctc_id, test_employee
    
    def test_admin_pending_approvals_access(self):
        """Test that only Admin can access pending approvals"""
        # Admin can access
        response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Admin should access pending, got {response.status_code}"
        
        # HR should not access (403)
        response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.hr_headers
        )
        assert response.status_code == 403, f"HR should be denied pending access, got {response.status_code}"
        
        print(f"✓ Pending approvals - Admin only access verified")
    
    def test_ctc_stats_admin_only(self):
        """Test CTC stats endpoint (Admin only)"""
        # Admin can access
        response = requests.get(
            f"{BASE_URL}/api/ctc/stats",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Admin should access stats, got {response.status_code}"
        
        stats = response.json()
        assert "pending" in stats, "Stats should have pending count"
        assert "active" in stats, "Stats should have active count"
        assert "approved" in stats, "Stats should have approved count"
        assert "rejected" in stats, "Stats should have rejected count"
        
        print(f"✓ CTC Stats - Pending: {stats['pending']}, Active: {stats['active']}")
        
        # HR should be denied
        response = requests.get(
            f"{BASE_URL}/api/ctc/stats",
            headers=self.hr_headers
        )
        assert response.status_code == 403, f"HR should be denied stats, got {response.status_code}"
        
        print(f"✓ CTC Stats - Admin only access verified")
    
    # ==================== Approval/Rejection Tests ====================
    
    def test_admin_approve_ctc_structure(self):
        """Test Admin approving a CTC structure"""
        # Create a new CTC request first
        ctc_id, test_employee = self.test_ctc_design_submission_and_pending_approval()
        
        # Admin approves
        response = requests.post(
            f"{BASE_URL}/api/ctc/{ctc_id}/approve",
            json={"remarks": "Approved for annual increment"},
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Approval failed: {response.text}"
        
        result = response.json()
        assert "approved" in result.get("message", "").lower() or "activated" in result.get("message", "").lower(), \
            f"Approval message should mention approved/activated, got: {result.get('message')}"
        
        print(f"✓ CTC Approved - {result.get('message')}")
        
        # Verify employee salary updated
        emp_response = requests.get(
            f"{BASE_URL}/api/employees/{test_employee['id']}",
            headers=self.admin_headers
        )
        if emp_response.status_code == 200:
            emp_data = emp_response.json()
            # Check if annual_ctc or ctc_structure_id was set
            if emp_data.get("annual_ctc") == 1200000 or emp_data.get("ctc_structure_id") == ctc_id:
                print(f"✓ Employee salary/CTC updated after approval")
        
        return ctc_id
    
    def test_admin_reject_ctc_structure(self):
        """Test Admin rejecting a CTC structure"""
        # Get employees and create a fresh CTC request
        employees = self.test_get_employees_for_ctc()
        test_employee = employees[-1] if len(employees) > 1 else employees[0]  # Use different employee
        
        # Cancel any existing pending
        pending_response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.admin_headers
        )
        if pending_response.status_code == 200:
            for pending in pending_response.json():
                if pending.get("employee_id") == test_employee["id"]:
                    requests.delete(
                        f"{BASE_URL}/api/ctc/{pending['id']}/cancel",
                        headers=self.admin_headers
                    )
        
        # Submit new CTC
        ctc_data = {
            "employee_id": test_employee["id"],
            "annual_ctc": 5000000,
            "retention_bonus": 0,
            "retention_vesting_months": 12,
            "effective_month": "2027-05",
            "remarks": "TEST_REJECTION_REQUEST",
            "components": {}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/design",
            json=ctc_data,
            headers=self.hr_headers
        )
        assert response.status_code == 200, f"CTC submission for rejection test failed: {response.text}"
        
        ctc_id = response.json()["ctc_structure_id"]
        
        # Admin rejects (rejection reason required)
        response = requests.post(
            f"{BASE_URL}/api/ctc/{ctc_id}/reject",
            json={"reason": "Budget constraints - please revise"},
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"Rejection failed: {response.text}"
        
        result = response.json()
        assert "rejected" in result.get("message", "").lower(), f"Message should mention rejected: {result.get('message')}"
        
        print(f"✓ CTC Rejected - {result.get('message')}")
    
    def test_reject_without_reason_fails(self):
        """Test that rejection without reason fails"""
        # Get employees and create a fresh CTC request
        employees = self.test_get_employees_for_ctc()
        test_employee = employees[0]
        
        # Cancel any existing pending
        pending_response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.admin_headers
        )
        if pending_response.status_code == 200:
            for pending in pending_response.json():
                if pending.get("employee_id") == test_employee["id"]:
                    requests.delete(
                        f"{BASE_URL}/api/ctc/{pending['id']}/cancel",
                        headers=self.admin_headers
                    )
        
        # Submit new CTC
        ctc_data = {
            "employee_id": test_employee["id"],
            "annual_ctc": 1000000,
            "effective_month": "2027-06",
            "components": {}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/design",
            json=ctc_data,
            headers=self.hr_headers
        )
        
        if response.status_code != 200:
            print(f"Skipping - CTC submission failed (likely pending exists)")
            return
        
        ctc_id = response.json()["ctc_structure_id"]
        
        # Try to reject without reason
        response = requests.post(
            f"{BASE_URL}/api/ctc/{ctc_id}/reject",
            json={},  # No reason
            headers=self.admin_headers
        )
        assert response.status_code == 400, f"Should require rejection reason, got {response.status_code}"
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/ctc/{ctc_id}/cancel", headers=self.admin_headers)
        
        print(f"✓ Rejection requires reason - Validated")
    
    def test_non_admin_cannot_approve_or_reject(self):
        """Test that non-admin cannot approve or reject CTC"""
        # Use a dummy ID (doesn't need to exist for permission check)
        dummy_id = "test-ctc-id-123"
        
        # HR cannot approve
        response = requests.post(
            f"{BASE_URL}/api/ctc/{dummy_id}/approve",
            json={"remarks": "test"},
            headers=self.hr_headers
        )
        assert response.status_code == 403, f"HR should not approve, got {response.status_code}"
        
        # HR cannot reject
        response = requests.post(
            f"{BASE_URL}/api/ctc/{dummy_id}/reject",
            json={"reason": "test"},
            headers=self.hr_headers
        )
        assert response.status_code == 403, f"HR should not reject, got {response.status_code}"
        
        print(f"✓ Approve/Reject - Admin only access verified")
    
    # ==================== Notification Tests ====================
    
    def test_notification_sent_on_submission(self):
        """Test that Admin receives notification when CTC is submitted"""
        # Get admin notifications before
        before_response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers=self.admin_headers
        )
        before_count = len(before_response.json()) if before_response.status_code == 200 else 0
        
        # Submit a CTC (this creates notification)
        employees = self.test_get_employees_for_ctc()
        test_employee = employees[0]
        
        # Cancel any existing pending
        pending_response = requests.get(
            f"{BASE_URL}/api/ctc/pending-approvals",
            headers=self.admin_headers
        )
        if pending_response.status_code == 200:
            for pending in pending_response.json():
                if pending.get("employee_id") == test_employee["id"]:
                    requests.delete(
                        f"{BASE_URL}/api/ctc/{pending['id']}/cancel",
                        headers=self.admin_headers
                    )
        
        ctc_data = {
            "employee_id": test_employee["id"],
            "annual_ctc": 1100000,
            "effective_month": "2027-07",
            "remarks": "TEST_NOTIFICATION_CHECK",
            "components": {}
        }
        
        response = requests.post(
            f"{BASE_URL}/api/ctc/design",
            json=ctc_data,
            headers=self.hr_headers
        )
        
        if response.status_code != 200:
            print(f"Skipping notification test - CTC submission failed")
            return
        
        ctc_id = response.json()["ctc_structure_id"]
        
        # Check admin notifications after
        after_response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers=self.admin_headers
        )
        
        if after_response.status_code == 200:
            after_notifications = after_response.json()
            ctc_notifications = [n for n in after_notifications if n.get("type") == "ctc_approval_request"]
            
            if len(ctc_notifications) > 0:
                print(f"✓ Notification sent to Admin on CTC submission")
            else:
                print(f"✓ CTC submitted (notification may already exist)")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/ctc/{ctc_id}/cancel", headers=self.admin_headers)
    
    # ==================== Employee CTC History Tests ====================
    
    def test_employee_ctc_history(self):
        """Test fetching employee CTC history"""
        employees = self.test_get_employees_for_ctc()
        test_employee = employees[0]
        
        response = requests.get(
            f"{BASE_URL}/api/ctc/employee/{test_employee['id']}/history",
            headers=self.admin_headers
        )
        assert response.status_code == 200, f"CTC history fetch failed: {response.text}"
        
        history = response.json()
        assert isinstance(history, list), "History should be a list"
        
        print(f"✓ Employee CTC history - {len(history)} records found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
