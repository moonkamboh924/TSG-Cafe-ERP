"""
Business hours utility functions for managing opening/closing times and new day logic
"""
from datetime import datetime, time, timedelta

def get_business_hours():
    """Get the configured business opening and closing times"""
    from app.models import SystemSetting
    
    opening_time_str = SystemSetting.get_setting('opening_time', '09:00')
    closing_time_str = SystemSetting.get_setting('closing_time', '23:00')
    
    # Parse time strings to time objects
    opening_time = time.fromisoformat(opening_time_str)
    closing_time = time.fromisoformat(closing_time_str)
    
    return opening_time, closing_time

def get_new_day_start_time():
    """Get the configured new day start time"""
    from app.models import SystemSetting
    
    new_day_start_str = SystemSetting.get_setting('new_day_start_time', '06:00')
    return time.fromisoformat(new_day_start_str)

def is_business_open(check_time=None):
    """
    Check if the business is currently open
    
    Args:
        check_time: datetime to check (defaults to now)
    
    Returns:
        bool: True if business is open
    """
    if check_time is None:
        check_time = datetime.now()
    
    opening_time, closing_time = get_business_hours()
    current_time = check_time.time()
    
    # Handle cases where closing time is past midnight (e.g., 02:00)
    if closing_time < opening_time:
        # Business operates past midnight
        return current_time >= opening_time or current_time <= closing_time
    else:
        # Normal operating hours within same day
        return opening_time <= current_time <= closing_time

def get_business_day(check_datetime=None):
    """
    Get the business day for a given datetime based on new_day_start_time
    
    The business day changes at new_day_start_time, not at midnight.
    For example, if new_day_start_time is 06:00:
    - 2025-12-01 05:59:59 belongs to business day 2025-11-30
    - 2025-12-01 06:00:00 belongs to business day 2025-12-01
    
    Args:
        check_datetime: datetime to check (defaults to now)
    
    Returns:
        date: The business day date
    """
    if check_datetime is None:
        check_datetime = datetime.now()
    
    new_day_start = get_new_day_start_time()
    current_time = check_datetime.time()
    
    # If current time is before new day start time, it belongs to previous day
    if current_time < new_day_start:
        business_day = check_datetime.date() - timedelta(days=1)
    else:
        business_day = check_datetime.date()
    
    return business_day

def get_business_day_range(business_date):
    """
    Get the datetime range for a specific business day
    
    Args:
        business_date: date object for the business day
    
    Returns:
        tuple: (start_datetime, end_datetime) for the business day
    """
    new_day_start = get_new_day_start_time()
    
    # Start of business day
    start_datetime = datetime.combine(business_date, new_day_start)
    
    # End of business day (just before next day starts)
    end_datetime = datetime.combine(business_date + timedelta(days=1), new_day_start)
    
    return start_datetime, end_datetime

def format_business_hours():
    """
    Format business hours as a readable string
    
    Returns:
        str: Formatted business hours (e.g., "09:00 AM - 11:00 PM")
    """
    opening_time, closing_time = get_business_hours()
    
    opening_str = opening_time.strftime('%I:%M %p').lstrip('0')
    closing_str = closing_time.strftime('%I:%M %p').lstrip('0')
    
    return f"{opening_str} - {closing_str}"

def get_current_business_day_sales():
    """
    Get sales for the current business day
    
    Returns:
        Query: SQLAlchemy query filtered for current business day
    """
    from app.models import Sale
    
    business_day = get_business_day()
    start_datetime, end_datetime = get_business_day_range(business_day)
    
    return Sale.query.filter(
        Sale.created_at >= start_datetime,
        Sale.created_at < end_datetime
    )

def is_new_business_day_started(last_check_time):
    """
    Check if a new business day has started since last_check_time
    
    Args:
        last_check_time: datetime of last check
    
    Returns:
        bool: True if we've crossed into a new business day
    """
    if last_check_time is None:
        return True
    
    last_business_day = get_business_day(last_check_time)
    current_business_day = get_business_day()
    
    return current_business_day > last_business_day
