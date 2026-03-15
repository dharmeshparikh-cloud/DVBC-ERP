"""
Excel Upload Router - Bulk Data Import
Handles Excel file uploads for bulk importing employees, attendance, and other data.
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import os
import io
import pandas as pd
from openpyxl import load_workbook

from .models import User
from .deps import get_db, get_role_group
from .deps import get_current_user

router = APIRouter(prefix="/excel-upload", tags=["Excel Upload"])

# Upload directory
UPLOAD_DIR = "/app/backend/uploads/excel"
os.makedirs(UPLOAD_DIR, exist_ok=True)

HR_ADMIN_ROLES = ["admin", "hr_manager", "hr_executive"]


@router.get("/templates")
async def get_upload_templates(current_user: User = Depends(get_current_user)):
    """Get list of available Excel templates for download."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR/Admin can access templates")
    
    templates = [
        {
            "id": "employees",
            "name": "Employee Master Import",
            "description": "Bulk import new employees",
            "columns": ["first_name", "last_name", "email", "phone", "department", "designation", 
                       "date_of_joining", "salary", "reporting_manager_id"],
            "required": ["first_name", "last_name", "email", "department", "designation", "date_of_joining"],
            "sample_data": [
                {"first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", 
                 "phone": "9876543210", "department": "Engineering", "designation": "Software Engineer",
                 "date_of_joining": "2024-01-15", "salary": 50000}
            ]
        },
        {
            "id": "attendance",
            "name": "Attendance Import",
            "description": "Bulk import attendance records",
            "columns": ["employee_id", "date", "status", "check_in_time", "check_out_time", "work_location"],
            "required": ["employee_id", "date", "status"],
            "valid_status": ["present", "absent", "half_day", "on_leave", "work_from_home"],
            "sample_data": [
                {"employee_id": "DVC001", "date": "2024-03-01", "status": "present", 
                 "check_in_time": "09:00", "check_out_time": "18:00", "work_location": "in_office"}
            ]
        },
        {
            "id": "leave_balance",
            "name": "Leave Balance Import",
            "description": "Bulk set leave balances",
            "columns": ["employee_id", "casual_leave", "sick_leave", "earned_leave", "comp_off"],
            "required": ["employee_id"],
            "sample_data": [
                {"employee_id": "DVC001", "casual_leave": 12, "sick_leave": 6, "earned_leave": 15, "comp_off": 0}
            ]
        },
        {
            "id": "salary_structure",
            "name": "Salary Structure Import",
            "description": "Bulk update salary structures",
            "columns": ["employee_id", "basic", "hra", "special_allowance", "conveyance", 
                       "medical_allowance", "pf_contribution", "professional_tax"],
            "required": ["employee_id", "basic"],
            "sample_data": [
                {"employee_id": "DVC001", "basic": 20000, "hra": 10000, "special_allowance": 15000}
            ]
        },
        {
            "id": "client_master",
            "name": "Client Master Import",
            "description": "Bulk import existing clients",
            "columns": ["company_name", "industry", "website", "city", "state", "country", 
                       "address", "primary_contact_name", "primary_contact_email", 
                       "primary_contact_phone", "primary_contact_designation", "contract_value", "notes"],
            "required": ["company_name"],
            "sample_data": [
                {"company_name": "ABC Industries", "industry": "Manufacturing", "website": "https://abc.com",
                 "city": "Mumbai", "state": "Maharashtra", "country": "India", "address": "123 Industrial Area",
                 "primary_contact_name": "John Smith", "primary_contact_email": "john@abc.com",
                 "primary_contact_phone": "9876543210", "primary_contact_designation": "CEO", "contract_value": 500000}
            ]
        }
    ]
    
    return {"templates": templates}


@router.get("/templates/{template_id}/download")
async def download_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Generate and return a template Excel file."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR/Admin can download templates")
    
    templates = {
        "employees": {
            "columns": ["first_name", "last_name", "email", "phone", "department", "designation", 
                       "date_of_joining", "salary", "reporting_manager_id", "gender", "date_of_birth"],
            "sample": [
                ["John", "Doe", "john.doe@example.com", "9876543210", "Engineering", 
                 "Software Engineer", "2024-01-15", 50000, "", "male", "1990-05-20"],
                ["Jane", "Smith", "jane.smith@example.com", "9876543211", "Sales", 
                 "Sales Executive", "2024-02-01", 35000, "", "female", "1992-08-15"]
            ]
        },
        "attendance": {
            "columns": ["employee_id", "date", "status", "check_in_time", "check_out_time", 
                       "work_location", "notes"],
            "sample": [
                ["DVC001", "2024-03-01", "present", "09:00", "18:00", "in_office", ""],
                ["DVC002", "2024-03-01", "work_from_home", "09:30", "18:30", "remote", "Client meeting"]
            ]
        },
        "leave_balance": {
            "columns": ["employee_id", "casual_leave", "sick_leave", "earned_leave", 
                       "comp_off", "maternity_leave", "paternity_leave"],
            "sample": [
                ["DVC001", 12, 6, 15, 0, 0, 0],
                ["DVC002", 10, 6, 12, 2, 0, 0]
            ]
        },
        "salary_structure": {
            "columns": ["employee_id", "annual_ctc", "basic", "hra", "special_allowance", 
                       "conveyance", "medical_allowance", "pf_contribution", "professional_tax"],
            "sample": [
                ["DVC001", 600000, 20000, 10000, 15000, 1600, 1250, 2400, 200],
                ["DVC002", 480000, 16000, 8000, 12000, 1600, 1000, 1920, 200]
            ]
        },
        "client_master": {
            "columns": ["company_name", "industry", "website", "city", "state", "country", 
                       "address", "primary_contact_name", "primary_contact_email", 
                       "primary_contact_phone", "primary_contact_designation", "contract_value", "notes"],
            "sample": [
                ["ABC Industries", "Manufacturing", "https://abc.com", "Mumbai", "Maharashtra", 
                 "India", "123 Industrial Area", "John Smith", "john@abc.com", "9876543210", "CEO", 500000, "Key client"],
                ["XYZ Tech", "IT/Software", "https://xyz.tech", "Bangalore", "Karnataka", 
                 "India", "Tech Park", "Jane Doe", "jane@xyz.tech", "9876543211", "CTO", 800000, "New client"]
            ]
        }
    }
    
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_id]
    
    # Create DataFrame
    df = pd.DataFrame(template["sample"], columns=template["columns"])
    
    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)
        
        # Add instructions sheet
        instructions = pd.DataFrame({
            'Instructions': [
                f'Template: {template_id}',
                'Fill in your data starting from row 2',
                'Required fields are marked with * in column headers',
                'Date format: YYYY-MM-DD',
                'Time format: HH:MM (24-hour)',
                'Do not modify column headers'
            ]
        })
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={template_id}_template.xlsx"
        }
    )


@router.post("/upload/{upload_type}")
async def upload_excel(
    upload_type: str,
    file: UploadFile = File(...),
    dry_run: bool = Form(default=True),
    current_user: User = Depends(get_current_user)
):
    """
    Upload and process Excel file for bulk import.
    
    - upload_type: employees, attendance, leave_balance, salary_structure
    - dry_run: If True, validates data without saving (default)
    """
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR/Admin can upload Excel files")
    
    valid_types = ["employees", "attendance", "leave_balance", "salary_structure", "client_master"]
    
    # Role check - client_master requires Admin/Finance
    if upload_type == "client_master":
        if current_user.role not in ["admin", "finance_manager", "finance_executive"]:
            raise HTTPException(status_code=403, detail="Only Admin/Finance can upload client data")
    elif current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR/Admin can upload Excel files")
    
    if upload_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid upload type. Must be one of: {valid_types}")
    
    # Validate file
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    # Read file
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents), sheet_name=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
    
    if df.empty:
        raise HTTPException(status_code=400, detail="Excel file is empty")
    
    # Process based on type
    db = get_db()
    
    if upload_type == "employees":
        return await process_employee_upload(db, df, dry_run, current_user)
    elif upload_type == "attendance":
        return await process_attendance_upload(db, df, dry_run, current_user)
    elif upload_type == "leave_balance":
        return await process_leave_balance_upload(db, df, dry_run, current_user)
    elif upload_type == "salary_structure":
        return await process_salary_structure_upload(db, df, dry_run, current_user)
    elif upload_type == "client_master":
        return await process_client_master_upload(db, df, dry_run, current_user)


async def process_employee_upload(db, df: pd.DataFrame, dry_run: bool, current_user: User):
    """Process employee bulk upload."""
    required_cols = ["first_name", "last_name", "email", "department", "designation", "date_of_joining"]
    
    # Validate columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_cols}")
    
    results = {"valid": [], "errors": [], "warnings": []}
    
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row number (1-indexed + header)
        errors = []
        warnings = []
        
        # Validate required fields
        for col in required_cols:
            if pd.isna(row.get(col)) or str(row.get(col)).strip() == "":
                errors.append(f"{col} is required")
        
        # Validate email format
        email = str(row.get("email", "")).strip().lower()
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("Invalid email format")
        
        # Check for duplicate email
        if email:
            existing = await db.employees.find_one({"email": email}, {"_id": 0, "id": 1})
            if existing:
                errors.append(f"Email {email} already exists")
        
        # Validate salary
        salary = row.get("salary")
        if salary and (not isinstance(salary, (int, float)) or salary < 0):
            errors.append("Invalid salary value")
        
        employee_data = {
            "first_name": str(row.get("first_name", "")).strip(),
            "last_name": str(row.get("last_name", "")).strip(),
            "email": email,
            "phone": str(row.get("phone", "")).strip() if pd.notna(row.get("phone")) else "",
            "department": str(row.get("department", "")).strip(),
            "designation": str(row.get("designation", "")).strip(),
            "date_of_joining": str(row.get("date_of_joining", "")).strip(),
            "salary": float(salary) if pd.notna(salary) else 0,
            "gender": str(row.get("gender", "")).strip().lower() if pd.notna(row.get("gender")) else "",
            "date_of_birth": str(row.get("date_of_birth", "")).strip() if pd.notna(row.get("date_of_birth")) else "",
        }
        
        if not salary or salary == 0:
            warnings.append("Salary is not set")
        
        if errors:
            results["errors"].append({
                "row": row_num,
                "data": employee_data,
                "errors": errors
            })
        else:
            results["valid"].append({
                "row": row_num,
                "data": employee_data,
                "warnings": warnings
            })
            if warnings:
                results["warnings"].append({"row": row_num, "warnings": warnings})
    
    # If not dry run, save valid records
    if not dry_run and results["valid"]:
        created_count = 0
        for item in results["valid"]:
            emp_data = item["data"]
            emp_data["id"] = str(uuid.uuid4())
            emp_data["employee_id"] = await generate_employee_id(db)
            emp_data["is_active"] = True
            emp_data["go_live_status"] = "pending"
            emp_data["created_at"] = datetime.now(timezone.utc).isoformat()
            emp_data["created_by"] = current_user.id
            
            await db.employees.insert_one(emp_data)
            created_count += 1
        
        return {
            "message": f"Successfully imported {created_count} employees",
            "created": created_count,
            "errors": len(results["errors"]),
            "error_details": results["errors"]
        }
    
    return {
        "dry_run": True,
        "message": "Validation complete. Set dry_run=false to import.",
        "valid_count": len(results["valid"]),
        "error_count": len(results["errors"]),
        "valid_records": results["valid"],
        "error_records": results["errors"]
    }


async def process_attendance_upload(db, df: pd.DataFrame, dry_run: bool, current_user: User):
    """Process attendance bulk upload."""
    required_cols = ["employee_id", "date", "status"]
    valid_statuses = ["present", "absent", "half_day", "on_leave", "work_from_home", "holiday"]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_cols}")
    
    results = {"valid": [], "errors": []}
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        errors = []
        
        emp_code = str(row.get("employee_id", "")).strip()
        date_val = str(row.get("date", "")).strip()
        status = str(row.get("status", "")).strip().lower()
        
        if not emp_code:
            errors.append("employee_id is required")
        if not date_val:
            errors.append("date is required")
        if not status:
            errors.append("status is required")
        elif status not in valid_statuses:
            errors.append(f"Invalid status. Must be one of: {valid_statuses}")
        
        # Validate employee exists
        if emp_code:
            emp = await db.employees.find_one({"employee_id": emp_code}, {"_id": 0, "id": 1})
            if not emp:
                errors.append(f"Employee {emp_code} not found")
        
        attendance_data = {
            "employee_code": emp_code,
            "employee_id": emp.get("id") if emp_code and not errors else None,
            "date": date_val,
            "status": status,
            "check_in_time": str(row.get("check_in_time", "")).strip() if pd.notna(row.get("check_in_time")) else None,
            "check_out_time": str(row.get("check_out_time", "")).strip() if pd.notna(row.get("check_out_time")) else None,
            "work_location": str(row.get("work_location", "in_office")).strip().lower() if pd.notna(row.get("work_location")) else "in_office",
            "notes": str(row.get("notes", "")).strip() if pd.notna(row.get("notes")) else ""
        }
        
        if errors:
            results["errors"].append({"row": row_num, "data": attendance_data, "errors": errors})
        else:
            results["valid"].append({"row": row_num, "data": attendance_data})
    
    if not dry_run and results["valid"]:
        created_count = 0
        updated_count = 0
        
        for item in results["valid"]:
            att_data = item["data"]
            
            # Check if record exists
            existing = await db.attendance.find_one({
                "employee_id": att_data["employee_id"],
                "date": att_data["date"]
            }, {"_id": 0, "id": 1})
            
            if existing:
                await db.attendance.update_one(
                    {"id": existing["id"]},
                    {"$set": {
                        "status": att_data["status"],
                        "check_in_time": att_data["check_in_time"],
                        "check_out_time": att_data["check_out_time"],
                        "work_location": att_data["work_location"],
                        "notes": att_data["notes"],
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "updated_by": current_user.id,
                        "source": "excel_upload"
                    }}
                )
                updated_count += 1
            else:
                att_data["id"] = str(uuid.uuid4())
                att_data["created_at"] = datetime.now(timezone.utc).isoformat()
                att_data["created_by"] = current_user.id
                att_data["source"] = "excel_upload"
                att_data["approval_status"] = "approved"  # Auto-approve bulk uploads
                await db.attendance.insert_one(att_data)
                created_count += 1
        
        return {
            "message": f"Successfully processed attendance: {created_count} created, {updated_count} updated",
            "created": created_count,
            "updated": updated_count,
            "errors": len(results["errors"]),
            "error_details": results["errors"]
        }
    
    return {
        "dry_run": True,
        "valid_count": len(results["valid"]),
        "error_count": len(results["errors"]),
        "valid_records": results["valid"],
        "error_records": results["errors"]
    }


async def process_leave_balance_upload(db, df: pd.DataFrame, dry_run: bool, current_user: User):
    """Process leave balance bulk upload."""
    if "employee_id" not in df.columns:
        raise HTTPException(status_code=400, detail="employee_id column is required")
    
    results = {"valid": [], "errors": []}
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        errors = []
        
        emp_code = str(row.get("employee_id", "")).strip()
        if not emp_code:
            errors.append("employee_id is required")
            results["errors"].append({"row": row_num, "errors": errors})
            continue
        
        emp = await db.employees.find_one({"employee_id": emp_code}, {"_id": 0, "id": 1})
        if not emp:
            errors.append(f"Employee {emp_code} not found")
            results["errors"].append({"row": row_num, "employee_id": emp_code, "errors": errors})
            continue
        
        balance_data = {
            "employee_id": emp["id"],
            "employee_code": emp_code,
            "casual": {"total": int(row.get("casual_leave", 0) or 0), "used": 0, "available": int(row.get("casual_leave", 0) or 0)},
            "sick": {"total": int(row.get("sick_leave", 0) or 0), "used": 0, "available": int(row.get("sick_leave", 0) or 0)},
            "earned": {"total": int(row.get("earned_leave", 0) or 0), "used": 0, "available": int(row.get("earned_leave", 0) or 0)},
            "comp_off": {"total": int(row.get("comp_off", 0) or 0), "used": 0, "available": int(row.get("comp_off", 0) or 0)}
        }
        
        results["valid"].append({"row": row_num, "data": balance_data})
    
    if not dry_run and results["valid"]:
        updated_count = 0
        for item in results["valid"]:
            bal = item["data"]
            await db.leave_balances.update_one(
                {"employee_id": bal["employee_id"]},
                {"$set": {
                    "casual": bal["casual"],
                    "sick": bal["sick"],
                    "earned": bal["earned"],
                    "comp_off": bal["comp_off"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "updated_by": current_user.id
                }},
                upsert=True
            )
            updated_count += 1
        
        return {
            "message": f"Successfully updated {updated_count} leave balances",
            "updated": updated_count,
            "errors": len(results["errors"])
        }
    
    return {
        "dry_run": True,
        "valid_count": len(results["valid"]),
        "error_count": len(results["errors"]),
        "valid_records": results["valid"],
        "error_records": results["errors"]
    }


async def process_salary_structure_upload(db, df: pd.DataFrame, dry_run: bool, current_user: User):
    """Process salary structure bulk upload."""
    if "employee_id" not in df.columns:
        raise HTTPException(status_code=400, detail="employee_id column is required")
    
    results = {"valid": [], "errors": []}
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        errors = []
        
        emp_code = str(row.get("employee_id", "")).strip()
        if not emp_code:
            errors.append("employee_id is required")
            results["errors"].append({"row": row_num, "errors": errors})
            continue
        
        emp = await db.employees.find_one({"employee_id": emp_code}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1})
        if not emp:
            errors.append(f"Employee {emp_code} not found")
            results["errors"].append({"row": row_num, "employee_id": emp_code, "errors": errors})
            continue
        
        # Build salary structure
        basic = float(row.get("basic", 0) or 0)
        if basic <= 0:
            errors.append("basic salary must be greater than 0")
            results["errors"].append({"row": row_num, "employee_id": emp_code, "errors": errors})
            continue
        
        salary_data = {
            "employee_id": emp["id"],
            "employee_code": emp_code,
            "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "annual_ctc": float(row.get("annual_ctc", 0) or 0),
            "components": {
                "basic": basic,
                "hra": float(row.get("hra", 0) or 0),
                "special_allowance": float(row.get("special_allowance", 0) or 0),
                "conveyance": float(row.get("conveyance", 0) or 0),
                "medical_allowance": float(row.get("medical_allowance", 0) or 0),
                "pf_contribution": float(row.get("pf_contribution", 0) or 0),
                "professional_tax": float(row.get("professional_tax", 0) or 0)
            }
        }
        
        results["valid"].append({"row": row_num, "data": salary_data})
    
    if not dry_run and results["valid"]:
        created_count = 0
        for item in results["valid"]:
            sal = item["data"]
            
            # Update employee salary
            monthly_gross = sum(v for k, v in sal["components"].items() if k not in ["pf_contribution", "professional_tax"])
            await db.employees.update_one(
                {"id": sal["employee_id"]},
                {"$set": {"salary": monthly_gross}}
            )
            
            # Create CTC structure
            ctc_record = {
                "id": str(uuid.uuid4()),
                "employee_id": sal["employee_id"],
                "employee_name": sal["employee_name"],
                "annual_ctc": sal["annual_ctc"] or (monthly_gross * 12),
                "components": sal["components"],
                "status": "active",
                "effective_month": datetime.now().strftime("%Y-%m"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": current_user.id,
                "source": "excel_upload"
            }
            
            # Deactivate previous structures
            await db.ctc_structures.update_many(
                {"employee_id": sal["employee_id"], "status": "active"},
                {"$set": {"status": "superseded"}}
            )
            
            await db.ctc_structures.insert_one(ctc_record)
            created_count += 1
        
        return {
            "message": f"Successfully created {created_count} salary structures",
            "created": created_count,
            "errors": len(results["errors"])
        }
    
    return {
        "dry_run": True,
        "valid_count": len(results["valid"]),
        "error_count": len(results["errors"]),
        "valid_records": results["valid"],
        "error_records": results["errors"]
    }


async def generate_employee_id(db) -> str:
    """Generate next employee ID."""
    last = await db.employees.find_one(
        {"employee_id": {"$regex": "^DVC"}},
        sort=[("employee_id", -1)]
    )
    
    if last and last.get("employee_id"):
        try:
            num = int(last["employee_id"].replace("DVC", ""))
            return f"DVC{num + 1:03d}"
        except (ValueError, TypeError):
            pass
    
    return "DVC001"


# Import regex for validation
import re



async def process_client_master_upload(db, df: pd.DataFrame, dry_run: bool, current_user: User):
    """Process client master bulk upload."""
    required_cols = ["company_name"]
    
    # Validate columns
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_cols}")
    
    results = {"valid": [], "errors": [], "warnings": []}
    
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row number (header is row 1)
        
        # Required field validation
        company_name = str(row.get("company_name", "")).strip()
        if not company_name:
            results["errors"].append({
                "row": row_num,
                "error": "company_name is required",
                "data": row.to_dict()
            })
            continue
        
        # Check for duplicate in existing data
        existing = await db.client_master.find_one({
            "company_name": {"$regex": f"^{re.escape(company_name)}$", "$options": "i"}
        })
        if existing:
            results["warnings"].append({
                "row": row_num,
                "warning": f"Client '{company_name}' already exists - will be skipped",
                "data": row.to_dict()
            })
            continue
        
        # Build contacts list if primary contact provided
        contacts = []
        primary_contact_name = str(row.get("primary_contact_name", "")).strip()
        if primary_contact_name:
            contacts.append({
                "id": str(uuid.uuid4()),
                "name": primary_contact_name,
                "email": str(row.get("primary_contact_email", "")).strip(),
                "phone": str(row.get("primary_contact_phone", "")).strip(),
                "designation": str(row.get("primary_contact_designation", "")).strip(),
                "is_primary": True,
                "added_by": current_user.id,
                "added_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Build valid record
        client_record = {
            "id": str(uuid.uuid4()),
            "company_name": company_name,
            "industry": str(row.get("industry", "")).strip() or "Other",
            "website": str(row.get("website", "")).strip(),
            "city": str(row.get("city", "")).strip(),
            "state": str(row.get("state", "")).strip(),
            "country": str(row.get("country", "India")).strip() or "India",
            "address": str(row.get("address", "")).strip(),
            "contacts": contacts,
            "revenue_history": [],
            "status": "active",
            "created_from": "excel_import",
            "created_by": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Add contract_value if provided
        contract_value = row.get("contract_value")
        if pd.notna(contract_value):
            try:
                client_record["contract_value"] = float(contract_value)
            except (ValueError, TypeError):
                pass
        
        # Add notes if provided
        notes = str(row.get("notes", "")).strip()
        if notes:
            client_record["notes"] = notes
        
        results["valid"].append({
            "row": row_num,
            "data": client_record
        })
    
    # If not dry run, insert records
    if not dry_run:
        created_count = 0
        for record in results["valid"]:
            await db.client_master.insert_one(record["data"])
            created_count += 1
        
        return {
            "message": f"Successfully imported {created_count} clients",
            "created": created_count,
            "warnings": len(results["warnings"]),
            "errors": len(results["errors"])
        }
    
    return {
        "dry_run": True,
        "valid_count": len(results["valid"]),
        "warning_count": len(results["warnings"]),
        "error_count": len(results["errors"]),
        "valid_records": results["valid"],
        "warning_records": results["warnings"],
        "error_records": results["errors"]
    }
