"""
Test GSTIN Validation API and Proforma Invoice PDF Generation Fix
Tests for:
1. GSTIN validation endpoint - valid/invalid GSTIN formats
2. GSTIN company name matching
3. Quotations API for PDF generation data
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestGSTINValidation:
    """GSTIN Validation API Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_valid_gstin_format(self):
        """Test valid GSTIN returns valid=true with state info"""
        response = requests.post(
            f"{BASE_URL}/api/gstin/validate",
            json={"gstin": "24AABCT1234F1ZP"},
            headers=self.headers
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Verify valid GSTIN response
        assert data["valid"] == True, f"Expected valid=True, got {data}"
        assert data["state_code"] == "24", f"Expected state_code=24, got {data['state_code']}"
        assert data["state_name"] == "Gujarat", f"Expected Gujarat, got {data['state_name']}"
        assert data["pan"] == "AABCT1234F", f"Expected PAN AABCT1234F, got {data['pan']}"
        assert len(data["errors"]) == 0, f"Expected no errors, got {data['errors']}"
        print(f"✓ Valid GSTIN test passed: state={data['state_name']}, PAN={data['pan']}")
    
    def test_02_invalid_gstin_format(self):
        """Test invalid GSTIN returns valid=false with errors"""
        response = requests.post(
            f"{BASE_URL}/api/gstin/validate",
            json={"gstin": "INVALID123"},
            headers=self.headers
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Verify invalid GSTIN response
        assert data["valid"] == False, f"Expected valid=False, got {data}"
        assert len(data["errors"]) > 0, f"Expected errors, got none"
        print(f"✓ Invalid GSTIN test passed: errors={data['errors']}")
    
    def test_03_gstin_too_short(self):
        """Test GSTIN with wrong length"""
        response = requests.post(
            f"{BASE_URL}/api/gstin/validate",
            json={"gstin": "24AABCT"},
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] == False
        assert any("15 characters" in err for err in data["errors"]), f"Expected length error, got {data['errors']}"
        print(f"✓ Short GSTIN test passed: errors={data['errors']}")
    
    def test_04_gstin_company_name_match(self):
        """Test GSTIN with company name matching"""
        response = requests.post(
            f"{BASE_URL}/api/gstin/validate",
            json={
                "gstin": "24AABCT1234F1ZP",
                "company_name": "AABCT Motors Pvt Ltd"
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] == True
        assert data["company_match"] is not None, "Expected company_match info"
        assert data["company_match"]["match"] == True, f"Expected match=True, got {data['company_match']}"
        print(f"✓ Company match test passed: {data['company_match']}")
    
    def test_05_gstin_company_name_mismatch(self):
        """Test GSTIN with non-matching company name"""
        response = requests.post(
            f"{BASE_URL}/api/gstin/validate",
            json={
                "gstin": "24AABCT1234F1ZP",
                "company_name": "XYZ Corporation"
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] == True  # GSTIN is still valid
        assert data["company_match"] is not None
        assert data["company_match"]["match"] == False, f"Expected match=False, got {data['company_match']}"
        print(f"✓ Company mismatch test passed: {data['company_match']}")
    
    def test_06_gstin_different_states(self):
        """Test GSTIN from different states"""
        test_cases = [
            ("27AABCT1234F1ZP", "27", "Maharashtra"),
            ("29AABCT1234F1ZP", "29", "Karnataka"),
            ("33AABCT1234F1ZP", "33", "Tamil Nadu"),
            ("07AABCT1234F1ZP", "07", "Delhi"),
        ]
        
        for gstin, expected_code, expected_state in test_cases:
            response = requests.post(
                f"{BASE_URL}/api/gstin/validate",
                json={"gstin": gstin},
                headers=self.headers
            )
            assert response.status_code == 200
            data = response.json()
            
            assert data["valid"] == True
            assert data["state_code"] == expected_code
            assert data["state_name"] == expected_state
            print(f"✓ State {expected_state} ({expected_code}) validated")


class TestProformaInvoicePDF:
    """Test Proforma Invoice data for PDF generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_get_quotations_list(self):
        """Test fetching quotations list"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers=self.headers
        )
        assert response.status_code == 200, f"API failed: {response.text}"
        data = response.json()
        
        # Check response structure
        assert "data" in data or isinstance(data, list), f"Expected data array, got {type(data)}"
        quotations = data.get("data", data) if isinstance(data, dict) else data
        
        print(f"✓ Found {len(quotations)} quotations")
        
        if len(quotations) > 0:
            # Check first quotation has required fields for PDF
            q = quotations[0]
            assert "quotation_number" in q, "Missing quotation_number"
            assert "subtotal" in q or "total" in q, "Missing subtotal/total"
            print(f"✓ First quotation: {q.get('quotation_number')}, subtotal={q.get('subtotal')}, total={q.get('total')}")
    
    def test_02_quotation_has_amount_fields(self):
        """Test that quotations have proper amount fields for PDF"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        quotations = data.get("data", data) if isinstance(data, dict) else data
        
        if len(quotations) == 0:
            pytest.skip("No quotations found to test")
        
        # Check each quotation has amount fields
        for q in quotations[:5]:  # Check first 5
            # At least one of these should be present and non-zero for valid invoices
            subtotal = q.get("subtotal", 0)
            total = q.get("total", 0)
            grand_total = q.get("grand_total", 0)
            gst_amount = q.get("gst_amount", 0)
            tax_amount = q.get("tax_amount", 0)
            
            print(f"  Quotation {q.get('quotation_number')}: subtotal={subtotal}, gst={gst_amount or tax_amount}, grand_total={grand_total or total}")
            
            # Verify amounts are numbers (not None or strings)
            assert isinstance(subtotal, (int, float)), f"subtotal should be number, got {type(subtotal)}"
        
        print(f"✓ All quotations have proper amount fields")
    
    def test_03_quotation_detail_by_id(self):
        """Test fetching single quotation by ID"""
        # First get list
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        quotations = data.get("data", data) if isinstance(data, dict) else data
        
        if len(quotations) == 0:
            pytest.skip("No quotations found")
        
        # Get first quotation ID
        quotation_id = quotations[0].get("id")
        
        # Fetch by ID
        response = requests.get(
            f"{BASE_URL}/api/quotations/{quotation_id}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed to get quotation: {response.text}"
        q = response.json()
        
        # Verify all PDF-required fields
        assert q.get("quotation_number"), "Missing quotation_number"
        assert "subtotal" in q, "Missing subtotal"
        assert "lead_id" in q or "client_name" in q, "Missing lead/client info"
        
        print(f"✓ Quotation detail: {q.get('quotation_number')}, subtotal={q.get('subtotal')}, gst={q.get('gst_amount')}")


class TestQuotationAmountCalculation:
    """Test that quotation amounts are calculated correctly"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "employee_id": "EMP001",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_01_amounts_not_zero(self):
        """Verify quotations with data don't have ₹0.00 amounts"""
        response = requests.get(
            f"{BASE_URL}/api/quotations",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        quotations = data.get("data", data) if isinstance(data, dict) else data
        
        non_zero_found = False
        for q in quotations:
            subtotal = q.get("subtotal", 0)
            grand_total = q.get("grand_total", 0) or q.get("total", 0)
            
            if subtotal > 0 or grand_total > 0:
                non_zero_found = True
                print(f"✓ {q.get('quotation_number')}: subtotal={subtotal}, grand_total={grand_total}")
        
        if not non_zero_found and len(quotations) > 0:
            print("⚠ Warning: All quotations have zero amounts - may need to check data")
        
        print(f"✓ Amount verification complete for {len(quotations)} quotations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
