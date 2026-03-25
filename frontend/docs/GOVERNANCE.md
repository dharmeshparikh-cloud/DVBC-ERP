# NETRA ERP - Sales Module Governance

## Overview

The Sales Module follows strict governance rules to ensure consistency, maintainability, and performance across all data-intensive views.

## Core Rule: Use SalesDataTable for Primary Data Listings

All primary sales data listing pages **MUST** use the `SalesDataTable` component or its specialized variants instead of manual HTML tables.

### Governed Table Components

| Component | Purpose | Location |
|-----------|---------|----------|
| `SalesDataTable.jsx` | Core reusable Excel-like table | `/src/components/sales/` |
| `LeadsTable.jsx` | Lead management listing | `/src/components/sales/` |
| `MeetingsTable.jsx` | Meeting tracking listing | `/src/components/sales/` |
| `FollowUpsTable.jsx` | Follow-up management listing | `/src/components/sales/` |
| `QuotationsTable.jsx` | Quotation tracking listing | `/src/components/sales/` |
| `AgreementsTable.jsx` | Agreement tracking listing | `/src/components/sales/` |
| `SOWTable.jsx` | SOW listing | `/src/components/sales/` |
| `ProformaInvoiceTable.jsx` | Proforma invoice listing | `/src/components/sales/` |

### Features Provided by SalesDataTable

- ✅ Excel-style column filters (dropdown, text, number range, date range)
- ✅ Global search with debouncing
- ✅ Sorting (ASC/DESC) with visual indicators
- ✅ Server-side pagination
- ✅ Filter chips with clear functionality
- ✅ Sticky header
- ✅ Color coding (Red=overdue, Yellow=due, Green=progressing)
- ✅ Quick views (My Leads, Today Follow-ups, Hot Deals, etc.)
- ✅ Standardized API response format

### Allowed Exceptions

The following table use cases are **exempt** from this governance rule:

1. **Dashboard Summary Tables**: Aggregate/summary views that show statistics rather than CRUD data listings.
2. **CSV Preview Tables**: Temporary data displays for import previews.
3. **Detail View Nested Tables**: Read-only tables embedded within detail/view pages (e.g., team deployment in Agreement View).
4. **Payment Schedule Displays**: Financial breakdown tables in pricing/quotation builders.
5. **Inline Editing Tables**: Specialized tables with cell-level editing (e.g., SOW Builder).

### Files Marked for Future Refactoring

- `ConsultingMeetings.js` (2300+ lines) - Complex component that needs to be broken down.

## Running the Governance Check

```bash
cd /app/frontend
node scripts/check-sales-governance.js
```

This script will:
1. Scan all primary sales listing pages
2. Verify they use governed table components
3. Report any violations
4. Provide a summary of compliance status

## Adding a New Sales Table

When creating a new sales-related data listing:

1. **Create a specialized table component** in `/src/components/sales/`
2. **Extend from SalesDataTable pattern**:
   ```jsx
   import SalesDataTable from './SalesDataTable';
   
   const MyNewTable = ({ onRowClick, externalFilters }) => {
     const columns = [...]; // Define columns
     const quickViews = [...]; // Define quick views
     
     return (
       <SalesDataTable
         endpoint="/api/my-endpoint"
         columns={columns}
         quickViews={quickViews}
         // ... other props
       />
     );
   };
   ```
3. **Add the new component to the allowed files list** in the governance checker
4. **Use the component in your page** instead of manual tables

## API Response Format

All sales listing APIs must return data in this standardized format:

```json
{
  "data": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

## Checklist Alignment

Each sales funnel step has a checklist that must match the actual mandatory fields:

| Step | Required Fields |
|------|-----------------|
| Lead Capture | Full name, Company name, Email |
| Record Meeting | Meeting date/time, MOM summary |
| Pricing Plan | Team member added, Total investment > 0, Payment start date |
| Scope of Work | SOW document created, At least one scope item with title |
| Quotation | Lead selected, Pricing plan linked, Quotation number generated |
| Agreement | Lead with quotation selected, Quotation linked, Agreement type, Signed status |
| Record Payment | Payment received, Payment verified |
| Kickoff Request | PM assigned, Request submitted, Approved |
| Project Created | Project created in system |

## Contact

For questions about sales module governance, contact the development team.
