# DVBC - NETRA Changelog

## Feb 15, 2026 — Real-Time Notifications
- In-app notification bell in header with unread badge and dropdown
- Browser push notifications via Web Notification API (polls every 15s)
- Admin auto-notified for: approval requests, leave requests, expenses, approval completions/rejections
- Failed logins excluded from notifications (per user request)
- Mark as read (individual + mark all) functionality
- Color-coded by type: amber=approval, blue=leave, purple=expense, green=approved, red=rejected

## Feb 15, 2026 — Login Activity Dashboard Widget
- Added Login Activity widget on admin Dashboard (recent logins, failed attempts, IP tracking)
- Widget shows success/failed counters and color-coded event badges

## Feb 15, 2026 — Login Page Redesign
- Updated login page with both methods equally visible (email/password + Google)
- Added company logo and "DVBC - NETRA" branding
- Clear guidance for Google Workspace vs non-Workspace users

## Feb 15, 2026 — Sidebar Navigation Overhaul
- Made sidebar sections collapsible (click chevron to expand/collapse)
- Compact design fitting more items on screen
- Added DVBC - NETRA branding to sidebar header
- All 5 domain sections accessible: My Workspace, HR, Sales, Consulting, Admin

## Feb 15, 2026 — Google Auth + Security Audit Log
- Google OAuth (Emergent Auth) with domain restriction to @dvconsulting.co.in
- Pre-registered users only (email must match existing employee record)
- Admin email/password fallback always available
- Admin OTP password reset (6-digit, 10-min expiry)
- Change Password endpoint for logged-in users
- Security Audit Log page (admin-only) with filterable table, Export CSV
- All auth events tracked: logins, failures, domain rejections, OTP, password changes
