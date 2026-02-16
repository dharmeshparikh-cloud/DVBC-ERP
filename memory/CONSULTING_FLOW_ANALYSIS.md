# Consulting Flow Analysis

## Complete Flow Requirement (User-Defined)

```
Sales Closes Agreement → Kickoff Request → PM Approval → Consultant Assignment → 
SOW/Meetings/Team Deployment visible → Consultant works on SOW (with RM approval) → 
Roadmap created → Client approval → Monthly activity → PM scores → Payroll
```

---

## Current State Analysis

### ✅ IMPLEMENTED (Exists in Codebase)

| Stage | Component/Endpoint | Status | Notes |
|-------|-------------------|--------|-------|
| 1. Kickoff Request Creation | `KickoffRequests.js`, `POST /kickoff-requests` | ✅ Full | Sales can create, PM sees pending |
| 2. PM Review/Approval | `KickoffRequests.js`, `POST /kickoff-requests/{id}/accept` | ✅ Full | Accept/Reject/Return flows |
| 3. Project Creation on Accept | `server.py:accept_kickoff_request` | ✅ Partial | Creates project but doesn't assign consultants |
| 4. Consultant Assignment | `POST /projects/{id}/assign-consultant` | ✅ Backend | API exists, no dedicated UI |
| 5. My Projects (Consulting) | `ConsultingSOWList.js` | ✅ Basic | Shows handed-over SOWs |
| 6. Project Tasks | `ConsultingProjectTasks.js` | ✅ Full | Task management with approvals |
| 7. Roadmap Creation | `ProjectRoadmap.js`, `POST /roadmaps` | ✅ Partial | Basic roadmap with phases |
| 8. Gantt Chart | `GanttChart.js` | ✅ Basic | Task visualization |
| 9. Payroll | `Payroll.js` | ✅ Full | Salary slip generation |

### ❌ MISSING (Needs Implementation)

| Stage | Requirement | Priority | Effort |
|-------|-------------|----------|--------|
| A. Consultant Assignment UI | Dedicated page/dialog to assign consultants after kickoff approval | P0 | Medium |
| B. SOW Reflection Page | Admin/RM/Consultant views showing SOW, Meetings, Team, Payment frequency | P0 | High |
| C. SOW Change Workflow | Consultant edits → RM approval → (Optional Client approval) → Reflect in SOW | P1 | High |
| D. Payment Reminders Page | Upcoming installments linked to project timeline (no values shown) | P1 | Medium |
| E. Performance Scoring | PM scores monthly activity → Links to payroll | P1 | Medium |
| F. Stage Navigation | Each page shows current stage + "Go Back" to previous flow | P0 | Low |
| G. Master SOW Storage | New SOWs auto-stored in master data for sales reuse | P2 | Low |
| H. Enhanced Roadmap | Monthly client approval workflow | P1 | Medium |

---

## Proposed Consulting Flow Pages

### Page Structure with Stages

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: KICKOFF APPROVAL                                          │
│  Page: /kickoff-requests (PM view)                                  │
│  Actions: Review, Accept, Reject, Return                            │
│  Next: Consultant Assignment                                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: CONSULTANT ASSIGNMENT (NEW)                               │
│  Page: /consulting/assign-team/{projectId}                          │
│  Actions: Select consultants, Set roles, Confirm assignment         │
│  Shows: SOW, Meetings, Payment frequency from agreement             │
│  Next: My Projects                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: MY PROJECTS (REDESIGN)                                    │
│  Page: /consulting/my-projects                                      │
│  Role Views: Admin (all), RM (team's), Consultant (assigned)        │
│  Shows: SOW summary, Team, Meetings, Payment schedule, Progress     │
│  Actions: View SOW, Edit SOW (with approval), View Roadmap          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 4: SOW MANAGEMENT                                            │
│  Page: /consulting/sow/{projectId}                                  │
│  Consultant: Can edit (creates approval request)                    │
│  RM: Approves/rejects changes                                       │
│  Client: Optional approval step                                     │
│  Changes reflect after approval                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 5: ROADMAP & OPERATIONS                                      │
│  Page: /consulting/roadmap/{projectId}                              │
│  Actions: Create monthly roadmap, Submit for client approval        │
│  Gantt: Visual timeline of all tasks                                │
│  Integration: Tasks sync with Gantt chart                           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 6: PAYMENT REMINDERS (NEW)                                   │
│  Page: /consulting/payments                                         │
│  Shows: Upcoming installment dates per project                      │
│  No values displayed, just: "Installment Due: March 15, 2026"       │
│  Links: Back to project details                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 7: MONTHLY REVIEW & PERFORMANCE                              │
│  Page: /consulting/monthly-review/{projectId}                       │
│  PM Actions: Review activity, Score consultant performance          │
│  Integration: Scores feed into payroll calculations                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Navigation Component (Stage Indicator)

Each consulting page should have:

```jsx
<ConsultingStageNav 
  currentStage={3}
  projectId={projectId}
  stages={[
    { id: 1, name: 'Kickoff', path: '/kickoff-requests', completed: true },
    { id: 2, name: 'Team Assignment', path: `/consulting/assign-team/${projectId}`, completed: true },
    { id: 3, name: 'My Projects', path: '/consulting/my-projects', current: true },
    { id: 4, name: 'SOW Management', path: `/consulting/sow/${projectId}` },
    { id: 5, name: 'Roadmap', path: `/consulting/roadmap/${projectId}` },
    { id: 6, name: 'Payments', path: '/consulting/payments' },
    { id: 7, name: 'Performance', path: `/consulting/monthly-review/${projectId}` }
  ]}
/>
```

---

## Implementation Priority

### Phase 1 (Immediate - P0)
1. Create `MyProjects.js` with stage navigation
2. Add Consultant Assignment UI after kickoff acceptance
3. Implement "Go Back" navigation pattern

### Phase 2 (Next Sprint - P1)
4. SOW Change Workflow with RM approval
5. Payment Reminders page
6. Performance Scoring integration

### Phase 3 (Future - P2)
7. Enhanced Roadmap with client approval
8. Master SOW auto-storage
9. Advanced Gantt integration
