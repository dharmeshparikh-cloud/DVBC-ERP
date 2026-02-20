# DVBC-NETRA ERP: Sales to Project E2E Flow

## Complete Flow Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   LEAD      │ ──▶ │  QUOTATION  │ ──▶ │  AGREEMENT  │ ──▶ │   KICKOFF   │
│  (Sales)    │     │   (Sales)   │     │   (Sales)   │     │   REQUEST   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  Create Lead        Create Pricing      Sign Agreement      PM Accepts
  Qualify Lead       Generate Quote      Add SOW Items       Convert to
  Convert to         Finalize Quote                          PROJECT
  Client                                                          │
                                                                  ▼
                                                         ┌─────────────┐
                                                         │   PROJECT   │
                                                         │ (Consulting)│
                                                         └─────────────┘
                                                                  │
                                                                  ▼
                                                         Assign Consultants
                                                         Track Meetings
                                                         Manage SOW Items
```

---

## STEP 1: Lead Creation

**Endpoint:** `POST /api/leads`

**Required Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| first_name | string | ✅ Yes | Contact's first name |
| last_name | string | ✅ Yes | Contact's last name |
| company | string | ✅ Yes | Company name |
| email | string | Optional | Contact email |
| phone | string | Optional | Contact phone |
| lead_source | string | Optional | Source of lead (Referral, Website, etc.) |
| status | string | Optional | Lead status (new, contacted, qualified, etc.) |
| assigned_to | string | Optional | Sales rep user ID |
| notes | string | Optional | Additional notes |

**Example:**
```json
{
  "first_name": "Hery",
  "last_name": "Shah",
  "company": "Hery India Pvt Ltd",
  "email": "hery.shah@heryindia.com",
  "phone": "9876500002",
  "lead_source": "Referral",
  "status": "new",
  "assigned_to": "rahul-user-id"
}
```

---

## STEP 2: Lead Qualification & Client Conversion

**Update Lead Status:**
`PATCH /api/leads/{lead_id}`
```json
{"status": "qualified"}
```

**Convert to Client:**
`POST /api/leads/{lead_id}/convert`

This creates a Client record linked to the Lead.

---

## STEP 3: Pricing Plan & Quotation

**Create Pricing Plan:**
`POST /api/pricing-plans`

**Required Fields:**
| Field | Type | Required |
|-------|------|----------|
| name | string | ✅ Yes |
| consultants | array | ✅ Yes |
| total_months | int | ✅ Yes |
| discount_percentage | float | Optional |
| gst_percentage | float | Optional |

**Create Quotation:**
`POST /api/quotations`

**Required Fields:**
| Field | Type | Required |
|-------|------|----------|
| lead_id | string | ✅ Yes |
| pricing_plan_id | string | ✅ Yes |
| base_rate_per_meeting | float | ✅ Yes |
| valid_until | date | ✅ Yes |

**Finalize Quotation:**
`PATCH /api/quotations/{quotation_id}/finalize`

---

## STEP 4: Agreement Creation

**Endpoint:** `POST /api/agreements`

**Required Fields:**
| Field | Type | Required |
|-------|------|----------|
| quotation_id | string | ✅ Yes |
| client_id | string | ✅ Yes |
| lead_id | string | Optional |
| start_date | date | ✅ Yes |
| end_date | date | ✅ Yes |

The agreement inherits values from the quotation.

**Sign Agreement:**
`POST /api/agreements/{agreement_id}/sign`

---

## STEP 5: SOW (Statement of Work)

**Add SOW Items:**
`POST /api/sow-items`

**Required Fields:**
| Field | Type | Required |
|-------|------|----------|
| agreement_id | string | ✅ Yes |
| category | string | ✅ Yes |
| description | string | ✅ Yes |
| deliverables | array | ✅ Yes |
| priority | string | Optional |

---

## STEP 6: Kickoff Request (Sales → Consulting Handover)

**Endpoint:** `POST /api/kickoff-requests`

**Required Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| agreement_id | string | ✅ Yes | Linked agreement |
| client_name | string | ✅ Yes | Client company name |
| project_name | string | ✅ Yes | Name for the project |
| project_type | string | Optional | online/offline/mixed |
| total_meetings | int | Optional | Total meetings committed |
| meeting_frequency | string | Optional | Weekly/Monthly/Quarterly |
| project_tenure_months | int | Optional | Duration in months |
| expected_start_date | date | Optional | Proposed start date |
| assigned_pm_id | string | Optional | Assigned Project Manager |
| notes | string | Optional | Handover notes |

**Example:**
```json
{
  "agreement_id": "agr-123",
  "client_name": "Hery India Pvt Ltd",
  "project_name": "Business Consulting - Hery India",
  "project_type": "mixed",
  "total_meetings": 24,
  "meeting_frequency": "Monthly",
  "project_tenure_months": 12,
  "expected_start_date": "2026-03-01",
  "assigned_pm_id": "dharmesh-user-id",
  "notes": "Key focus: Process optimization and digital transformation"
}
```

---

## STEP 7: Kickoff Acceptance (PM/Consultant)

**Accept Kickoff:**
`PUT /api/kickoff-requests/{request_id}/accept`

This creates a PROJECT and assigns the consultant.

**Who Can Accept:**
- Admin
- HR Manager
- Senior Consultant (with reportees)
- Principal Consultant

---

## STEP 8: Project Created

**Project Fields (Auto-populated):**
| Field | Source |
|-------|--------|
| name | From kickoff.project_name |
| client_name | From kickoff.client_name |
| lead_id | From kickoff.lead_id |
| agreement_id | From kickoff.agreement_id |
| project_type | From kickoff.project_type |
| start_date | From kickoff.expected_start_date |
| total_meetings_committed | From kickoff.total_meetings |
| assigned_consultants | [PM who accepted] |
| budget | From agreement.total_value |
| created_by | PM who accepted |

---

## User Roles in Flow

| Step | Sales (Rahul) | Consultant (Dharmesh) | Admin |
|------|---------------|----------------------|-------|
| Create Lead | ✅ Can do | ❌ No access | ✅ Can do |
| Create Quotation | ✅ Can do | ❌ No access | ✅ Can do |
| Create Agreement | ✅ Can do | ❌ No access | ✅ Can do |
| Submit Kickoff | ✅ Can do | ❌ No access | ✅ Can do |
| Accept Kickoff | ❌ No | ✅ Can accept | ✅ Can do |
| Manage Project | View only | ✅ Full access | ✅ Can do |

---

## API Testing Summary

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| /api/leads | POST | ✅ Working | Create lead |
| /api/leads/{id} | PATCH | ✅ Working | Update status |
| /api/leads/{id}/convert | POST | ✅ Working | Convert to client |
| /api/pricing-plans | POST | ✅ Working | Create pricing |
| /api/quotations | POST | ✅ Working | Create quote |
| /api/quotations/{id}/finalize | PATCH | ✅ Working | Finalize |
| /api/agreements | POST | ✅ Working | Needs quotation_id |
| /api/kickoff-requests | POST | ✅ Working | Submit handover |
| /api/kickoff-requests/{id}/accept | PUT | ✅ Working | Creates project |
| /api/projects | GET | ✅ Working | List projects |

---

## Test Credentials

| Role | Email | Password | Can Do |
|------|-------|----------|--------|
| Sales | rahul.kumar@dvbc.com | Welcome@EMP001 | Create leads, quotes, agreements |
| Admin | admin@dvbc.com | admin123 | Everything |
| HR Manager | hr.manager@dvbc.com | hr123 | Onboarding, approvals |

---

## Key Findings

1. **Lead → Client** conversion works but client_id not returned in response
2. **Agreement requires quotation_id** - cannot skip quotation step
3. **Kickoff → Project** flow is fully functional
4. **Role-based access** properly enforced throughout flow
