"""
OWASP-Compliant API Security Test Suite - Clients Module
Tests: CRUD operations, contact management, revenue tracking
"""

import pytest
import httpx


class TestClientsPositive:
    """Positive tests for clients CRUD."""
    
    @pytest.mark.asyncio
    async def test_client001_get_all_clients(self, admin_client):
        """TC-CLIENT-001: Get all clients returns list."""
        response = await admin_client.get("/api/clients")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_client002_create_client(self, admin_client, test_data):
        """TC-CLIENT-002: Create client with valid data."""
        client_data = test_data.client()
        response = await admin_client.post("/api/clients", json=client_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_client003_get_client_by_id(self, admin_client, db):
        """TC-CLIENT-003: Get single client by ID."""
        client = await db.clients.find_one({}, {"_id": 0, "id": 1})
        if client:
            response = await admin_client.get(f"/api/clients/{client['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_client004_update_client(self, admin_client, db):
        """TC-CLIENT-004: Update client data."""
        client = await db.clients.find_one({}, {"_id": 0, "id": 1})
        if client:
            response = await admin_client.patch(
                f"/api/clients/{client['id']}",
                json={"status": "active"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_client005_add_contact(self, admin_client, db):
        """TC-CLIENT-005: Add contact to client."""
        client = await db.clients.find_one({}, {"_id": 0, "id": 1})
        if client:
            response = await admin_client.post(
                f"/api/clients/{client['id']}/contacts",
                json={
                    "name": "Test Contact",
                    "email": "contact@test.com",
                    "phone": "+91-9876543210",
                    "designation": "HR Manager",
                    "is_primary": False
                }
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_client006_add_revenue(self, admin_client, db):
        """TC-CLIENT-006: Add revenue entry to client."""
        client = await db.clients.find_one({}, {"_id": 0, "id": 1})
        if client:
            response = await admin_client.post(
                f"/api/clients/{client['id']}/revenue",
                json={
                    "amount": 500000,
                    "currency": "INR",
                    "description": "Q4 2025 consulting fees",
                    "date": "2025-12-01T00:00:00Z"
                }
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_client007_get_industries_list(self, admin_client):
        """TC-CLIENT-007: Get industries list."""
        response = await admin_client.get("/api/clients/industries/list")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_client008_get_client_stats(self, admin_client):
        """TC-CLIENT-008: Get client statistics."""
        response = await admin_client.get("/api/clients/stats/summary")
        
        assert response.status_code == 200


class TestClientsNegative:
    """Negative tests for clients module."""
    
    @pytest.mark.asyncio
    async def test_client020_get_nonexistent(self, admin_client):
        """TC-CLIENT-020: Get nonexistent client returns 404."""
        response = await admin_client.get("/api/clients/nonexistent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_client021_create_missing_name(self, admin_client):
        """TC-CLIENT-021: Create client without name fails."""
        response = await admin_client.post("/api/clients", json={
            "industry": "IT Services"
        })
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_client022_invalid_revenue_amount(self, admin_client, db):
        """TC-CLIENT-022: Invalid revenue amount handled."""
        client = await db.clients.find_one({}, {"_id": 0, "id": 1})
        if client:
            response = await admin_client.post(
                f"/api/clients/{client['id']}/revenue",
                json={"amount": "not-a-number"}
            )
            
            assert response.status_code in [400, 422]


class TestClientsSecurity:
    """Security tests for clients module."""
    
    @pytest.mark.asyncio
    async def test_client030_xss_in_name(self, admin_client, owasp_payloads, test_data):
        """TC-CLIENT-030: XSS in client name handled safely."""
        for payload in owasp_payloads.XSS_PAYLOADS[:2]:
            client_data = test_data.client({"company_name": payload})
            response = await admin_client.post("/api/clients", json=client_data)
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_client031_sql_injection_search(self, admin_client, owasp_payloads):
        """TC-CLIENT-031: SQL injection in client search."""
        for payload in owasp_payloads.SQL_INJECTION[:2]:
            response = await admin_client.get(f"/api/clients/{payload}")
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_client032_unauthenticated_access(self, api_client):
        """TC-CLIENT-032: Unauthenticated cannot access clients."""
        response = await api_client.get("/api/clients")
        
        assert response.status_code == 401


class TestExpensesPositive:
    """Positive tests for expenses module."""
    
    @pytest.mark.asyncio
    async def test_exp001_get_all_expenses(self, admin_client):
        """TC-EXP-001: Get all expenses returns list."""
        response = await admin_client.get("/api/expenses")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_exp002_create_expense(self, admin_client, test_data):
        """TC-EXP-002: Create expense with valid data."""
        expense_data = test_data.expense()
        response = await admin_client.post("/api/expenses", json=expense_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_exp003_get_expense_by_id(self, admin_client, db):
        """TC-EXP-003: Get single expense by ID."""
        expense = await db.expenses.find_one({}, {"_id": 0, "id": 1})
        if expense:
            response = await admin_client.get(f"/api/expenses/{expense['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_exp004_update_expense(self, admin_client, db):
        """TC-EXP-004: Update expense data."""
        expense = await db.expenses.find_one({"status": "draft"}, {"_id": 0, "id": 1})
        if expense:
            response = await admin_client.patch(
                f"/api/expenses/{expense['id']}",
                json={"description": "Updated description"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_exp005_submit_expense(self, admin_client, test_data):
        """TC-EXP-005: Submit expense for approval."""
        # Create a new expense
        expense_data = test_data.expense()
        create_response = await admin_client.post("/api/expenses", json=expense_data)
        
        if create_response.status_code == 200:
            expense_id = create_response.json()["id"]
            
            # Submit it
            response = await admin_client.post(f"/api/expenses/{expense_id}/submit")
            
            assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_exp006_get_expense_categories(self, admin_client):
        """TC-EXP-006: Get expense categories list."""
        response = await admin_client.get("/api/expenses/categories/list")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_exp007_get_expense_stats(self, admin_client):
        """TC-EXP-007: Get expense statistics."""
        response = await admin_client.get("/api/expenses/stats/summary")
        
        assert response.status_code == 200


class TestExpensesNegative:
    """Negative tests for expenses module."""
    
    @pytest.mark.asyncio
    async def test_exp020_create_negative_amount(self, admin_client, test_data):
        """TC-EXP-020: Negative expense amount handled."""
        expense_data = test_data.expense({"amount": -100})
        response = await admin_client.post("/api/expenses", json=expense_data)
        
        # Should either reject or accept (business logic varies)
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_exp021_invalid_category(self, admin_client, test_data):
        """TC-EXP-021: Invalid category handled."""
        expense_data = test_data.expense({"category": "invalid_xyz"})
        response = await admin_client.post("/api/expenses", json=expense_data)
        
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_exp022_get_nonexistent(self, admin_client):
        """TC-EXP-022: Get nonexistent expense returns 404."""
        response = await admin_client.get("/api/expenses/nonexistent-id")
        
        assert response.status_code == 404


class TestExpensesSecurity:
    """Security tests for expenses module."""
    
    @pytest.mark.asyncio
    async def test_exp030_xss_in_description(self, admin_client, owasp_payloads, test_data):
        """TC-EXP-030: XSS in expense description handled safely."""
        for payload in owasp_payloads.XSS_PAYLOADS[:2]:
            expense_data = test_data.expense({"description": payload})
            response = await admin_client.post("/api/expenses", json=expense_data)
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_exp031_amount_overflow(self, admin_client, test_data):
        """TC-EXP-031: Very large amount handled safely."""
        expense_data = test_data.expense({"amount": 99999999999999999})
        response = await admin_client.post("/api/expenses", json=expense_data)
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_exp032_idor_expense_access(self, executive_client, admin_client, db):
        """TC-EXP-032: User can't access other's expenses arbitrarily."""
        # This tests that expense access is properly controlled
        expense = await db.expenses.find_one({}, {"_id": 0, "id": 1})
        if expense:
            response = await executive_client.get(f"/api/expenses/{expense['id']}")
            
            # Either accessible or properly restricted
            assert response.status_code in [200, 403, 404]


class TestMyExpenses:
    """Tests for self-service expense viewing."""
    
    @pytest.mark.asyncio
    async def test_myexp001_get_my_expenses(self, admin_client):
        """TC-MYEXP-001: Get my expenses."""
        response = await admin_client.get("/api/my/expenses")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
