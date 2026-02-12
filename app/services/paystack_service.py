import httpx
from typing import Optional, Dict, Any
from app.config import settings

class PaystackService:
    BASE_URL = "https://api.paystack.co"
    
    @classmethod
    async def initialize_payment(cls, email: str, amount_usd: float, reference: str, callback_url: str = None) -> Dict[str, Any]:
        """Initialize payment with Paystack (in GHS)"""
        try:
            # Convert USD to GHS using fixed rate from config
            amount_ghs = amount_usd * settings.USD_TO_GHS_RATE
            amount_kobo = int(amount_ghs * 100)  # Convert to kobo
            
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "email": email,
                "amount": amount_kobo,
                "reference": reference,
                "currency": "GHS"
            }
            
            if callback_url:
                payload["callback_url"] = callback_url
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{cls.BASE_URL}/transaction/initialize",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text}
                    
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    async def verify_payment(cls, reference: str) -> Dict[str, Any]:
        """Verify payment with Paystack"""
        try:
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.BASE_URL}/transaction/verify/{reference}",
                    headers=headers,
                    timeout=30.0
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}
    
    @classmethod
    async def get_transaction_history(cls, email: str = None, page: int = 1) -> Dict[str, Any]:
        """Get transaction history from Paystack"""
        try:
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"
            }
            
            params = {"perPage": 50, "page": page}
            if email:
                params["customer.email"] = email
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{cls.BASE_URL}/transaction",
                    headers=headers,
                    params=params,
                    timeout=30.0
                )
                
                return response.json() if response.status_code == 200 else {"error": response.text}
                
        except Exception as e:
            return {"error": str(e)}