"""
Utility functions for the ERP system
"""
from decimal import Decimal

def format_currency(amount, currency_code=None):
    """
    Format currency amounts with system currency
    
    Args:
        amount: Numeric amount to format
        currency_code: Currency code (defaults to system currency)
    
    Returns:
        Formatted currency string
    """
    from app.utils.currency_utils import format_currency as format_curr
    return format_curr(amount, currency_code)

def parse_currency(currency_string):
    """
    Parse currency string back to decimal value
    
    Args:
        currency_string: String like "₨1,234.56"
    
    Returns:
        Decimal value
    """
    from app.utils.currency_utils import parse_currency as parse_curr
    return parse_curr(currency_string)

def get_currency_symbol():
    """Get current system currency symbol"""
    from app.utils.currency_utils import get_currency_symbol as get_symbol
    return get_symbol()

# Legacy support - keep for backward compatibility
CURRENCY_SYMBOL = "₨"
CURRENCY_CODE = "PKR"
CURRENCY_NAME = "Pakistani Rupee"

# Tax rates
DEFAULT_TAX_RATE = Decimal('0.16')  # 16% GST in Pakistan
