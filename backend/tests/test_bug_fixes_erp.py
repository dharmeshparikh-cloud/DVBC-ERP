"""
Test Bug Fixes for ERP - Testing duplicate phone validation, leads API, IFSC verification
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDuplicatePhoneValidation:
    """Test duplicate phone number validation for employee creation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup admin auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_create_employee_with_phone(self):
        """Test creating employee with phone number"""
        # First, get existing employees to find a unique phone number
        response = self.session.get(f"{BASE_URL}/api/employees")
        assert response.status_code == 200
        employees = response.json()
        
        # Generate a unique phone number (using timestamp)
        import time
        unique_phone = f"9{int(time.time()) % 1000000000:09d}"
        
        employee_data = {
            "first_name": "TEST_Employee",
            "last_name": "PhoneCheck",
            "email": f"test_phone_{int(time.time())}@example.com",
            "phone": unique_phone,
            "department": "Consulting",
            "designation": "Consultant"
        }
        
        response = self.session.post(f"{BASE_URL}/api/employees", json=employee_data)
        print(f"Create employee response: {response.status_code} - {response.text}")
        
        # Should succeed
        assert response.status_code == 200
        
        # Try to create another employee with the same phone number
        duplicate_data = {
            "first_name": "TEST_Duplicate",
            "last_name": "PhoneCheck",
            "email": f"test_phone_dup_{int(time.time())}@example.com",
            "phone": unique_phone,
            "department": "Consulting",
            "designation": "Consultant"
        }
        
        response = self.session.post(f"{BASE_URL}/api/employees", json=duplicate_data)
        print(f"Duplicate phone response: {response.status_code} - {response.text}")
        
        # Should fail with 400
        assert response.status_code == 400
        assert "phone number already exists" in response.text.lower()


class TestLeadsSearchAndFilter:
    """Test leads search and filter functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup sales manager auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as sales manager
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sales.manager@dvbc.com",
            "password": "sales123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_get_leads(self):
        """Test getting all leads"""
        response = self.session.get(f"{BASE_URL}/api/leads")
        assert response.status_code == 200
        leads = response.json()
        print(f"Total leads: {len(leads)}")
        assert isinstance(leads, list)
    
    def test_leads_filter_by_status(self):
        """Test filtering leads by status"""
        response = self.session.get(f"{BASE_URL}/api/leads?status=new")
        assert response.status_code == 200
        leads = response.json()
        print(f"New leads: {len(leads)}")
        
        # Check all returned leads have status 'new'
        for lead in leads:
            assert lead.get("status") == "new"
    
    def test_create_lead_for_search_test(self):
        """Create a test lead for search functionality testing"""
        import time
        unique_id = int(time.time())
        
        lead_data = {
            "first_name": "SearchTest",
            "last_name": f"Lead{unique_id}",
            "company": f"TestCompany{unique_id}",
            "email": f"searchtest{unique_id}@testcompany.com",
            "phone": f"+91{unique_id % 10000000000:010d}"
        }
        
        response = self.session.post(f"{BASE_URL}/api/leads", json=lead_data)
        print(f"Create lead response: {response.status_code}")
        
        # Endpoint might return 200 or 201 depending on implementation
        assert response.status_code in [200, 201]
        
        # The search/filter happens on frontend using useMemo, not backend
        # Backend just returns all leads and frontend filters
        return response.json()


class TestExpenseReceipts:
    """Test expense receipt upload functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_get_expenses(self):
        """Test getting expenses"""
        response = self.session.get(f"{BASE_URL}/api/expenses")
        assert response.status_code == 200
        expenses = response.json()
        print(f"Total expenses: {len(expenses)}")
        assert isinstance(expenses, list)
    
    def test_create_expense_and_upload_receipt(self):
        """Test creating an expense and uploading receipt separately"""
        import time
        import base64
        
        # Create a simple base64 encoded "image" (just text for testing)
        sample_receipt = base64.b64encode(b"Sample receipt image data").decode('utf-8')
        
        # Step 1: Create a basic expense
        expense_data = {
            "category": "local_conveyance",
            "description": f"TEST expense {int(time.time())}",
            "amount": 500,
            "expense_date": "2026-01-15"
        }
        
        response = self.session.post(f"{BASE_URL}/api/expenses", json=expense_data)
        print(f"Create expense response: {response.status_code} - {response.text}")
        
        # Should succeed
        assert response.status_code in [200, 201]
        
        # Verify expense was created
        data = response.json()
        assert data.get("message") == "Expense created"
        assert data.get("expense_id") is not None
        
        expense_id = data.get("expense_id")
        
        # Step 2: Upload receipt to the expense
        receipt_data = {
            "file_data": f"data:image/png;base64,{sample_receipt}",
            "file_name": "receipt.png",
            "file_type": "image/png"
        }
        
        receipt_response = self.session.post(f"{BASE_URL}/api/expenses/{expense_id}/upload-receipt", json=receipt_data)
        print(f"Upload receipt response: {receipt_response.status_code} - {receipt_response.text}")
        
        assert receipt_response.status_code == 200
        assert "receipt_id" in receipt_response.json()
        
        # Step 3: Verify receipt was added
        detail_response = self.session.get(f"{BASE_URL}/api/expenses/{expense_id}")
        assert detail_response.status_code == 200
        expense = detail_response.json()
        print(f"Expense with receipt: receipts count = {len(expense.get('receipts', []))}")
        assert len(expense.get("receipts", [])) > 0


class TestBankDetailsIFSCVerification:
    """Test IFSC verification (external Razorpay API)"""
    
    def test_razorpay_ifsc_api_valid(self):
        """Test IFSC lookup with valid code"""
        # Using HDFC Bank IFSC code
        ifsc_code = "HDFC0001234"
        
        response = requests.get(f"https://ifsc.razorpay.com/{ifsc_code}")
        print(f"IFSC response for {ifsc_code}: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Bank: {data.get('BANK')}, Branch: {data.get('BRANCH')}")
            assert "BANK" in data
            assert "BRANCH" in data
        elif response.status_code == 404:
            # IFSC code not found is valid behavior
            print("IFSC code not found (404) - this is expected for test IFSC")
    
    def test_razorpay_ifsc_api_invalid(self):
        """Test IFSC lookup with invalid code"""
        ifsc_code = "INVALID0000"
        
        response = requests.get(f"https://ifsc.razorpay.com/{ifsc_code}")
        print(f"Invalid IFSC response: {response.status_code}")
        
        # Should return 404 for invalid IFSC
        assert response.status_code == 404


class TestAuthenticationLogin:
    """Test authentication and login functionality"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@dvbc.com",
            "password": "admin123"
        })
        print(f"Admin login response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
    
    def test_sales_manager_login(self):
        """Test sales manager login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sales.manager@dvbc.com",
            "password": "sales123"
        })
        print(f"Sales manager login response: {response.status_code}")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
