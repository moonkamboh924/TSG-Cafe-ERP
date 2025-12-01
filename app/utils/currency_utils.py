"""
Currency utility functions for multi-currency support
"""
from decimal import Decimal

# Comprehensive currency configuration for Asian and global currencies
CURRENCIES = {
    # Pakistani & South Asian
    'PKR': {'symbol': '₨', 'name': 'Pakistani Rupee', 'decimal_places': 2, 'position': 'before'},
    'INR': {'symbol': '₹', 'name': 'Indian Rupee', 'decimal_places': 2, 'position': 'before'},
    'BDT': {'symbol': '৳', 'name': 'Bangladeshi Taka', 'decimal_places': 2, 'position': 'before'},
    'LKR': {'symbol': 'Rs', 'name': 'Sri Lankan Rupee', 'decimal_places': 2, 'position': 'before'},
    'NPR': {'symbol': 'रू', 'name': 'Nepalese Rupee', 'decimal_places': 2, 'position': 'before'},
    'AFN': {'symbol': '؋', 'name': 'Afghan Afghani', 'decimal_places': 2, 'position': 'before'},
    'MVR': {'symbol': 'Rf', 'name': 'Maldivian Rufiyaa', 'decimal_places': 2, 'position': 'before'},
    
    # Middle East
    'AED': {'symbol': 'د.إ', 'name': 'UAE Dirham', 'decimal_places': 2, 'position': 'before'},
    'SAR': {'symbol': '﷼', 'name': 'Saudi Riyal', 'decimal_places': 2, 'position': 'before'},
    'QAR': {'symbol': 'ر.ق', 'name': 'Qatari Riyal', 'decimal_places': 2, 'position': 'before'},
    'OMR': {'symbol': 'ر.ع.', 'name': 'Omani Rial', 'decimal_places': 3, 'position': 'before'},
    'KWD': {'symbol': 'د.ك', 'name': 'Kuwaiti Dinar', 'decimal_places': 3, 'position': 'before'},
    'BHD': {'symbol': 'د.ب', 'name': 'Bahraini Dinar', 'decimal_places': 3, 'position': 'before'},
    'IQD': {'symbol': 'ع.د', 'name': 'Iraqi Dinar', 'decimal_places': 3, 'position': 'before'},
    'JOD': {'symbol': 'د.ا', 'name': 'Jordanian Dinar', 'decimal_places': 3, 'position': 'before'},
    'LBP': {'symbol': 'ل.ل', 'name': 'Lebanese Pound', 'decimal_places': 2, 'position': 'before'},
    'SYP': {'symbol': '£S', 'name': 'Syrian Pound', 'decimal_places': 2, 'position': 'before'},
    
    # East Asia
    'CNY': {'symbol': '¥', 'name': 'Chinese Yuan', 'decimal_places': 2, 'position': 'before'},
    'JPY': {'symbol': '¥', 'name': 'Japanese Yen', 'decimal_places': 0, 'position': 'before'},
    'KRW': {'symbol': '₩', 'name': 'South Korean Won', 'decimal_places': 0, 'position': 'before'},
    'TWD': {'symbol': 'NT$', 'name': 'Taiwan Dollar', 'decimal_places': 2, 'position': 'before'},
    'HKD': {'symbol': 'HK$', 'name': 'Hong Kong Dollar', 'decimal_places': 2, 'position': 'before'},
    'MOP': {'symbol': 'MOP$', 'name': 'Macanese Pataca', 'decimal_places': 2, 'position': 'before'},
    
    # Southeast Asia
    'THB': {'symbol': '฿', 'name': 'Thai Baht', 'decimal_places': 2, 'position': 'before'},
    'MYR': {'symbol': 'RM', 'name': 'Malaysian Ringgit', 'decimal_places': 2, 'position': 'before'},
    'SGD': {'symbol': 'S$', 'name': 'Singapore Dollar', 'decimal_places': 2, 'position': 'before'},
    'IDR': {'symbol': 'Rp', 'name': 'Indonesian Rupiah', 'decimal_places': 0, 'position': 'before'},
    'PHP': {'symbol': '₱', 'name': 'Philippine Peso', 'decimal_places': 2, 'position': 'before'},
    'VND': {'symbol': '₫', 'name': 'Vietnamese Dong', 'decimal_places': 0, 'position': 'after'},
    'MMK': {'symbol': 'K', 'name': 'Myanmar Kyat', 'decimal_places': 2, 'position': 'before'},
    'KHR': {'symbol': '៛', 'name': 'Cambodian Riel', 'decimal_places': 2, 'position': 'before'},
    'LAK': {'symbol': '₭', 'name': 'Lao Kip', 'decimal_places': 2, 'position': 'before'},
    'BND': {'symbol': 'B$', 'name': 'Brunei Dollar', 'decimal_places': 2, 'position': 'before'},
    
    # Central Asia
    'KZT': {'symbol': '₸', 'name': 'Kazakhstani Tenge', 'decimal_places': 2, 'position': 'before'},
    'UZS': {'symbol': 'soʻm', 'name': 'Uzbekistani Som', 'decimal_places': 2, 'position': 'before'},
    'KGS': {'symbol': 'с', 'name': 'Kyrgyzstani Som', 'decimal_places': 2, 'position': 'before'},
    'TJS': {'symbol': 'SM', 'name': 'Tajikistani Somoni', 'decimal_places': 2, 'position': 'before'},
    'TMT': {'symbol': 'm', 'name': 'Turkmenistan Manat', 'decimal_places': 2, 'position': 'before'},
    'AZN': {'symbol': '₼', 'name': 'Azerbaijani Manat', 'decimal_places': 2, 'position': 'before'},
    'GEL': {'symbol': '₾', 'name': 'Georgian Lari', 'decimal_places': 2, 'position': 'before'},
    'AMD': {'symbol': '֏', 'name': 'Armenian Dram', 'decimal_places': 2, 'position': 'before'},
    
    # Major Global Currencies
    'USD': {'symbol': '$', 'name': 'US Dollar', 'decimal_places': 2, 'position': 'before'},
    'EUR': {'symbol': '€', 'name': 'Euro', 'decimal_places': 2, 'position': 'before'},
    'GBP': {'symbol': '£', 'name': 'British Pound', 'decimal_places': 2, 'position': 'before'},
    'CAD': {'symbol': 'C$', 'name': 'Canadian Dollar', 'decimal_places': 2, 'position': 'before'},
    'AUD': {'symbol': 'A$', 'name': 'Australian Dollar', 'decimal_places': 2, 'position': 'before'},
    'NZD': {'symbol': 'NZ$', 'name': 'New Zealand Dollar', 'decimal_places': 2, 'position': 'before'},
    'CHF': {'symbol': 'CHF', 'name': 'Swiss Franc', 'decimal_places': 2, 'position': 'before'},
    'SEK': {'symbol': 'kr', 'name': 'Swedish Krona', 'decimal_places': 2, 'position': 'before'},
    'NOK': {'symbol': 'kr', 'name': 'Norwegian Krone', 'decimal_places': 2, 'position': 'before'},
    'DKK': {'symbol': 'kr', 'name': 'Danish Krone', 'decimal_places': 2, 'position': 'before'},
    'RUB': {'symbol': '₽', 'name': 'Russian Ruble', 'decimal_places': 2, 'position': 'before'},
    'TRY': {'symbol': '₺', 'name': 'Turkish Lira', 'decimal_places': 2, 'position': 'before'},
    'ZAR': {'symbol': 'R', 'name': 'South African Rand', 'decimal_places': 2, 'position': 'before'},
    'BRL': {'symbol': 'R$', 'name': 'Brazilian Real', 'decimal_places': 2, 'position': 'before'},
    'MXN': {'symbol': 'Mex$', 'name': 'Mexican Peso', 'decimal_places': 2, 'position': 'before'},
}

def get_currency_info(currency_code='PKR'):
    """
    Get currency information for a given currency code
    
    Args:
        currency_code: ISO currency code (e.g., 'PKR', 'USD')
    
    Returns:
        dict: Currency information (symbol, name, decimal_places, position)
    """
    return CURRENCIES.get(currency_code.upper(), CURRENCIES['PKR'])

def get_system_currency():
    """
    Get the system's configured currency from settings
    
    Returns:
        str: Currency code (e.g., 'PKR')
    """
    from app.models import SystemSetting
    return SystemSetting.get_setting('currency', 'PKR')

def get_currency_symbol(currency_code=None):
    """
    Get currency symbol for display
    
    Args:
        currency_code: ISO currency code (defaults to system currency)
    
    Returns:
        str: Currency symbol
    """
    if currency_code is None:
        currency_code = get_system_currency()
    
    currency_info = get_currency_info(currency_code)
    return currency_info['symbol']

def format_currency(amount, currency_code=None, include_symbol=True):
    """
    Format amount with proper currency symbol and decimal places
    
    Args:
        amount: Numeric amount to format
        currency_code: ISO currency code (defaults to system currency)
        include_symbol: Whether to include currency symbol
    
    Returns:
        str: Formatted currency string
    """
    if amount is None:
        amount = 0
    
    # Get currency code
    if currency_code is None:
        currency_code = get_system_currency()
    
    # Get currency info
    currency_info = get_currency_info(currency_code)
    symbol = currency_info['symbol']
    decimal_places = currency_info['decimal_places']
    position = currency_info['position']
    
    # Convert to Decimal for precise formatting
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))
    elif isinstance(amount, str):
        try:
            amount = Decimal(amount)
        except:
            amount = Decimal('0')
    
    # Format with appropriate decimal places
    if decimal_places == 0:
        formatted = f"{amount:,.0f}"
    elif decimal_places == 2:
        formatted = f"{amount:,.2f}"
    elif decimal_places == 3:
        formatted = f"{amount:,.3f}"
    else:
        formatted = f"{amount:,.{decimal_places}f}"
    
    # Add currency symbol based on position
    if not include_symbol:
        return formatted
    
    if position == 'before':
        return f"{symbol}{formatted}"
    else:
        return f"{formatted} {symbol}"

def parse_currency(currency_string):
    """
    Parse currency string back to decimal value
    
    Args:
        currency_string: String like "₨1,234.56" or "$100.50"
    
    Returns:
        Decimal: Numeric value
    """
    if not currency_string:
        return Decimal('0')
    
    # Remove all currency symbols and common separators
    cleaned = str(currency_string)
    
    # Remove all known currency symbols
    for curr_code, curr_info in CURRENCIES.items():
        cleaned = cleaned.replace(curr_info['symbol'], '')
    
    # Remove spaces and commas
    cleaned = cleaned.replace(',', '').replace(' ', '').strip()
    
    try:
        return Decimal(cleaned)
    except:
        return Decimal('0')

def get_currency_list():
    """
    Get list of all supported currencies for dropdown
    
    Returns:
        list: List of dicts with currency info for UI
    """
    currencies = []
    
    # Group currencies by region
    regions = {
        'South Asia': ['PKR', 'INR', 'BDT', 'LKR', 'NPR', 'AFN', 'MVR'],
        'Middle East': ['AED', 'SAR', 'QAR', 'OMR', 'KWD', 'BHD', 'IQD', 'JOD', 'LBP', 'SYP'],
        'East Asia': ['CNY', 'JPY', 'KRW', 'TWD', 'HKD', 'MOP'],
        'Southeast Asia': ['THB', 'MYR', 'SGD', 'IDR', 'PHP', 'VND', 'MMK', 'KHR', 'LAK', 'BND'],
        'Central Asia': ['KZT', 'UZS', 'KGS', 'TJS', 'TMT', 'AZN', 'GEL', 'AMD'],
        'Major Currencies': ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'NZD', 'CHF', 'RUB', 'TRY', 'BRL', 'MXN', 'ZAR'],
    }
    
    for region, codes in regions.items():
        for code in codes:
            if code in CURRENCIES:
                info = CURRENCIES[code]
                currencies.append({
                    'code': code,
                    'name': info['name'],
                    'symbol': info['symbol'],
                    'region': region
                })
    
    return currencies

def convert_currency_display(amount, old_currency, new_currency):
    """
    Convert currency display (NOTE: This doesn't do exchange rate conversion,
    just reformats the same numeric value in different currency)
    
    For actual exchange rate conversion, you would need to integrate with
    an exchange rate API service.
    
    Args:
        amount: Numeric amount
        old_currency: Old currency code
        new_currency: New currency code
    
    Returns:
        str: Formatted amount in new currency
    """
    # Parse the amount
    if isinstance(amount, str):
        amount = parse_currency(amount)
    
    # Format in new currency
    return format_currency(amount, new_currency)
