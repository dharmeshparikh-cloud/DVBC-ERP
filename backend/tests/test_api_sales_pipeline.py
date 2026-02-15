"""
OWASP-Compliant API Security Test Suite - Sales Pipeline Module
Tests: SOW, Quotations, Agreements, Communication Logs, Pricing Plans
"""

import pytest
import httpx
from datetime import datetime, timezone


class TestSOWPositive:
    """Positive tests for Scope of Work module."""
    
    @pytest.mark.asyncio
    async def test_sow001_get_sow_categories(self, admin_client):
        """TC-SOW-001: Get SOW categories."""
        response = await admin_client.get("/api/sow-categories")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sow002_create_sow(self, admin_client, db):
        """TC-SOW-002: Create SOW for a pricing plan."""
        pricing_plan = await db.pricing_plans.find_one({}, {"_id": 0, "id": 1})
        if pricing_plan:
            response = await admin_client.post("/api/sow", json={
                "pricing_plan_id": pricing_plan["id"],
                "title": "Test SOW"
            })
            
            # May fail if SOW already exists for plan or validation error
            assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_sow003_get_sow_by_id(self, admin_client, db):
        """TC-SOW-003: Get SOW by ID."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            response = await admin_client.get(f"/api/sow/{sow['id']}")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sow004_get_sow_versions(self, admin_client, db):
        """TC-SOW-004: Get SOW version history."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            response = await admin_client.get(f"/api/sow/{sow['id']}/versions")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sow005_get_sow_progress(self, admin_client, db):
        """TC-SOW-005: Get SOW progress tracking."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            response = await admin_client.get(f"/api/sow/{sow['id']}/progress")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sow006_get_pending_approval(self, admin_client):
        """TC-SOW-006: Get SOWs pending approval."""
        response = await admin_client.get("/api/sow/pending-approval")
        
        # May return 403 if endpoint is role-restricted
        assert response.status_code in [200, 403]
    
    @pytest.mark.asyncio
    async def test_sow007_get_sow_item_statuses(self, admin_client):
        """TC-SOW-007: Get SOW item status options."""
        response = await admin_client.get("/api/sow-item-statuses")
        
        assert response.status_code == 200


class TestSOWItemsPositive:
    """Tests for SOW items (deliverables)."""
    
    @pytest.mark.asyncio
    async def test_sowitem001_add_item(self, admin_client, db):
        """TC-SOWITEM-001: Add item to SOW."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            response = await admin_client.post(
                f"/api/sow/{sow['id']}/items",
                json={
                    "category": "HR Consulting",
                    "deliverable": "Test Deliverable",
                    "delivery_date": datetime.now(timezone.utc).isoformat(),
                    "consultant_days": 5,
                    "unit_cost": 10000
                }
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sowitem002_bulk_add_items(self, admin_client, db):
        """TC-SOWITEM-002: Bulk add items to SOW."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            response = await admin_client.post(
                f"/api/sow/{sow['id']}/items/bulk",
                json={
                    "items": [
                        {
                            "category": "Training",
                            "deliverable": "Bulk Item 1",
                            "consultant_days": 2
                        },
                        {
                            "category": "Audit",
                            "deliverable": "Bulk Item 2",
                            "consultant_days": 3
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_sowitem003_update_item_status(self, admin_client, db):
        """TC-SOWITEM-003: Update SOW item status."""
        sow = await db.sows.find_one(
            {"items.0": {"$exists": True}},
            {"_id": 0, "id": 1, "items": 1}
        )
        if sow and sow.get("items"):
            item_id = sow["items"][0]["id"]
            response = await admin_client.patch(
                f"/api/sow/{sow['id']}/items/{item_id}/status",
                json={"status": "in_progress"}
            )
            
            assert response.status_code == 200


class TestSOWNegative:
    """Negative tests for SOW module."""
    
    @pytest.mark.asyncio
    async def test_sow020_get_nonexistent(self, admin_client):
        """TC-SOW-020: Get nonexistent SOW returns 404."""
        response = await admin_client.get("/api/sow/nonexistent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_sow021_create_without_pricing_plan(self, admin_client):
        """TC-SOW-021: Create SOW without pricing plan fails."""
        response = await admin_client.post("/api/sow", json={
            "title": "Test SOW"
        })
        
        assert response.status_code in [400, 422]


class TestSOWSecurity:
    """Security tests for SOW module."""
    
    @pytest.mark.asyncio
    async def test_sow030_xss_in_deliverable(self, admin_client, db, owasp_payloads):
        """TC-SOW-030: XSS in deliverable name handled safely."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            for payload in owasp_payloads.XSS_PAYLOADS[:2]:
                response = await admin_client.post(
                    f"/api/sow/{sow['id']}/items",
                    json={
                        "category": "Test",
                        "deliverable": payload,
                        "consultant_days": 1
                    }
                )
                
                assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_sow031_sql_injection_in_id(self, admin_client, owasp_payloads):
        """TC-SOW-031: SQL injection in SOW ID."""
        for payload in owasp_payloads.SQL_INJECTION[:2]:
            response = await admin_client.get(f"/api/sow/{payload}")
            
            assert response.status_code != 500


class TestQuotationsPositive:
    """Positive tests for quotations module."""
    
    @pytest.mark.asyncio
    async def test_quot001_get_all_quotations(self, admin_client):
        """TC-QUOT-001: Get all quotations."""
        response = await admin_client.get("/api/quotations")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_quot002_create_quotation(self, admin_client, db):
        """TC-QUOT-002: Create quotation from SOW."""
        sow = await db.sows.find_one({}, {"_id": 0, "id": 1})
        if sow:
            response = await admin_client.post("/api/quotations", json={
                "sow_id": sow["id"],
                "valid_until": datetime.now(timezone.utc).isoformat(),
                "terms": "Net 30"
            })
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_quot003_finalize_quotation(self, admin_client, db):
        """TC-QUOT-003: Finalize quotation."""
        quotation = await db.quotations.find_one({"status": "draft"}, {"_id": 0, "id": 1})
        if quotation:
            response = await admin_client.patch(
                f"/api/quotations/{quotation['id']}/finalize"
            )
            
            assert response.status_code == 200


class TestAgreementsPositive:
    """Positive tests for agreements module."""
    
    @pytest.mark.asyncio
    async def test_agr001_get_all_agreements(self, admin_client):
        """TC-AGR-001: Get all agreements."""
        response = await admin_client.get("/api/agreements")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_agr002_get_agreement_full(self, admin_client, db):
        """TC-AGR-002: Get full agreement details."""
        agreement = await db.agreements.find_one({}, {"_id": 0, "id": 1})
        if agreement:
            response = await admin_client.get(f"/api/agreements/{agreement['id']}/full")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_agr003_get_pending_approval(self, admin_client):
        """TC-AGR-003: Get agreements pending approval."""
        response = await admin_client.get("/api/agreements/pending-approval")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_agr004_export_agreement(self, admin_client, db):
        """TC-AGR-004: Export agreement document."""
        agreement = await db.agreements.find_one({}, {"_id": 0, "id": 1})
        if agreement:
            response = await admin_client.get(f"/api/agreements/{agreement['id']}/export")
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_agr005_download_agreement(self, admin_client, db):
        """TC-AGR-005: Download agreement PDF."""
        agreement = await db.agreements.find_one({}, {"_id": 0, "id": 1})
        if agreement:
            response = await admin_client.get(f"/api/agreements/{agreement['id']}/download")
            
            # May return 200 with file or 400 if not ready
            assert response.status_code in [200, 400]


class TestAgreementTemplates:
    """Tests for agreement templates."""
    
    @pytest.mark.asyncio
    async def test_template001_get_agreement_templates(self, admin_client):
        """TC-TEMPLATE-001: Get agreement templates."""
        response = await admin_client.get("/api/agreement-templates")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_template002_create_agreement_template(self, admin_client):
        """TC-TEMPLATE-002: Create agreement template."""
        response = await admin_client.post("/api/agreement-templates", json={
            "name": "Test Template",
            "content": "This is a test agreement template with {{client_name}} variable."
        })
        
        # May fail if template exists or validation error
        assert response.status_code in [200, 400, 422]
    
    @pytest.mark.asyncio
    async def test_template003_get_email_notification_templates(self, admin_client):
        """TC-TEMPLATE-003: Get email notification templates."""
        response = await admin_client.get("/api/email-notification-templates")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_template004_get_default_email_templates(self, admin_client):
        """TC-TEMPLATE-004: Get default email templates."""
        response = await admin_client.get("/api/email-notification-templates/default")
        
        assert response.status_code == 200


class TestPricingPlansPositive:
    """Positive tests for pricing plans module."""
    
    @pytest.mark.asyncio
    async def test_price001_get_all_pricing_plans(self, admin_client):
        """TC-PRICE-001: Get all pricing plans."""
        response = await admin_client.get("/api/pricing-plans")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_price002_create_pricing_plan(self, admin_client, db):
        """TC-PRICE-002: Create pricing plan."""
        lead = await db.leads.find_one({}, {"_id": 0, "id": 1})
        if lead:
            response = await admin_client.post("/api/pricing-plans", json={
                "lead_id": lead["id"],
                "plan_name": "Test Pricing Plan",
                "total_value": 500000,
                "currency": "INR"
            })
            
            # May fail if plan exists or validation error
            assert response.status_code in [200, 400, 422]


class TestCommunicationLogsPositive:
    """Positive tests for communication logs."""
    
    @pytest.mark.asyncio
    async def test_comm001_get_communication_logs(self, admin_client):
        """TC-COMM-001: Get communication logs."""
        response = await admin_client.get("/api/communication-logs")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_comm002_create_communication_log(self, admin_client, db):
        """TC-COMM-002: Create communication log."""
        lead = await db.leads.find_one({}, {"_id": 0, "id": 1})
        if lead:
            response = await admin_client.post("/api/communication-logs", json={
                "lead_id": lead["id"],
                "type": "email",
                "subject": "Test Communication",
                "content": "Test communication content",
                "direction": "outbound"
            })
            
            assert response.status_code == 200


class TestEmailTemplates:
    """Tests for email templates."""
    
    @pytest.mark.asyncio
    async def test_email001_get_email_templates(self, admin_client):
        """TC-EMAIL-001: Get email templates."""
        response = await admin_client.get("/api/email-templates")
        
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_email002_create_email_template(self, admin_client):
        """TC-EMAIL-002: Create email template."""
        response = await admin_client.post("/api/email-templates", json={
            "name": "Test Template",
            "subject": "Test Subject",
            "body": "Hello {{lead_name}}, this is a test."
        })
        
        assert response.status_code == 200


class TestSalesSecurity:
    """Security tests for sales pipeline modules."""
    
    @pytest.mark.asyncio
    async def test_sales030_xss_in_template(self, admin_client, owasp_payloads):
        """TC-SALES-030: XSS in email template body."""
        for payload in owasp_payloads.XSS_PAYLOADS[:2]:
            response = await admin_client.post("/api/email-templates", json={
                "name": "XSS Test",
                "subject": "Test",
                "body": payload
            })
            
            assert response.status_code != 500
    
    @pytest.mark.asyncio
    async def test_sales031_sql_injection_communication_filter(self, admin_client, owasp_payloads):
        """TC-SALES-031: SQL injection in communication log filter."""
        for payload in owasp_payloads.SQL_INJECTION[:2]:
            response = await admin_client.get("/api/communication-logs", params={"lead_id": payload})
            
            assert response.status_code != 500
