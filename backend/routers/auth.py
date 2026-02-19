"""
Authentication Router - Login, Register, Password Management, Google Auth
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from typing import Optional
import os
import uuid
import random
import string
import httpx

from .models import User, UserCreate, UserLogin, Token
from .deps import get_db, sanitize_text, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 43200

# Google Auth Config
ALLOWED_DOMAIN = os.environ.get('ALLOWED_DOMAIN', 'dvconsulting.co.in')
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user from JWT token."""
    db = get_db()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_data = await db.users.find_one({"email": email}, {"_id": 0})
    if user_data is None:
        raise credentials_exception
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    return User(**user_data)


async def log_security_event(event_type: str, email: str = None, details: dict = None, request: Request = None):
    """Log a security event to the audit log collection."""
    db = get_db()
    log_entry = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "email": email,
        "details": details or {},
        "ip_address": request.client.host if request else None,
        "user_agent": request.headers.get("user-agent", "") if request else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.security_audit_logs.insert_one(log_entry)


# ============== Pydantic Models ==============

from pydantic import BaseModel, EmailStr

class GoogleAuthRequest(BaseModel):
    session_id: str


class OTPRequestModel(BaseModel):
    email: EmailStr


class OTPVerifyModel(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class ChangePasswordModel(BaseModel):
    current_password: str
    new_password: str


# ============== Endpoints ==============

@router.post("/register", response_model=User)
async def register(user_create: UserCreate):
    """Register a new user."""
    db = get_db()
    existing_user = await db.users.find_one({"email": user_create.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_create.model_dump(exclude={"password"})
    # Sanitize user input to prevent XSS
    if 'full_name' in user_dict:
        user_dict['full_name'] = sanitize_text(user_dict['full_name'])
    if 'department' in user_dict and user_dict['department']:
        user_dict['department'] = sanitize_text(user_dict['department'])
    
    user = User(**user_dict)
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['hashed_password'] = get_password_hash(user_create.password)
    
    await db.users.insert_one(doc)
    return user


@router.post("/login", response_model=Token)
async def login(user_login: UserLogin, request: Request = None):
    """Login with Employee ID or email and password."""
    db = get_db()
    
    user_data = None
    login_identifier = None
    
    # Priority: Employee ID > Email
    if user_login.employee_id:
        # Look up user by employee_id from employees collection
        employee = await db.employees.find_one({"employee_id": user_login.employee_id.upper()}, {"_id": 0})
        if employee:
            # Get linked user
            user_data = await db.users.find_one({"email": employee.get("email")}, {"_id": 0})
            login_identifier = user_login.employee_id
        else:
            # Also check if employee_id is stored directly in users (for admin/hr)
            user_data = await db.users.find_one({"employee_id": user_login.employee_id.upper()}, {"_id": 0})
            login_identifier = user_login.employee_id
    elif user_login.email:
        # Fallback to email login (for backward compatibility and admin users)
        user_data = await db.users.find_one({"email": user_login.email}, {"_id": 0})
        login_identifier = user_login.email
    else:
        raise HTTPException(status_code=400, detail="Employee ID or Email is required")
    
    if not user_data:
        await log_security_event("password_login_failed", email=login_identifier, details={"reason": "user_not_found"}, request=request)
        raise HTTPException(status_code=401, detail="Invalid Employee ID or password")

    # Check if account is active
    if not user_data.get("is_active", True):
        await log_security_event("password_login_failed", email=login_identifier, details={"reason": "account_disabled"}, request=request)
        raise HTTPException(status_code=401, detail="Your account has been disabled. Please contact HR.")

    if not verify_password(user_login.password, user_data.get('hashed_password', '')):
        await log_security_event("password_login_failed", email=login_identifier, details={"reason": "wrong_password"}, request=request)
        raise HTTPException(status_code=401, detail="Invalid Employee ID or password")

    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])

    # Check if first login (default password)
    requires_password_change = user_data.get('requires_password_change', False)
    
    user_data.pop('hashed_password', None)
    user = User(**user_data)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    await log_security_event("password_login_success", email=login_identifier, request=request)
    await db.users.update_one({"email": user.email}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat(), "auth_method": "password"}})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "requires_password_change": requires_password_change
    }


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.post("/google", response_model=Token)
async def google_auth(auth_req: GoogleAuthRequest, request: Request):
    """Authenticate via Google (Emergent Auth) - restricted to allowed domain, pre-registered users only."""
    db = get_db()
    
    # 1. Call Emergent Auth to get session data
    try:
        async with httpx.AsyncClient() as client_http:
            resp = await client_http.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": auth_req.session_id},
                timeout=10.0
            )
            if resp.status_code != 200:
                await log_security_event("google_login_failed", details={"reason": "emergent_auth_error", "status": resp.status_code}, request=request)
                raise HTTPException(status_code=401, detail="Google authentication failed")
            session_data = resp.json()
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach authentication service")

    google_email = session_data.get("email", "").lower()
    google_name = session_data.get("name", "")

    # 2. Domain restriction
    email_domain = google_email.split("@")[-1] if "@" in google_email else ""
    if email_domain != ALLOWED_DOMAIN:
        await log_security_event("google_login_rejected_domain", email=google_email, details={"domain": email_domain, "allowed": ALLOWED_DOMAIN}, request=request)
        raise HTTPException(status_code=403, detail=f"Access restricted to @{ALLOWED_DOMAIN} accounts only")

    # 3. Pre-registered check — user must exist in DB
    user_data = await db.users.find_one({"email": google_email}, {"_id": 0})
    if not user_data:
        await log_security_event("google_login_rejected_unregistered", email=google_email, request=request)
        raise HTTPException(status_code=403, detail="Your account is not registered. Please contact your administrator.")

    if not user_data.get("is_active", True):
        await log_security_event("google_login_rejected_inactive", email=google_email, request=request)
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact your administrator.")

    # 4. Update google profile info if available
    update_fields = {"last_login": datetime.now(timezone.utc).isoformat(), "auth_method": "google"}
    if google_name and not user_data.get("full_name"):
        update_fields["full_name"] = sanitize_text(google_name)
    if session_data.get("picture"):
        update_fields["google_picture"] = session_data["picture"]
    await db.users.update_one({"email": google_email}, {"$set": update_fields})

    # 5. Issue JWT token (same as password login)
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    user_data.pop('hashed_password', None)
    user = User(**user_data)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    await log_security_event("google_login_success", email=google_email, request=request)
    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/admin/request-otp")
async def request_admin_otp(otp_req: OTPRequestModel, request: Request):
    """Generate an OTP for admin password reset. Only admin-role users can request OTP."""
    db = get_db()
    user_data = await db.users.find_one({"email": otp_req.email}, {"_id": 0})
    if not user_data:
        await log_security_event("otp_request_failed", email=otp_req.email, details={"reason": "user_not_found"}, request=request)
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get("role") != "admin":
        await log_security_event("otp_request_rejected", email=otp_req.email, details={"reason": "not_admin"}, request=request)
        raise HTTPException(status_code=403, detail="OTP password reset is only available for admin accounts")

    # Generate 6-digit OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    await db.otp_tokens.delete_many({"email": otp_req.email})
    await db.otp_tokens.insert_one({
        "email": otp_req.email,
        "otp": otp_code,
        "expires_at": otp_expiry.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    await log_security_event("otp_generated", email=otp_req.email, details={"otp_code": otp_code}, request=request)
    # In production, send OTP via email/SMS. For now, return it (admin can view in audit log)
    return {"message": "OTP generated successfully", "otp": otp_code, "expires_in_minutes": 10}


@router.post("/admin/reset-password")
async def reset_admin_password(otp_verify: OTPVerifyModel, request: Request):
    """Verify OTP and reset admin password."""
    db = get_db()
    otp_record = await db.otp_tokens.find_one({"email": otp_verify.email, "otp": otp_verify.otp}, {"_id": 0})
    if not otp_record:
        await log_security_event("otp_verify_failed", email=otp_verify.email, details={"reason": "invalid_otp"}, request=request)
        raise HTTPException(status_code=400, detail="Invalid OTP")

    expires_at = datetime.fromisoformat(otp_record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.otp_tokens.delete_many({"email": otp_verify.email})
        await log_security_event("otp_verify_failed", email=otp_verify.email, details={"reason": "otp_expired"}, request=request)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if len(otp_verify.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_hash = get_password_hash(otp_verify.new_password)
    await db.users.update_one({"email": otp_verify.email}, {"$set": {"hashed_password": new_hash}})
    await db.otp_tokens.delete_many({"email": otp_verify.email})

    await log_security_event("password_reset_success", email=otp_verify.email, request=request)
    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(pwd_data: ChangePasswordModel, current_user: User = Depends(get_current_user), request: Request = None):
    """Change password for current user (admin only, since employees use Google)."""
    db = get_db()
    user_data = await db.users.find_one({"email": current_user.email}, {"_id": 0})
    if not user_data or not user_data.get("hashed_password"):
        raise HTTPException(status_code=400, detail="No password set for this account")

    if not verify_password(pwd_data.current_password, user_data["hashed_password"]):
        await log_security_event("password_change_failed", email=current_user.email, details={"reason": "wrong_current_password"}, request=request)
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(pwd_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_hash = get_password_hash(pwd_data.new_password)
    await db.users.update_one({"email": current_user.email}, {"$set": {"hashed_password": new_hash}})

    await log_security_event("password_change_success", email=current_user.email, request=request)
    return {"message": "Password changed successfully"}



# ============== Admin Password Management ==============

class AdminResetPasswordModel(BaseModel):
    employee_id: str
    new_password: str


class AdminToggleAccessModel(BaseModel):
    employee_id: str
    is_active: bool


@router.post("/admin/reset-employee-password")
async def admin_reset_employee_password(
    data: AdminResetPasswordModel, 
    current_user: User = Depends(get_current_user), 
    request: Request = None
):
    """Reset password for an employee. Only Admin and HR Managers can do this."""
    db = get_db()
    
    # Check if current user is Admin or HR Manager
    is_admin = current_user.role == "admin"
    is_hr = current_user.role == "hr_manager" or (current_user.department and "HR" in current_user.department.upper())
    
    if not (is_admin or is_hr):
        await log_security_event("admin_password_reset_rejected", email=current_user.email, details={"reason": "not_authorized", "target": data.employee_id}, request=request)
        raise HTTPException(status_code=403, detail="Only Admin and HR Managers can reset passwords")
    
    # Find the employee
    employee = await db.employees.find_one({"employee_id": data.employee_id.upper()}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find the linked user
    user_data = await db.users.find_one({"email": employee.get("email")}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="No user account found for this employee")
    
    # Prevent non-admin from resetting admin passwords
    if user_data.get("role") == "admin" and not is_admin:
        raise HTTPException(status_code=403, detail="Only Admin can reset another Admin's password")
    
    # Validate password
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Reset password
    new_hash = get_password_hash(data.new_password)
    await db.users.update_one(
        {"email": employee.get("email")}, 
        {"$set": {
            "hashed_password": new_hash,
            "requires_password_change": True,
            "password_reset_at": datetime.now(timezone.utc).isoformat(),
            "password_reset_by": current_user.email
        }}
    )
    
    await log_security_event(
        "admin_password_reset_success", 
        email=current_user.email, 
        details={"target_employee": data.employee_id, "target_email": employee.get("email")}, 
        request=request
    )
    
    return {"message": f"Password reset successfully for {employee.get('first_name')} {employee.get('last_name')}", "employee_id": data.employee_id}


@router.post("/admin/toggle-employee-access")
async def admin_toggle_employee_access(
    data: AdminToggleAccessModel, 
    current_user: User = Depends(get_current_user), 
    request: Request = None
):
    """Enable or disable employee access. Only Admin and HR Managers can do this."""
    db = get_db()
    
    # Check if current user is Admin or HR Manager
    is_admin = current_user.role == "admin"
    is_hr = current_user.role == "hr_manager" or (current_user.department and "HR" in current_user.department.upper())
    
    if not (is_admin or is_hr):
        await log_security_event("admin_toggle_access_rejected", email=current_user.email, details={"reason": "not_authorized", "target": data.employee_id}, request=request)
        raise HTTPException(status_code=403, detail="Only Admin and HR Managers can toggle employee access")
    
    # Find the employee
    employee = await db.employees.find_one({"employee_id": data.employee_id.upper()}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find the linked user
    user_data = await db.users.find_one({"email": employee.get("email")}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="No user account found for this employee")
    
    # Prevent disabling admin accounts (except by other admins)
    if user_data.get("role") == "admin":
        raise HTTPException(status_code=403, detail="Cannot disable Admin accounts")
    
    # Toggle access
    await db.users.update_one(
        {"email": employee.get("email")}, 
        {"$set": {
            "is_active": data.is_active,
            "access_modified_at": datetime.now(timezone.utc).isoformat(),
            "access_modified_by": current_user.email
        }}
    )
    
    # Also update employee record
    await db.employees.update_one(
        {"employee_id": data.employee_id.upper()},
        {"$set": {"is_active": data.is_active}}
    )
    
    action = "enabled" if data.is_active else "disabled"
    await log_security_event(
        f"admin_access_{action}", 
        email=current_user.email, 
        details={"target_employee": data.employee_id, "target_email": employee.get("email")}, 
        request=request
    )
    
    return {"message": f"Access {action} for {employee.get('first_name')} {employee.get('last_name')}", "employee_id": data.employee_id, "is_active": data.is_active}
