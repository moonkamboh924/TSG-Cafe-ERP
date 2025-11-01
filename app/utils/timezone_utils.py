"""
Timezone utility functions for system-wide timezone handling
"""
from datetime import datetime, timezone
import pytz
from app.models import SystemSetting

def get_system_timezone():
    """Get the configured system timezone"""
    timezone_str = SystemSetting.get_setting('timezone', 'Asia/Karachi')
    try:
        return pytz.timezone(timezone_str)
    except pytz.UnknownTimeZoneError:
        # Fallback to default if invalid timezone
        return pytz.timezone('Asia/Karachi')

def get_current_time():
    """Get current time in system timezone"""
    system_tz = get_system_timezone()
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(system_tz)

def convert_utc_to_local(utc_datetime):
    """Convert UTC datetime to system timezone"""
    if utc_datetime is None:
        return None
    
    system_tz = get_system_timezone()
    
    # If datetime is naive, assume it's UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.UTC.localize(utc_datetime)
    
    return utc_datetime.astimezone(system_tz)

def convert_local_to_utc(local_datetime):
    """Convert local datetime to UTC"""
    if local_datetime is None:
        return None
    
    system_tz = get_system_timezone()
    
    # If datetime is naive, assume it's in system timezone
    if local_datetime.tzinfo is None:
        try:
            local_datetime = system_tz.localize(local_datetime)
        except AttributeError:
            # Handle case where local_datetime might already be timezone-aware
            local_datetime = local_datetime.replace(tzinfo=system_tz)
    
    return local_datetime.astimezone(pytz.UTC)

def format_datetime(dt, format_str=None):
    """Format datetime according to system settings"""
    if dt is None:
        return ''
    
    # Always convert to local timezone first
    if hasattr(dt, 'tzinfo'):
        if dt.tzinfo is None:
            # Naive datetime, assume UTC
            dt = pytz.UTC.localize(dt)
        dt = convert_utc_to_local(dt)
    else:
        # Not a datetime object, convert to local time
        dt = convert_utc_to_local(dt)
    
    # Get system date and time format settings
    date_format = SystemSetting.get_setting('date_format', 'DD/MM/YYYY')
    time_format = SystemSetting.get_setting('time_format', '12')
    
    if format_str:
        return dt.strftime(format_str)
    
    # Convert system format to Python strftime format
    if date_format == 'DD/MM/YYYY':
        date_fmt = '%d/%m/%Y'
    elif date_format == 'MM/DD/YYYY':
        date_fmt = '%m/%d/%Y'
    elif date_format == 'YYYY-MM-DD':
        date_fmt = '%Y-%m-%d'
    else:
        date_fmt = '%d/%m/%Y'  # Default
    
    if time_format == '24':
        time_fmt = '%H:%M:%S'
    else:
        time_fmt = '%I:%M:%S %p'  # 12-hour with AM/PM
    
    return dt.strftime(f"{date_fmt} {time_fmt}")

def format_date_only(dt):
    """Format date only according to system settings"""
    if dt is None:
        return ''
    
    # Always convert to local timezone first
    if hasattr(dt, 'tzinfo'):
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        dt = convert_utc_to_local(dt)
    else:
        dt = convert_utc_to_local(dt)
    
    date_format = SystemSetting.get_setting('date_format', 'DD/MM/YYYY')
    
    if date_format == 'DD/MM/YYYY':
        return dt.strftime('%d/%m/%Y')
    elif date_format == 'MM/DD/YYYY':
        return dt.strftime('%m/%d/%Y')
    elif date_format == 'YYYY-MM-DD':
        return dt.strftime('%Y-%m-%d')
    else:
        return dt.strftime('%d/%m/%Y')  # Default

def format_time_only(dt):
    """Format time only according to system settings"""
    if dt is None:
        return ''
    
    # Always convert to local timezone first
    if hasattr(dt, 'tzinfo'):
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        dt = convert_utc_to_local(dt)
    else:
        dt = convert_utc_to_local(dt)
    
    time_format = SystemSetting.get_setting('time_format', '12')
    
    if time_format == '24':
        return dt.strftime('%H:%M:%S')
    else:
        return dt.strftime('%I:%M:%S %p')

def get_timezone_info():
    """Get current timezone information"""
    system_tz = get_system_timezone()
    current_time = get_current_time()
    
    return {
        'timezone': system_tz.zone,
        'current_time': current_time,
        'utc_offset': current_time.strftime('%z'),
        'timezone_name': current_time.strftime('%Z')
    }

def sync_existing_records():
    """
    Sync existing records when timezone is updated.
    This function can be extended to handle any timezone-related updates.
    Currently, it's a placeholder for future functionality.
    """
    try:
        from app.models import SystemSetting, AuditLog
        from app.extensions import db
        from datetime import datetime
        
        # Log the timezone sync operation
        timezone = SystemSetting.get_setting('timezone', 'Asia/Karachi')
        
        # Create audit log entry for timezone sync
        sync_log = AuditLog(
            user_id=None,  # System operation
            action='sync',
            entity='timezone_settings',
            entity_id=None,
            meta_json=f'{{"new_timezone": "{timezone}", "sync_time": "{datetime.now(timezone.utc).isoformat()}"}}',
            created_at=datetime.now(timezone.utc)
        )
        
        db.session.add(sync_log)
        db.session.commit()
        
        return True
        
    except Exception as e:
        import logging
        logging.error(f"Error in sync_existing_records: {str(e)}")
        return False
