# Backend Architecture - Strict Boundaries

## Module Responsibilities

### 1. `routers/auth.py` - Authentication ONLY
**Purpose:** Handle user authentication flows

**Contains:**
- `login()` - User login with JWT token generation
- `register()` - New user registration
- `get_me()` - Get current user profile
- `google_auth()` - Google OAuth integration
- `change_password()` - User password change
- `admin_reset_employee_password()` - Admin password reset
- `verify_password()` - Password verification helper
- `get_password_hash()` - Password hashing helper
- `create_access_token()` - JWT token creation
- `log_security_event()` - Security audit logging

**Does NOT contain:**
- `get_current_user` - Moved to deps.py
- Business logic
- Database queries beyond auth

---

### 2. `routers/deps.py` - Dependencies & Utilities
**Purpose:** Shared dependencies used across all routers

**Contains:**
- `get_current_user` - **CANONICAL** authentication dependency
- `get_current_user_from_token` - Alias for get_current_user
- `get_db()` - Database connection
- `PaginationParams` - Pagination parameter model
- `paginate_response()` - Pagination helper
- Role constants (ADMIN_ROLES, HR_ROLES, SALES_ROLES, etc.)
- `has_role()` - Role checking helper
- `get_role_group()` - Dynamic role group lookup
- `sanitize_text()` - Text sanitization
- `clean_mongo_doc()` - MongoDB document cleaning
- `api_response()` - Standardized API response helper

**Import Pattern:**
```python
from .deps import get_current_user, get_db, has_role, SALES_ROLES
```

---

### 3. `routers/models.py` - Pydantic Models ONLY
**Purpose:** Data models and schemas

**Contains:**
- User, Lead, Client, Meeting, etc. models
- Request/Response schemas
- Enums (UserRole, LeadStatus, etc.)

**Does NOT contain:**
- Business logic
- Database operations

---

### 4. `services/` - Business Logic
**Purpose:** Complex business logic separated from routes

**Current Services:**
- `email_service.py` - Email sending
- `cache_service.py` - Caching logic
- `redis_cache.py` - Redis operations
- `websocket_manager.py` - Real-time updates
- `bank_validation_service.py` - Bank account validation
- `integrity_scheduler.py` - Data integrity checks

---

### 5. `routers/*.py` - API Endpoints ONLY
**Purpose:** HTTP endpoint definitions

**Should:**
- Import `get_current_user` from `deps.py`
- Import `get_password_hash` from `auth.py` if needed
- Keep endpoint handlers thin
- Delegate complex logic to services

**Import Pattern:**
```python
from .deps import get_current_user, get_db, has_role, SALES_ROLES
from .auth import get_password_hash  # Only if needed
from .models import User, Lead
```

---

## Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────>│  auth.py    │────>│  Database   │
│   Login     │     │  login()    │     │   users     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    JWT Token (sub: user.id)
                           │
                           ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────>│  deps.py    │────>│  Database   │
│   Request   │     │  get_current│     │   users     │
│  + Token    │     │  _user()    │     │  (by id)    │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Migration Completed

### Files Modified (57 total):
All routers now import `get_current_user` from `deps.py` instead of `auth.py`.

### Breaking Change:
- `auth.py` no longer exports `get_current_user`
- All routers MUST use: `from .deps import get_current_user`

### Files that still import from auth.py (for get_password_hash only):
- `employees.py`
- `go_live.py`
- `users.py`

---

## Rules

1. **Never** add business logic to `auth.py` or `deps.py`
2. **Never** import `get_current_user` from `auth.py`
3. **Always** use `deps.py` for shared utilities
4. **Always** use `services/` for complex business logic
5. **Keep** routers thin - just HTTP handling
