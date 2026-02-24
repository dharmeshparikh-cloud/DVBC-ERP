# Self-Service Candidate Onboarding Module - Design Document

**Version:** 1.0  
**Date:** December 2025  
**Module:** HR Add-on  
**Status:** Design Phase

---

## Table of Contents

1. [Overview](#1-overview)
2. [Database Schema](#2-database-schema)
3. [API Endpoints](#3-api-endpoints)
4. [Email Templates](#4-email-templates)
5. [Security Considerations](#5-security-considerations)
6. [Workflow Diagram](#6-workflow-diagram)
7. [Frontend Components](#7-frontend-components)
8. [Integration Steps](#8-integration-steps)
9. [Audit Trail](#9-audit-trail)
10. [Implementation Phases](#10-implementation-phases)

---

## 1. Overview

### Purpose
Enable HR to send secure onboarding links to candidates, allowing them to self-submit personal information and documents before joining. This reduces manual data entry, ensures data accuracy, and streamlines the onboarding process.

### Key Features
- Secure, time-limited onboarding links
- Public-facing form (no authentication required for candidates)
- Document upload capability
- HR review and approval workflow
- Automatic employee record creation on approval
- Full audit trail

### User Roles
| Role | Capabilities |
|------|-------------|
| HR Admin | Send invites, review, approve/reject, edit submissions |
| HR Manager | Send invites, review, approve/reject |
| Candidate | Fill form, upload documents (public access via token) |

---

## 2. Database Schema

### 2.1 New Collections

#### `onboarding_invitations`
Stores invitation metadata and token information.

```javascript
{
  "id": "uuid",                          // Primary key
  "token": "string",                     // Secure random token (64 chars)
  "token_hash": "string",                // SHA-256 hash of token (for lookup)
  "candidate_email": "string",           // Email address
  "candidate_name": "string",            // Name (optional, for personalization)
  "position": "string",                  // Job position offered
  "department": "string",                // Target department
  "reporting_manager_id": "string",      // Assigned reporting manager
  "expected_joining_date": "date",       // Expected start date
  
  // Token lifecycle
  "status": "string",                    // pending | submitted | approved | rejected | expired | revoked
  "expires_at": "datetime",              // Token expiry (default: 7 days)
  "max_submissions": 1,                  // Allow resubmission count
  "submission_count": 0,                 // Current submission count
  
  // Tracking
  "sent_at": "datetime",                 // When email was sent
  "sent_by": "string",                   // HR user who sent
  "sent_by_name": "string",
  "first_accessed_at": "datetime",       // When candidate first opened link
  "submitted_at": "datetime",            // When form was submitted
  "ip_address": "string",                // Submission IP (for audit)
  "user_agent": "string",                // Browser info
  
  // Metadata
  "notes": "string",                     // HR notes
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### `onboarding_submissions`
Stores candidate-submitted data.

```javascript
{
  "id": "uuid",                          // Primary key
  "invitation_id": "string",             // FK to onboarding_invitations
  "token_hash": "string",                // For quick lookup
  
  // Personal Information
  "personal": {
    "first_name": "string",
    "last_name": "string",
    "date_of_birth": "date",
    "gender": "string",                  // male | female | other | prefer_not_to_say
    "blood_group": "string",
    "marital_status": "string",
    "nationality": "string",
    "personal_email": "string",
    "phone": "string",
    "alternate_phone": "string",
    "current_address": {
      "line1": "string",
      "line2": "string",
      "city": "string",
      "state": "string",
      "pincode": "string",
      "country": "string"
    },
    "permanent_address": {
      "line1": "string",
      "line2": "string",
      "city": "string",
      "state": "string",
      "pincode": "string",
      "country": "string"
    },
    "same_as_current": "boolean"
  },
  
  // Identity Documents
  "identity": {
    "pan_number": "string",
    "aadhaar_number": "string",          // Stored encrypted
    "passport_number": "string",
    "passport_expiry": "date",
    "driving_license": "string"
  },
  
  // Educational Qualifications
  "education": [
    {
      "degree": "string",                // e.g., B.Tech, MBA
      "specialization": "string",
      "institution": "string",
      "university": "string",
      "year_of_passing": "number",
      "percentage_cgpa": "string",
      "document_id": "string"            // Reference to uploaded document
    }
  ],
  
  // Employment History
  "employment_history": [
    {
      "company_name": "string",
      "designation": "string",
      "from_date": "date",
      "to_date": "date",
      "is_current": "boolean",
      "ctc": "number",
      "reason_for_leaving": "string",
      "hr_contact": "string",
      "document_id": "string"            // Experience/relieving letter
    }
  ],
  
  // Bank Details
  "bank_details": {
    "account_holder_name": "string",
    "account_number": "string",          // Stored encrypted
    "bank_name": "string",
    "branch": "string",
    "ifsc_code": "string",
    "account_type": "string"             // savings | current
  },
  
  // Emergency Contact
  "emergency_contact": {
    "name": "string",
    "relationship": "string",
    "phone": "string",
    "address": "string"
  },
  
  // Uploaded Documents (references to file storage)
  "documents": [
    {
      "id": "uuid",
      "type": "string",                  // photo | pan | aadhaar | education | experience | bank_proof | other
      "original_filename": "string",
      "stored_filename": "string",
      "file_path": "string",
      "file_size": "number",
      "mime_type": "string",
      "uploaded_at": "datetime"
    }
  ],
  
  // Declaration
  "declaration": {
    "agreed": "boolean",
    "agreed_at": "datetime",
    "ip_address": "string"
  },
  
  // Review workflow
  "status": "string",                    // submitted | under_review | approved | rejected | needs_revision
  "review": {
    "reviewed_by": "string",
    "reviewed_by_name": "string",
    "reviewed_at": "datetime",
    "comments": "string",
    "rejection_reason": "string",
    "revision_notes": "string"
  },
  
  // HR edits tracking
  "hr_modifications": [
    {
      "field": "string",
      "old_value": "any",
      "new_value": "any",
      "modified_by": "string",
      "modified_at": "datetime",
      "reason": "string"
    }
  ],
  
  // Result
  "employee_id": "string",               // Created employee ID (after approval)
  "employee_code": "string",             // Generated employee code
  
  // Metadata
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### `onboarding_audit_logs`
Dedicated audit trail for onboarding actions.

```javascript
{
  "id": "uuid",
  "invitation_id": "string",
  "submission_id": "string",
  "action": "string",                    // invite_sent | link_accessed | form_submitted | 
                                         // reviewed | approved | rejected | revoked | 
                                         // employee_created | notification_sent | document_uploaded
  "actor_type": "string",                // hr | candidate | system
  "actor_id": "string",                  // User ID or 'candidate'
  "actor_name": "string",
  "actor_email": "string",
  "details": {
    // Action-specific details
  },
  "ip_address": "string",
  "user_agent": "string",
  "timestamp": "datetime"
}
```

### 2.2 Indexes

```javascript
// onboarding_invitations
db.onboarding_invitations.createIndex({ "token_hash": 1 }, { unique: true });
db.onboarding_invitations.createIndex({ "candidate_email": 1 });
db.onboarding_invitations.createIndex({ "status": 1 });
db.onboarding_invitations.createIndex({ "expires_at": 1 });
db.onboarding_invitations.createIndex({ "sent_by": 1, "created_at": -1 });

// onboarding_submissions
db.onboarding_submissions.createIndex({ "invitation_id": 1 }, { unique: true });
db.onboarding_submissions.createIndex({ "token_hash": 1 });
db.onboarding_submissions.createIndex({ "status": 1 });
db.onboarding_submissions.createIndex({ "created_at": -1 });

// onboarding_audit_logs
db.onboarding_audit_logs.createIndex({ "invitation_id": 1, "timestamp": -1 });
db.onboarding_audit_logs.createIndex({ "submission_id": 1, "timestamp": -1 });
db.onboarding_audit_logs.createIndex({ "action": 1, "timestamp": -1 });
```

---

## 3. API Endpoints

### 3.1 HR Endpoints (Authenticated)

| Method | Endpoint | Description | Access |
|--------|----------|-------------|--------|
| POST | `/api/onboarding/invitations` | Send new onboarding invitation | HR_ROLES |
| GET | `/api/onboarding/invitations` | List all invitations with filters | HR_ROLES |
| GET | `/api/onboarding/invitations/{id}` | Get invitation details | HR_ROLES |
| DELETE | `/api/onboarding/invitations/{id}` | Revoke invitation | HR_ADMIN_ROLES |
| POST | `/api/onboarding/invitations/{id}/resend` | Resend invitation email | HR_ROLES |
| GET | `/api/onboarding/submissions` | List all submissions | HR_ROLES |
| GET | `/api/onboarding/submissions/{id}` | Get submission details | HR_ROLES |
| PATCH | `/api/onboarding/submissions/{id}` | HR edits submission | HR_ROLES |
| POST | `/api/onboarding/submissions/{id}/approve` | Approve & create employee | HR_ADMIN_ROLES |
| POST | `/api/onboarding/submissions/{id}/reject` | Reject submission | HR_ADMIN_ROLES |
| POST | `/api/onboarding/submissions/{id}/request-revision` | Ask candidate to revise | HR_ROLES |
| GET | `/api/onboarding/stats` | Dashboard statistics | HR_ROLES |
| GET | `/api/onboarding/audit-logs/{invitation_id}` | View audit trail | HR_ADMIN_ROLES |

### 3.2 Public Endpoints (Token-based)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/onboarding/verify/{token}` | Verify token validity | Token |
| GET | `/api/onboarding/form/{token}` | Get form structure & prefilled data | Token |
| POST | `/api/onboarding/submit/{token}` | Submit onboarding form | Token |
| POST | `/api/onboarding/upload/{token}` | Upload document | Token |
| GET | `/api/onboarding/status/{token}` | Check submission status | Token |

### 3.3 Endpoint Specifications

#### POST `/api/onboarding/invitations`
```json
// Request
{
  "candidate_email": "john.doe@email.com",
  "candidate_name": "John Doe",
  "position": "Senior Consultant",
  "department": "Consulting",
  "reporting_manager_id": "emp-123",
  "expected_joining_date": "2025-01-15",
  "expires_in_days": 7,
  "notes": "Referred by existing employee"
}

// Response
{
  "id": "inv-uuid-123",
  "token": "abc123...",  // Only returned once, not stored
  "onboarding_url": "https://netra.dvconsulting.co.in/onboarding/abc123...",
  "expires_at": "2025-01-10T00:00:00Z",
  "email_sent": true,
  "message": "Onboarding invitation sent successfully"
}
```

#### POST `/api/onboarding/submit/{token}`
```json
// Request
{
  "personal": { ... },
  "identity": { ... },
  "education": [ ... ],
  "employment_history": [ ... ],
  "bank_details": { ... },
  "emergency_contact": { ... },
  "declaration": {
    "agreed": true
  }
}

// Response
{
  "success": true,
  "submission_id": "sub-uuid-456",
  "message": "Your information has been submitted successfully. HR will review and contact you soon.",
  "reference_number": "ONB-2025-001234"
}
```

#### POST `/api/onboarding/submissions/{id}/approve`
```json
// Request
{
  "employee_id_prefix": "DVC",
  "department": "Consulting",
  "designation": "Senior Consultant",
  "ctc": 1500000,
  "joining_date": "2025-01-15",
  "work_location": "Mumbai",
  "reporting_manager_id": "emp-123",
  "notes": "Fast-tracked approval"
}

// Response
{
  "success": true,
  "employee_id": "emp-uuid-789",
  "employee_code": "DVC045",
  "message": "Employee record created successfully",
  "next_steps": [
    "IT assets provisioning",
    "Email account creation",
    "Workspace allocation"
  ]
}
```

---

## 4. Email Templates

### 4.1 Onboarding Invitation Email

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to DV Consulting - Complete Your Onboarding</title>
  <style>
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
    }
    .header {
      background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
      color: white;
      padding: 30px;
      text-align: center;
      border-radius: 8px 8px 0 0;
    }
    .header h1 {
      margin: 0;
      font-size: 24px;
    }
    .content {
      background: #ffffff;
      padding: 30px;
      border: 1px solid #e5e7eb;
      border-top: none;
    }
    .highlight-box {
      background: #f0f9ff;
      border-left: 4px solid #0284c7;
      padding: 15px 20px;
      margin: 20px 0;
      border-radius: 0 8px 8px 0;
    }
    .cta-button {
      display: inline-block;
      background: #0284c7;
      color: white !important;
      padding: 14px 32px;
      text-decoration: none;
      border-radius: 8px;
      font-weight: 600;
      margin: 20px 0;
    }
    .cta-button:hover {
      background: #0369a1;
    }
    .details-table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
    }
    .details-table td {
      padding: 10px;
      border-bottom: 1px solid #e5e7eb;
    }
    .details-table td:first-child {
      font-weight: 600;
      color: #6b7280;
      width: 40%;
    }
    .checklist {
      background: #f9fafb;
      padding: 20px;
      border-radius: 8px;
      margin: 20px 0;
    }
    .checklist h3 {
      margin-top: 0;
      color: #1e3a5f;
    }
    .checklist ul {
      margin: 0;
      padding-left: 20px;
    }
    .checklist li {
      margin: 8px 0;
    }
    .footer {
      background: #f9fafb;
      padding: 20px;
      text-align: center;
      font-size: 12px;
      color: #6b7280;
      border-radius: 0 0 8px 8px;
      border: 1px solid #e5e7eb;
      border-top: none;
    }
    .warning {
      background: #fef3c7;
      border: 1px solid #f59e0b;
      padding: 12px;
      border-radius: 6px;
      margin: 20px 0;
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Welcome to DV Consulting!</h1>
    <p style="margin: 10px 0 0 0; opacity: 0.9;">Complete Your Onboarding</p>
  </div>
  
  <div class="content">
    <p>Dear <strong>{{candidate_name}}</strong>,</p>
    
    <p>Congratulations on your offer to join DV Consulting as <strong>{{position}}</strong>! 
    We're excited to have you on board.</p>
    
    <div class="highlight-box">
      <strong>Next Step:</strong> Please complete your onboarding form by clicking the button below. 
      This will help us prepare everything for your first day.
    </div>
    
    <center>
      <a href="{{onboarding_url}}" class="cta-button">Complete Onboarding Form</a>
    </center>
    
    <table class="details-table">
      <tr>
        <td>Position</td>
        <td>{{position}}</td>
      </tr>
      <tr>
        <td>Department</td>
        <td>{{department}}</td>
      </tr>
      <tr>
        <td>Expected Joining Date</td>
        <td>{{expected_joining_date}}</td>
      </tr>
      <tr>
        <td>Link Valid Until</td>
        <td>{{expires_at}}</td>
      </tr>
    </table>
    
    <div class="checklist">
      <h3>Documents to Keep Ready</h3>
      <ul>
        <li>Passport-size photograph</li>
        <li>PAN Card</li>
        <li>Aadhaar Card</li>
        <li>Educational certificates (10th, 12th, Graduation, Post-graduation)</li>
        <li>Previous employment documents (Offer letters, Relieving letters, Payslips)</li>
        <li>Bank account details (Cancelled cheque or passbook copy)</li>
      </ul>
    </div>
    
    <div class="warning">
      <strong>Important:</strong> This link is unique to you and will expire on <strong>{{expires_at}}</strong>. 
      Please do not share this link with anyone.
    </div>
    
    <p>If you have any questions, please contact HR at 
    <a href="mailto:hr@dvconsulting.co.in">hr@dvconsulting.co.in</a>.</p>
    
    <p>We look forward to welcoming you!</p>
    
    <p>
      Best regards,<br>
      <strong>HR Team</strong><br>
      DV Consulting
    </p>
  </div>
  
  <div class="footer">
    <p>This is an automated message from NETRA ERP System.</p>
    <p>DV Consulting Pvt. Ltd. | Mumbai, India</p>
    <p style="margin-top: 10px;">
      If you did not expect this email, please ignore it or contact 
      <a href="mailto:hr@dvconsulting.co.in">hr@dvconsulting.co.in</a>
    </p>
  </div>
</body>
</html>
```

### 4.2 Submission Confirmation Email

```html
<!-- Subject: Your Onboarding Information Received - Reference #{{reference_number}} -->

<div class="header">
  <h1>Submission Received!</h1>
</div>

<div class="content">
  <p>Dear <strong>{{candidate_name}}</strong>,</p>
  
  <p>Thank you for completing your onboarding form. We have received your information successfully.</p>
  
  <div class="highlight-box">
    <strong>Reference Number:</strong> {{reference_number}}<br>
    <strong>Submitted On:</strong> {{submitted_at}}
  </div>
  
  <h3>What happens next?</h3>
  <ol>
    <li>Our HR team will review your submitted information</li>
    <li>You may be contacted if any clarification is needed</li>
    <li>Once approved, you'll receive your employee credentials</li>
    <li>Welcome kit and joining instructions will be sent before your start date</li>
  </ol>
  
  <p>Expected processing time: <strong>2-3 business days</strong></p>
</div>
```

### 4.3 Approval Notification Email

```html
<!-- Subject: Welcome Aboard! Your Onboarding is Complete - Employee ID: {{employee_code}} -->

<div class="header" style="background: linear-gradient(135deg, #059669 0%, #10b981 100%);">
  <h1>You're All Set!</h1>
</div>

<div class="content">
  <p>Dear <strong>{{candidate_name}}</strong>,</p>
  
  <p>Great news! Your onboarding has been approved, and you are now officially part of the DV Consulting family!</p>
  
  <table class="details-table">
    <tr>
      <td>Employee ID</td>
      <td><strong>{{employee_code}}</strong></td>
    </tr>
    <tr>
      <td>Designation</td>
      <td>{{designation}}</td>
    </tr>
    <tr>
      <td>Department</td>
      <td>{{department}}</td>
    </tr>
    <tr>
      <td>Reporting Manager</td>
      <td>{{reporting_manager_name}}</td>
    </tr>
    <tr>
      <td>Joining Date</td>
      <td>{{joining_date}}</td>
    </tr>
  </table>
  
  <div class="highlight-box">
    <strong>Your Login Credentials</strong><br>
    Portal: <a href="{{portal_url}}">{{portal_url}}</a><br>
    Username: {{employee_code}}<br>
    Temporary Password: Will be sent separately
  </div>
  
  <h3>First Day Instructions</h3>
  <ul>
    <li>Report to reception at 9:30 AM</li>
    <li>Carry original documents for verification</li>
    <li>HR will guide you through the orientation</li>
  </ul>
</div>
```

### 4.4 Rejection Notification Email

```html
<!-- Subject: Update on Your Application at DV Consulting -->

<div class="content">
  <p>Dear <strong>{{candidate_name}}</strong>,</p>
  
  <p>Thank you for your interest in joining DV Consulting and for taking the time to complete the onboarding process.</p>
  
  <p>After careful review, we regret to inform you that we are unable to proceed with your onboarding at this time.</p>
  
  {{#if rejection_reason}}
  <div class="highlight-box">
    <strong>Reason:</strong> {{rejection_reason}}
  </div>
  {{/if}}
  
  <p>We appreciate your understanding and wish you the best in your future endeavors. 
  Should circumstances change, we would be happy to reconnect.</p>
  
  <p>If you have any questions, please contact us at 
  <a href="mailto:hr@dvconsulting.co.in">hr@dvconsulting.co.in</a>.</p>
</div>
```

---

## 5. Security Considerations

### 5.1 Token Security

```python
# Token generation (64 characters, cryptographically secure)
import secrets
import hashlib

def generate_onboarding_token():
    """Generate a secure, unique onboarding token."""
    token = secrets.token_urlsafe(48)  # 64 chars
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash

# Token verification
def verify_token(token: str):
    """Verify token and check expiry."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    invitation = db.onboarding_invitations.find_one({
        "token_hash": token_hash,
        "status": {"$in": ["pending", "submitted"]},
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    return invitation
```

### 5.2 Security Measures

| Measure | Implementation |
|---------|----------------|
| **Token Expiry** | Default 7 days, configurable per invitation |
| **One-Time Use** | Token invalidated after successful submission (configurable) |
| **Rate Limiting** | 5 submissions per IP per hour |
| **CAPTCHA** | reCAPTCHA v3 on submission |
| **File Validation** | Whitelist extensions (pdf, jpg, png), max 5MB, virus scan |
| **Sensitive Data Encryption** | AES-256 for Aadhaar, bank account numbers |
| **HTTPS Only** | All endpoints enforce HTTPS |
| **CORS** | Restrict to company domain |
| **Input Sanitization** | XSS prevention, SQL injection (N/A for MongoDB) |
| **Audit Logging** | All actions logged with IP and user agent |

### 5.3 Data Privacy

```python
# Encryption for sensitive fields
from cryptography.fernet import Fernet

class SensitiveDataHandler:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()
    
    # Fields requiring encryption
    SENSITIVE_FIELDS = [
        "identity.aadhaar_number",
        "bank_details.account_number"
    ]
```

### 5.4 File Upload Security

```python
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_FILES_PER_SUBMISSION = 20

def validate_upload(file):
    # Check extension
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type .{ext} not allowed")
    
    # Check size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)")
    
    # Validate magic bytes (prevent extension spoofing)
    magic = file.read(8)
    file.seek(0)
    # ... validate magic bytes match extension
    
    return True
```

---

## 6. Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CANDIDATE ONBOARDING WORKFLOW                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   HR SENDS   │────▶│  CANDIDATE   │────▶│  CANDIDATE   │────▶│  HR REVIEWS  │
│  INVITATION  │     │ RECEIVES EMAIL│     │ FILLS FORM   │     │  SUBMISSION  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
       │                    │                    │                     │
       │                    │                    │                     │
       ▼                    ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Token Created│     │ Secure Link  │     │ Uploads Docs │     │    DECISION  │
│ Email Sent   │     │ Accessed     │     │ Submits Data │     │              │
│ Status:PENDING│     │ IP Logged    │     │Status:SUBMITTED│    │  ┌────┬────┐│
└──────────────┘     └──────────────┘     └──────────────┘     │  │    │    ││
                                                                │  ▼    │    ▼│
                                                         ┌─────┴──┐   │ ┌──┴────┐
                                                         │REVISION│   │ │REJECT │
                                                         │REQUIRED│   │ │       │
                                                         └────┬───┘   │ └───┬───┘
                                                              │       │     │
                                                              │       ▼     │
                                                              │ ┌──────────┐│
                                                              │ │ APPROVE  ││
                                                              │ │          ││
                                                              │ └────┬─────┘│
                                                              │      │      │
                                                              ▼      ▼      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                POST-DECISION                                 │
├─────────────────┬─────────────────────────────────────┬─────────────────────┤
│  NEEDS REVISION │           APPROVED                  │      REJECTED       │
├─────────────────┼─────────────────────────────────────┼─────────────────────┤
│ - Email sent    │ - Employee record created           │ - Rejection email   │
│ - Link reactivated│ - Employee code generated        │ - Status: REJECTED  │
│ - Can resubmit  │ - Credentials email sent            │ - Audit logged      │
│                 │ - Joins existing HR onboarding flow │                     │
│                 │ - Status: APPROVED                  │                     │
└─────────────────┴─────────────────────────────────────┴─────────────────────┘

                              AUDIT TRAIL
┌─────────────────────────────────────────────────────────────────────────────┐
│ invite_sent → link_accessed → document_uploaded (×N) → form_submitted →     │
│ reviewed → [approved|rejected|revision_requested] → employee_created        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 State Machine

```
┌─────────┐     send      ┌─────────┐     access    ┌──────────┐
│ (start) │─────────────▶│ PENDING │─────────────▶│ ACCESSED │
└─────────┘               └────┬────┘              └────┬─────┘
                               │                        │
                         expire│                  submit│
                               ▼                        ▼
                          ┌─────────┐            ┌───────────┐
                          │ EXPIRED │            │ SUBMITTED │
                          └─────────┘            └─────┬─────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────┐
                    │                                  │                  │
              request_revision                      approve             reject
                    ▼                                  ▼                  ▼
             ┌────────────┐                     ┌──────────┐       ┌──────────┐
             │ NEEDS_     │────resubmit───────▶│ APPROVED │       │ REJECTED │
             │ REVISION   │                     └──────────┘       └──────────┘
             └────────────┘
```

---

## 7. Frontend Components

### 7.1 HR Dashboard Components

```
/src/pages/onboarding/
├── OnboardingDashboard.js      # Main dashboard with stats & list
├── SendInvitation.js           # Modal to send new invitation
├── InvitationsList.js          # Table of all invitations
├── SubmissionReview.js         # Detailed submission review page
├── SubmissionEdit.js           # HR edit form
├── ApprovalDialog.js           # Approval confirmation with options
├── RejectionDialog.js          # Rejection with reason
└── AuditTrail.js               # Timeline of all actions

/src/pages/public/
└── CandidateOnboarding.js      # Public form (multi-step wizard)
```

### 7.2 Candidate Form Structure (Multi-step Wizard)

```
Step 1: Personal Information
├── Basic Details (Name, DOB, Gender, Blood Group)
├── Contact (Phone, Email)
└── Address (Current & Permanent)

Step 2: Identity Documents
├── PAN Number + Upload
├── Aadhaar Number + Upload
└── Passport (Optional) + Upload

Step 3: Educational Qualifications
├── Add multiple qualifications
└── Upload certificates for each

Step 4: Employment History
├── Add previous employers
├── Upload experience/relieving letters
└── Current employer notice period

Step 5: Bank Details
├── Account information
└── Upload cancelled cheque/passbook

Step 6: Emergency Contact
└── Contact person details

Step 7: Review & Declaration
├── Review all entered data
├── Edit option for each section
├── Declaration checkbox
└── Submit button
```

### 7.3 UI Wireframes

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ONBOARDING DASHBOARD                                          [+ Send Invite]│
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐        │
│  │    12       │ │     5       │ │     3       │ │     2       │        │
│  │  Pending    │ │  Submitted  │ │  Approved   │ │  Rejected   │        │
│  │  Invites    │ │  (Review)   │ │  (MTD)      │ │  (MTD)      │        │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘        │
├─────────────────────────────────────────────────────────────────────────┤
│ PENDING REVIEWS                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ Name          │ Position         │ Submitted  │ Status   │ Actions│  │
│ ├───────────────┼──────────────────┼────────────┼──────────┼────────│  │
│ │ John Doe      │ Sr. Consultant   │ 2 days ago │ ● Review │ [View] │  │
│ │ Jane Smith    │ Analyst          │ 1 day ago  │ ● Review │ [View] │  │
│ │ Mike Johnson  │ Manager          │ 3 hours ago│ ● New    │ [View] │  │
│ └───────────────┴──────────────────┴────────────┴──────────┴────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│ RECENT INVITATIONS                                                      │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ Email              │ Position     │ Sent       │ Status  │ Actions│  │
│ ├────────────────────┼──────────────┼────────────┼─────────┼────────│  │
│ │ abc@email.com      │ Developer    │ 5 days ago │ ⏳ Pending│[Resend]│  │
│ │ xyz@email.com      │ Designer     │ 1 week ago │ ❌ Expired│[Resend]│  │
│ └────────────────────┴──────────────┴────────────┴─────────┴────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Integration Steps

### 8.1 Backend Integration

#### Step 1: Create Router File
```
/app/backend/routers/onboarding.py
```

#### Step 2: Register Router in server.py
```python
# In server.py
from routers import onboarding

app.include_router(onboarding.router)
```

#### Step 3: Add RBAC Groups
```python
# In rbac_seeder.py, add:
ONBOARDING_ROLES = ["admin", "hr_manager", "hr_executive"]
```

#### Step 4: Create Email Templates
```
/app/backend/templates/
├── onboarding_invitation.html
├── onboarding_confirmation.html
├── onboarding_approved.html
└── onboarding_rejected.html
```

#### Step 5: Integrate with Employee Module
```python
# In onboarding.py approval endpoint
async def create_employee_from_submission(submission):
    """Convert approved submission to employee record."""
    
    employee_data = {
        "first_name": submission["personal"]["first_name"],
        "last_name": submission["personal"]["last_name"],
        "personal_email": submission["personal"]["personal_email"],
        # ... map all fields
    }
    
    # Use existing employee creation logic
    from routers.employees import create_employee_internal
    employee = await create_employee_internal(employee_data)
    
    return employee
```

### 8.2 Frontend Integration

#### Step 1: Add Routes
```javascript
// In App.js
<Route path="/hr/onboarding" element={<OnboardingDashboard />} />
<Route path="/hr/onboarding/review/:id" element={<SubmissionReview />} />
<Route path="/onboarding/:token" element={<CandidateOnboarding />} />  // Public
```

#### Step 2: Add Navigation
```javascript
// In Sidebar.js (HR section)
{
  name: 'Candidate Onboarding',
  href: '/hr/onboarding',
  icon: UserPlus,
  permission: 'onboarding.view'
}
```

#### Step 3: Add React Query Hooks
```javascript
// In useApi.js
export const useOnboardingStats = () => useQuery({...});
export const useOnboardingSubmissions = () => useQuery({...});
export const useSendOnboardingInvite = () => useMutation({...});
```

### 8.3 Database Setup

```javascript
// Run during deployment or manually
// Create indexes
db.onboarding_invitations.createIndex({ "token_hash": 1 }, { unique: true });
db.onboarding_invitations.createIndex({ "status": 1, "expires_at": 1 });
db.onboarding_submissions.createIndex({ "invitation_id": 1 });
db.onboarding_submissions.createIndex({ "status": 1 });
```

---

## 9. Audit Trail

### 9.1 Logged Events

| Event | Actor | Details Captured |
|-------|-------|------------------|
| `invite_sent` | HR | candidate_email, position, expires_at |
| `invite_resent` | HR | previous_sent_at, reason |
| `invite_revoked` | HR | reason |
| `link_accessed` | Candidate | ip_address, user_agent, first_access |
| `document_uploaded` | Candidate | file_type, file_size, filename |
| `form_submitted` | Candidate | submission_id, ip_address |
| `submission_viewed` | HR | viewer_id |
| `submission_edited` | HR | fields_changed, old_values, new_values |
| `revision_requested` | HR | revision_notes |
| `submission_approved` | HR | employee_id_created |
| `submission_rejected` | HR | rejection_reason |
| `notification_sent` | System | notification_type, recipient |

### 9.2 Audit Log Query Examples

```python
# Get full audit trail for an invitation
async def get_invitation_audit_trail(invitation_id: str):
    logs = await db.onboarding_audit_logs.find(
        {"invitation_id": invitation_id}
    ).sort("timestamp", 1).to_list(100)
    return logs

# Get HR user's recent actions
async def get_hr_audit_trail(user_id: str, days: int = 30):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    logs = await db.onboarding_audit_logs.find({
        "actor_id": user_id,
        "actor_type": "hr",
        "timestamp": {"$gte": since}
    }).sort("timestamp", -1).to_list(500)
    return logs
```

---

## 10. Implementation Phases

### Phase 1: Core Backend (3-4 days)
- [ ] Database schema creation & indexes
- [ ] Token generation & verification utilities
- [ ] Basic CRUD endpoints for invitations
- [ ] Email service integration
- [ ] Invitation email template

### Phase 2: Submission Handling (3-4 days)
- [ ] Public form data submission endpoint
- [ ] File upload endpoint with validation
- [ ] Submission storage & retrieval
- [ ] Confirmation email

### Phase 3: HR Review Flow (2-3 days)
- [ ] Submission listing & filtering
- [ ] Detailed view endpoint
- [ ] HR edit capability
- [ ] Approval/rejection endpoints

### Phase 4: Employee Integration (2 days)
- [ ] Employee creation from submission
- [ ] Link to existing onboarding flow
- [ ] Approval/rejection notifications

### Phase 5: Frontend - HR Dashboard (3-4 days)
- [ ] Dashboard with stats
- [ ] Invitation sending modal
- [ ] Submissions list & review pages
- [ ] Approval/rejection dialogs

### Phase 6: Frontend - Public Form (4-5 days)
- [ ] Multi-step wizard component
- [ ] Form validation
- [ ] File upload UI
- [ ] Review & submit step
- [ ] Success/error pages

### Phase 7: Testing & Polish (2-3 days)
- [ ] Unit tests for token handling
- [ ] Integration tests for workflow
- [ ] Security testing
- [ ] Email template refinement
- [ ] Error handling improvements

**Total Estimated Time: 3-4 weeks**

---

## Appendix A: API Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created (invitation sent, submission saved) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (invalid/missing token for HR endpoints) |
| 403 | Forbidden (token expired, revoked, or already used) |
| 404 | Not found (invalid token or submission ID) |
| 409 | Conflict (submission already exists for token) |
| 413 | File too large |
| 422 | Unprocessable entity (invalid file type) |
| 429 | Too many requests (rate limit exceeded) |

---

## Appendix B: Configuration Options

```python
# config.py
ONBOARDING_CONFIG = {
    "token_length": 48,
    "default_expiry_days": 7,
    "max_expiry_days": 30,
    "max_file_size_mb": 5,
    "max_files_per_submission": 20,
    "allowed_file_types": ["pdf", "jpg", "jpeg", "png"],
    "rate_limit_submissions_per_hour": 5,
    "enable_captcha": True,
    "auto_expire_check_interval_hours": 1,
    "send_reminder_before_expiry_days": 2,
}
```

---

**Document End**

*For implementation questions, contact the development team.*
