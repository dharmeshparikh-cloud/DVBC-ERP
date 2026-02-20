# DVBC-NETRA ERP: Complete Sales to Project E2E Flow
## Tested & Verified: February 20, 2026

---

## FLOW DIAGRAM

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    LEAD      │  ──▶ │   PRICING    │  ──▶ │  QUOTATION   │  ──▶ │   CLIENT     │
│  (Sales)     │      │    PLAN      │      │  (Finalize)  │      │  (Create)    │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
                                                                         │
┌──────────────────────────────────────────────────────────────────────────┘
│
▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  AGREEMENT   │  ──▶ │   PAYMENT    │  ──▶ │   KICKOFF    │  ──▶ │   PROJECT    │
│   (Sign)     │      │  VERIFICATION│      │   REQUEST    │      │  (Created)   │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘
                            │                      │                      │
                            ▼                      ▼                      ▼
                      SOW Handover           PM Accepts            Consultants
                        Triggered            & Creates              Assigned
```

---

## STEP-BY-STEP WITH API CALLS

### STEP 1: Create Lead
**Endpoint:** `POST /api/leads`

```json
{
  "first_name": "Hery",
  "last_name": "Modi",
  "company": "Hery India Corp",
  "email": "hery.modi@heryindia.com",
  "phone": "9988776655",
  "lead_source": "Referral",
  "status": "qualified",
  "assigned_to": "sales_user_id"
}
```

**Response:** `{ "id": "lead_xxx" }`

---

### STEP 2: Create Pricing Plan
**Endpoint:** `POST /api/pricing-plans`

```json
{
  "name": "Hery India - Premium 12M",
  "consultants": [
    {
      "name": "Senior Consultant",
      "level": "senior",
      "meetings_per_month": 2,
      "rate": 50000
    }
  ],
  "total_months": 12,
  "discount_percentage": 5,
  "gst_percentage": 18
}
```

**Response:** `{ "id": "plan_xxx" }`

---

### STEP 3: Create & Finalize Quotation
**Endpoint:** `POST /api/quotations`

```json
{
  "lead_id": "lead_xxx",
  "pricing_plan_id": "plan_xxx",
  "base_rate_per_meeting": 50000,
  "valid_until": "2026-03-31"
}
```

**Finalize:** `PATCH /api/quotations/{quote_id}/finalize`

---

### STEP 4: Create Client
**Endpoint:** `POST /api/clients`

```json
{
  "name": "Hery India Corp",
  "company_name": "Hery India Corp",
  "email": "accounts@heryindia.com",
  "phone": "9988776655",
  "lead_id": "lead_xxx",
  "industry": "Technology",
  "assigned_sales_rep": "sales_user_id"
}
```

---

### STEP 5: Create & Sign Agreement
**Endpoint:** `POST /api/agreements`

```json
{
  "quotation_id": "quote_xxx",
  "client_id": "client_xxx",
  "lead_id": "lead_xxx",
  "start_date": "2026-03-01",
  "end_date": "2027-02-28"
}
```

**Sign:** `POST /api/agreements/{agreement_id}/sign`

---

### STEP 6: Verify First Payment ⚠️ CRITICAL
**Endpoint:** `POST /api/payments/verify-installment`

```json
{
  "agreement_id": "agreement_xxx",
  "installment_number": 1,
  "expected_amount": 100000,
  "received_amount": 100000,
  "transaction_id": "TXN123456",
  "payment_date": "2026-02-20",
  "payment_mode": "Bank Transfer",
  "remarks": "First advance payment verified"
}
```

**Response:**
```json
{
  "message": "Payment verified successfully",
  "payment_id": "payment_xxx",
  "sow_handover_triggered": true
}
```

**⚠️ This step is REQUIRED before kickoff request can be created!**

---

### STEP 7: Submit Kickoff Request
**Endpoint:** `POST /api/kickoff-requests`

```json
{
  "agreement_id": "agreement_xxx",
  "client_name": "Hery India Corp",
  "project_name": "Business Consulting - Hery India",
  "project_type": "mixed",
  "total_meetings": 24,
  "meeting_frequency": "Monthly",
  "project_tenure_months": 12,
  "expected_start_date": "2026-03-01",
  "assigned_pm_id": "consultant_user_id",
  "notes": "Focus: Process optimization"
}
```

---

### STEP 8: Accept Kickoff → Project Created
**Endpoint:** `POST /api/kickoff-requests/{kickoff_id}/accept`

**Who Can Accept:**
- Admin
- HR Manager  
- Senior Consultant (with reportees)
- Principal Consultant

**Response:**
```json
{
  "message": "Kickoff request accepted",
  "project_id": "project_xxx"
}
```

---

### STEP 9: Assign Consultants to Project
**Endpoint:** `POST /api/projects/{project_id}/assign-consultant`

```json
{
  "project_id": "project_xxx",
  "consultant_id": "consultant_user_id",
  "role": "Lead Consultant",
  "allocation_percentage": 50
}
```

**Response:**
```json
{
  "message": "Consultant assigned successfully",
  "assignment_id": "assignment_xxx"
}
```

---

## TEST RESULTS SUMMARY

| Step | Status | Notes |
|------|--------|-------|
| 1. Create Lead | ✅ PASS | Lead ID: 33b835da-... |
| 2. Create Pricing Plan | ✅ PASS | Plan ID created |
| 3. Create Quotation | ✅ PASS | Quotation finalized |
| 4. Create Client | ✅ PASS | Client linked to lead |
| 5. Create Agreement | ✅ PASS | Agreement signed |
| 6. Verify Payment | ✅ PASS | SOW handover triggered |
| 7. Submit Kickoff | ✅ PASS | Kickoff ID: f1b63850-... |
| 8. Accept Kickoff | ✅ PASS | Project ID: bf64d6c3-... |
| 9. Assign Consultant | ✅ PASS | Assignment ID: c7b11c96-... |

---

## ROLE-BASED ACCESS

| Action | Sales | Consultant | Admin |
|--------|-------|------------|-------|
| Create Lead | ✅ | ❌ | ✅ |
| Create Quotation | ✅ | ❌ | ✅ |
| Sign Agreement | ✅ | ❌ | ✅ |
| Verify Payment | ✅ | ❌ | ✅ |
| Submit Kickoff | ✅ | ❌ | ✅ |
| Accept Kickoff | ❌ | ✅ | ✅ |
| Assign Consultant | ❌ | ✅ (PM) | ✅ |
| Manage Project | View | ✅ Full | ✅ Full |

---

## BUSINESS RULES

1. **Payment Before Kickoff**: First installment must be verified before kickoff request can be created
2. **SOW Auto-Handover**: First payment triggers SOW items to be transferred to consulting team
3. **PM Assignment**: Kickoff request specifies `assigned_pm_id` who becomes primary project owner
4. **Consultant Limits**: Consultants have max project allocation limits (configurable)
5. **Project Auto-Active**: Project status set to "active" on kickoff acceptance

---

## VERIFIED PROJECTS

| Project Name | Client | Status | Consultants |
|--------------|--------|--------|-------------|
| Hery PVT LTD - Business Consulting | Hery PVT LTD | active | 1 assigned |
| Business Consulting - Hery India | Hery India Corp | active | 1 assigned |

---

## DOWNLOAD LINK

📥 This document: `/app/test_reports/SALES_TO_PROJECT_E2E_COMPLETE.md`

---

*E2E Test Completed Successfully - February 20, 2026*
