# NETRA ERP - Test Credentials Reference

## Quick Login (Simplified Employee IDs)

| Employee ID | Name | Role | Password |
|-------------|------|------|----------|
| `ADMIN001` | Anupam Sharma | Admin | `admin123` |
| `PC001` | Dharmesh Patel | Principal Consultant | `password123` |
| `SE001` | Rahul Verma | Sales Executive | `password123` |
| `SM001` | Priya Singh | Sales Manager | `password123` |
| `SC001` | Vikram Rao | Senior Consultant | `password123` |
| `HR001` | Meera Iyer | HR Manager | `password123` |

---

## Client Portal

| Client ID | Name | Company | Password |
|-----------|------|---------|----------|
| `98000` | Rajesh Kumar | E2E Test Company Ltd | `Client@123` |

**Client Portal URL:** `/client-login`

---

## Role Permissions Summary

| Action | Who Can Do It |
|--------|---------------|
| **Create Agreement** | Sales Executive (SE001), Sales Manager (SM001) |
| **Submit for Approval** | Creator of the agreement |
| **Approve Agreement** | Principal Consultant (PC001), Admin (ADMIN001) |
| **Send to Client** | Principal Consultant (PC001), Admin (ADMIN001) |
| **Approve Kickoff** | Principal Consultant (PC001), Admin (ADMIN001) |
| **Assign Consultants** | Principal Consultant (PC001), Senior Consultant (SC001), Admin |
| **Access All Projects** | Principal Consultant (PC001), Senior Consultant (SC001), Admin |

---

## Agreement Workflow

```
SE001 (Sales Executive) → Creates agreement (draft)
                        → Submits for approval (pending_approval)
                                    ↓
PC001 (Principal Consultant) → Approves (approved)
                                    ↓
PC001 (Principal Consultant) → Sends to client
```

---

## Additional Users (DVC Series)

These users also exist with Employee IDs `DVC001` to `DVC041`:

| Employee ID | Name | Role |
|-------------|------|------|
| `DVC001` | Komal Menon | Principal Consultant |
| `DVC002` | Shweta Sharma | Principal Consultant |
| `DVC008` | Naveen Naidu | Senior Consultant |
| `DVC013` | Ajay Bhat | Consultant |
| `DVC030` | Rekha Agarwal | Sales Manager |

**Password for all DVC users:** `password123`

---

## Login Examples

**Employee Login (POST /api/auth/login):**
```json
{"employee_id": "PC001", "password": "password123"}
```
or
```json
{"email": "dharmesh@dvbc.com", "password": "password123"}
```

**Client Login (POST /api/client-auth/login):**
```json
{"client_id": "98000", "password": "Client@123"}
```

---

*Last updated: February 23, 2026*
