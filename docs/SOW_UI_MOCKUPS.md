# SOW Page UI/UX Mockups - Preview Only

## Current vs Proposed Comparison

---

## 1. SOW SUMMARY HEADER (NEW)

**Current State:** No summary - user must scroll through items to understand scope

**Proposed Design:**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  ← Back to Leads    SOW-20260317-159 • VVS Industries                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ TOTAL VALUE  │  │   DURATION   │  │    EFFORT    │  │    MARGIN    │             │
│  │              │  │              │  │              │  │              │             │
│  │  ₹14,25,000  │  │   14 Weeks   │  │   840 Hrs    │  │     32%      │             │
│  │  ──────────  │  │  ──────────  │  │  ──────────  │  │  ──────────  │             │
│  │  +12% target │  │  Oct 12 - Jan│  │ 4 Consultants│  │   Healthy    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                                      │
│  [📄 Export PDF]  [📋 Clone SOW]  [👁 Client Preview]  [✉️ Send for Review]          │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. TEMPLATE LIBRARY SELECTOR (NEW)

**Current State:** Manual entry only, no templates

**Proposed Design:**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  QUICK START FROM TEMPLATE                                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  ┌───┐          │  │  ┌───┐          │  │  ┌───┐          │  │  ┌───┐          │ │
│  │  │ 📊│ HR AUDIT │  │  │ 💼│ SALES    │  │  │ ⚙️│ OPS      │  │  │ 📚│ TRAINING │ │
│  │  └───┘          │  │  └───┘ TRANS.   │  │  └───┘ REVIEW   │  │  └───┘ PROGRAM  │ │
│  │                 │  │                 │  │                 │  │                 │ │
│  │  12 items       │  │  8 items        │  │  15 items       │  │  6 items        │ │
│  │  ~10 weeks      │  │  ~8 weeks       │  │  ~12 weeks      │  │  ~4 weeks       │ │
│  │                 │  │                 │  │                 │  │                 │ │
│  │  [Use Template] │  │  [Use Template] │  │  [Use Template] │  │  [Use Template] │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                                      │
│  [+ Create Custom SOW]                                        [Browse All Templates]│
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CATEGORY TABS + BULK ACTIONS (NEW)

**Current State:** Flat list, no filtering, single-row actions only

**Proposed Design:**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                  │
│  │  ALL   │ │ SALES  │ │   HR   │ │  OPS   │ │TRAINING│ │ANALYTICS│                 │
│  │  (12)  │ │  (3)   │ │  (4)   │ │  (2)   │ │  (2)   │ │  (1)   │                  │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘                  │
│   ═══════                                                                            │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ ☑ 3 selected    [Change Status ▾]  [Assign Consultant ▾]  [Delete]  [× Clear]  ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  🔍 Search scope items...                          View: [List] [Roadmap] [Gantt]   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. ENHANCED TABLE ROW (REDESIGNED)

**Current State:** Basic fields, no progress, no cost visibility

**Proposed Design:**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ # │ CATEGORY │ SCOPE ITEM          │ DELIVERABLES │ CONSULTANT │ TIMELINE │ COST   │ STATUS    │
├───┼──────────┼─────────────────────┼──────────────┼────────────┼──────────┼────────┼───────────┤
│   │          │                     │              │            │          │        │           │
│ ☐ │ ┌──────┐ │ Sales Strategy      │ ┌──────────┐ │ ┌────────┐ │ W1 → W4  │ ₹2.5L  │ ┌───────┐ │
│ 1 │ │ SALES│ │ Development         │ │ 3 items  │ │ │ 👤 AK  │ │ 4 weeks  │        │ │APPROVED│ │
│   │ └──────┘ │ ──────────────────  │ │ ✓✓○      │ │ └────────┘ │ ████████ │        │ └───────┘ │
│   │          │ Define GTM strategy │ └──────────┘ │            │ 100%     │        │           │
│   │          │ for Q1 2026         │              │            │          │        │           │
├───┼──────────┼─────────────────────┼──────────────┼────────────┼──────────┼────────┼───────────┤
│   │          │                     │              │            │          │        │           │
│ ☑ │ ┌──────┐ │ HR Policy Audit     │ ┌──────────┐ │ ┌────────┐ │ W2 → W6  │ ₹3.2L  │ ┌───────┐ │
│ 2 │ │  HR  │ │                     │ │ 5 items  │ │ │ 👤 PK  │ │ 4 weeks  │        │ │IN PROG │ │
│   │ └──────┘ │ ──────────────────  │ │ ✓✓✓○○    │ │ └────────┘ │ ████░░░░ │        │ └───────┘ │
│   │          │ Review all HR       │ └──────────┘ │            │ 60%      │        │           │
│   │          │ policies & SOPs     │ [+ Add]      │            │          │        │  [•••]    │
├───┼──────────┼─────────────────────┼──────────────┼────────────┼──────────┼────────┼───────────┤
│   │          │                     │              │            │          │        │           │
│ ☑ │ ┌──────┐ │ Operations Review   │ ┌──────────┐ │ ┌────────┐ │ W3 → W8  │ ₹4.1L  │ ┌───────┐ │
│ 3 │ │ OPS  │ │                     │ │ 4 items  │ │ │ 👤 RJ  │ │ 5 weeks  │        │ │PENDING │ │
│   │ └──────┘ │ ──────────────────  │ │ ○○○○     │ │ └────────┘ │ ░░░░░░░░ │        │ └───────┘ │
│   │          │ End-to-end process  │ └──────────┘ │            │ 0%       │        │           │
│   │          │ mapping & gaps      │              │            │          │        │  [•••]    │
└───┴──────────┴─────────────────────┴──────────────┴────────────┴──────────┴────────┴───────────┘

Legend:
  ████████ = Progress bar (filled = complete)
  ✓ = Deliverable complete   ○ = Deliverable pending
  [•••] = Row actions menu (Edit, Documents, Support, Delete)
```

---

## 5. DELIVERABLES POPUP (NEW)

**When clicking "3 items" in Deliverables column:**

```
┌─────────────────────────────────────────────────┐
│  DELIVERABLES - Sales Strategy Development     │
├─────────────────────────────────────────────────┤
│                                                 │
│  ✓  GTM Strategy Document (PDF)                │
│     Uploaded: Mar 15, 2026                      │
│                                                 │
│  ✓  Competitor Analysis Report                 │
│     Uploaded: Mar 18, 2026                      │
│                                                 │
│  ○  Pricing Recommendation Deck                │
│     Due: Mar 25, 2026                           │
│                                                 │
├─────────────────────────────────────────────────┤
│  [+ Add Deliverable]              [Close]       │
└─────────────────────────────────────────────────┘
```

---

## 6. GANTT TIMELINE VIEW (ENHANCED)

**Current State:** Basic week display

**Proposed Design:**
```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  TIMELINE VIEW                                           Oct 2026 ─────────────────▶│
├──────────────────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┤
│  SCOPE ITEM          │ W1   │ W2   │ W3   │ W4   │ W5   │ W6   │ W7   │ W8   │ W9   │
├──────────────────────┼──────┴──────┴──────┴──────┼──────┴──────┴──────┴──────┴──────┤
│                      │                           │                                   │
│  Sales Strategy      │ ████████████████████████  │                                   │
│  👤 AK               │ ████  COMPLETED  ████████ │                                   │
│                      │                           │                                   │
├──────────────────────┼──────┬──────┬─────────────┴───────────────┬──────┬──────┬────┤
│                      │      │      │                             │      │      │    │
│  HR Policy Audit     │      │ ░░░░░│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│      │      │    │
│  👤 PK               │      │ ░░░░░│░░░░  IN PROGRESS  ░░░░░░░░░░│      │      │    │
│                      │      │      │                             │      │      │    │
├──────────────────────┼──────┼──────┼──────┬──────────────────────┴──────┴──────┴────┤
│                      │      │      │      │                                         │
│  Operations Review   │      │      │ ▓▓▓▓▓│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
│  👤 RJ               │      │      │ ▓▓▓▓▓│▓▓▓▓  PENDING APPROVAL  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
│                      │      │      │      │                                         │
├──────────────────────┼──────┼──────┼──────┼──────┬──────┬──────┬──────┬─────────────┤
│                      │      │      │      │      │      │      │      │             │
│  Training Program    │      │      │      │      │      │ ████ │ ████ │ ███████████ │
│  👤 SM               │      │      │      │      │      │ NOT STARTED │             │
│                      │      │      │      │      │      │      │      │             │
└──────────────────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴─────────────┘

Legend: ████ Completed   ░░░░ In Progress   ▓▓▓▓ Pending   ─── Not Started
        ↔ Drag to resize   ← → Drag to move
```

---

## 7. CLIENT REVIEW PORTAL (NEW)

**Read-only view for client before signing agreement:**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                      │
│                    D&V BUSINESS CONSULTING                                           │
│                    ━━━━━━━━━━━━━━━━━━━━━━                                           │
│                                                                                      │
│                    SCOPE OF WORK                                                     │
│                    SOW-20260317-159                                                  │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  CLIENT                          PREPARED BY                                   │ │
│  │  VVS Industries Pvt Ltd          Amit Kumar, Principal Consultant              │ │
│  │  Mumbai, Maharashtra             D&V Business Consulting                       │ │
│  │                                  amit@dnv.com                                  │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────────────┐ │
│  │  ENGAGEMENT SUMMARY                                                            │ │
│  ├────────────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                                │ │
│  │  Duration:        14 Weeks (Oct 12, 2026 - Jan 18, 2027)                      │ │
│  │  Investment:      ₹14,25,000 + GST                                            │ │
│  │  Team Size:       4 Consultants                                               │ │
│  │  Engagement Type: Time & Materials                                            │ │
│  │                                                                                │ │
│  └────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  SCOPE ITEMS                                                                         │
│  ━━━━━━━━━━━                                                                        │
│                                                                                      │
│  1. SALES STRATEGY DEVELOPMENT                                        ₹2,50,000    │
│     ─────────────────────────────────────────────────────────────────────────────   │
│     Define go-to-market strategy for Q1 2026                                        │
│                                                                                      │
│     Deliverables:                                                                    │
│     • GTM Strategy Document (PDF)                                                   │
│     • Competitor Analysis Report                                                    │
│     • Pricing Recommendation Deck                                                   │
│                                                                                      │
│     Timeline: Week 1 - Week 4 (4 weeks)                                             │
│     Consultant: Amit Kumar                                                          │
│                                                                                      │
│  2. HR POLICY AUDIT                                                   ₹3,20,000    │
│     ─────────────────────────────────────────────────────────────────────────────   │
│     ...                                                                             │
│                                                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐        │
│  │  ✓  I accept this Scope of Work │  │  ✗  Request Changes              │        │
│  └──────────────────────────────────┘  └──────────────────────────────────┘        │
│                                                                                      │
│  By accepting, you agree to the terms outlined in this document.                    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. SOW PDF EXPORT PREVIEW

**Professional PDF layout:**

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                                 │ │
│ │  [D&V LOGO]                                        SCOPE OF WORK               │ │
│ │                                                    SOW-20260317-159             │ │
│ │                                                    Date: Mar 17, 2026           │ │
│ │                                                                                 │ │
│ │  ─────────────────────────────────────────────────────────────────────────────  │ │
│ │                                                                                 │ │
│ │  CLIENT INFORMATION                    ENGAGEMENT DETAILS                       │ │
│ │  ───────────────────                   ──────────────────                       │ │
│ │  VVS Industries Pvt Ltd                Duration: 14 Weeks                       │ │
│ │  123 Business Park                     Start: Oct 12, 2026                      │ │
│ │  Mumbai - 400001                       End: Jan 18, 2027                        │ │
│ │  Contact: Mr. Vijay Shah               Investment: ₹14,25,000                   │ │
│ │                                                                                 │ │
│ │  ─────────────────────────────────────────────────────────────────────────────  │ │
│ │                                                                                 │ │
│ │  SCOPE OF SERVICES                                                              │ │
│ │  ─────────────────                                                              │ │
│ │                                                                                 │ │
│ │  ┌─────┬──────────────────────────────────────┬──────────┬───────────┐          │ │
│ │  │ #   │ SCOPE ITEM                           │ DURATION │ VALUE     │          │ │
│ │  ├─────┼──────────────────────────────────────┼──────────┼───────────┤          │ │
│ │  │ 1   │ Sales Strategy Development           │ 4 weeks  │ ₹2,50,000 │          │ │
│ │  │ 2   │ HR Policy Audit                      │ 4 weeks  │ ₹3,20,000 │          │ │
│ │  │ 3   │ Operations Review                    │ 5 weeks  │ ₹4,10,000 │          │ │
│ │  │ 4   │ Training Program Design              │ 3 weeks  │ ₹4,45,000 │          │ │
│ │  ├─────┼──────────────────────────────────────┼──────────┼───────────┤          │ │
│ │  │     │ TOTAL                                │ 14 weeks │ ₹14,25,000│          │ │
│ │  └─────┴──────────────────────────────────────┴──────────┴───────────┘          │ │
│ │                                                                                 │ │
│ │  ─────────────────────────────────────────────────────────────────────────────  │ │
│ │                                                                                 │ │
│ │  TERMS & CONDITIONS                                                             │ │
│ │  ───────────────────                                                            │ │
│ │  1. Payment terms as per agreement                                              │ │
│ │  2. Any scope changes require written approval                                  │ │
│ │  3. Confidentiality clause applies                                              │ │
│ │                                                                                 │ │
│ │  ─────────────────────────────────────────────────────────────────────────────  │ │
│ │                                                                                 │ │
│ │  ACCEPTANCE                                                                     │ │
│ │                                                                                 │ │
│ │  Client Signature: ____________________    Date: ____________________           │ │
│ │                                                                                 │ │
│ │  D&V Representative: __________________    Date: ____________________           │ │
│ │                                                                                 │ │
│ └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│                                  Page 1 of 3                                        │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. FULL PAGE LAYOUT - PROPOSED

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  ← Back to Funnel    SOW Builder    SOW-20260317-159                    👤 EMP003  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ TOTAL VALUE  │  │   DURATION   │  │    EFFORT    │  │    STATUS    │             │
│  │  ₹14,25,000  │  │   14 Weeks   │  │ 4 Consultants│  │   APPROVED   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                                      │
│  [📄 Export PDF]  [📋 Clone]  [👁 Preview]  [✉️ Send to Client]           [💾 Save] │
│                                                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                              │
│  │ ALL  │ │SALES │ │  HR  │ │ OPS  │ │TRAIN │ │ANLYS │     🔍 Search...             │
│  │ (12) │ │ (3)  │ │ (4)  │ │ (2)  │ │ (2)  │ │ (1)  │                              │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     [List] [Road] [Gantt]    │
│   ═══════                                                                            │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐│
│  │ ☑ 2 selected         [Change Status ▾]  [Assign ▾]  [Delete]        [× Clear]  ││
│  └─────────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│  ┌───┬──────────┬─────────────────────┬────────────┬──────────┬────────┬──────────┐ │
│  │ # │ CATEGORY │ SCOPE ITEM          │ CONSULTANT │ TIMELINE │  COST  │  STATUS  │ │
│  ├───┼──────────┼─────────────────────┼────────────┼──────────┼────────┼──────────┤ │
│  │ ☐ │  SALES   │ Sales Strategy...   │  👤 AK     │ W1-W4    │ ₹2.5L  │ APPROVED │ │
│  │ ☑ │   HR     │ HR Policy Audit     │  👤 PK     │ W2-W6    │ ₹3.2L  │ IN PROG  │ │
│  │ ☑ │   OPS    │ Operations Review   │  👤 RJ     │ W3-W8    │ ₹4.1L  │ PENDING  │ │
│  │ ☐ │  TRAIN   │ Training Program    │  👤 SM     │ W6-W9    │ ₹4.5L  │  DRAFT   │ │
│  └───┴──────────┴─────────────────────┴────────────┴──────────┴────────┴──────────┘ │
│                                                                                      │
│  [+ Add from Template]  [+ Add Custom Row]                                          │
│                                                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  [← Previous: Pricing Plan]                            [Next: Quotation →]          │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## COLOR SPECIFICATIONS

| Element | Background | Text | Border |
|---------|------------|------|--------|
| Page | `bg-zinc-50/50` | - | - |
| Card | `bg-white` | - | `border-zinc-200` |
| Header | `bg-white` | `text-zinc-900` | `border-b border-zinc-200` |
| Category Badge - Sales | `bg-blue-50` | `text-blue-700` | `border-blue-200` |
| Category Badge - HR | `bg-purple-50` | `text-purple-700` | `border-purple-200` |
| Category Badge - Ops | `bg-amber-50` | `text-amber-700` | `border-amber-200` |
| Status - Draft | `bg-zinc-100` | `text-zinc-700` | - |
| Status - Pending | `bg-amber-50` | `text-amber-700` | - |
| Status - Approved | `bg-emerald-50` | `text-emerald-700` | - |
| Status - In Progress | `bg-blue-50` | `text-blue-700` | - |
| Primary Button | `bg-zinc-900` | `text-white` | - |
| Secondary Button | `bg-white` | `text-zinc-700` | `border-zinc-300` |

---

## TYPOGRAPHY

| Element | Class |
|---------|-------|
| Page Title | `text-2xl font-semibold tracking-tight text-zinc-900` |
| Section Title | `text-lg font-medium tracking-tight text-zinc-900` |
| Table Header | `text-[11px] uppercase tracking-wider font-semibold text-zinc-500` |
| Table Cell | `text-sm text-zinc-700` |
| Metric Value | `text-2xl font-bold tracking-tight text-zinc-900` |
| Metric Label | `text-xs uppercase tracking-wider text-zinc-500` |

---

## INTERACTION PATTERNS

| Action | Behavior |
|--------|----------|
| Row Hover | `bg-zinc-50/50` with subtle transition |
| Checkbox Select | Show bulk action bar immediately |
| Category Tab Click | Filter table + update URL params |
| View Toggle | Smooth transition between List/Roadmap/Gantt |
| Template Card Hover | Slight scale + shadow elevation |
| Status Change | Optimistic update + toast confirmation |
| Drag Row | Ghost preview + drop indicator line |

---

## SUMMARY OF IMPROVEMENTS

| Current | Proposed |
|---------|----------|
| No summary metrics | 4-card bento grid header |
| Manual item entry | Template library + auto-generate |
| Flat list | Category tabs + search |
| Single actions | Bulk selection + actions |
| Basic columns | Progress bars + deliverables + cost |
| Simple Gantt | Interactive timeline with drag |
| No client view | Dedicated client portal |
| No export | PDF export with branding |

