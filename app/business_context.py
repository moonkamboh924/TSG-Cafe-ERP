"""
Multi-Tenant Business Context Helper
Provides utilities for filtering queries by business_id
"""

from flask_login import current_user
from functools import wraps
from flask import abort

def get_current_business_id():
    """Get the business_id of the currently logged-in user"""
    if current_user.is_authenticated and hasattr(current_user, 'business_id'):
        return current_user.business_id
    return None

def require_business_context(f):
    """Decorator to ensure user has a business context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not hasattr(current_user, 'business_id') or current_user.business_id is None:
            abort(403, description="No business context available")
        return f(*args, **kwargs)
    return decorated_function

def filter_by_business(query, model=None):
    """
    Filter a query by current user's business_id
    
    Usage:
        items = filter_by_business(MenuItem.query).all()
    """
    business_id = get_current_business_id()
    if business_id is not None:
        return query.filter_by(business_id=business_id)
    return query

def add_business_id(data_dict):
    """
    Add business_id to a dictionary (for creating records)
    
    Usage:
        new_item = MenuItem(**add_business_id({
            'name': 'Pizza',
            'price': 10.99
        }))
    """
    business_id = get_current_business_id()
    if business_id is not None:
        data_dict['business_id'] = business_id
    return data_dict

def is_system_administrator():
    """Check if current user is a system administrator"""
    return (current_user.is_authenticated and 
            hasattr(current_user, 'role') and 
            current_user.role == 'system_administrator')

def can_access_all_businesses():
    """Check if current user can access data from all businesses"""
    return is_system_administrator()
