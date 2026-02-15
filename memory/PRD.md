# D&V Business Consulting - Comprehensive Business Management Application

## Product Overview
A comprehensive business management application for D&V Business Consulting, a 50-person HR consulting organization covering HR, Marketing, Sales, Finance, and Consulting projects.

---

## Latest Update (February 15, 2026)

### Payment Plan Breakup Feature ✅ (LATEST - Completed)

**Changes Made:**
1. **Removed:** Growth Consulting & Guarantee section from Pricing Plan Builder
2. **Added:** Payment Plan Breakup section with:
   - **Project Start Date** picker
   - **Payment Components** (Multi-select):
     - GST: 18% (Fixed, cannot be changed)
     - TDS: -10% (Editable, deducted from payment)
     - Conveyance: +5% (Editable, added to payment)
   - **Auto-Generated Payment Schedule Table** showing:
     - Frequency (Month 1, Month 2, Q1, Q2, etc.)
     - Due Date (calculated from start date)
     - Basic Amount (Total ÷ Number of payments)
     - GST (+18% if selected)
     - TDS (-10% if selected, deducted)
     - Conveyance (+5% if selected)
     - **Net Receivable** = Basic + GST + Conveyance - TDS
   - **Payment Reminder Note:** "Auto-reminders 7 days before due date"

**Calculation Example:**
```
Total Investment: ₹12,00,000
Duration: 12 months (Monthly payments)
Basic per month: ₹1,00,000

Components selected: GST, TDS, Conveyance
- GST (18%): +₹18,000
- TDS (10%): -₹10,000
- Conveyance (5%): +₹5,000

Net per month: ₹1,00,000 + ₹18,000 + ₹5,000 - ₹10,000 = ₹1,13,000
```

---

### P0 Sprint: Top-Down Pricing Redesign ✅ (Completed Earlier Today)

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
