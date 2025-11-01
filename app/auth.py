from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, AuditLog, SystemSetting, Business
from .extensions import db
import json
import re
import secrets
from datetime import datetime, timezone

bp = Blueprint('auth', __name__)

def require_permissions(*permissions):
    """Decorator to check user permissions"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_active:
                flash('Your account has been deactivated. Please contact the administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            # Check if password change is required (except for password change routes)
            if current_user.requires_password_change and request.endpoint not in ['admin.change_password_required', 'admin.change_password', 'auth.logout']:
                return redirect(url_for('admin.change_password_required'))
            
            for permission in permissions:
                if not current_user.has_permission(permission):
                    flash('You do not have permission to access this resource.', 'error')
                    return redirect(url_for('dashboard.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit(action, entity, entity_id=None, meta=None):
    """Helper function to log audit entries"""
    try:
        audit_log = AuditLog(
            user_id=current_user.id if current_user.is_authenticated else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta_json=json.dumps(meta) if meta else None
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
    """Public registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        full_name = request.form.get('full_name', '').strip()
        business_name = request.form.get('business_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        # Check required fields
        if not first_name:
            errors.append('First name is required')
        if not last_name:
            errors.append('Last name is required')
        if not full_name:
            errors.append('Full name is required')
        if not business_name:
            errors.append('Business name is required')
        if not email:
            errors.append('Email is required')
        if not phone:
            errors.append('Phone number is required')
        if not address:
            errors.append('Address is required')
        if not password:
            errors.append('Password is required')
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_regex, email):
            errors.append('Invalid email format')
        
        # Check if email already exists
        if email and User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        # Validate password strength
        if password:
            if len(password) < 8:
                errors.append('Password must be at least 8 characters long')
            if not re.search(r'[A-Z]', password):
                errors.append('Password must contain at least one uppercase letter')
            if not re.search(r'[a-z]', password):
                errors.append('Password must contain at least one lowercase letter')
            if not re.search(r'[0-9]', password):
                errors.append('Password must contain at least one number')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                errors.append('Password must contain at least one special character')
        
        # Check password confirmation
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        # If there are errors, show them
        if errors:
            for error in errors:
                flash(error, 'error')
            erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
            return render_template('auth/register.html', erp_name=erp_name)
        
        try:
            # MULTI-TENANT: Create Business first
            # Check if business name already exists
            existing_business = Business.query.filter_by(business_name=business_name).first()
            if existing_business:
                flash('Business name already exists. Please choose a different name.', 'error')
                erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
                return render_template('auth/register.html', erp_name=erp_name)
            
            # Create new business
            business = Business(
                business_name=business_name,
                owner_email=email,
                subscription_plan='free',
                is_active=True
            )
            db.session.add(business)
            db.session.flush()  # Get business.id
            
            # Check if this is the first user (fresh system)
            is_first_user = User.query.count() == 0
            
            # Generate employee ID (globally unique for now, until we fix schema)
            # TODO: After removing UNIQUE constraint, make this per-business
            employee_id = User.generate_next_employee_id()
            username = User.generate_username(first_name, last_name, employee_id)
            
            # Check if username already exists in this business
            counter = 1
            original_username = username
            while User.query.filter_by(business_id=business.id, username=username).first():
                username = f"{original_username}{counter}"
                counter += 1
            
            # Generate email verification token
            verification_token = secrets.token_urlsafe(32)
            
            # Create new user with all fields
            user = User(
                business_id=business.id,  # MULTI-TENANT
                employee_id=employee_id,
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                full_name=full_name,
                phone=phone,
                address=address,
                department='Management',
                designation='Owner',
                role='admin',  # Business owner is admin
                is_owner=True,  # MULTI-TENANT: Mark as business owner
                is_active=True,
                is_protected=is_first_user,  # Protect first user
                requires_password_change=False,
                email_verified=False,  # Require email verification
                email_verification_token=verification_token
            )
            user.set_password(password)
            
            # Set full navigation permissions for business owner
            user.set_navigation_permissions(['admin', 'pos', 'menu', 'inventory', 'finance', 'reports'])
            
            db.session.add(user)
            db.session.flush()  # Get user.id
            
            # Update business with owner_id
            business.owner_id = user.id
            
            # MULTI-TENANT: Create business-specific settings
            # Create settings for this business
            settings_to_create = [
                ('restaurant_name', business_name),
                ('restaurant_phone', phone),
                ('restaurant_address', address),
                ('restaurant_email', email),
                ('restaurant_subtitle', 'Powered by Trisync Global'),
                ('copyright_company', business_name),
                ('tax_rate', '16'),
                ('currency', 'PKR'),
                ('date_format', 'DD/MM/YYYY'),
                ('time_format', '12'),
                ('timezone', 'Asia/Karachi')
            ]
            
            for key, value in settings_to_create:
                setting = SystemSetting(
                    business_id=business.id,
                    key=key,
                    value=value
                )
                db.session.add(setting)
            
            db.session.commit()
            
            log_audit('register', 'user', user.id, {'username': username, 'email': email, 'is_first_user': is_first_user})
            
            # TODO: Send verification email (implement email service)
            # Show success message with email for login
            if is_first_user:
                flash(f'Welcome! Your account has been created as System Administrator. Please login with your email: {email}', 'success')
            else:
                flash(f'Account created successfully! Please login with your email: {email}', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            
            # Parse error message for user-friendly display
            error_msg = str(e)
            if 'UNIQUE constraint failed: users.employee_id' in error_msg:
                flash('Registration failed: Employee ID conflict. Please try again.', 'error')
            elif 'UNIQUE constraint failed: users.email' in error_msg:
                flash('This email is already registered. Please use a different email or login.', 'error')
            elif 'UNIQUE constraint failed: users.username' in error_msg:
                flash('Username already exists. Please try again.', 'error')
            elif 'UNIQUE constraint failed: businesses.business_name' in error_msg:
                flash('Business name already exists. Please choose a different name.', 'error')
            else:
                flash(f'Registration failed: {error_msg}', 'error')
            
            erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
            return render_template('auth/register.html', erp_name=erp_name)
    
    # GET request - show registration form
    erp_name = SystemSetting.get_setting('restaurant_name', 'My Business')
    return render_template('auth/register.html', erp_name=erp_name)

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
            flash('If this email is registered, you will receive a notification within 12-24 hours.', 'success')
            log_audit('password_reset_request', 'user', meta={'email': email, 'status': 'email_not_found'})
            return render_template('auth/forgot_password.html')
        
        # Check if there's already a pending request
        existing_request = PasswordResetRequest.query.filter_by(
            user_id=user.id,
            status='pending'
        ).first()
        
        if existing_request:
            flash('You already have a pending password reset request. Please wait for admin approval.', 'error')
            return render_template('auth/forgot_password.html')
        
        try:
            # Create password reset request
            reset_request = PasswordResetRequest(
                user_id=user.id,
                status='pending'
            )
            db.session.add(reset_request)
            db.session.commit()
            
            log_audit('password_reset_request', 'user', user.id, {
                'email': email,
                'request_id': reset_request.id
            })
            
            flash('Your password reset request has been submitted successfully! You will receive a notification within 12-24 hours.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/forgot_password.html')
    
    # GET request - show forgot password form
    return render_template('auth/forgot_password.html')
