# CONSULTING FLOW SCENARIO ANALYSIS
## Paresh (Sales) → Raju (Senior Manager) → Project Completion

---

## 📋 SCENARIO SETUP
- **Sales Person:** Paresh (role: executive/sales_manager)
- **Senior Manager:** Raju (role: senior_consultant/principal_consultant)
- **Scenario:** Kickoff sent → Accepted → Project execution → All payments recorded

---

## STEP-BY-STEP FLOW ANALYSIS

### ═══════════════════════════════════════════════════════════════
### PHASE 1: PRE-KICKOFF (Before Paresh can send kickoff)
### ═══════════════════════════════════════════════════════════════

#### STEP 1: Lead Created & Qualified
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | Lead exists in `leads` collection |
| ✅ RECORDED | Lead ID, company, contact, status, assigned_to |
| ❌ MISSED | Nothing |
| 🚫 BLOCKED | Nothing |

#### STEP 2: Quotation/Pricing Plan Created
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | `pricing_plans` collection |
| ✅ RECORDED | Services, pricing, payment schedule breakdown |
| ❌ MISSED | Nothing |
| 🚫 BLOCKED | Nothing |

#### STEP 3: Agreement Sent & Approved
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | `agreements` collection with status="approved" |
| ✅ RECORDED | Agreement number, approved_at, pricing_plan_id |
| ❌ MISSED | Nothing |
| 🚫 BLOCKED | Nothing |

#### STEP 4: First Installment Payment Received
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | `payment_verifications` with installment_number=1, status="verified" |
| ✅ RECORDED | Amount, transaction ID, verification date |
| ❌ MISSED | Nothing |
| 🚫 BLOCKED | **CRITICAL** - Kickoff request BLOCKED without this! |

**Code Reference:** `routers/kickoff.py` lines 41-51
```python
first_payment = await db.payment_verifications.find_one({
    "agreement_id": kickoff_create.agreement_id,
    "installment_number": 1,
    "status": "verified"
})
if not first_payment:
    raise HTTPException(status_code=400, 
        detail="First installment payment must be verified before creating kickoff request")
```

---

### ═══════════════════════════════════════════════════════════════
### PHASE 2: PARESH SENDS KICKOFF REQUEST
### ═══════════════════════════════════════════════════════════════

#### STEP 5: Paresh Creates Kickoff Request
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | POST `/api/kickoff-requests` |
| ✅ RECORDED | project_name, client_name, agreement_id, lead_id, assigned_pm_id (Raju), project_value, total_meetings, expected_start_date |
| ❌ MISSED | **No SOW scopes attached to kickoff** |
| ❌ MISSED | **No formal scope confirmation from client** |
| 🚫 BLOCKED | If first payment not verified |

**What Paresh fills:**
```json
{
  "agreement_id": "agr-xxx",
  "lead_id": "lead-xxx",
  "project_name": "Business Consulting - ABC Corp",
  "client_name": "ABC Corp",
  "assigned_pm_id": "raju-user-id",
  "project_type": "lean",
  "project_value": 500000,
  "total_meetings": 36,
  "expected_start_date": "2026-03-01"
}
```

**System Auto-Records:**
- `requested_by`: Paresh's user ID
- `requested_by_name`: "Paresh"
- `status`: "pending"
- `created_at`: timestamp

**Notification Sent:**
- ✅ Email to Raju (if configured)
- ✅ WebSocket notification to Raju
- ✅ In-app notification created

---

### ═══════════════════════════════════════════════════════════════
### PHASE 3: RAJU ACCEPTS KICKOFF
### ═══════════════════════════════════════════════════════════════

#### STEP 6: Raju Reviews Kickoff Request
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | GET `/api/kickoff-requests/{id}/details` |
| ✅ RECORDED | View logged (if audit enabled) |
| ❌ MISSED | **No checklist for Raju to verify before accepting** |
| ❌ MISSED | **No client confirmation attached** |
| 🚫 BLOCKED | Nothing |

**What Raju Sees:**
- Kickoff request details
- Agreement details
- Lead details
- Meeting history with lead
- Payment status (first payment verified)

**What Raju CANNOT See (GAPS):**
- ❌ SOW scopes that will be delivered
- ❌ Client's signed scope confirmation
- ❌ Resource availability check
- ❌ Consultant workload status

#### STEP 7: Raju Accepts Kickoff → PROJECT AUTO-CREATED
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | POST `/api/kickoff-requests/{id}/accept` |
| ✅ RECORDED | Project created with status="active" |
| ❌ MISSED | **No kickoff meeting scheduled automatically** |
| ❌ MISSED | **No milestone definition** |
| ❌ MISSED | **No consultant assignment prompt** |
| 🚫 BLOCKED | If kickoff status != "pending" |

**What Gets Auto-Created (Project):**
```json
{
  "id": "proj-xxx",
  "name": "Business Consulting - ABC Corp",
  "client_name": "ABC Corp",
  "lead_id": "lead-xxx",
  "agreement_id": "agr-xxx",
  "pricing_plan_id": "plan-xxx",
  "project_type": "lean",
  "start_date": "2026-02-21",
  "total_meetings_committed": 36,
  "project_value": 500000,
  "status": "active",
  "created_by": "raju-user-id"
}
```

**What Gets Updated:**
- Kickoff request: `status` → "converted", `project_id` → new project ID
- Enhanced SOW: `project_id` linked, `consulting_kickoff_complete` = true

**Notifications Sent:**
- ✅ To Paresh: "Kickoff Accepted - Project Created"
- ✅ To HR Manager: "New Project Created - Needs Staffing"

---

### ═══════════════════════════════════════════════════════════════
### PHASE 4: PROJECT EXECUTION (MAJOR GAPS HERE!)
### ═══════════════════════════════════════════════════════════════

#### STEP 8: Kickoff Meeting with Client
| Aspect | Status | Details |
|--------|--------|---------|
| ❌ COVERED | **NO** | No kickoff meeting workflow exists! |
| ❌ RECORDED | Nothing - completely missing |
| ❌ MISSED | Meeting scheduling, attendees, agenda, MOM |
| 🚫 BLOCKED | **NOTHING BLOCKS THIS** - Project starts without client kickoff! |

**CRITICAL GAP:** Project is "active" but no formal kickoff meeting with client is mandated or tracked.

#### STEP 9: Consultant Assignment
| Aspect | Status | Details |
|--------|--------|---------|
| ⚠️ COVERED | PARTIAL | `consultant_assignments` collection exists |
| ✅ RECORDED | consultant_id, project_id, role, start_date |
| ❌ MISSED | **No HR approval workflow** |
| ❌ MISSED | **No workload check before assignment** |
| ❌ MISSED | **No client notification of team** |
| 🚫 BLOCKED | Nothing - anyone can assign |

**Current Assignment Flow (Weak):**
1. PM directly assigns consultant
2. No approval needed
3. No notification to consultant's manager
4. No workload validation

#### STEP 10: Conduct Consulting Meetings
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | `meetings` collection with type="consulting" |
| ✅ RECORDED | title, date, time, attendees, project_id, status |
| ✅ RECORDED | MOM (summary, discussion_points, action_items) |
| ❌ MISSED | **No automatic tracking of committed vs delivered** |
| ❌ MISSED | **No client attendance confirmation** |
| 🚫 BLOCKED | Nothing |

**Tracking Available:**
- GET `/api/consulting-meetings/tracking` - Shows committed vs actual per project

#### STEP 11: SOW Progress Tracking
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | `enhanced_sow` with scope progress |
| ✅ RECORDED | Scope status, progress %, consultant notes |
| ❌ MISSED | **No milestone linkage** |
| ❌ MISSED | **No client sign-off per scope** |
| ❌ MISSED | **No progress reports auto-generated** |
| 🚫 BLOCKED | Nothing |

#### STEP 12: Milestone Completion & Payment Trigger
| Aspect | Status | Details |
|--------|--------|---------|
| ❌ COVERED | **NO** | No milestone entity exists! |
| ❌ RECORDED | Nothing |
| ❌ MISSED | Milestone definition, completion tracking, payment linkage |
| 🚫 BLOCKED | **Payments are TIME-BASED not MILESTONE-BASED** |

**CRITICAL GAP:** Payments are due by "Month 1", "Month 2" etc. NOT by "Milestone 1 Complete", "Milestone 2 Complete".

---

### ═══════════════════════════════════════════════════════════════
### PHASE 5: PAYMENT COLLECTION (BY CONSULTANT)
### ═══════════════════════════════════════════════════════════════

#### STEP 13: View Payment Schedule
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | GET `/api/project-payments/project/{id}` |
| ✅ RECORDED | Installments with amounts, due dates, status |
| ⚠️ VISIBILITY | Consultant sees DATES only, not amounts |
| ❌ MISSED | **No milestone linkage** |
| 🚫 BLOCKED | Nothing |

**What Consultant Sees:**
```json
{
  "payments": [
    {"frequency": "Month 1", "due_date": "2026-03-01", "status": "received"},
    {"frequency": "Month 2", "due_date": "2026-04-01", "status": "pending"},
    {"frequency": "Month 3", "due_date": "2026-05-01", "status": "pending"}
  ]
}
```
**Note:** Consultant CANNOT see amounts (hidden by design)

#### STEP 14: Send Payment Reminder
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | POST `/api/project-payments/send-reminder` |
| ✅ RECORDED | Reminder sent timestamp, installment number |
| ❌ MISSED | **No escalation if payment overdue** |
| ❌ MISSED | **No auto-reminder scheduling** |
| 🚫 BLOCKED | Must have valid project_id and installment_number |

#### STEP 15: Record Payment (Consultant Action)
| Aspect | Status | Details |
|--------|--------|---------|
| ✅ COVERED | YES | POST `/api/project-payments/record-payment` |
| ✅ RECORDED | transaction_id, amount_received, payment_date, recorded_by |
| ❌ MISSED | **No verification workflow (just direct recording)** |
| ❌ MISSED | **No finance team approval** |
| 🚫 BLOCKED | Must be assigned to project or have admin role |

**Consultant Records:**
```json
{
  "project_id": "proj-xxx",
  "installment_number": 2,
  "transaction_id": "TXN123456",
  "amount_received": 150000,
  "payment_date": "2026-04-05"
}
```

#### STEP 16-18: Repeat for Each Installment
Same flow for Month 2, Month 3, etc.

---

### ═══════════════════════════════════════════════════════════════
### PHASE 6: PROJECT COMPLETION (MAJOR GAPS!)
### ═══════════════════════════════════════════════════════════════

#### STEP 19: All Payments Recorded
| Aspect | Status | Details |
|--------|--------|---------|
| ⚠️ COVERED | PARTIAL | Payments are recorded but... |
| ✅ RECORDED | All installment payments with status="received" |
| ❌ MISSED | **No "all payments complete" flag** |
| ❌ MISSED | **No automatic notification to PM** |
| ❌ MISSED | **No trigger for project completion check** |
| 🚫 BLOCKED | Nothing |

#### STEP 20: Project Completion
| Aspect | Status | Details |
|--------|--------|---------|
| ❌ COVERED | **NO** | No completion workflow exists! |
| ❌ RECORDED | Nothing |
| ❌ MISSED | Completion validation, sign-off, archive |
| 🚫 BLOCKED | **NOTHING** - Project stays "active" forever! |

**CRITICAL GAP:** There is NO endpoint to:
1. Validate all meetings delivered
2. Validate all SOW scopes completed
3. Validate all payments received
4. Validate client sign-off
5. Change project status to "completed"

---

## 📊 SUMMARY SCORECARD

### What's COVERED ✅
| # | Feature | Working |
|---|---------|---------|
| 1 | First payment verification before kickoff | ✅ |
| 2 | Kickoff request workflow | ✅ |
| 3 | PM notification on kickoff | ✅ |
| 4 | Project auto-creation on accept | ✅ |
| 5 | SOW linkage to project | ✅ |
| 6 | HR notification for staffing | ✅ |
| 7 | Consulting meeting creation | ✅ |
| 8 | Meeting MOM recording | ✅ |
| 9 | SOW progress tracking | ✅ |
| 10 | Payment schedule display | ✅ |
| 11 | Payment reminder sending | ✅ |
| 12 | Payment recording | ✅ |

### What's RECORDED 📝
| # | Data Point | Collection |
|---|------------|------------|
| 1 | Kickoff request details | kickoff_requests |
| 2 | Project details | projects |
| 3 | Meeting details + MOM | meetings |
| 4 | SOW progress | enhanced_sow |
| 5 | Payment schedule | Via pricing_plans |
| 6 | Payment transactions | payment_verifications |
| 7 | Consultant assignments | consultant_assignments |
| 8 | Notifications | notifications |

### What's MISSED ❌
| # | Missing Feature | Impact |
|---|----------------|--------|
| 1 | Kickoff meeting with client | Project starts without client alignment |
| 2 | Milestone definition | No deliverable-based tracking |
| 3 | Milestone-payment linkage | Payments are time-based, not output-based |
| 4 | Client sign-off per milestone | No proof of acceptance |
| 5 | Progress reports | No automated reporting |
| 6 | Final deliverable submission | No formal output tracking |
| 7 | Project completion workflow | Projects stay "active" forever |
| 8 | All-payments-received check | No trigger for completion |
| 9 | Client feedback collection | No NPS/testimonials |
| 10 | Project archive | No archival process |
| 11 | Consultant assignment approval | No HR validation |

### What BLOCKS Progress 🚫
| # | Blocker | When |
|---|---------|------|
| 1 | First payment not verified | Cannot create kickoff request |
| 2 | Kickoff status != pending | Cannot accept kickoff |
| 3 | **NOTHING ELSE** | Everything else proceeds without validation |

---

## 🔴 CRITICAL ISSUES TO FIX

### Issue 1: No Project Completion Gate
**Current:** Project can stay "active" forever with no validation
**Impact:** No way to formally close a project
**Fix:** Add completion endpoint with validation

### Issue 2: No Milestone System
**Current:** Payments are by "Month 1, 2, 3" not by deliverables
**Impact:** Payment not linked to actual work done
**Fix:** Create milestone entity linking SOW scopes → Payments

### Issue 3: No Client Sign-off
**Current:** No tracking of client acceptance
**Impact:** Disputes possible, no audit trail
**Fix:** Add sign-off workflow at milestone + project level

### Issue 4: No Kickoff Meeting Mandate
**Current:** Project "active" immediately on PM accept
**Impact:** Work may start without client alignment
**Fix:** Require kickoff meeting completion before execution

---

*Scenario Analysis for: Paresh → Raju → Consultant Flow*
*Generated: February 21, 2026*
