# NETRA ERP - Test Credentials Reference

> **Password for ALL employees:** `password123`  
> **Password for Admin:** `admin123`  
> **Password for Clients:** `Client@123` (must change on first login)

---

## Quick Reference (One User Per Role)

| Role | Email | Password | Key Permissions |
|------|-------|----------|-----------------|
| **Admin** | `admin@company.com` | `admin123` | Full system access |
| **Principal Consultant** | `komal.menon87@dvconsulting.co.in` | `password123` | Approve agreements, kickoffs, client communications |
| **Sales Executive** | `arvind.mehta68@dvconsulting.co.in` | `password123` | Create leads, agreements (draft), quotations |
| **Sales Manager** | `rekha.agarwal96@dvconsulting.co.in` | `password123` | Manage sales team (cannot approve agreements) |
| **Senior Consultant** | `naveen.naidu54@dvconsulting.co.in` | `password123` | Consulting work, project assignments |
| **Consultant** | `ajay.bhat66@dvconsulting.co.in` | `password123` | Basic consulting tasks |
| **HR Manager** | `ashok.mittal41@dvconsulting.co.in` | `password123` | HR management |
| **Manager** | `arun.kumar73@dvconsulting.co.in` | `password123` | Team management |

---

## Client Portal

| Client ID | Name | Company | Password |
|-----------|------|---------|----------|
| `98000` | Rajesh Kumar | E2E Test Company Ltd | `Client@123` |

**Client Portal URL:** `/client-login`

---

## Role Hierarchy & Permissions

### Agreement Workflow
```
Sales Executive → Creates agreement (draft)
                → Submits for approval (pending_approval)
                         ↓
Principal Consultant/Admin → Approves (approved)
                         ↓
Principal Consultant/Admin → Sends to client
```

### Kickoff Approval Workflow
```
Sales Executive → Creates kickoff request
                         ↓
Principal Consultant → Internal approval (generates Project ID)
                         ↓
Client → External approval via email link (creates Client User)
```

### Who Can Do What?

| Action | Allowed Roles |
|--------|---------------|
| Create Agreement | All Sales roles |
| Submit Agreement for Approval | Creator |
| Approve/Reject Agreement | Principal Consultant, Admin |
| Send Agreement to Client | Principal Consultant, Admin |
| Approve Kickoff | Principal Consultant, Admin |
| Assign Consultants to Projects | Principal Consultant, Senior Consultant, Admin |
| Access All Projects Page | Principal Consultant, Senior Consultant, Admin |

---

## Login Endpoints

- **Employee Login:** `POST /api/auth/login`
  ```json
  {"email": "arvind.mehta68@dvconsulting.co.in", "password": "password123"}
  ```

- **Client Login:** `POST /api/client-auth/login`
  ```json
  {"client_id": "98000", "password": "Client@123"}
  ```

---

## All Available Test Users

### Admin (1)
- `admin@company.com` / `admin123`

### Principal Consultants (3)
- `komal.menon87@dvconsulting.co.in`
- `shweta.sharma54@dvconsulting.co.in`
- `deepika.iyer71@dvconsulting.co.in`

### Sales Executives (3)
- `arvind.mehta68@dvconsulting.co.in`
- `sunita.mishra54@dvconsulting.co.in`
- `seema.menon86@dvconsulting.co.in`

### Sales Managers (3)
- `rekha.agarwal96@dvconsulting.co.in`
- `jyoti.patil56@dvconsulting.co.in`
- `kiran.desai59@dvconsulting.co.in`

### Senior Consultants (3)
- `naveen.naidu54@dvconsulting.co.in`
- `yogesh.patel5@dvconsulting.co.in`
- `ritu.kumar2@dvconsulting.co.in`

### Consultants (3)
- `ajay.bhat66@dvconsulting.co.in`
- `ramesh.agarwal28@dvconsulting.co.in`
- `anjali.pillai94@dvconsulting.co.in`

### HR (2)
- `ashok.mittal41@dvconsulting.co.in` (HR Manager)
- `gaurav.choudhary13@dvconsulting.co.in` (HR Executive)

### Managers (2)
- `arun.kumar73@dvconsulting.co.in`
- `pallavi.rao57@dvconsulting.co.in`

---

*Last updated: February 23, 2026*
