# NETRA ERP Test Credentials

## Employee Login Credentials

### Admin
- **Employee ID:** ADMIN001
- **Password:** admin123
- **Role:** admin
- **Access:** Full system access

### HR Manager  
- **Employee ID:** DVC037
- **Password:** test123
- **Role:** hr_manager
- **Access:** HR department, employee management

### Principal Consultant
- **Employee ID:** DVC001
- **Password:** test123 (may need reset)
- **Role:** principal_consultant
- **Access:** Consulting department, kickoff approvals

### Sales Executive
- **Employee ID:** DVC034
- **Password:** test123 (may need reset)
- **Role:** executive
- **Access:** Sales funnel, leads management

## Client Portal
- Client portal uses separate authentication at /client-login
- Client IDs start with 98XXX format (e.g., 98000)
- Client credentials are created automatically during kickoff approval

## API Testing
```bash
# Login as Admin
curl -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"ADMIN001","password":"admin123"}'

# Use token in subsequent requests
curl -X GET "$API_URL/api/rbac/roles" \
  -H "Authorization: Bearer $TOKEN"
```

## Notes
- All passwords should be changed on first login in production
- Google OAuth is available for @dvconsulting.co.in domain accounts
- Default password for new employees is provided by HR
