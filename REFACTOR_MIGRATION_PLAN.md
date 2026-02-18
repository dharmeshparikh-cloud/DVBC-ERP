# Server.py Refactoring Migration Plan

## Overview
This document tracks the progress of refactoring the monolithic `server.py` file into a modular router-based architecture.

## Current Status
- **Original Size:** ~14,000+ lines
- **Current Size:** 9,488 lines  
- **Lines Reduced:** ~4,500+ lines
- **Last Updated:** February 2025

## Completed Migrations

### Stats Router (`/app/backend/routers/stats.py`)
- [x] `/stats/dashboard` - Main dashboard statistics
- [x] `/stats/sales-dashboard` - Sales pipeline stats
- [x] `/stats/sales-dashboard-enhanced` - Enhanced sales metrics with team performance
- [x] `/stats/hr-dashboard` - HR employee/attendance/payroll stats
- [x] `/stats/consulting-dashboard` - Consulting delivery stats

**Notes:** All endpoints match frontend expected data formats. Legacy code removed from server.py.

### Auth Router (`/app/backend/routers/auth.py`)
- [x] Login endpoints (password, Google OAuth)
- [x] Token management
- [x] Password reset flow

### Meetings Router (`/app/backend/routers/meetings.py`)
- [x] Meeting CRUD operations
- [x] MoM generation

### Employees Router (`/app/backend/routers/employees.py`)
- [x] Employee management
- [x] Employee onboarding

### CTC Router (`/app/backend/routers/ctc.py`)
- [x] CTC structure management
- [x] Salary component calculations

### Letters Router (`/app/backend/routers/letters.py`)
- [x] Offer letter templates
- [x] Letter generation and email sending
- [x] Public acceptance endpoint

### Role Management Router (`/app/backend/routers/role_management.py`)
- [x] Role request/approval workflow
- [x] Level-based permissions

## Remaining in server.py

### Endpoints Still in server.py (To Be Migrated)
These endpoints are functional but should be moved to dedicated routers for better organization:

1. **Sales Funnel Endpoints** (~2000 lines)
   - Quotations, Agreements, Pricing Plans
   - Kickoff requests
   - Sales targets
   
2. **Client Management** (~500 lines)
   - Client CRUD
   - Revenue tracking
   
3. **Project Management** (~1500 lines)
   - Project CRUD
   - Project assignments
   - SOW management

4. **Expense Management** (~500 lines)
   - Expense CRUD
   - Expense approvals

5. **Leave Management** (~400 lines)
   - Leave requests
   - Leave approvals

6. **Travel Management** (~800 lines)
   - Travel requests
   - Travel approvals

7. **Reports** (~600 lines)
   - Various report generation

8. **Security/Audit** (~300 lines)
   - Audit logs
   - Security events

9. **Consultant Features** (~600 lines)
   - Consultant dashboard
   - Assignments

10. **Miscellaneous** (~800 lines)
    - Follow-up tasks
    - Email templates
    - Various utility endpoints

## Migration Guidelines

### Before Migrating an Endpoint:
1. **Check Frontend Usage:** Verify which components call the endpoint
2. **Note Expected Data Format:** Ensure response format matches frontend expectations
3. **Test Thoroughly:** Use curl to verify both legacy and new endpoints return identical data

### Migration Steps:
1. Create or update the router file in `/app/backend/routers/`
2. Copy the endpoint logic, updating imports as needed
3. Test the new endpoint with curl
4. Remove the legacy code from server.py
5. Verify frontend still works
6. Update this document

### Common Issues:
- **Different field names:** Frontend expects specific field names (e.g., `total_leads` not `leads_count`)
- **Missing dependencies:** Ensure all imports are available in the router file
- **Auth dependencies:** Use `get_current_user` from auth router

## Priority Order
1. ✅ Stats endpoints (Dashboard critical)
2. Sales Funnel (High usage)
3. Client Management (Business critical)
4. Project Management (Team usage)
5. Other endpoints (Lower priority)
