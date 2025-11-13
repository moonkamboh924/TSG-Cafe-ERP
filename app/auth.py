"""
Authentication Blueprint for TSG Cafe ERP
Handles login, logout, and redirects registration to tenant system
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from .models import User, SystemSetting, AuditLog
from .extensions import db
from datetime import datetime, timezone
from functools import wraps

bp = Blueprint('auth', __name__)

def require_permissions(*required_permissions):
    """Decorator to require specific permissions for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Check if user has required permissions
            if hasattr(current_user, 'navigation_permissions'):
                user_permissions = current_user.navigation_permissions or []
                
                # Check each required permission
                for permission in required_permissions:
                    # Allow both exact match and base permission
                    # e.g., 'dashboard' permission allows 'dashboard.view'
                    base_permission = permission.split('.')[0]
                    
                    if permission not in user_permissions and base_permission not in user_permissions:
                        # If user is admin or owner, allow all permissions
                        if hasattr(current_user, 'role') and current_user.role == 'admin':
                            continue
                        if hasattr(current_user, 'is_owner') and current_user.is_owner:
                            continue
                        abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit(action, entity, entity_id=None, meta=None):
    """Log audit trail"""
    try:
        if current_user.is_authenticated:
            business_id = current_user.business_id
            user_id = current_user.id
        else:
            business_id = None
            user_id = None
            
        audit_log = AuditLog(
            business_id=business_id,
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta_json=str(meta) if meta else None,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        try:
            from logging_config import log_audit_error
            log_audit_error(f"Audit log error: {str(e)}")
        except ImportError:
            pass

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
            return render_template('auth/login.html', erp_name=erp_name)
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Check if account is locked
            if user.is_account_locked():
                minutes_left = int((user.account_locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
                flash(f'Account is locked due to multiple failed login attempts. Please try again in {minutes_left} minutes.', 'error')
                log_audit('login_failed', 'user', meta={'email': email, 'reason': 'account_locked'})
                erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
                return render_template('auth/login.html', erp_name=erp_name)
            
            # Check password
            if user.check_password(password):
                # Check if account is active
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact the administrator.', 'error')
                    log_audit('login_failed', 'user', meta={'email': email, 'reason': 'account_inactive'})
                    erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
                    return render_template('auth/login.html', erp_name=erp_name)
                
                # Successful login - reset failed attempts
                user.reset_failed_login()
                db.session.commit()
                
                login_user(user, remember=True)
                log_audit('login', 'user', user.id)
                
                # Check if password change is required
                if user.requires_password_change:
                    return redirect(url_for('admin.change_password_required'))
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard.index'))
            else:
                # Failed login - increment counter
                user.increment_failed_login()
                db.session.commit()
                
                remaining_attempts = 5 - user.failed_login_attempts
                if remaining_attempts > 0:
                    flash(f'Invalid email or password. {remaining_attempts} attempts remaining.', 'error')
                else:
                    flash('Account locked due to multiple failed login attempts. Please try again in 15 minutes.', 'error')
                log_audit('login_failed', 'user', meta={'email': email, 'reason': 'invalid_password'})
        else:
            flash('Invalid email or password.', 'error')
            log_audit('login_failed', 'user', meta={'email': email, 'reason': 'user_not_found'})
    
    # Get ERP name from settings
    erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
    return render_template('auth/login.html', erp_name=erp_name)

@bp.route('/logout')
@login_required
def logout():
    log_audit('logout', 'user', current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Redirect to new tenant registration system"""
    return redirect(url_for('tenant.register'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle forgot password requests"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('auth/forgot_password.html')
        
        # Check if user exists
        from app.models import User, PasswordResetRequest
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Don't reveal if email exists or not for security
            flash('If an account with that email exists, we have sent password reset instructions.', 'info')
            return render_template('auth/forgot_password.html')
        
        try:
            # Create password reset request
            reset_request = PasswordResetRequest(
                business_id=user.business_id,
                user_id=user.id,
                email=email,
                status='pending',
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(reset_request)
            db.session.commit()
            
            flash('If an account with that email exists, we have sent password reset instructions.', 'info')
            log_audit('password_reset_requested', 'user', user.id, {'email': email})
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/forgot_password.html')
    
    # GET request - show forgot password form
    return render_template('auth/forgot_password.html')
