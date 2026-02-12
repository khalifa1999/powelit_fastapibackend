from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.models.user import User
from app.models.payment import Subscription
from app.models.schemas import SubscriptionResponse
from app.services.paystack_service import PaystackService
from app.services.currency_service import CurrencyService
from app.dependencies import get_active_user
import uuid
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

@router.get("/packages")
async def get_subscription_packages():
    """Get available subscription packages with pricing"""
    pricing = CurrencyService.get_ghs_pricing()
    exchange_info = CurrencyService.get_exchange_rate_info()
    
    return {
        "packages": pricing,
        "exchange_rate": exchange_info,
        "note": "All prices are displayed in both USD and Ghana Cedis (GHS)"
    }

@router.post("/subscribe", response_model=SubscriptionResponse)
async def initiate_subscription(
    tier: str,
    current_user: User = Depends(get_active_user)
):
    """Initiate subscription payment via Paystack"""
    
    # Get pricing for the tier
    pricing = CurrencyService.get_ghs_pricing()
    if tier not in pricing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subscription tier. Available tiers: {list(pricing.keys())}"
        )
    
    tier_info = pricing[tier]
    
    # Generate unique reference
    reference = f"sub_{uuid.uuid4().hex[:12]}"
    
    # Calculate subscription period (1 month from now)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    # Create subscription record
    subscription = Subscription(
        user_id=str(current_user.id),
        tier=tier,
        amount_usd=tier_info["usd"],
        amount_ghs=tier_info["ghs"],
        reference=reference,
        expires_at=expires_at
    )
    await subscription.save()
    
    # Initialize Paystack payment
    payment_result = await PaystackService.initialize_payment(
        email=current_user.email,
        amount_usd=tier_info["usd"],
        reference=reference,
        callback_url="https://your-app.com/payment-success"  # TODO: Update with frontend URL
    )
    
    if "error" in payment_result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment initialization failed: {payment_result['error']}"
        )
    
    return SubscriptionResponse(
        authorization_url=payment_result["data"]["authorization_url"],
        reference=payment_result["data"]["reference"],
        access_code=payment_result["data"]["access_code"]
    )

@router.get("/history")
async def get_payment_history(current_user: User = Depends(get_active_user)):
    """Get user's payment history"""
    
    # Get subscriptions from database
    subscriptions = await Subscription.find({"user_id": str(current_user.id)}).to_list()
    
    # Format response
    subscription_history = []
    for sub in subscriptions:
        subscription_history.append({
            "id": str(sub.id),
            "tier": sub.tier,
            "amount_usd": sub.amount_usd,
            "amount_ghs": sub.amount_ghs,
            "status": sub.status,
            "reference": sub.reference,
            "expires_at": sub.expires_at,
            "created_at": sub.created_at
        })
    
    return {
        "subscriptions": subscription_history,
        "total": len(subscription_history)
    }

@router.post("/webhook")
async def paystack_webhook(request: Request):
    """Paystack webhook endpoint (no security for MVP)"""
    
    try:
        # Get JSON data from request
        event = await request.json()
        
        if event.get("event") == "charge.success":
            data = event["data"]
            reference = data["reference"]
            
            # Find subscription by reference
            subscription = await Subscription.find_one({"reference": reference})
            if subscription:
                # Update subscription status
                subscription.status = "success"
                subscription.paystack_data = data
                await subscription.save()
                
                # Update user subscription
                user = await User.get(subscription.user_id)
                if user:
                    user.subscription_tier = subscription.tier
                    user.subscription_expires = subscription.expires_at
                    
                    # Update analysis limits based on tier
                    pricing = CurrencyService.get_ghs_pricing()
                    if subscription.tier in pricing:
                        user.analyses_limit = pricing[subscription.tier]["analyses_limit"]
                    
                    # Reset monthly usage
                    user.analyses_used = 0
                    await user.save()
                    
                    print(f"✅ User {user.email} upgraded to {subscription.tier} tier")
        
        elif event.get("event") == "charge.failed":
            data = event["data"]
            reference = data["reference"]
            
            # Update subscription status to failed
            subscription = await Subscription.find_one({"reference": reference})
            if subscription:
                subscription.status = "failed"
                subscription.paystack_data = data
                await subscription.save()
                
                print(f"❌ Payment failed for reference: {reference}")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "detail": str(e)}

@router.get("/verify/{reference}")
async def verify_payment_reference(reference: str):
    """Verify payment status by reference"""
    
    verification_result = await PaystackService.verify_payment(reference)
    
    if "error" in verification_result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment verification failed: {verification_result['error']}"
        )
    
    return verification_result

@router.post("/cancel")
async def cancel_subscription(
    reference: str,
    current_user: User = Depends(get_active_user)
):
    """Cancel pending subscription"""
    
    # Find subscription
    subscription = await Subscription.find_one({
        "reference": reference,
        "user_id": str(current_user.id),
        "status": "pending"
    })
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pending subscription not found"
        )
    
    # Mark as cancelled
    subscription.status = "cancelled"
    await subscription.save()
    
    return {"message": "Subscription cancelled successfully"}