from typing import Dict, Any
from app.config import settings

class CurrencyService:
    """Currency conversion service for USD to GHS"""
    
    @classmethod
    def usd_to_ghs(cls, usd_amount: float) -> float:
        """Convert USD to GHS using fixed rate"""
        rate = settings.USD_TO_GHS_RATE
        return round(usd_amount * rate, 2)
    
    @classmethod
    def ghs_to_usd(cls, ghs_amount: float) -> float:
        """Convert GHS to USD using fixed rate"""
        rate = settings.USD_TO_GHS_RATE
        return round(ghs_amount / rate, 2)
    
    @classmethod
    def get_ghs_pricing(cls) -> Dict[str, Dict[str, Any]]:
        """Get subscription pricing tiers in both USD and GHS"""
        return {
            "solo": {
                "usd": 22.0,
                "ghs": cls.usd_to_ghs(22.0),
                "description": "Perfect for freelancers and individual projects",
                "analyses_limit": 50
            },
            "business": {
                "usd": 95.0, 
                "ghs": cls.usd_to_ghs(95.0),
                "description": "For consulting firms and small businesses",
                "analyses_limit": 200
            },
            "enterprise": {
                "usd": 500.0,  # Base enterprise pricing
                "ghs": cls.usd_to_ghs(500.0),
                "description": "Custom pricing for large organizations (GH₵ 8,000+ available)",
                "analyses_limit": 1000
            }
        }
    
    @classmethod
    def format_currency(cls, amount: float, currency: str = "GHS") -> str:
        """Format currency amount with proper symbol"""
        if currency.upper() == "GHS":
            return f"GH₵{amount:,.2f}"
        elif currency.upper() == "USD":
            return f"${amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    
    @classmethod
    def get_exchange_rate_info(cls) -> Dict[str, Any]:
        """Get current exchange rate information"""
        return {
            "rate": settings.USD_TO_GHS_RATE,
            "base": "USD",
            "target": "GHS",
            "last_updated": "Fixed rate configuration",
            "note": "Using fixed rate of 1 USD = 11.01 GHS as configured"
        }