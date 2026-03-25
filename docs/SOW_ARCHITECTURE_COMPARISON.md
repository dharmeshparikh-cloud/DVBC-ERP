# SOW Architecture Comparison: Current vs Proposed

## 📊 CURRENT STATE ANALYSIS

### Backend Collections & Files

| Collection/File | Purpose | Status |
|-----------------|---------|--------|
| `sow` | Legacy SOW collection | EXISTS but rarely used |
| `enhanced_sow` | Main SOW collection for Sales + Consulting | **ACTIVE - PRIMARY** |
| `sow_categories` | Domain/Category master (Sales, HR, Ops...) | EXISTS |
| `sow_scope_templates` | Pre-defined scope templates | EXISTS |
| `sow_change_requests` | Change request tracking | EXISTS |
| `project_sow` | Was meant for delivery layer | EXISTS but **EMPTY/UNUSED** |

### Backend Routers

| Router | Prefix | Purpose | Lines |
|--------|--------|---------|-------|
| `sow_legacy.py` | `/sow` | Original SOW CRUD | 431 |
| `enhanced_sow.py` | `/enhanced-sow` | Role-based workflow (Sales→Consulting) | **1657** |
| `sow_masters.py` | `/sow-masters` | Admin: Categories & Templates | 393 |

### Frontend Pages

| Page | Path | Used By | Purpose |
|------|------|---------|---------|
| `SOWBuilder.js` | `/sales-funnel/sow` | Sales | Create/Edit SOW items |
| `SalesSOWList.js` | `/sales-funnel/sow-list` | Sales | List all SOWs |
| `ConsultingSOWList.js` | `/consulting/sow-list` | Consulting | View handed-over SOWs |
| `SOWChangeRequests.js` | `/consulting/sow-changes` | Consulting | Request scope changes |

---

## 🔄 WHAT CURRENTLY EXISTS vs PROPOSED

### SOW MASTER (Your Proposed)

| Field | Proposed | Current `enhanced_sow` | Gap |
|-------|----------|------------------------|-----|
| SOW ID | ✓ | `id` field exists | ✅ None |
| Domain[] | Multi-select | `category` (single) | ⚠️ **SINGLE not MULTI** |
| Title | Unique | `title` exists | ⚠️ No uniqueness check |
| Deliverables[] | Standardized | `scopes[].description` only | ❌ **NO DELIVERABLES MASTER** |
| Version | For pre-lock | `version` exists | ✅ None |
| is_locked | After kickoff | `sales_handover_complete` + `consulting_kickoff_complete` | ⚠️ Different naming |

### PROJECT SOW (Your Proposed)

| Feature | Proposed | Current State | Gap |
|---------|----------|---------------|-----|
| Separate collection | `PROJECT_SOW` | **NO** - same `enhanced_sow` | ❌ **MAJOR GAP** |
| Derived from SOW_MASTER | Reference by ID | Direct editing | ❌ **NO SEPARATION** |
| PM can customize | Yes | Yes (same doc) | ⚠️ No audit trail |
| Status: Open/WIP/Delivered/NA/ReOpen | Custom | `status` on scopes only | ⚠️ Item-level not SOW-level |

### TASK STRUCTURE (Your Proposed)

| Feature | Proposed | Current State | Gap |
|---------|----------|---------------|-----|
| Task collection | `TASKS` under PROJECT_SOW | **NONE** | ❌ **DOESN'T EXIST** |
| Task ID, SOW ID, Title, Assigned, Status, Proof, Remarks | Full structure | N/A | ❌ **DOESN'T EXIST** |
| Task Status: Open/WIP/Delivered/Blocked | 4 statuses | N/A | ❌ **DOESN'T EXIST** |

### PROOF MANAGEMENT (Your Proposed)

| Feature | Proposed | Current State | Gap |
|---------|----------|---------------|-----|
| `PROOF_COLLECTION` | entity_type + entity_id | `scopes[].attachments[]` | ⚠️ Embedded, not separate |
| SOW-level proof | Yes | No | ❌ **ONLY ITEM LEVEL** |
| Task-level proof | Yes | N/A (no tasks) | ❌ **DOESN'T EXIST** |
| Version history | Yes | Basic timestamps | ⚠️ Limited |

---

## ⚠️ DANGEROUS / RISKY AREAS

### 🔴 HIGH RISK

| Risk | Description | Impact | Mitigation |
|------|-------------|--------|------------|
| **Data Migration** | 50+ existing SOWs in `enhanced_sow` need migration | Data loss if not careful | Create backup, write migration script with rollback |
| **Dual System Period** | Old UI hitting old endpoints while building new | Confusion, data inconsistency | Feature flag to switch, not gradual |
| **SSOT Violation** | Current system allows editing SOW from Sales AND Consulting | "Who owns the data?" conflicts | Strict lock after kickoff |
| **No Task System** | Tasks don't exist - building from scratch | Scope creep, over-engineering | Start minimal, iterate |

### 🟠 MEDIUM RISK

| Risk | Description | Impact | Mitigation |
|------|-------------|--------|------------|
| **Domain Multi-Select** | Current: single category. Proposed: multi-select | Schema change, UI change | Add `domains[]` field, keep `category` for backward compat |
| **Deliverables Master** | Doesn't exist - free text currently | Need new master collection | Create `deliverables_master` with seeding |
| **Enhanced_sow is 1657 lines** | Huge router, hard to refactor safely | Risk breaking existing features | Extract new endpoints to new router |
| **ConsultingMeetings.js** | 2300+ lines, uses SOW data | Breaking this page impacts consultants | Touch minimally, use new API |

### 🟡 LOW RISK

| Risk | Description | Impact | Mitigation |
|------|-------------|--------|------------|
| **SOW Categories → Domains** | Rename/extend existing | Mostly naming | Add alias, deprecate old |
| **Proof Storage** | Object Storage already exists | Just reuse | Use existing integration |
| **RBAC** | Already have role checks | Tighten existing | Audit and update |

---

## 📝 WHAT WILL CHANGE

### Backend Changes

```
KEEP (Extend):
├── enhanced_sow.py → Add lock mechanism, PROJECT_SOW creation
├── sow_masters.py → Add deliverables_master endpoints
├── Object Storage → Reuse for proofs

CREATE NEW:
├── project_sow.py → PROJECT_SOW CRUD + Task management
├── tasks.py → Task CRUD under PROJECT_SOW
├── proof.py → Proof management (entity_type pattern)

COLLECTIONS:
├── enhanced_sow → Rename/migrate to sow_master
├── project_sow → Create new (link to sow_master)
├── tasks → Create new (link to project_sow)
├── proof_collection → Create new
├── deliverables_master → Create new
├── sow_domains → Extend sow_categories
```

### Frontend Changes

```
KEEP (Extend):
├── SOWBuilder.js → Add domain multi-select, deliverables
├── SalesSOWList.js → Minor updates
├── useSOW.js → Add new hooks

CREATE NEW:
├── ProjectSOWTab.js → New tab in Project detail
├── TaskManager.js → Task CRUD under SOW
├── ProofUpload.js → Reusable proof component

MODIFY:
├── ProjectDetail.js → Add SOW Delivery tab
├── ConsultingSOWList.js → Point to PROJECT_SOW
```

### Data Flow Change

```
CURRENT:
Lead → Pricing → SOW (enhanced_sow) → Kickoff → Project
                    ↓
              Consulting edits same SOW

PROPOSED:
Lead → Pricing → SOW_MASTER (locked after kickoff)
                    ↓
              Kickoff creates PROJECT_SOW (copy)
                    ↓
              Consulting works on PROJECT_SOW + TASKS
```

---

## 🚨 BREAKING CHANGES

| Change | What Breaks | Who Affected |
|--------|-------------|--------------|
| `enhanced_sow` → `sow_master` | All existing API calls | Frontend, Reports |
| Add `domains[]` (multi) | Single category logic | Filters, Reports |
| PROJECT_SOW separation | Consulting SOW list | ConsultingSOWList.js |
| Task system | Nothing (new) | N/A |
| Lock mechanism | Sales can't edit after kickoff | Sales team workflow |

---

## ✅ SAFE TO REUSE

| Component | Location | Reuse For |
|-----------|----------|-----------|
| Object Storage | `integration_playbook` | Proof uploads |
| SOWTable.jsx | `/components/sales/` | Display tables |
| sow_categories | DB collection | → sow_domains (extend) |
| sow_scope_templates | DB collection | AI suggestions |
| Status badges | UI components | Task/SOW status |
| RBAC checks | `deps.py` | Role enforcement |

---

## 📋 RECOMMENDED APPROACH

### Option A: Big Bang (Risky but Clean)
1. Build entire new system
2. Migrate data in one shot
3. Switch over completely

**Risk**: If migration fails, rollback is complex

### Option B: Incremental (Safer but Messier)
1. Add new collections alongside existing
2. Build new UI in parallel
3. Migrate gradually with feature flags
4. Deprecate old system after validation

**Risk**: Dual maintenance, confusion

### Option C: Hybrid (Recommended)
1. **Phase 1**: Add new collections (sow_master, project_sow, tasks, proof)
2. **Phase 2**: Build new API endpoints in NEW router (not modify enhanced_sow.py)
3. **Phase 3**: Build new UI tab in Project detail
4. **Phase 4**: Migrate existing data to sow_master
5. **Phase 5**: Update Sales SOW Builder to use sow_master
6. **Phase 6**: Deprecate enhanced_sow endpoints

**Risk**: Medium, but controlled

---

## ❓ QUESTIONS BEFORE PROCEEDING

1. **Existing SOWs**: Should existing `enhanced_sow` records become `sow_master` entries AND auto-create `project_sow` for any with `consulting_kickoff_complete=true`?

2. **Domain Multi-Select**: Should we migrate existing single `category` to `domains[category]` array?

3. **Deliverables**: Start with empty master or pre-seed with common deliverables per domain?

4. **Task Templates**: Create task templates per deliverable, or AI-only suggestions?

5. **Cutover Date**: Hard switch or gradual migration?

