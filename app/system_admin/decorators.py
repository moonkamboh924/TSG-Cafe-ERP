"""
System Admin Decorators
Shared decorators for system administrator access control
"""

from functools import wraps
from flask import redirect, url_for, jsonify, request
from flask_login import current_user

def require_system_admin(f):
    """Decorator to ensure only system administrators can access routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
            
        if current_user.role != 'system_administrator':
            # Check if this is an API endpoint
            if request.endpoint and '/api/' in request.endpoint:
                return jsonify({'error': 'Access denied. System administrator privileges required.'}), 403
            # Redirect to regular dashboard for non-API routes
            return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def system_admin_api_required(f):
    """Decorator specifically for API endpoints requiring system admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
            
        if current_user.role != 'system_administrator':
            return jsonify({'error': 'Access denied. System administrator privileges required.'}), 403
            
        return f(*args, **kwargs)
    return decorated_function
