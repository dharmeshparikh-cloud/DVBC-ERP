"""
Payments Router - Payment Verification for Sales-to-Consulting Handoff
Handles first installment verification before kickoff requests can be created
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from .models import PaymentVerification, PaymentVerificationCreate, User
from .deps import get_db, SALES_EXECUTIVE_ROLES
from .auth import get_current_user

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/verify-installment")
async def verify_installment_payment(
    payment_data: PaymentVerificationCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Verify first installment payment for an agreement.
    This is required before a kickoff request can be created.
    Also triggers SOW handover to consulting if this is the first installment.
    """
    db = get_db()
    
    # Only sales roles can verify payments
    if current_user.role not in SALES_EXECUTIVE_ROLES:
        raise HTTPException(status_code=403, detail="Only sales roles can verify payments")
    
    # Verify agreement exists
    agreement = await db.agreements.find_one({"id": payment_data.agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Check if payment for this installment already exists
    existing_payment = await db.payment_verifications.find_one({
        "agreement_id": payment_data.agreement_id,
        "installment_number": payment_data.installment_number
    })
    if existing_payment:
        raise HTTPException(status_code=400, detail=f"Payment for installment {payment_data.installment_number} already verified")
    
    # Validate transaction ID is not duplicated
    duplicate_txn = await db.payment_verifications.find_one({"transaction_id": payment_data.transaction_id})
    if duplicate_txn:
        raise HTTPException(status_code=400, detail="Transaction ID already exists in another payment record")
    
    # Create payment verification record
    payment = PaymentVerification(
        **payment_data.model_dump(),
        verified_by=current_user.id,
        verified_by_name=current_user.full_name
    )
    
    doc = payment.model_dump()
    doc['payment_date'] = doc['payment_date'].isoformat()
    doc['verified_at'] = doc['verified_at'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.payment_verifications.insert_one(doc)
    
    # Update agreement with payment info
    update_data = {
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if payment_data.installment_number == 1:
        update_data["first_installment_received"] = True
        update_data["first_installment_transaction_id"] = payment_data.transaction_id
        update_data["first_installment_amount"] = payment_data.received_amount
        update_data["first_installment_date"] = payment_data.payment_date.isoformat()
        update_data["first_installment_verified_by"] = current_user.id
        
        # Get pricing plan ID from agreement or quotation
        pricing_plan_id = agreement.get('pricing_plan_id') or payment_data.pricing_plan_id
        if not pricing_plan_id and agreement.get('quotation_id'):
            quotation = await db.quotations.find_one({"id": agreement['quotation_id']}, {"_id": 0})
            if quotation:
                pricing_plan_id = quotation.get('pricing_plan_id')
        
        # Trigger SOW handover when first installment is verified
        if pricing_plan_id:
            # Update enhanced_sow to mark as handed over to consulting
            await db.enhanced_sow.update_one(
                {"pricing_plan_id": pricing_plan_id},
                {"$set": {
                    "sales_handover_complete": True,
                    "sales_handover_at": datetime.now(timezone.utc).isoformat(),
                    "sales_handover_by": current_user.id,
                    "sales_handover_by_name": current_user.full_name,
                    "agreement_id": payment_data.agreement_id,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            update_data["sow_handover_complete"] = True
    
    await db.agreements.update_one(
        {"id": payment_data.agreement_id},
        {"$set": update_data}
    )
    
    return {
        "message": "Payment verified successfully",
        "payment_id": payment.id,
        "sow_handover_triggered": payment_data.installment_number == 1
    }


@router.get("/agreement/{agreement_id}")
async def get_agreement_payments(
    agreement_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all payment verifications for an agreement."""
    db = get_db()
    
    payments = await db.payment_verifications.find(
        {"agreement_id": agreement_id},
        {"_id": 0}
    ).sort("installment_number", 1).to_list(100)
    
    return payments


@router.get("/check-eligibility/{agreement_id}")
async def check_kickoff_eligibility(
    agreement_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if an agreement is eligible for kickoff request.
    Returns whether first installment has been verified.
    """
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Check if first installment is verified
    first_payment = await db.payment_verifications.find_one({
        "agreement_id": agreement_id,
        "installment_number": 1,
        "status": "verified"
    })
    
    # Check if SOW handover is complete
    sow_handover = False
    pricing_plan_id = agreement.get('pricing_plan_id')
    if not pricing_plan_id and agreement.get('quotation_id'):
        quotation = await db.quotations.find_one({"id": agreement['quotation_id']}, {"_id": 0})
        if quotation:
            pricing_plan_id = quotation.get('pricing_plan_id')
    
    if pricing_plan_id:
        enhanced_sow = await db.enhanced_sow.find_one(
            {"pricing_plan_id": pricing_plan_id},
            {"_id": 0, "sales_handover_complete": 1}
        )
        if enhanced_sow:
            sow_handover = enhanced_sow.get('sales_handover_complete', False)
    
    return {
        "agreement_id": agreement_id,
        "is_eligible": bool(first_payment),
        "first_installment_verified": bool(first_payment),
        "first_installment_transaction_id": first_payment.get('transaction_id') if first_payment else None,
        "first_installment_amount": first_payment.get('received_amount') if first_payment else None,
        "sow_handover_complete": sow_handover,
        "agreement_status": agreement.get('status')
    }


@router.delete("/{payment_id}")
async def delete_payment_verification(
    payment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a payment verification (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete payment records")
    
    payment = await db.payment_verifications.find_one({"id": payment_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    
    # Check if kickoff request exists for this agreement
    kickoff = await db.kickoff_requests.find_one({"agreement_id": payment['agreement_id']})
    if kickoff:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete payment - kickoff request already exists for this agreement"
        )
    
    await db.payment_verifications.delete_one({"id": payment_id})
    
    # Reset agreement payment fields if this was first installment
    if payment.get('installment_number') == 1:
        await db.agreements.update_one(
            {"id": payment['agreement_id']},
            {"$set": {
                "first_installment_received": False,
                "first_installment_transaction_id": None,
                "first_installment_amount": None,
                "first_installment_date": None,
                "first_installment_verified_by": None,
                "sow_handover_complete": False,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Reset SOW handover
        if payment.get('pricing_plan_id'):
            await db.enhanced_sow.update_one(
                {"pricing_plan_id": payment['pricing_plan_id']},
                {"$set": {
                    "sales_handover_complete": False,
                    "sales_handover_at": None,
                    "sales_handover_by": None,
                    "sales_handover_by_name": None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
    return {"message": "Payment record deleted"}
