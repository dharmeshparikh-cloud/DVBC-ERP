# ONBOARDING FLOW MIGRATION PLAN
## Upgrade: Legacy Manual Onboarding → Self-Service Onboarding

**Version:** 1.0
**Date:** February 24, 2026
**Status:** PENDING APPROVAL

---

## 1. EXECUTIVE SUMMARY

This document outlines the migration strategy for upgrading NETRA's employee onboarding system from the current HR-manual process to a new candidate self-service model. The migration ensures:

- Zero data loss
- No duplicate employee records
- Seamless transition for HR users
- Backward compatibility for in-progress onboarding
- Single source of truth for employee data

---

## 2. CURRENT VS. NEW FLOW COMPARISON

### 2.1 Step-by-Step Mapping

| # | OLD FLOW (Manual) | NEW FLOW (Self-Service) | Actor |
|---|-------------------|-------------------------|-------|
| 1 | HR enters candidate name, email | HR sends invite with name, email, position | HR |
| 2 | HR enters personal details manually | Candidate fills personal details | Candidate |
| 3 | HR enters DOB, address, phone | Candidate fills DOB, address, phone | Candidate |
| 4 | HR enters identity docs (PAN, Aadhaar) | Candidate uploads identity docs | Candidate |
| 5 | HR enters education details | Candidate enters education + uploads certificates | Candidate |
| 6 | HR enters employment history | Candidate enters history + uploads letters | Candidate |
| 7 | HR enters bank details | Candidate enters bank details + uploads proof | Candidate |
| 8 | HR selects department | HR assigns department (after review) | HR |
| 9 | HR selects reporting manager | HR assigns reporting manager (after review) | HR |
| 10 | HR enters joining date | HR assigns joining date (after review) | HR |
| 11 | HR uploads documents (optional) | Candidate uploads all required documents | Candidate |
| 12 | **Employee ID generated immediately** | **Employee ID generated ONLY on completion** | System |
| 13 | **Employee record created immediately** | **Employee record created ONLY on completion** | System |
| 14 | HR completes missing items in Go-Live | Go-Live mostly pre-filled from onboarding | HR |
| 15 | Admin approves Go-Live | Admin approves Go-Live (unchanged) | Admin |

### 2.2 Key Differences

| Aspect | OLD Flow | NEW Flow |
|--------|----------|----------|
| Data Entry | 100% by HR | ~70% by Candidate, 30% by HR |
| Employee ID | Generated on form start | Generated on completion |
| Employee Record | Created with incomplete data | Created only when 100% complete |
| Documents | Optional, uploaded by HR | Mandatory, uploaded by Candidate |
| Verification | Post-hoc in Go-Live | Built into onboarding checklist |
| Status Tracking | Employee status field | Separate onboarding_submissions collection |

---

## 3. DATABASE SCHEMA CHANGES

### 3.1 NEW Collection: `onboarding_submissions`

```javascript
{
  "id": "uuid",                          // Submission ID (NOT employee ID)
  "token": "secure-uuid",                // For public link access
  "status": "draft|submitted|revision_requested|approved|rejected",
  
  // From HR invite
  "invited_by": "hr-user-id",
  "invited_by_name": "Meera Iyer",
  "invited_at": "2026-02-24T10:00:00Z",
  "candidate_email": "candidate@gmail.com",
  "candidate_name": "Pallavi Rao",
  "offered_position": "Consultant",
  
  // From Candidate (self-service)
  "candidate_details": {
    "first_name": "Pallavi",
    "last_name": "Rao",
    "date_of_birth": "1995-05-15",
    "gender": "female",
    "blood_group": "B+",
    "marital_status": "single",
    "nationality": "Indian",
    "personal_email": "pallavi@gmail.com",
    "phone": "9876543210",
    "alternate_phone": "9876543211",
    "current_address": {...},
    "permanent_address": {...},
    "pan_number": "ABCDE1234F",
    "aadhaar_number": "1234-5678-9012",
    "passport_number": null,
    "driving_license": null
  },
  "education": [...],
  "employment_history": [...],
  "bank_details": {...},
  "emergency_contact": {...},
  "documents": [
    {"type": "pan_card", "file_id": "...", "uploaded_at": "..."},
    {"type": "aadhaar", "file_id": "...", "uploaded_at": "..."},
    ...
  ],
  "declaration_signed": true,
  "submitted_at": "2026-02-24T14:00:00Z",
  
  // From HR (review phase)
  "hr_assigned": {
    "department": "Consulting",
    "reporting_manager_id": "manager-uuid",
    "reporting_manager_name": "Komal Menon",
    "joining_date": "2026-03-01",
    "official_email": "pallavi.rao@dvconsulting.co.in",
    "employment_type": "full_time",
    "designation": "Consultant"
  },
  "hr_verification": {
    "documents_verified": true,
    "documents_verified_by": "hr-uuid",
    "documents_verified_at": "2026-02-24T16:00:00Z",
    "bank_verified": true,
    "bank_verified_by": "hr-uuid",
    "bank_verified_at": "2026-02-24T16:00:00Z"
  },
  
  // Completion
  "completed_at": "2026-02-24T17:00:00Z",
  "completed_by": "hr-uuid",
  "employee_id_generated": "DVC042",  // Only set on completion
  "employee_record_id": "emp-uuid",   // Link to employees collection
  
  // Tracking
  "link_expires_at": "2026-03-03T10:00:00Z",  // 7 days from invite
  "revision_history": [...],
  "audit_log": [...]
}
```

### 3.2 EXISTING Collection: `employees` (UNCHANGED SCHEMA)

The final employee record schema remains **identical** to current:

```javascript
{
  "id": "uuid",
  "employee_id": "DVC042",           // Human-readable ID
  "first_name": "Pallavi",
  "last_name": "Rao",
  "email": "pallavi.rao@dvconsulting.co.in",  // Official email
  "personal_email": "pallavi@gmail.com",
  "phone": "9876543210",
  "department": "Consulting",
  "designation": "Consultant",
  "reporting_manager": "manager-uuid",
  "joining_date": "2026-03-01",
  "employment_type": "full_time",
  "bank_details": {...},
  "documents": [...],
  "status": "onboarded",             // Not active until Go-Live
  "go_live_status": "not_submitted",
  "onboarding_source": "self_service",  // NEW: Track source
  "onboarding_submission_id": "submission-uuid",  // NEW: Link back
  "created_at": "2026-02-24T17:00:00Z",
  "created_by": "hr-uuid"
}
```

### 3.3 Migration Index for Legacy Records

```javascript
// Add to existing employees
{
  "onboarding_source": "legacy",     // For employees onboarded via old flow
  "onboarding_submission_id": null   // No submission record
}
```

---

## 4. UI/UX CHANGES

### 4.1 HR Sidebar Navigation (SINGLE ENTRY POINT)

```
BEFORE:
├── Onboarding          → Opens HROnboarding.js (manual form)

AFTER:
├── Onboarding          → Opens OnboardingHub.js (NEW unified page)
    ├── Tab: "Send Invite"     → New candidate invite form
    ├── Tab: "Pending Review"  → Candidate submissions to review
    ├── Tab: "In Progress"     → Legacy onboarding (if any exist)
    ├── Tab: "Completed"       → History of completed onboarding
```

### 4.2 New Components Required

| Component | Purpose | Access |
|-----------|---------|--------|
| `OnboardingHub.js` | Unified HR dashboard for all onboarding | HR Only |
| `SendInviteForm.js` | HR sends invite to candidate | HR Only |
| `PendingSubmissions.js` | HR reviews candidate submissions | HR Only |
| `SubmissionReview.js` | Detailed review + HR assignment | HR Only |
| `LegacyOnboarding.js` | Continue old flow for in-progress | HR Only |
| `CandidateOnboarding.js` | Public self-service form | Public (token) |
| `OnboardingSuccess.js` | Candidate confirmation page | Public |

### 4.3 UI Flow Diagrams

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ONBOARDING HUB (HR View)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Send Invite]    [Pending Review (3)]    [In Progress (1)]    [Completed]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PENDING REVIEW TAB:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Name          │ Position    │ Submitted   │ Progress  │ Actions        ││
│  ├───────────────┼─────────────┼─────────────┼───────────┼────────────────┤│
│  │ Pallavi Rao   │ Consultant  │ 2 hours ago │ 100%      │ [Review]       ││
│  │ Arun Kumar    │ Sr. Consult │ 1 day ago   │ 85%       │ [View]         ││
│  │ Neha Singh    │ Executive   │ 3 days ago  │ 100%      │ [Review]       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  IN PROGRESS TAB (Legacy):                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ⚠️ These are legacy onboarding records. Complete using old flow.        ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │ EMP041 - Rahul Verma │ Started 5 days ago │ 60% │ [Continue]            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUBMISSION REVIEW (HR Reviews Candidate)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Candidate: Pallavi Rao                                                     │
│  Position: Consultant                                                       │
│  Submitted: Feb 24, 2026 at 2:00 PM                                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ CANDIDATE PROVIDED:                           Status                    ││
│  │ ✅ Personal Details                           Complete                  ││
│  │ ✅ Identity Documents (PAN, Aadhaar)          View Documents            ││
│  │ ✅ Education Details                          View Details              ││
│  │ ✅ Employment History                         View Details              ││
│  │ ✅ Bank Details                               View & Validate           ││
│  │ ✅ Emergency Contact                          Complete                  ││
│  │ ✅ Declaration Signed                         Signed                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ HR TO ASSIGN:                                                           ││
│  │ Department:        [Consulting         ▼]                               ││
│  │ Reporting Manager: [Komal Menon        ▼]                               ││
│  │ Joining Date:      [📅 March 1, 2026    ]                               ││
│  │ Official Email:    [pallavi.rao@dvconsulting.co.in]                     ││
│  │ Employment Type:   [Full Time          ▼]                               ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ HR VERIFICATION:                                                        ││
│  │ ☐ I have verified all uploaded documents                                ││
│  │ ☐ I have validated bank details (IFSC: Valid ✓)                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Request Revision]  [Reject with Reason]  [✓ Complete Onboarding]         │
│                                                                             │
│  ⚠️ Completing onboarding will generate Employee ID and create record      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. BACKEND API CHANGES

### 5.1 NEW Endpoints

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/api/onboarding/invite` | HR sends invite | HR Only |
| GET | `/api/onboarding/submissions` | List all submissions | HR Only |
| GET | `/api/onboarding/submissions/{id}` | Get submission details | HR Only |
| PATCH | `/api/onboarding/submissions/{id}/hr-assign` | HR assigns dept/manager | HR Only |
| POST | `/api/onboarding/submissions/{id}/request-revision` | Ask candidate to fix | HR Only |
| POST | `/api/onboarding/submissions/{id}/reject` | Reject candidate | HR Only |
| POST | `/api/onboarding/submissions/{id}/complete` | Complete & create employee | HR Only |
| GET | `/api/onboarding/public/{token}` | Get form (public) | Public |
| POST | `/api/onboarding/public/{token}/save` | Save progress (public) | Public |
| POST | `/api/onboarding/public/{token}/submit` | Submit form (public) | Public |
| POST | `/api/onboarding/public/{token}/upload` | Upload document (public) | Public |
| GET | `/api/onboarding/legacy` | List legacy in-progress | HR Only |

### 5.2 Employee ID Generation (UNCHANGED MECHANISM)

```python
# SAME LOGIC - but called at DIFFERENT time

# OLD: Called when HR starts onboarding
# NEW: Called when HR clicks "Complete Onboarding"

async def generate_employee_id():
    """Generate next sequential Employee ID (DVC format)"""
    employees = await db.employees.find(
        {"employee_id": {"$regex": "^DVC\\d+$"}},
        {"employee_id": 1}
    ).to_list(None)
    
    max_num = 0
    for emp in employees:
        match = re.match(r"DVC(\d+)", emp.get("employee_id", ""))
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    return f"DVC{max_num + 1:03d}"
```

### 5.3 Duplicate Prevention

```python
async def check_duplicate_candidate(email: str, pan: str = None, aadhaar: str = None):
    """Prevent duplicate records for same candidate"""
    
    # Check in employees collection
    existing_employee = await db.employees.find_one({
        "$or": [
            {"email": email},
            {"personal_email": email},
            {"pan_number": pan} if pan else {"_id": None},
            {"aadhaar_number": aadhaar} if aadhaar else {"_id": None}
        ]
    })
    
    if existing_employee:
        raise HTTPException(
            status_code=409,
            detail=f"Employee already exists with ID: {existing_employee['employee_id']}"
        )
    
    # Check in pending submissions
    pending_submission = await db.onboarding_submissions.find_one({
        "status": {"$in": ["draft", "submitted", "revision_requested"]},
        "$or": [
            {"candidate_email": email},
            {"candidate_details.pan_number": pan} if pan else {"_id": None}
        ]
    })
    
    if pending_submission:
        raise HTTPException(
            status_code=409,
            detail="Onboarding already in progress for this candidate"
        )
```

---

## 6. DATA CONSISTENCY SAFEGUARDS

### 6.1 Transaction for Employee Creation

```python
async def complete_onboarding(submission_id: str, hr_user: User):
    """Atomic operation: Generate ID + Create Employee + Archive Submission"""
    
    async with await db.client.start_session() as session:
        async with session.start_transaction():
            # 1. Lock submission
            submission = await db.onboarding_submissions.find_one_and_update(
                {"id": submission_id, "status": "submitted"},
                {"$set": {"status": "processing"}},
                session=session
            )
            
            if not submission:
                raise HTTPException(400, "Submission not found or already processed")
            
            # 2. Generate Employee ID (atomic increment)
            employee_id = await generate_employee_id_atomic(session)
            
            # 3. Create Employee Record
            employee_record = build_employee_from_submission(submission, employee_id)
            await db.employees.insert_one(employee_record, session=session)
            
            # 4. Update Submission
            await db.onboarding_submissions.update_one(
                {"id": submission_id},
                {"$set": {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "completed_by": hr_user.id,
                    "employee_id_generated": employee_id,
                    "employee_record_id": employee_record["id"]
                }},
                session=session
            )
            
            # 5. Move documents to employee folder
            await move_documents_to_employee(submission, employee_record["id"], session)
            
            return employee_record
```

### 6.2 Validation Rules

| Rule | Check Point | Action |
|------|-------------|--------|
| Email unique | On invite + On submit | Reject duplicate |
| PAN unique | On submit | Reject duplicate |
| Aadhaar unique | On submit | Reject duplicate |
| All fields complete | Before complete | Block completion |
| HR assignments filled | Before complete | Block completion |
| Documents verified | Before complete | Block completion |

---

## 7. RBAC & PERMISSIONS

### 7.1 Permission Matrix (UNCHANGED)

| Action | HR Executive | HR Manager | Admin |
|--------|--------------|------------|-------|
| Send Invite | ✅ | ✅ | ✅ |
| View Submissions | ✅ | ✅ | ✅ |
| Assign Department | ✅ | ✅ | ✅ |
| Verify Documents | ❌ | ✅ | ✅ |
| Verify Bank | ❌ | ✅ | ✅ |
| Complete Onboarding | ❌ | ✅ | ✅ |
| Reject Candidate | ❌ | ✅ | ✅ |

### 7.2 Audit Trail

```javascript
// Every action logged
{
  "submission_id": "...",
  "action": "invite_sent|submitted|revision_requested|approved|rejected|completed",
  "actor_id": "user-id",
  "actor_name": "Meera Iyer",
  "actor_role": "hr_manager",
  "timestamp": "2026-02-24T10:00:00Z",
  "details": {
    "changes": {...},
    "reason": "..." // For rejections/revisions
  }
}
```

---

## 8. MIGRATION STRATEGY

### 8.1 Phase 1: Deploy New Components (Day 1)

1. Deploy `onboarding_submissions` collection
2. Deploy new API endpoints
3. Deploy new frontend components
4. Keep old HROnboarding.js functional
5. NO DISRUPTION to existing users

### 8.2 Phase 2: Enable New Flow (Day 2)

1. Update sidebar navigation to OnboardingHub
2. New candidates → Self-service flow
3. Existing in-progress → Legacy tab
4. Monitor for issues

### 8.3 Phase 3: Complete Legacy (Day 3-14)

1. HR completes all legacy onboarding
2. Monitor legacy count → 0
3. Hide legacy tab when empty

### 8.4 Phase 4: Deprecate Old Flow (Day 15+)

1. Remove legacy tab
2. Archive old HROnboarding.js
3. Full transition complete

### 8.5 Rollback Strategy

```
IF issues detected:
1. Re-enable old HROnboarding.js link in sidebar
2. Pause new invite sending
3. Fix issues
4. Resume migration

Data is NEVER lost because:
- onboarding_submissions preserved
- employees collection unchanged
- Both flows write to same final schema
```

---

## 9. USER EXPERIENCE GUIDELINES

### 9.1 For HR Users

| Scenario | Action |
|----------|--------|
| New candidate to onboard | "Send Invite" tab → Enter email, name, position → Send |
| Candidate submitted form | "Pending Review" tab → Review → Assign dept/manager → Complete |
| Candidate needs to fix data | "Request Revision" → Enter reason → Candidate gets email |
| Legacy onboarding exists | "In Progress" tab → Continue with old form |
| Check completed onboarding | "Completed" tab → View history |

### 9.2 For Candidates

| Scenario | Action |
|----------|--------|
| Receive invite email | Click link → Fill form step-by-step → Submit |
| Can't complete in one session | Progress auto-saved → Resume later with same link |
| Need to correct data | Receive revision email → Edit and resubmit |
| Submission approved | Receive "Welcome" email with Employee ID |

### 9.3 Notification Templates

| Event | Recipient | Subject |
|-------|-----------|---------|
| Invite sent | Candidate | "Welcome! Complete your onboarding for DVBC" |
| Reminder (3 days) | Candidate | "Reminder: Complete your onboarding" |
| Revision requested | Candidate | "Action needed: Update your onboarding details" |
| Rejected | Candidate | "Update on your application to DVBC" |
| Completed | Candidate | "Welcome to DVBC! Your Employee ID: DVC042" |
| New submission | HR | "New onboarding submission: Pallavi Rao" |

---

## 10. SUCCESS METRICS

| Metric | Target | Measurement |
|--------|--------|-------------|
| HR time per onboarding | -50% | Time from invite to completion |
| Data accuracy | +30% | Fewer corrections needed post-onboarding |
| Candidate satisfaction | 90%+ | Post-onboarding survey |
| Legacy migration | 100% | All legacy records completed |
| Zero duplicates | 0 | Duplicate detection hits |

---

## 11. APPROVAL CHECKLIST

Before implementation, confirm:

- [ ] Database schema approved
- [ ] UI/UX flow approved
- [ ] RBAC permissions approved
- [ ] Notification templates approved
- [ ] Migration timeline approved
- [ ] Rollback plan understood

---

**Document prepared by:** AI Assistant
**Requires approval from:** User
**Implementation start:** Upon approval
