"""
System Admin Decorators
Shared decorators for system administrator access control
"""

from functools import wraps
from flask import redirect, url_for, jsonify, request, flash
from flask_login import current_user

def require_system_admin(f):
    """Decorator to ensure only system administrators can access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        # Enhanced security checks
        if not current_user.can_access_system_admin_panel():
            # Check if this is an API endpoint
            if request.endpoint and '/api/' in request.endpoint:
                return jsonify({'error': 'Access denied. System administrator privileges required.'}), 403
            else:
                flash('Access denied. System administrator privileges required.', 'error')
                return redirect(url_for('dashboard.index'))
        
        # Additional security: Check if account is locked
        if current_user.is_account_locked():
            if request.endpoint and '/api/' in request.endpoint:
                return jsonify({'error': 'Account is temporarily locked due to security reasons.'}), 423
            else:
                flash('Account is temporarily locked due to security reasons.', 'error')
                return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def system_admin_api_required(f):
    """Decorator specifically for API endpoints requiring system admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Enhanced security checks for API endpoints
        if not current_user.can_access_system_admin_panel():
            return jsonify({'error': 'Access denied. System administrator privileges required.'}), 403
        
        # Check if account is locked
        if current_user.is_account_locked():
            return jsonify({'error': 'Account is temporarily locked due to security reasons.'}), 423
        
        # Additional security: Log API access for system admin
        from flask import request
        import logging
        logging.info(f"System Admin API Access: {current_user.username} -> {request.endpoint}")
            
        return f(*args, **kwargs)
    return decorated_function

def require_super_admin(f):
    """Decorator for operations requiring super admin privileges (MM001 only)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        if not current_user.has_super_admin_privileges():
            if request.endpoint and '/api/' in request.endpoint:
                return jsonify({'error': 'Access denied. Super administrator privileges required.'}), 403
            else:
                flash('Access denied. Super administrator privileges required.', 'error')
                return redirect(url_for('dashboard.index'))
            
        return f(*args, **kwargs)
    return decorated_function

def require_navigation_permission(permission):
    """Decorator to require specific navigation permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.can_access_system_admin_panel():
                abort(403)
            
            if not current_user.has_navigation_permission(permission):
                flash(f'You do not have permission to access {permission.replace("_", " ").title()}', 'error')
                return redirect(url_for('system_admin_dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
