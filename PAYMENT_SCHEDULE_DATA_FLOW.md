# PAYMENT SCHEDULE DATA FLOW ANALYSIS
## Where Does Consultant Get Payment Schedule?

---

## 📊 COMPLETE DATA FLOW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SALES PHASE (Before Kickoff)                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: SALES Creates PRICING PLAN                                             │
│  ────────────────────────────────────────────────────────                       │
│  Collection: pricing_plans                                                       │
│  Endpoint: POST /api/pricing-plans                                              │
│  Created By: Sales Executive                                                    │
│                                                                                 │
│  Contains:                                                                      │
│  ├── lead_id                                                                    │
│  ├── consultants[] (team composition)                                           │
│  ├── duration_months                                                            │
│  ├── total_amount                                                               │
│  └── payment_plan: {                                                            │
│        schedule_breakdown: [                                                    │
│          {frequency: "Month 1", due_date: "2026-03-01", basic: 100000, ...},   │
│          {frequency: "Month 2", due_date: "2026-04-01", basic: 100000, ...},   │
│          {frequency: "Month 3", due_date: "2026-05-01", basic: 100000, ...}    │
│        ]                                                                        │
│      }                                                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: SALES Creates QUOTATION (links to pricing_plan)                        │
│  ────────────────────────────────────────────────────────                       │
│  Collection: quotations                                                          │
│  Endpoint: POST /api/quotations                                                 │
│                                                                                 │
│  Contains:                                                                      │
│  ├── pricing_plan_id ──────────────────────► Links to pricing_plan             │
│  └── ...                                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: SALES Creates AGREEMENT (links to quotation)                           │
│  ────────────────────────────────────────────────────────                       │
│  Collection: agreements                                                          │
│  Endpoint: POST /api/agreements                                                 │
│                                                                                 │
│  Contains:                                                                      │
│  ├── quotation_id ────────────────────────► Links to quotation                 │
│  ├── pricing_plan_id ─────────────────────► Direct link to pricing_plan        │
│  └── status: "approved"                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: FIRST PAYMENT VERIFIED                                                 │
│  ────────────────────────────────────────────────────────                       │
│  Collection: payment_verifications                                              │
│  Endpoint: POST /api/payments/verify                                            │
│                                                                                 │
│  Contains:                                                                      │
│  ├── agreement_id ────────────────────────► Links to agreement                 │
│  ├── installment_number: 1                                                      │
│  ├── status: "verified"                                                         │
│  └── received_amount                                                            │
│                                                                                 │
│  🔒 BLOCKER: Kickoff request BLOCKED without this!                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: KICKOFF REQUEST Created & Accepted                                     │
│  ────────────────────────────────────────────────────────                       │
│  Collection: kickoff_requests                                                   │
│  Endpoint: POST /api/kickoff-requests/{id}/accept                               │
│                                                                                 │
│  On Accept → PROJECT Created with:                                              │
│  ├── agreement_id ────────────────────────► From kickoff                       │
│  ├── pricing_plan_id ─────────────────────► From agreement                     │
│  └── status: "active"                                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         CONSULTING PHASE (After Kickoff)                        │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: CONSULTANT Views Payment Schedule                                      │
│  ────────────────────────────────────────────────────────                       │
│  Endpoint: GET /api/project-payments/project/{project_id}                       │
│  File: /app/backend/routers/project_payments.py                                 │
│                                                                                 │
│  DATA LOOKUP CHAIN:                                                             │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  project.pricing_plan_id                                                 │  │
│  │         │                                                                 │  │
│  │         ▼                                                                 │  │
│  │  pricing_plans.find(id: pricing_plan_id)                                 │  │
│  │         │                                                                 │  │
│  │         ▼                                                                 │  │
│  │  pricing_plan.payment_plan.schedule_breakdown[]                          │  │
│  │         │                                                                 │  │
│  │         ▼                                                                 │  │
│  │  Return to Consultant (with visibility rules)                            │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  VISIBILITY RULES (Role-Based):                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │  Role                    │ Sees Dates │ Sees Amounts │ Sees First Payment │  │
│  │  ─────────────────────────────────────────────────────────────────────── │  │
│  │  Consultant              │     ✅     │      ❌      │        ❌          │  │
│  │  Reporting Manager       │     ✅     │      ❌      │        ❌          │  │
│  │  Project Manager         │     ✅     │      ❌      │        ✅          │  │
│  │  Principal Consultant    │     ✅     │      ✅      │        ✅          │  │
│  │  Admin                   │     ✅     │      ✅      │        ✅          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: CONSULTANT Records Payment                                             │
│  ────────────────────────────────────────────────────────                       │
│  Collection: installment_payments                                               │
│  Endpoint: POST /api/project-payments/record-payment                            │
│                                                                                 │
│  Consultant submits:                                                            │
│  ├── project_id                                                                 │
│  ├── installment_number (2, 3, 4, ...)                                         │
│  ├── transaction_id                                                             │
│  ├── amount_received                                                            │
│  └── payment_date                                                               │
│                                                                                 │
│  System records:                                                                │
│  ├── recorded_by: consultant_id                                                 │
│  ├── expected_amount (from pricing_plan)                                        │
│  └── status: "received"                                                         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ❌ GAPS IN PAYMENT SCHEDULE FLOW

### GAP 1: Schedule Breakdown May Not Exist
```
pricing_plan.payment_plan.schedule_breakdown = []  // Can be empty!
```

**Problem:** If sales doesn't create schedule_breakdown, consultant sees NO payment schedule.

**Where it breaks:** `project_payments.py` line 143-144
```python
schedule_breakdown = pricing_plan["payment_plan"].get("schedule_breakdown", [])
# If empty, no schedule shown to consultant!
```

**Fix Needed:** Validate schedule_breakdown exists before kickoff accept.

---

### GAP 2: No Due Date Calculation
```
schedule_breakdown[].due_date = "2026-03-01"  // Hardcoded by sales!
```

**Problem:** Due dates are manually entered by sales, not calculated from project start.

**Impact:** If project starts late, due dates are still the old ones.

**Fix Needed:** Calculate due dates relative to project.start_date.

---

### GAP 3: No Linkage to SOW/Milestones
```
schedule_breakdown = [
  {frequency: "Month 1", due_date: "...", ...},  // Not linked to any milestone!
  {frequency: "Month 2", due_date: "...", ...},
]
```

**Problem:** Payments are TIME-BASED ("Month 1"), not MILESTONE-BASED ("Scope X Complete").

**Impact:** Payment due even if no work delivered.

**Fix Needed:** Add `linked_scope_ids[]` to each schedule item.

---

### GAP 4: No Payment Completion Check
```
// After all payments recorded, NOTHING happens!
installment_payments.find({project_id: "xxx"})  // Just stored, no trigger
```

**Problem:** Recording all payments doesn't trigger project completion check.

**Impact:** Project stays "active" even after all payments received.

**Fix Needed:** After payment recording, check if all payments complete → notify PM.

---

### GAP 5: First Payment is Separate
```
First Payment:    payment_verifications (installment_number: 1)
Other Payments:   installment_payments (installment_number: 2, 3, ...)
```

**Problem:** First payment is in different collection from other payments!

**Impact:** Completion check must query TWO collections.

**Current Code (project_payments.py):**
```python
# First payment
first_payment = await db.payment_verifications.find_one(...)

# Other payments  
recorded_payments = await db.installment_payments.find(...)
```

---

## 📋 REQUIRED FIXES FOR YOUR REQUIREMENT

### Fix 1: Validate Schedule Exists Before Kickoff Accept

**File:** `/app/backend/routers/kickoff.py`
```python
# ADD before project creation
pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id})
schedule = pricing_plan.get("payment_plan", {}).get("schedule_breakdown", [])
if not schedule:
    raise HTTPException(400, "Pricing plan has no payment schedule. Cannot proceed with kickoff.")
```

### Fix 2: Calculate Due Dates from Project Start

**File:** `/app/backend/routers/kickoff.py`
```python
# ADD when creating project
def calculate_payment_due_dates(schedule_breakdown, project_start_date):
    """Recalculate due dates relative to project start"""
    for idx, item in enumerate(schedule_breakdown):
        # Month 1 = 30 days after start, Month 2 = 60 days, etc.
        due_date = project_start_date + timedelta(days=(idx + 1) * 30)
        item['due_date'] = due_date.isoformat()
    return schedule_breakdown
```

### Fix 3: Link SOW Scopes to Payment Installments

**File:** `/app/backend/models/enhanced_sow.py`
```python
class EnhancedScopeItem(BaseModel):
    # ADD
    linked_payment_installment: Optional[int] = None  # Which installment this unlocks
```

**File:** Payment schedule creation
```python
schedule_breakdown = [
    {
        "frequency": "Month 1",
        "due_date": "2026-03-01",
        "linked_scope_ids": ["scope-1", "scope-2"],  # ADD THIS
        ...
    }
]
```

### Fix 4: Trigger Completion Check After Payment

**File:** `/app/backend/routers/project_payments.py`
```python
# ADD after recording payment
async def check_all_payments_complete(project_id: str):
    """Check if all payments received and notify"""
    project = await db.projects.find_one({"id": project_id})
    pricing_plan = await db.pricing_plans.find_one({"id": project.get("pricing_plan_id")})
    
    total_installments = len(pricing_plan.get("payment_plan", {}).get("schedule_breakdown", []))
    
    # Count recorded payments
    recorded = await db.installment_payments.count_documents({"project_id": project_id})
    
    # Check first payment
    first_payment = await db.payment_verifications.find_one({
        "agreement_id": project.get("agreement_id"),
        "status": "verified"
    })
    if first_payment:
        recorded += 1
    
    if recorded >= total_installments:
        # All payments complete! Notify PM
        await send_notification(
            project.get("created_by"),  # PM
            f"All {total_installments} payments recorded for {project.get('name')}"
        )
        
        # Update project
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"all_payments_received": True}}
        )
```

---

## 📊 DATA FLOW DIAGRAM (Your Requirement)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        YOUR REQUIRED COMPLETION FLOW                            │
└─────────────────────────────────────────────────────────────────────────────────┘

     SALES                    PM/MANAGER                    CONSULTANT
       │                          │                              │
       │  1. Create Pricing Plan  │                              │
       │     with schedule_breakdown                             │
       │     + linked_scope_ids   │                              │
       ├─────────────────────────►│                              │
       │                          │                              │
       │  2. First Payment        │                              │
       │     Verified             │                              │
       ├─────────────────────────►│                              │
       │                          │                              │
       │                          │  3. Accept Kickoff           │
       │                          │     → Project Created        │
       │                          │     → Due dates calculated   │
       │                          │     → SOW linked             │
       │                          ├─────────────────────────────►│
       │                          │                              │
       │                          │                              │  4. View Schedule
       │                          │                              │     GET /project-payments
       │                          │                              │     (sees dates only)
       │                          │                              │
       │                          │                              │  5. Complete SOW Scope
       │                          │                              │     status → "implemented"
       │                          │                              │
       │                          │                              │  6. Linked Payment Due
       │                          │                              │     (auto-triggered)
       │                          │                              │
       │                          │                              │  7. Record Payment
       │                          │                              │     POST /record-payment
       │                          │                              │
       │                          │  8. All Payments?            │
       │                          │◄────────────────────────────┤
       │                          │                              │
       │                          │  9. All SOW Implemented?     │
       │                          │     ✓ Yes → Can Complete     │
       │                          │     ✗ No → Block             │
       │                          │                              │
       │                          │  10. Complete Project        │
       │                          │      POST /projects/complete │
       │                          │                              │
```

---

## ✅ SUMMARY: What Exists vs What's Needed

| Component | Exists | Gap | Priority |
|-----------|--------|-----|----------|
| Pricing Plan with schedule_breakdown | ✅ | No validation if empty | P1 |
| Schedule flows to project | ✅ | Due dates not recalculated | P2 |
| Consultant sees schedule | ✅ (dates only) | No SOW linkage shown | P2 |
| Consultant records payment | ✅ | No completion trigger | P0 |
| All-payments-complete check | ❌ | **MISSING** | P0 |
| SOW-Payment linkage | ❌ | **MISSING** | P1 |
| Project completion validation | ❌ | **MISSING** | P0 |

---

*Analysis: Payment Schedule Data Flow*
*Generated: February 21, 2026*
