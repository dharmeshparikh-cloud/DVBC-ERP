# Component Refactoring Analysis Report

## 1. ApprovalsCenter.js Analysis (3,576 lines)

### 1.1 Import Dependencies
```javascript
// React Core
React, useState, useEffect, useContext, useCallback, useRef, useMemo

// External Libraries
axios, useQueryClient (@tanstack/react-query), toast (sonner)

// UI Components (13)
Card, CardContent, CardHeader, CardTitle, Button, Badge, Dialog, DialogContent, 
DialogHeader, DialogTitle, DialogFooter, DialogDescription, Textarea, Checkbox, 
Input, Label

// Icons (31)
CheckCircle, XCircle, Clock, AlertCircle, ChevronRight, FileText, Calendar, User, 
MessageSquare, Send, DollarSign, Building2, CreditCard, Eye, Loader2, Rocket, Key, 
Wallet, Shield, RefreshCw, CheckSquare, Square, Zap, Bell, Menu, Briefcase, Play, 
Receipt, Upload, Download, Paperclip, RotateCcw, Edit3, Trash2, X

// Custom Hooks (28)
usePendingApprovals, useMyRequests, useAllApprovals, useCtcApprovals, useGoLivePending,
useGoLiveChecklist, usePermissionRequests, useModificationRequests, useBankChangeRequests,
useEmployeeChangeRequests, useAgreementApprovals, useKickoffApprovals, useExpenseApprovals,
useExpenseReceipts, useApprovalAction, useApproveAgreement, useRejectAgreement,
useApproveKickoff, useRejectKickoff, useApproveExpense, useRejectExpense, useSendBackExpense,
usePartialApproveExpense, useUploadExpenseReceipt, useDeleteExpenseReceipt,
useApprovePermissionRequest, useRejectPermissionRequest, useApproveCTC, useRejectCTC,
useBankChangeAction, useApproveProfileChange, useRejectProfileChange, useApproveGoLive,
useRejectGoLive, useApproveModificationRequest, useRejectModificationRequest, useBulkApprovalAction

// Context
AuthContext, API (from App.js), ThemeContext
```

### 1.2 State Variables (50+)
```
UI Navigation:
- activeTab (string)
- mobileMenuOpen (boolean)

Selection States:
- selectedApproval, selectedCtc, selectedBank, selectedPermission,
  selectedGoLive, selectedAgreement, selectedKickoff, selectedExpense

Dialog States:
- actionDialog, ctcDetailDialog, bankDetailDialog, permissionDetailDialog,
  goLiveDetailDialog, agreementDetailDialog, kickoffDetailDialog, expenseDetailDialog,
  receiptUploadDialog, receiptsListDialog, sendBackDialog, partialApprovalDialog,
  bulkActionDialog

Form States:
- comments, rejectReason, expenseRemarks, sendBackComments, approvedAmount,
  modificationReason, bulkComments

Loading States:
- actionLoading, uploadingReceipt, loadingReceipts, bulkLoading

Data States:
- goLiveChecklist, expenseReceipts, selectedItems (Set)

Real-time States:
- wsConnected, lastRefresh, wsRef (ref)
```

### 1.3 Logical Sections (11 Approval Types)
```
1. Generic Approvals (pending, my requests, all)
2. CTC Structure Approvals (Admin)
3. Permission Change Requests (Admin)
4. Go-Live Approvals (Admin)
5. Modification Requests (Admin)
6. Bank Change Requests (HR)
7. Profile Change Requests (HR)
8. Agreement Approvals (Manager, Admin)
9. Kickoff Approvals (SC, PC, Admin)
10. Expense Approvals (Manager, HR)
11. Bulk Actions
```

### 1.4 API Endpoints Used (20+)
```
/api/approvals/{id}/action
/api/agreements/{id}/approve|reject
/api/sales-funnel/approve-kickoff/{id}
/api/sales-funnel/reject-kickoff/{id}
/api/expenses/{id}/approve|reject|send-back|approve-with-modification
/api/expenses/{id}/upload-receipt|receipts
/api/permission-change-requests/{id}/approve|reject
/api/ctc/{id}/approve|reject
/api/admin/bank-change-request/{id}/approve|reject
/api/hr/bank-change-request/{id}/approve|reject
/api/hr/employee-change-request/{id}/approve|reject
/api/go-live/checklist/{id}
/api/go-live/{id}/approve|reject
```

### 1.5 Handler Functions (25+)
```
fetchData, handleAction, openActionDialog, handleAgreementAction,
handleKickoffAction, handleExpenseAction, handleReceiptUpload,
fetchExpenseReceipts, handleDownloadReceipt, handleDeleteReceipt,
handleSendBack, handlePartialApproval, openExpenseDetails,
handlePermissionAction, handleCtcAction, handleBankAction,
handleProfileChangeAction, fetchGoLiveChecklist, handleGoLiveAction,
toggleItemSelection, selectAllPending, clearSelection,
handleBulkAction, openBulkActionDialog
```

---

## 2. EmployeeMobileApp.js Analysis (2,316 lines)

### 2.1 Import Dependencies
```javascript
// React Core
React, useState, useEffect, useContext, useRef, useMemo

// External Libraries
axios, useQueryClient (@tanstack/react-query), toast (sonner)

// Custom Hooks (8)
useMobileDashboardData, useMyAssignedClients, useCheckIn, useCheckOut,
useSubmitExpense, useUploadReceipt, useSubmitLeaveRequest,
useSubmitTravelReimbursement, useLocationSearch

// Icons (24)
CheckCircle, Clock, MapPin, LogIn, LogOut, Calendar, Receipt, Home, Building2,
Navigation, Loader2, AlertCircle, ChevronRight, Plus, Camera, FileText,
TrendingUp, User, Bell, Settings, Coffee, Sun, Moon, Briefcase, IndianRupee,
CalendarDays, CheckCircle2, XCircle, Timer, Wallet, X, RotateCcw, Send, Car, Bike, Search

// Context
AuthContext, API (from App.js)
```

### 2.2 State Variables (35+)
```
Navigation:
- activeTab (string)

Location/Check-in:
- location, locationLoading, showCheckInModal, showCheckOutModal,
  selectedWorkLocation, justification, showJustification, locationValidation

Camera/Selfie:
- selfieData, showCamera, stream, videoRef, canvasRef

Time:
- currentTime

Expense Form:
- showExpenseModal, expenseForm (object), lineItemForm (object)

Leave Form:
- showLeaveModal, leaveForm (object)

Travel:
- showTravelModal, travelClaims, travelForm (object), locationSearchQuery,
  locationSearchResults, searchingLocations, selectingFor,
  showTravelReimbursementModal, lastTravelReimbursement, lastAttendanceId,
  travelClaimVehicle, submittingTravelClaim

Client Selection:
- selectedClient
```

### 2.3 Logical Sections (6 Tabs)
```
1. Home Tab - Dashboard with attendance, leaves, quick actions
2. Attendance Tab - Check-in/out, attendance history
3. Leaves Tab - Leave balance, request leave
4. Expenses Tab - Submit expenses, view history
5. Travel Tab (Sales Team) - Travel claims
6. Profile Tab - User info, logout
```

### 2.4 API Interactions
```
/api/mobile/dashboard
/api/mobile/my-assigned-clients
/api/mobile/check-in
/api/mobile/check-out
/api/expenses/submit
/api/expenses/{id}/upload-receipt
/api/leaves/request
/api/travel/claims
/api/travel/reimbursement
```

### 2.5 Key Functions (15+)
```
captureLocation, startCamera, captureSelfie, stopCamera, retakeSelfie,
handleCheckIn, openCheckIn, handleCheckOut, handleSubmitAutoTravelClaim,
handleSubmitExpense, addLineItem, removeLineItem, handleSubmitLeave,
searchLocations, selectLocation, handleSubmitManualTravelClaim, fetchTravelClaims
```

---

## 3. Proposed Modular Structure

### 3.1 ApprovalsCenter Refactoring

```
frontend/src/
├── pages/
│   └── ApprovalsCenter.jsx          # Main container (reduced to ~200 lines)
│
├── components/
│   └── approvals/
│       ├── ApprovalCard.jsx          # (existing) Generic approval card
│       ├── ApprovalFilters.jsx       # NEW: Filter/tab controls
│       ├── ApprovalStats.jsx         # NEW: Stats cards section
│       ├── BulkActionsBar.jsx        # NEW: Bulk selection UI
│       │
│       ├── sections/
│       │   ├── PendingApprovalsSection.jsx
│       │   ├── CtcApprovalsSection.jsx
│       │   ├── PermissionApprovalsSection.jsx
│       │   ├── GoLiveApprovalsSection.jsx
│       │   ├── BankChangeSection.jsx
│       │   ├── ProfileChangeSection.jsx
│       │   ├── AgreementApprovalsSection.jsx
│       │   ├── KickoffApprovalsSection.jsx
│       │   ├── ExpenseApprovalsSection.jsx
│       │   └── MyRequestsSection.jsx
│       │
│       └── dialogs/
│           ├── ApprovalActionDialog.jsx
│           ├── CtcDetailDialog.jsx
│           ├── BankDetailDialog.jsx
│           ├── PermissionDetailDialog.jsx
│           ├── GoLiveDetailDialog.jsx
│           ├── AgreementDetailDialog.jsx
│           ├── KickoffDetailDialog.jsx
│           ├── ExpenseDetailDialog.jsx
│           └── BulkActionDialog.jsx
│
└── hooks/
    └── useApprovals.js              # (existing) All approval hooks
```

### 3.2 EmployeeMobileApp Refactoring

```
frontend/src/
├── pages/
│   └── EmployeeMobileApp.jsx        # Main container (reduced to ~300 lines)
│
├── components/
│   └── mobile/
│       ├── MobileHeader.jsx          # NEW: Header with user info
│       ├── MobileNavigation.jsx      # NEW: Bottom tab navigation
│       │
│       ├── tabs/
│       │   ├── HomeTab.jsx           # Dashboard, quick actions
│       │   ├── AttendanceTab.jsx     # Check-in/out, history
│       │   ├── LeavesTab.jsx         # Leave balance, requests
│       │   ├── ExpensesTab.jsx       # Expense submission, history
│       │   ├── TravelTab.jsx         # Travel claims (sales)
│       │   └── ProfileTab.jsx        # User profile, settings
│       │
│       ├── attendance/
│       │   ├── CheckInModal.jsx      # Check-in with selfie, location
│       │   ├── CheckOutModal.jsx     # Check-out confirmation
│       │   ├── SelfieCapture.jsx     # Camera component
│       │   ├── LocationCapture.jsx   # GPS location component
│       │   └── TravelClaimModal.jsx  # Post check-out travel claim
│       │
│       ├── forms/
│       │   ├── ExpenseForm.jsx       # Expense submission form
│       │   ├── LeaveForm.jsx         # Leave request form
│       │   └── TravelClaimForm.jsx   # Manual travel claim
│       │
│       └── cards/
│           ├── AttendanceCard.jsx    # Today's attendance status
│           ├── LeaveBalanceCard.jsx  # Leave balance display
│           └── ExpenseCard.jsx       # Expense item card
│
└── hooks/
    └── useMobileApp.js              # (existing) Mobile hooks
```

---

## 4. Implementation Priority

### Phase 1: Extract Dialogs (Low Risk)
1. Extract all dialog components from ApprovalsCenter
2. Test each dialog independently
3. No change to data flow

### Phase 2: Extract Sections (Medium Risk)
1. Extract approval type sections one by one
2. Pass data via props
3. Keep handlers in parent or move to hooks

### Phase 3: Extract Mobile Tabs (Medium Risk)
1. Extract each tab as independent component
2. Share state via props or context
3. Keep form handlers in parent initially

### Phase 4: Create Shared Hooks (Low Risk)
1. Extract common logic into custom hooks
2. No UI changes

---

## 5. Verification Checklist

### API Contract Preservation
- [ ] All endpoints remain unchanged
- [ ] Request/response payloads unchanged
- [ ] Error handling preserved

### State Management
- [ ] No duplicate state
- [ ] Proper state lifting
- [ ] Form persistence works

### Routing
- [ ] All routes functional
- [ ] Tab navigation works
- [ ] Deep linking preserved

### Role-Based Access
- [ ] Admin-only sections work
- [ ] HR-only sections work
- [ ] Manager sections work

### Performance
- [ ] No new re-renders
- [ ] Memoization preserved
- [ ] Lazy loading where needed
