"""
Utility functions for the Sangat Cafe ERP system
"""
from decimal import Decimal

def format_currency(amount, currency_symbol="₨"):
    """
    Format currency amounts with PKR symbol
    
    Args:
        amount: Numeric amount to format
        currency_symbol: Currency symbol (default: ₨ for PKR)
    
    Returns:
        Formatted currency string
    """
    if amount is None:
        return f"{currency_symbol}0.00"
    
    # Convert to Decimal for precise formatting
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    elif isinstance(amount, str):
        amount = Decimal(amount)
    
    # Format with commas and 2 decimal places
    formatted = f"{amount:,.2f}"
    return f"{currency_symbol}{formatted}"

def parse_currency(currency_string):
    """
    Parse currency string back to decimal value
    
    Args:
        currency_string: String like "₨1,234.56"
    
    Returns:
        Decimal value
    """
    if not currency_string:
        return Decimal('0.00')
    
    # Remove currency symbol and commas
    cleaned = currency_string.replace('₨', '').replace(',', '').strip()
    return Decimal(cleaned)

# Currency configuration
CURRENCY_SYMBOL = "₨"
CURRENCY_CODE = "PKR"
CURRENCY_NAME = "Pakistani Rupee"

# Tax rates
DEFAULT_TAX_RATE = Decimal('0.16')  # 16% GST in Pakistan
