# React Query Migration Map

## Component 1: ApprovalsCenter.js (3576 lines)

### GET Requests (Queries)
| API Endpoint | Line | Component Section | React Query Key |
|--------------|------|-------------------|-----------------|
| `/approvals/pending` | 181 | fetchData | `['approvals', 'pending']` |
| `/approvals/my-requests` | 182 | fetchData | `['approvals', 'my-requests']` |
| `/ctc/pending-approvals` | 186 | fetchData (Admin) | `['ctc', 'pending-approvals']` |
| `/go-live/pending` | 187 | fetchData (Admin) | `['go-live', 'pending']` |
| `/permission-change-requests` | 188 | fetchData (Admin) | `['permissions', 'pending-requests']` |
| `/employees/modification-requests/pending` | 189 | fetchData (Admin) | `['employees', 'modification-requests']` |
| `/hr/bank-change-requests` | 193 | fetchData (HR) | `['hr', 'bank-change-requests']` |
| `/hr/employee-change-requests` | 194 | fetchData (HR) | `['hr', 'employee-change-requests']` |
| `/agreements/pending-approval` | 199 | fetchData (Manager) | `['agreements', 'pending-approval']` |
| `/sales-funnel/pending-kickoff-approvals` | 208 | fetchData (PC/SC) | `['kickoff', 'pending-approvals']` |
| `/expenses/pending-approvals` | 213 | fetchData (Manager/HR) | `['expenses', 'pending-approvals']` |
| `/approvals/all` | 278 | fetchData (Manager) | `['approvals', 'all']` |
| `/go-live/checklist/{id}` | 676 | viewGoLiveDetails | `['go-live', 'checklist', id]` |
| `/expenses/{id}/receipts` | 462 | loadReceipts | `['expenses', id, 'receipts']` |

### POST/PATCH/DELETE Requests (Mutations)
| API Endpoint | Line | Action | Invalidates |
|--------------|------|--------|-------------|
| `/approvals/{id}/action` | 301 | handleAction | `['approvals']` |
| `/agreements/{id}/approve` | 361 | approveAgreement | `['agreements']` |
| `/agreements/{id}/reject` | 365 | rejectAgreement | `['agreements']` |
| `/sales-funnel/approve-kickoff/{id}` | 384 | approveKickoff | `['kickoff']` |
| `/sales-funnel/reject-kickoff/{id}` | 388 | rejectKickoff | `['kickoff']` |
| `/expenses/{id}/approve` | 407 | approveExpense | `['expenses']` |
| `/expenses/{id}/reject` | 415 | rejectExpense | `['expenses']` |
| `/expenses/{id}/upload-receipt` | 441 | uploadReceipt | `['expenses', id, 'receipts']` |
| `/expenses/{id}/receipts/{rid}` (DELETE) | 505 | deleteReceipt | `['expenses', id, 'receipts']` |
| `/expenses/{id}/send-back` | 522 | sendBackExpense | `['expenses']` |
| `/expenses/{id}/approve-with-modification` | 561 | partialApprove | `['expenses']` |
| `/permission-change-requests/{id}/approve` | 593 | approvePermission | `['permissions']` |
| `/permission-change-requests/{id}/reject` | 596 | rejectPermission | `['permissions']` |
| `/ctc/{id}/approve` | 615 | approveCTC | `['ctc']` |
| `/ctc/{id}/reject` | 618 | rejectCTC | `['ctc']` |
| `/hr/bank-change-request/{id}/approve\|reject` | 640 | handleBankAction | `['hr', 'bank-change-requests']` |
| `/hr/employee-change-request/{id}/approve` | 658 | approveProfileChange | `['hr', 'employee-change-requests']` |
| `/hr/employee-change-request/{id}/reject` | 661 | rejectProfileChange | `['hr', 'employee-change-requests']` |
| `/go-live/{id}/approve` | 688 | approveGoLive | `['go-live']` |
| `/go-live/{id}/reject` | 691 | rejectGoLive | `['go-live']` |
| `/employees/modification-requests/{id}/approve` | 1309 | approveModification | `['employees', 'modification-requests']` |
| `/employees/modification-requests/{id}/reject` | 1328 | rejectModification | `['employees', 'modification-requests']` |

---

## Component 2: HROnboarding.js (2098 lines)

### GET Requests (Queries)
| API Endpoint | Line | Component Section | React Query Key |
|--------------|------|-------------------|-----------------|
| `/employees/all` | 212, 243, 538 | fetchManagers, loadExisting | `['employees', 'all']` |
| `/permission-config/suggest-department` | 275 | fetchSuggestedDepartment | `['permissions', 'suggest-dept', designation]` |

### POST/PATCH Requests (Mutations)
| API Endpoint | Line | Action | Invalidates |
|--------------|------|--------|-------------|
| `/employees` (POST) | 440, 808 | createEmployee | `['employees']` |
| `/employees/{id}/grant-access` | 471, 826 | grantAccess | `['employees', id]` |

---

## Component 3: EmployeeMobileApp.js (2313 lines)

### GET Requests (Queries)
| API Endpoint | Line | Component Section | React Query Key |
|--------------|------|-------------------|-----------------|
| `/my/attendance` | 115 | fetchData | `['my', 'attendance', month]` |
| `/my/leave-balance` | 116 | fetchData | `['my', 'leave-balance']` |
| `/my/expenses` | 117 | fetchData | `['my', 'expenses']` |
| `/clients` | 118 | fetchData | `['clients']` |
| `/projects` | 119 | fetchData | `['projects']` |
| `/my/assigned-clients` | 149 | fetchAssignedClients | `['my', 'assigned-clients']` |
| `/travel/location-search` | 553, 651 | searchLocation | `['travel', 'location-search', query]` |
| `/my/travel-reimbursements` | 633 | fetchTravelHistory | `['my', 'travel-reimbursements', month]` |

### POST Requests (Mutations)
| API Endpoint | Line | Action | Invalidates |
|--------------|------|--------|-------------|
| `/my/check-in` | 279 | handleCheckIn | `['my', 'attendance']` |
| `/my/check-out` | 341 | handleCheckOut | `['my', 'attendance']` |
| `/travel/reimbursement` | 374, 603 | submitTravelExpense | `['my', 'travel-reimbursements']` |
| `/expenses` (POST) | 419 | submitExpense | `['my', 'expenses']` |
| `/expenses/{id}/upload-receipt` | 441 | uploadReceipt | `['my', 'expenses']` |
| `/leave-requests` (POST) | 523 | submitLeave | `['my', 'leave-balance']` |

---

## Cache Strategy

| Data Type | staleTime | gcTime | Reason |
|-----------|-----------|--------|--------|
| Approvals | 60000 (1 min) | 300000 | Frequently updated, needs fresh data |
| Employee list | 300000 (5 min) | 600000 | Master data, changes infrequently |
| My data (attendance, etc.) | 120000 (2 min) | 300000 | Personal data, moderate refresh |
| Receipts | 60000 (1 min) | 300000 | Document data |
| Master data (clients, projects) | 300000 (5 min) | 600000 | Reference data |

---

## Migration Order (Risk-based)

1. **EmployeeMobileApp.js** - Simpler structure, isolated mobile view
2. **HROnboarding.js** - Moderate complexity, form-based
3. **ApprovalsCenter.js** - Most complex, highest risk (migrate last)
