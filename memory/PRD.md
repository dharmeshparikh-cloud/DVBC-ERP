# D&V Business Consulting - Comprehensive Business Management Application

## Product Overview
A comprehensive business management application for D&V Business Consulting, a 50-person HR consulting organization covering HR, Marketing, Sales, Finance, and Consulting projects.

---

## Latest Update (February 15, 2026)

### New Features: Custom Payments, Notes & Agreement Sections ✅ (LATEST)

**1. Custom (Irregular) Payment Schedule:**
- New "Custom (Irregular)" option in Payment Schedule dropdown
- Users can manually define each payment with:
  - **Date** - custom due date
  - **Amount** - flexible amount per payment
  - **Description/Milestone** - e.g., "30% Upfront", "Final Delivery"
- Add unlimited payments via "Add Payment" button
- Validation shows error (red) when total doesn't match project value
- Validation shows success (green) when totals match

**Example - 30-40-30 Split:**
```
Payment #1: ₹3,00,000 - "30% Upfront - Project Kickoff"
Payment #2: ₹4,00,000 - "40% - Mid-Project Milestone"
Payment #3: ₹3,00,000 - "30% - Final Delivery"
Total: ₹10,00,000 ✅ (matches project value)
```

**2. Notes & Descriptions Section:**
- 4 textarea fields for adding notes across sections:
  - Pricing Notes
  - Team Deployment Notes
  - Payment Terms Notes
  - General Notes
- Notes are saved with the pricing plan and included in agreements

**3. Agreement Sections Configuration:**
- 8 toggleable checkboxes to control what appears in the agreement:
  1. Pricing Summary
  2. Team Deployment
  3. Payment Schedule
  4. GST Details
  5. TDS Details
  6. Conveyance Details
  7. Discount Details
  8. Notes & Terms
- Visual eye icon shows section visibility status
- Unchecked sections are hidden from final agreement

---

### Bug Fixes & Enhancements ✅ (Completed Earlier)

**1. Multiple Team Members Bug Fix:**
- **Issue:** Adding multiple team members was replacing previous entries (race condition)
- **Fix:** `recalculateAllocations()` now accepts optional `currentTeam` parameter, avoiding setTimeout race condition
- **Result:** Can now add unlimited team members that accumulate correctly

**2. Dynamic Payment Count Display:**
- **Issue:** Conveyance helper text showed hardcoded "12 months" regardless of payment schedule
- **Fix:** Added `numberOfPayments` useMemo that calculates actual payments based on schedule
- **Result:** 
  - Monthly (12 months) → "(split across 12 payments)"
  - Quarterly (12 months) → "(split across 4 payments)"
  - Upfront → "(split across 1 payment)"

**3. Conveyance Summary Tooltip:**
- Added help icon (?) next to conveyance input
- Tooltip shows: Total amount, Per-payment amount, Distribution info

---

### Lumpsum Conveyance Feature ✅ (Completed)

**Changes Made:**
Changed the Conveyance field from a percentage-based input to a **lumpsum amount** that is distributed evenly across all payment periods.

1. **Previous Behavior:** Conveyance was 5% of basic amount per payment
2. **New Behavior:** Conveyance is a fixed lumpsum amount (e.g., ₹60,000) distributed evenly across all payments

**UI Changes:**
- Conveyance input now shows ₹ symbol instead of %
- Helper text: "(split across X payments)" - dynamically calculated
- Column header: "CONVEYANCE (LUMPSUM)" instead of "CONVEYANCE (5%)"

**Calculation Example (Quarterly):**
```
Total Investment: ₹12,00,000
Conveyance Lumpsum: ₹48,000
Duration: 12 months (Quarterly payments = 4 quarters)
Basic per quarter: ₹3,00,000

Distribution:
- Conveyance per quarter: ₹48,000 ÷ 4 = ₹12,000

Net per quarter: ₹3,00,000 + ₹54,000 (GST) + ₹12,000 (Conv) = ₹3,66,000
Total Conveyance: +₹48,000.00
```

---

### Payment Plan Breakup Feature ✅ (Completed Earlier)

**Major Feature: Top-Down Pricing Model**
Implemented a complete redesign of the pricing model. Instead of the salesperson manually calculating rates and totals (bottom-up), they now simply enter the **Total Client Investment** and the system automatically allocates costs to team members based on admin-defined allocation rules.

**Key Changes:**

1. **Admin Masters Module (NEW)**
   - Created `/admin-masters` page (admin-only access)
   - Manages **Tenure Types** with allocation percentages:
     - Full-time Engagement: 70%
     - Weekly Engagement: 20%
     - Bi-weekly Engagement: 10%
     - Monthly Engagement: 5%
     - Quarterly Review: 2.5%
     - On-demand Support: 0%
   - Manages **Consultant Roles** with rate ranges
   - Manages **Meeting Types** with default durations
   - Backend: `/app/backend/routers/masters.py`
   - Frontend: `/app/frontend/src/pages/AdminMasters.js`

2. **Top-Down Pricing Flow**
   ```
   Total Client Investment (₹10,00,000)
         ↓
   Team Member Selection (Role + Tenure Type)
         ↓
   Auto-Calculate: Allocation % (normalized)
         ↓
   Auto-Calculate: Breakup Amount = Total × Allocation %
         ↓
   Auto-Calculate: Rate/Meeting = Breakup ÷ Total Meetings (READ-ONLY)
   ```

3. **Calculation Example:**
   - Total Investment: ₹10,00,000
   - Team Member: Principal Consultant (Full-time: 70%)
   - If only 1 member: Allocation = 100% (normalized)
   - Breakup Amount: ₹10,00,000
   - Total Meetings: 22/month × 12 months = 264
   - Rate/Meeting: ₹10,00,000 ÷ 264 = ₹3,788 (READ-ONLY)

4. **Rate Override: NOT ALLOWED**
   - Rate per Meeting field is locked (read-only)
   - Shows lock icon to indicate auto-calculated value

**New API Endpoints:**
- `GET /api/masters/tenure-types` - List tenure types with allocation %
- `POST /api/masters/tenure-types` - Create tenure type
- `PUT /api/masters/tenure-types/{id}` - Update tenure type
- `DELETE /api/masters/tenure-types/{id}` - Soft delete tenure type
- `GET /api/masters/consultant-roles` - List consultant roles
- `POST /api/masters/consultant-roles` - Create consultant role
- `GET /api/masters/meeting-types` - List meeting types
- `POST /api/masters/seed-defaults` - Seed default master data
- `POST /api/masters/calculate-allocation` - Calculate allocation breakdown

**Files Modified/Created:**
- `/app/backend/routers/masters.py` (NEW)
- `/app/backend/routers/__init__.py` (NEW)
- `/app/backend/server.py` (Updated - added masters router)
- `/app/backend/sales_workflow.py` (Updated - added total_investment, allocation fields)
- `/app/frontend/src/pages/AdminMasters.js` (NEW)
- `/app/frontend/src/pages/sales-funnel/PricingPlanBuilder.js` (REWRITTEN)
- `/app/frontend/src/App.js` (Updated - added admin-masters route)
- `/app/frontend/src/components/Layout.js` (Updated - added Admin Masters nav)

---

## Previous Updates

### Complete Sales Flow Redesign ✅ (Feb 14, 2026)

**Major Feature: Pricing Plan as Source of Truth**
The entire sales flow has been redesigned so that the **Pricing Plan** is the single source of truth for team deployment and pricing data. Data now flows correctly through the pipeline:

```
Pricing Plan → Quotation → Agreement
     ↓              ↓           ↓
  Team Data    Inherited    Inherited
  (Source)     from Plan    from Plan
```

### Team Deployment & Financial Data Separation ✅

**Major Feature: Team Deployment Structure for Kickoff Requests**
- Added Team Deployment Structure to Agreement creation
- PM can review team commitments before accepting projects

**Major Feature: Consulting Team Financial Data Isolation**
- Consulting team (PM, Consultants) can NO longer see pricing/P&L data
- Replaced pricing columns with Meeting Frequency and Project Tenure

---

## Code Architecture

```
/app/
├── backend/
│   ├── .env
│   ├── routers/
│   │   ├── __init__.py
│   │   └── masters.py           # NEW: Admin Masters CRUD
│   ├── models/
│   ├── sales_workflow.py        # Updated: total_investment, allocation fields
│   ├── requirements.txt
│   └── server.py                # Updated: includes masters router
└── frontend/
    └── src/
        ├── App.js               # Updated: admin-masters route
        ├── components/
        │   └── Layout.js        # Updated: Admin Masters nav
        └── pages/
            ├── AdminMasters.js  # NEW: Admin Masters UI
            └── sales-funnel/
                ├── Agreements.js
                ├── PricingPlanBuilder.js  # REWRITTEN: Top-down pricing
                └── Quotations.js
```

---

## Technical Stack

### Frontend
- React 18
- Tailwind CSS
- Shadcn/UI components
- DHTMLX Gantt

### Backend
- FastAPI
- Pydantic models
- Motor (async MongoDB driver)
- JWT authentication

### Database
- MongoDB

---

## Test Credentials

- **Admin:** admin@company.com / admin123
- **Manager:** manager@company.com / manager123
- **Executive:** executive@company.com / executive123

---

## Upcoming Tasks (P1)

1. **P&L Variance Tracking**
   - Implement logic to flag over-delivery (actual vs. committed meetings)
   - Create variance alerts for projects exceeding committed scope

2. **Employee Cost Integration**
   - Integrate with HR/Payroll data to pull actual employee CTC
   - Enable actual cost calculations for P&L analysis

3. **Project P&L Dashboard**
   - Dashboard showing committed vs. actual costs and revenue
   - Variance alerts and profitability indicators

4. **Masters Sync Engine**
   - Ensure all forms across the application are automatically updated when admin changes master data

---

## Future Tasks (P2)

1. **Finance Module**
   - Full P&L, invoicing, and revenue recognition

2. **Detailed Reporting**
   - Role-wise and client-wise profitability reports

3. **Real Email Integration (SMTP)**
   - Replace mock email system with actual SMTP service

4. **Rocket Reach Integration**
   - Lead enrichment from Rocket Reach API

---

## Backlog (P3)

1. Marketing Flow Module
2. Finance & Accounts Flow Module
3. **Refactor server.py** - Break monolithic file into modular FastAPI routers

---

## Mocked Features

- **Email sending** - Currently logs to console (SMTP not integrated)

---

## 3rd Party Integrations

- **Emergent-managed Google Auth** - Domain restricted (@dvconsulting.co.in)
- **DHTMLX Gantt** - For project roadmap/Gantt charts

---

## Key Files Reference

- `/app/backend/server.py` - Main API server
- `/app/backend/routers/masters.py` - Admin Masters module
- `/app/backend/sales_workflow.py` - Sales models (PricingPlan, Quotation, Agreement)
- `/app/frontend/src/pages/AdminMasters.js` - Admin Masters UI
- `/app/frontend/src/pages/sales-funnel/PricingPlanBuilder.js` - Top-down pricing UI
- `/app/memory/PRD.md` - This file
