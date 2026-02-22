"""
Travel Router - Travel reimbursements, distance calculations, location search
Extracted from server.py for better modularity and load performance.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
import uuid
import os
import math
import httpx
from routers.deps import get_db, oauth2_scheme, SECRET_KEY, ALGORITHM
from routers.models import User
from jose import JWTError, jwt

router = APIRouter(tags=["Travel"])

# Travel rates per km
TRAVEL_RATES = {
    "car": 7.0,
    "two_wheeler": 3.0,
    "public_transport": 0,
    "cab": 0
}

# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db = get_db()
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    return User(**user)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers using Haversine formula"""
    distance_meters = calculate_distance(lat1, lon1, lat2, lon2)
    return round(distance_meters / 1000, 2)


@router.get("/travel/rates")
async def get_travel_rates(current_user: User = Depends(get_current_user)):
    """Get current travel reimbursement rates"""
    return {
        "rates": TRAVEL_RATES,
        "description": {
            "car": "₹7 per km for personal car",
            "two_wheeler": "₹3 per km for bike/scooter",
            "public_transport": "Actual expense with receipt",
            "cab": "Actual expense with receipt"
        }
    }


@router.post("/travel/calculate-distance")
async def calculate_travel_distance(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate distance between two locations.
    Used by sales team for manual travel entries.
    """
    start = data.get("start_location", {})
    end = data.get("end_location", {})
    
    if not start.get("latitude") or not start.get("longitude"):
        raise HTTPException(status_code=400, detail="Start location coordinates required")
    if not end.get("latitude") or not end.get("longitude"):
        raise HTTPException(status_code=400, detail="End location coordinates required")
    
    distance = calculate_distance_km(
        start["latitude"], start["longitude"],
        end["latitude"], end["longitude"]
    )
    
    is_round_trip = data.get("is_round_trip", False)
    if is_round_trip:
        distance *= 2
    
    vehicle_type = data.get("vehicle_type", "car")
    rate = TRAVEL_RATES.get(vehicle_type, 0)
    
    calculated_amount = round(distance * rate, 2) if rate > 0 else 0
    
    return {
        "distance_km": distance,
        "is_round_trip": is_round_trip,
        "vehicle_type": vehicle_type,
        "rate_per_km": rate,
        "calculated_amount": calculated_amount,
        "requires_receipt": rate == 0
    }


@router.get("/travel/location-search")
async def search_locations(
    query: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Search for locations using Google Geocoding API.
    Used by sales team to find client meeting locations.
    """
    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "address": query,
                "key": GOOGLE_MAPS_API_KEY,
                "components": "country:IN",
                "language": "en"
            }
            
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=params,
                timeout=10.0
            )
            
            if response.status_code != 200:
                return {"results": [], "error": "Location service unavailable"}
            
            data = response.json()
            
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                return {"results": [], "error": data.get("error_message", f"API error: {data.get('status')}")}
            
            results = []
            
            for result in data.get("results", [])[:5]:
                geometry = result.get("geometry", {})
                location = geometry.get("location", {})
                
                address_components = result.get("address_components", [])
                name = result.get("formatted_address", "").split(",")[0]
                
                for comp in address_components:
                    types = comp.get("types", [])
                    if "point_of_interest" in types or "establishment" in types:
                        name = comp.get("long_name", name)
                        break
                    elif "sublocality_level_1" in types or "locality" in types:
                        name = comp.get("long_name", name)
                
                results.append({
                    "place_id": result.get("place_id", ""),
                    "name": name,
                    "address": result.get("formatted_address", ""),
                    "latitude": location.get("lat", 0),
                    "longitude": location.get("lng", 0),
                    "types": result.get("types", [])
                })
            
            return {"results": results}
            
    except Exception as e:
        return {"results": [], "error": str(e)}


@router.get("/travel/place-details/{place_id}")
async def get_place_details(
    place_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed place information including coordinates from Google Geocoding API.
    """
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    "place_id": place_id,
                    "key": GOOGLE_MAPS_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to get place details")
            
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                raise HTTPException(status_code=404, detail="Place not found")
            
            result = data["results"][0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            name = result.get("formatted_address", "").split(",")[0]
            
            return {
                "place_id": result.get("place_id"),
                "name": name,
                "address": result.get("formatted_address", ""),
                "latitude": location.get("lat", 0),
                "longitude": location.get("lng", 0)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/travel/reimbursement")
async def create_travel_reimbursement(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Create a travel reimbursement request.
    Supports both auto (from attendance) and manual entries.
    """
    db = get_db()
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found")
    
    start_location = data.get("start_location", {})
    end_location = data.get("end_location", {})
    
    if not start_location.get("latitude") or not end_location.get("latitude"):
        raise HTTPException(status_code=400, detail="Both start and end locations are required")
    
    distance = calculate_distance_km(
        start_location["latitude"], start_location["longitude"],
        end_location["latitude"], end_location["longitude"]
    )
    
    is_round_trip = data.get("is_round_trip", False)
    if is_round_trip:
        distance *= 2
    
    vehicle_type = data.get("vehicle_type", "car")
    rate = TRAVEL_RATES.get(vehicle_type, 0)
    calculated_amount = round(distance * rate, 2)
    
    actual_amount = data.get("actual_amount")
    final_amount = actual_amount if actual_amount else calculated_amount
    
    travel_record = {
        "id": str(uuid.uuid4()),
        "employee_id": employee["id"],
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "travel_date": data.get("travel_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "travel_type": data.get("travel_type", "manual"),
        "attendance_id": data.get("attendance_id"),
        "start_location": start_location,
        "end_location": end_location,
        "is_round_trip": is_round_trip,
        "distance_km": distance,
        "vehicle_type": vehicle_type,
        "rate_per_km": rate,
        "calculated_amount": calculated_amount,
        "actual_amount": actual_amount,
        "final_amount": final_amount,
        "client_id": data.get("client_id"),
        "client_name": data.get("client_name"),
        "project_id": data.get("project_id"),
        "project_name": data.get("project_name"),
        "status": "pending",
        "notes": data.get("notes"),
        "receipt": data.get("receipt"),
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.travel_reimbursements.insert_one(travel_record)
    
    return {
        "message": "Travel reimbursement request created",
        "id": travel_record["id"],
        "distance_km": distance,
        "calculated_amount": calculated_amount,
        "final_amount": final_amount
    }


@router.get("/travel/reimbursements")
async def get_travel_reimbursements(
    status: Optional[str] = None,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get travel reimbursement requests for current user or all (HR/Admin)"""
    db = get_db()
    query = {}
    
    if current_user.role not in ["admin", "hr_manager", "manager"]:
        employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
        if employee:
            query["employee_id"] = employee["id"]
    
    if status:
        query["status"] = status
    
    if month:
        query["travel_date"] = {"$regex": f"^{month}"}
    
    records = await db.travel_reimbursements.find(query, {"_id": 0, "receipt": 0}).sort("created_at", -1).to_list(500)
    
    total_distance = sum(r.get("distance_km", 0) for r in records)
    total_amount = sum(r.get("final_amount", 0) for r in records)
    pending_amount = sum(r.get("final_amount", 0) for r in records if r.get("status") == "pending")
    
    return {
        "records": records,
        "summary": {
            "total_records": len(records),
            "total_distance_km": round(total_distance, 2),
            "total_amount": round(total_amount, 2),
            "pending_amount": round(pending_amount, 2)
        }
    }


@router.get("/travel/reimbursements/{travel_id}")
async def get_travel_reimbursement(
    travel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific travel reimbursement record"""
    db = get_db()
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    return record


@router.post("/travel/reimbursements/{travel_id}/approve")
async def approve_travel_reimbursement(
    travel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve a travel reimbursement (HR/Admin only)"""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager", "manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin/Manager can approve")
    
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    if record["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    
    await db.travel_reimbursements.update_one(
        {"id": travel_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Travel reimbursement approved"}


@router.post("/travel/reimbursements/{travel_id}/reject")
async def reject_travel_reimbursement(
    travel_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """Reject a travel reimbursement (HR/Admin only)"""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager", "manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin/Manager can reject")
    
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    await db.travel_reimbursements.update_one(
        {"id": travel_id},
        {"$set": {
            "status": "rejected",
            "rejection_reason": data.get("reason", "Rejected") if data else "Rejected",
            "rejected_by": current_user.id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Travel reimbursement rejected"}


@router.post("/travel/reimbursements/{travel_id}/convert-to-expense")
async def convert_travel_to_expense(
    travel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Convert an approved travel reimbursement to an expense for payroll integration"""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can convert to expense")
    
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    if record["status"] != "approved":
        raise HTTPException(status_code=400, detail="Only approved requests can be converted")
    
    expense_id = f"TRV{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
    
    expense_doc = {
        "id": expense_id,
        "employee_id": record["employee_id"],
        "employee_name": record["employee_name"],
        "description": f"Travel Reimbursement: {record['start_location'].get('name', 'Start')} to {record['end_location'].get('name', 'End')}" + (" (Round Trip)" if record.get("is_round_trip") else ""),
        "category": "travel_reimbursement",
        "expense_date": record["travel_date"],
        "line_items": [{
            "description": f"Travel: {record['distance_km']} km @ ₹{record['rate_per_km']}/km ({record['vehicle_type']})",
            "category": "travel_reimbursement",
            "amount": record["final_amount"],
            "date": record["travel_date"]
        }],
        "total_amount": record["final_amount"],
        "status": "approved",
        "travel_reimbursement_id": travel_id,
        "client_id": record.get("client_id"),
        "client_name": record.get("client_name"),
        "project_id": record.get("project_id"),
        "project_name": record.get("project_name"),
        "notes": record.get("notes"),
        "created_by": current_user.id,
        "approved_by": current_user.id,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.expenses.insert_one(expense_doc)
    
    await db.travel_reimbursements.update_one(
        {"id": travel_id},
        {"$set": {
            "status": "linked_to_expense",
            "expense_id": expense_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Travel reimbursement converted to expense",
        "expense_id": expense_id,
        "amount": record["final_amount"]
    }


@router.get("/my/travel-reimbursements")
async def get_my_travel_reimbursements(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get current user's travel reimbursements"""
    db = get_db()
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        return {"records": [], "summary": {}}
    
    query = {"employee_id": employee["id"]}
    if month:
        query["travel_date"] = {"$regex": f"^{month}"}
    
    records = await db.travel_reimbursements.find(query, {"_id": 0, "receipt": 0}).sort("created_at", -1).to_list(200)
    
    total_distance = sum(r.get("distance_km", 0) for r in records)
    total_amount = sum(r.get("final_amount", 0) for r in records)
    pending_count = len([r for r in records if r.get("status") == "pending"])
    approved_count = len([r for r in records if r.get("status") == "approved"])
    
    return {
        "records": records,
        "summary": {
            "total_records": len(records),
            "pending_count": pending_count,
            "approved_count": approved_count,
            "total_distance_km": round(total_distance, 2),
            "total_amount": round(total_amount, 2)
        }
    }


@router.post("/attendance/{attendance_id}/calculate-travel")
async def calculate_attendance_travel(
    attendance_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate travel reimbursement from attendance record (for consultants).
    Uses check-in and check-out locations.
    """
    db = get_db()
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found")
    
    attendance = await db.attendance.find_one({"id": attendance_id}, {"_id": 0})
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    if attendance.get("employee_id") != employee["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this attendance")
    
    check_in_location = attendance.get("geo_location", {})
    check_out_location = attendance.get("check_out_location", {})
    
    if not check_in_location.get("latitude") or not check_out_location.get("latitude"):
        raise HTTPException(status_code=400, detail="Both check-in and check-out locations are required")
    
    home_location = data.get("home_location", {})
    
    vehicle_type = data.get("vehicle_type", "car")
    rate = TRAVEL_RATES.get(vehicle_type, 7.0)
    is_round_trip = data.get("is_round_trip", True)
    
    if home_location.get("latitude"):
        distance = calculate_distance_km(
            home_location["latitude"], home_location["longitude"],
            check_in_location["latitude"], check_in_location["longitude"]
        )
    else:
        distance = calculate_distance_km(
            check_in_location["latitude"], check_in_location["longitude"],
            check_out_location["latitude"], check_out_location["longitude"]
        )
    
    if is_round_trip:
        distance *= 2
    
    calculated_amount = round(distance * rate, 2)
    
    return {
        "attendance_id": attendance_id,
        "travel_date": attendance.get("date"),
        "check_in_location": {
            "latitude": check_in_location.get("latitude"),
            "longitude": check_in_location.get("longitude"),
            "address": check_in_location.get("address")
        },
        "check_out_location": {
            "latitude": check_out_location.get("latitude"),
            "longitude": check_out_location.get("longitude"),
            "address": check_out_location.get("address")
        },
        "distance_km": distance,
        "is_round_trip": is_round_trip,
        "vehicle_type": vehicle_type,
        "rate_per_km": rate,
        "calculated_amount": calculated_amount
    }


@router.get("/travel/stats")
async def get_travel_stats(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get travel reimbursement statistics (HR/Admin)"""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can view stats")
    
    query = {}
    if month:
        query["travel_date"] = {"$regex": f"^{month}"}
    
    records = await db.travel_reimbursements.find(query, {"_id": 0}).to_list(2000)
    
    total_records = len(records)
    pending = [r for r in records if r.get("status") == "pending"]
    approved = [r for r in records if r.get("status") == "approved"]
    
    total_distance = sum(r.get("distance_km", 0) for r in records)
    total_amount = sum(r.get("final_amount", 0) for r in records)
    pending_amount = sum(r.get("final_amount", 0) for r in pending)
    
    by_vehicle = {}
    for r in records:
        vt = r.get("vehicle_type", "unknown")
        if vt not in by_vehicle:
            by_vehicle[vt] = {"count": 0, "distance": 0, "amount": 0}
        by_vehicle[vt]["count"] += 1
        by_vehicle[vt]["distance"] += r.get("distance_km", 0)
        by_vehicle[vt]["amount"] += r.get("final_amount", 0)
    
    return {
        "total_records": total_records,
        "pending_count": len(pending),
        "approved_count": len(approved),
        "total_distance_km": round(total_distance, 2),
        "total_amount": round(total_amount, 2),
        "pending_amount": round(pending_amount, 2),
        "by_vehicle_type": by_vehicle
    }
