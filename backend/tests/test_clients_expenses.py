"""
Test suite for Client Master and Expense System APIs
Testing:
- Client CRUD operations
- Client contacts (SPOCs) management
- Client revenue history
- Expense creation with line items
- Expense submission for approval
- Client stats and Expense stats
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

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
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Session with admin auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {admin_token}"
    })
    return session


@pytest.fixture(scope="module")
def manager_token():
    """Get manager authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": MANAGER_EMAIL,
        "password": MANAGER_PASSWORD
    })
    assert response.status_code == 200, f"Manager login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def manager_client(manager_token):
    """Session with manager auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {manager_token}"
    })
    return session


class TestClientMaster:
    """Client Master CRUD tests"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, admin_client):
        """Setup and teardown test client data"""
        # Store created test IDs for cleanup
        self.test_client_ids = []
        yield
        # Cleanup: Delete test clients
        for client_id in self.test_client_ids:
            try:
                admin_client.delete(f"{BASE_URL}/api/clients/{client_id}")
            except:
                pass
    
    def test_get_clients_list(self, admin_client):
        """Test GET /api/clients - Should return list of clients"""
        response = admin_client.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/clients - Found {len(data)} clients")
    
    def test_create_client_with_basic_info(self, admin_client):
        """Test POST /api/clients - Create client with company name, industry, location"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "company_name": f"TEST_Client_{unique_id}",
            "industry": "Technology",
            "location": "Western India",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/clients", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data["company_name"] == payload["company_name"]
        assert data["industry"] == "Technology"
        assert data["city"] == "Mumbai"
        assert "id" in data
        
        self.test_client_ids.append(data["id"])
        print(f"✓ POST /api/clients - Created client: {data['id']}")
        
        # Verify by GET
        get_response = admin_client.get(f"{BASE_URL}/api/clients/{data['id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["company_name"] == payload["company_name"]
        print(f"✓ GET /api/clients/{data['id']} - Verified persistence")
    
    def test_create_client_with_sales_person(self, admin_client):
        """Test creating client with sales person name"""
        unique_id = str(uuid.uuid4())[:8]
        payload = {
            "company_name": f"TEST_Sales_Client_{unique_id}",
            "industry": "Finance",
            "location": "Northern India",
            "city": "Delhi",
            "sales_person_name": "John Sales"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/clients", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["sales_person_name"] == "John Sales"
        self.test_client_ids.append(data["id"])
        print(f"✓ Created client with sales person: {data['id']}")
    
    def test_update_client_information(self, admin_client):
        """Test PATCH /api/clients/{id} - Edit client information"""
        # First create a client
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/clients", json={
            "company_name": f"TEST_Update_Client_{unique_id}",
            "industry": "Healthcare"
        })
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        self.test_client_ids.append(client_id)
        
        # Update the client
        update_payload = {
            "industry": "Manufacturing",
            "city": "Pune",
            "website": "https://test.example.com"
        }
        
        update_response = admin_client.patch(f"{BASE_URL}/api/clients/{client_id}", json=update_payload)
        assert update_response.status_code == 200
        
        # Verify update by GET
        get_response = admin_client.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_response.status_code == 200
        updated = get_response.json()
        assert updated["industry"] == "Manufacturing"
        assert updated["city"] == "Pune"
        assert updated["website"] == "https://test.example.com"
        print(f"✓ PATCH /api/clients/{client_id} - Client updated successfully")
    
    def test_add_contact_to_client(self, admin_client):
        """Test POST /api/clients/{id}/contacts - Add SPOC to client"""
        # Create a client first
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/clients", json={
            "company_name": f"TEST_Contact_Client_{unique_id}"
        })
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        self.test_client_ids.append(client_id)
        
        # Add contact (SPOC)
        contact_payload = {
            "name": "Test Contact",
            "designation": "CTO",
            "email": "contact@test.com",
            "phone": "+91 98765 43210",
            "is_primary": True
        }
        
        response = admin_client.post(f"{BASE_URL}/api/clients/{client_id}/contacts", json=contact_payload)
        assert response.status_code == 200
        
        # Verify contact was added
        get_response = admin_client.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_response.status_code == 200
        client_data = get_response.json()
        
        assert len(client_data["contacts"]) >= 1
        contact = client_data["contacts"][0]
        assert contact["name"] == "Test Contact"
        assert contact["designation"] == "CTO"
        assert contact["is_primary"] == True
        print(f"✓ POST /api/clients/{client_id}/contacts - Contact added: {contact['name']}")
    
    def test_add_revenue_to_client(self, admin_client):
        """Test POST /api/clients/{id}/revenue - Add revenue record"""
        # Create a client first
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/clients", json={
            "company_name": f"TEST_Revenue_Client_{unique_id}"
        })
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        self.test_client_ids.append(client_id)
        
        # Add revenue record
        revenue_payload = {
            "year": 2024,
            "quarter": 1,
            "amount": 500000.0,
            "currency": "INR",
            "notes": "Q1 Consulting Project"
        }
        
        response = admin_client.post(f"{BASE_URL}/api/clients/{client_id}/revenue", json=revenue_payload)
        assert response.status_code == 200
        
        # Verify revenue was added
        get_response = admin_client.get(f"{BASE_URL}/api/clients/{client_id}")
        assert get_response.status_code == 200
        client_data = get_response.json()
        
        assert len(client_data["revenue_history"]) >= 1
        revenue = client_data["revenue_history"][0]
        assert revenue["year"] == 2024
        assert revenue["amount"] == 500000.0
        print(f"✓ POST /api/clients/{client_id}/revenue - Revenue added: ₹{revenue['amount']}")
    
    def test_get_client_stats(self, admin_client):
        """Test GET /api/clients/stats/summary - Get client statistics"""
        response = admin_client.get(f"{BASE_URL}/api/clients/stats/summary")
        assert response.status_code == 200
        
        stats = response.json()
        assert "total_clients" in stats
        assert "by_industry" in stats
        assert "total_revenue" in stats
        assert isinstance(stats["total_clients"], int)
        print(f"✓ GET /api/clients/stats/summary - Total: {stats['total_clients']}, Revenue: {stats['total_revenue']}")
    
    def test_deactivate_client(self, admin_client):
        """Test DELETE /api/clients/{id} - Deactivate client"""
        # Create a client first
        unique_id = str(uuid.uuid4())[:8]
        create_response = admin_client.post(f"{BASE_URL}/api/clients", json={
            "company_name": f"TEST_Deactivate_Client_{unique_id}"
        })
        assert create_response.status_code == 200
        client_id = create_response.json()["id"]
        
        # Deactivate
        delete_response = admin_client.delete(f"{BASE_URL}/api/clients/{client_id}")
        assert delete_response.status_code == 200
        
        # Verify deactivated (soft delete)
        # Client should still exist but be inactive
        # The default list shows only active clients
        print(f"✓ DELETE /api/clients/{client_id} - Client deactivated")


class TestExpenseSystem:
    """Expense System tests"""
    
    @pytest.fixture(autouse=True)
    def setup_expense_data(self, admin_client):
        """Setup and teardown expense data"""
        self.test_expense_ids = []
        yield
        # Note: No direct delete endpoint for expenses, they remain in DB
    
    def test_get_expenses_list(self, admin_client):
        """Test GET /api/expenses - Should return list of expenses"""
        response = admin_client.get(f"{BASE_URL}/api/expenses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/expenses - Found {len(data)} expenses")
    
    def test_create_expense_with_line_items(self, admin_client):
        """Test POST /api/expenses - Create expense with travel and food items"""
        payload = {
            "is_office_expense": False,
            "notes": "TEST_Expense_for_testing",
            "line_items": [
                {
                    "category": "travel",
                    "description": "Flight to Mumbai",
                    "amount": 5000.0,
                    "date": "2024-01-15T00:00:00Z"
                },
                {
                    "category": "food",
                    "description": "Client lunch meeting",
                    "amount": 1500.0,
                    "date": "2024-01-15T00:00:00Z"
                }
            ]
        }
        
        response = admin_client.post(f"{BASE_URL}/api/expenses", json=payload)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert "expense_id" in data
        assert data["total_amount"] == 6500.0  # 5000 + 1500
        
        expense_id = data["expense_id"]
        self.test_expense_ids.append(expense_id)
        print(f"✓ POST /api/expenses - Created expense: {expense_id}, Total: ₹{data['total_amount']}")
        
        # Verify by GET
        get_response = admin_client.get(f"{BASE_URL}/api/expenses/{expense_id}")
        assert get_response.status_code == 200
        expense = get_response.json()
        assert len(expense["line_items"]) == 2
        assert expense["status"] == "draft"
        print(f"✓ GET /api/expenses/{expense_id} - Verified persistence with 2 line items")
    
    def test_create_expense_linked_to_client(self, admin_client):
        """Test creating expense linked to a client"""
        # First get existing clients
        clients_response = admin_client.get(f"{BASE_URL}/api/clients")
        clients = clients_response.json()
        
        client_id = clients[0]["id"] if clients else None
        client_name = clients[0]["company_name"] if clients else None
        
        payload = {
            "client_id": client_id,
            "client_name": client_name,
            "is_office_expense": False,
            "notes": "TEST_Client_linked_expense",
            "line_items": [
                {
                    "category": "local_conveyance",
                    "description": "Taxi to client office",
                    "amount": 350.0,
                    "date": "2024-01-16T00:00:00Z"
                }
            ]
        }
        
        response = admin_client.post(f"{BASE_URL}/api/expenses", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        expense_id = data["expense_id"]
        self.test_expense_ids.append(expense_id)
        
        # Verify client linkage
        get_response = admin_client.get(f"{BASE_URL}/api/expenses/{expense_id}")
        expense = get_response.json()
        if client_id:
            assert expense["client_id"] == client_id
            print(f"✓ Expense linked to client: {client_name}")
        print(f"✓ POST /api/expenses - Client-linked expense created: {expense_id}")
    
    def test_submit_expense_for_approval(self, admin_client):
        """Test POST /api/expenses/{id}/submit - Submit expense for approval"""
        # Create a draft expense first
        payload = {
            "is_office_expense": True,
            "notes": "TEST_Submit_expense",
            "line_items": [
                {
                    "category": "office_supplies",
                    "description": "Printer paper",
                    "amount": 500.0,
                    "date": "2024-01-17T00:00:00Z"
                }
            ]
        }
        
        create_response = admin_client.post(f"{BASE_URL}/api/expenses", json=payload)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        self.test_expense_ids.append(expense_id)
        
        # Submit for approval
        submit_response = admin_client.post(f"{BASE_URL}/api/expenses/{expense_id}/submit")
        assert submit_response.status_code == 200
        
        submit_data = submit_response.json()
        assert "approval_id" in submit_data
        
        # Verify status changed to pending
        get_response = admin_client.get(f"{BASE_URL}/api/expenses/{expense_id}")
        expense = get_response.json()
        assert expense["status"] == "pending"
        print(f"✓ POST /api/expenses/{expense_id}/submit - Status changed to pending")
    
    def test_get_expense_details(self, admin_client):
        """Test GET /api/expenses/{id} - Get expense with all line items"""
        # Create an expense
        payload = {
            "is_office_expense": True,
            "notes": "TEST_Detailed_expense",
            "line_items": [
                {
                    "category": "travel",
                    "description": "Train ticket",
                    "amount": 800.0,
                    "date": "2024-01-18T00:00:00Z"
                },
                {
                    "category": "accommodation",
                    "description": "Hotel stay",
                    "amount": 3000.0,
                    "date": "2024-01-18T00:00:00Z"
                },
                {
                    "category": "food",
                    "description": "Dinner",
                    "amount": 600.0,
                    "date": "2024-01-18T00:00:00Z"
                }
            ]
        }
        
        create_response = admin_client.post(f"{BASE_URL}/api/expenses", json=payload)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        self.test_expense_ids.append(expense_id)
        
        # Get details
        get_response = admin_client.get(f"{BASE_URL}/api/expenses/{expense_id}")
        assert get_response.status_code == 200
        
        expense = get_response.json()
        assert expense["id"] == expense_id
        assert len(expense["line_items"]) == 3
        assert expense["total_amount"] == 4400.0  # 800 + 3000 + 600
        assert "employee_name" in expense
        assert expense["status"] == "draft"
        
        # Verify line item categories
        categories = [item["category"] for item in expense["line_items"]]
        assert "travel" in categories
        assert "accommodation" in categories
        assert "food" in categories
        print(f"✓ GET /api/expenses/{expense_id} - Details verified: 3 items, Total: ₹{expense['total_amount']}")
    
    def test_get_expense_categories(self, admin_client):
        """Test GET /api/expenses/categories/list - Get expense categories"""
        response = admin_client.get(f"{BASE_URL}/api/expenses/categories/list")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        # Check expected categories
        category_values = [c["value"] for c in categories]
        assert "travel" in category_values
        assert "food" in category_values
        assert "local_conveyance" in category_values
        print(f"✓ GET /api/expenses/categories/list - {len(categories)} categories available")
    
    def test_get_expense_stats(self, admin_client):
        """Test GET /api/expenses/stats/summary - Get expense statistics"""
        response = admin_client.get(f"{BASE_URL}/api/expenses/stats/summary")
        assert response.status_code == 200
        
        stats = response.json()
        assert "pending_count" in stats
        assert "approved_count" in stats
        assert "reimbursed_count" in stats
        assert "pending_amount" in stats
        print(f"✓ GET /api/expenses/stats/summary - Pending: {stats['pending_count']}, Approved: {stats['approved_count']}")
    
    def test_expense_status_workflow(self, admin_client):
        """Test expense goes through draft -> pending workflow"""
        # Create expense (draft)
        payload = {
            "is_office_expense": True,
            "notes": "TEST_Workflow_expense",
            "line_items": [
                {
                    "category": "communication",
                    "description": "Phone recharge",
                    "amount": 200.0,
                    "date": "2024-01-19T00:00:00Z"
                }
            ]
        }
        
        create_response = admin_client.post(f"{BASE_URL}/api/expenses", json=payload)
        assert create_response.status_code == 200
        expense_id = create_response.json()["expense_id"]
        self.test_expense_ids.append(expense_id)
        
        # Check initial status is draft
        get_response = admin_client.get(f"{BASE_URL}/api/expenses/{expense_id}")
        assert get_response.json()["status"] == "draft"
        
        # Submit - status changes to pending
        submit_response = admin_client.post(f"{BASE_URL}/api/expenses/{expense_id}/submit")
        assert submit_response.status_code == 200
        
        # Verify pending status
        get_response = admin_client.get(f"{BASE_URL}/api/expenses/{expense_id}")
        assert get_response.json()["status"] == "pending"
        print(f"✓ Expense workflow: draft -> pending verified for {expense_id}")


class TestNavigationLinks:
    """Test navigation endpoints are accessible"""
    
    def test_clients_endpoint_accessible(self, admin_client):
        """Test /api/clients endpoint is accessible (Clients link in Sales Funnel)"""
        response = admin_client.get(f"{BASE_URL}/api/clients")
        assert response.status_code == 200
        print("✓ /api/clients endpoint accessible (Sales Funnel > Clients)")
    
    def test_expenses_endpoint_accessible(self, admin_client):
        """Test /api/expenses endpoint is accessible (Expenses link in Management)"""
        response = admin_client.get(f"{BASE_URL}/api/expenses")
        assert response.status_code == 200
        print("✓ /api/expenses endpoint accessible (Management > Expenses)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
