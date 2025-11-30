"""
Tenant Registration Blueprint
Handles new business registration for multi-tenant ERP
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from ..services.tenant_service import TenantService
from ..extensions import db
import re

bp = Blueprint('tenant', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Public tenant registration page"""
    if request.method == 'POST':
        # Get form data
        business_name = request.form.get('business_name', '').strip()
        owner_email = request.form.get('owner_email', '').strip().lower()
        owner_name = request.form.get('owner_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        password = request.form.get('password', '')
        email_verification_code = request.form.get('email_verification_code', '').strip()
        mobile_verification_code = request.form.get('mobile_verification_code', '').strip()
        subscription_plan = request.form.get('subscription_plan', 'basic')
        
        # Validation
        errors = []
        
        if not business_name or len(business_name) < 2:
            errors.append('Business name must be at least 2 characters long')
        
        if not owner_email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', owner_email):
            errors.append('Please enter a valid email address')
        
        if not owner_name or len(owner_name) < 2:
            errors.append('Owner name must be at least 2 characters long')
        
        if not phone_number or len(phone_number) < 10:
            errors.append('Please enter a valid phone number')
        
        if not password or len(password) < 8:
            errors.append('Password must be at least 8 characters long')
        
        if not email_verification_code or len(email_verification_code) != 6:
            errors.append('Please enter the 6-digit email verification code')
        
        if not mobile_verification_code or len(mobile_verification_code) != 6:
            errors.append('Please enter the 6-digit mobile verification code')
        
        # Validate plan exists in database
        from ..models import SubscriptionPlan
        plan_exists = SubscriptionPlan.query.filter_by(plan_code=subscription_plan, is_active=True).first()
        if not plan_exists:
            subscription_plan = 'basic'  # Fallback to basic plan
        
        # Get plans for rendering
        from ..models import SubscriptionPlan
        plans_query = SubscriptionPlan.query.filter_by(is_active=True, is_visible=True).order_by(SubscriptionPlan.display_order).all()
        plans = [plan.to_dict() for plan in plans_query]
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('tenant/register.html', 
                                 plans=plans,
                                 business_name=business_name,
                                 owner_email=owner_email,
                                 owner_name=owner_name,
                                 phone_number=phone_number,
                                 subscription_plan=subscription_plan)
        
        try:
            # TODO: Verify the codes against stored codes in session/cache
            # For now, we'll proceed with registration
            
            # Create new tenant
            result = TenantService.create_tenant(
                business_name=business_name,
                owner_email=owner_email,
                owner_name=owner_name,
                phone_number=phone_number,
                password=password,
                subscription_plan=subscription_plan
            )
            
            # Show success notification and redirect to login
            flash('Registration successful! Welcome to TSG Cafe ERP.', 'success')
            return redirect(url_for('auth.login'))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('tenant/register.html',
                                 plans=plans,
                                 business_name=business_name,
                                 owner_email=owner_email,
                                 owner_name=owner_name,
                                 phone_number=phone_number,
                                 subscription_plan=subscription_plan)
        except Exception as e:
            # Show actual error for debugging
            flash(f'Registration failed: {str(e)}', 'error')
            # Also log the error
            import traceback
            print(f"Registration error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return render_template('tenant/register.html',
                                 plans=plans,
                                 business_name=business_name,
                                 owner_email=owner_email,
                                 owner_name=owner_name,
                                 phone_number=phone_number,
                                 subscription_plan=subscription_plan)
    
    # GET request - fetch plans from database
    from ..models import SubscriptionPlan
    plans_query = SubscriptionPlan.query.filter_by(is_active=True, is_visible=True).order_by(SubscriptionPlan.display_order).all()
    plans = [plan.to_dict() for plan in plans_query]
    
    return render_template('tenant/register.html', plans=plans)

@bp.route('/api/check-availability', methods=['POST'])
def check_availability():
    """API endpoint to check business name and email availability"""
    data = request.get_json()
    business_name = data.get('business_name', '').strip()
    owner_email = data.get('owner_email', '').strip().lower()
    
    result = {
        'business_name_available': True,
        'email_available': True
    }
    
    if business_name:
        from ..models import Business
        existing_business = Business.query.filter_by(business_name=business_name).first()
        result['business_name_available'] = existing_business is None
    
    if owner_email:
        from ..models import User
        existing_user = User.query.filter_by(email=owner_email).first()
        result['email_available'] = existing_user is None
    
    return jsonify(result)

@bp.route('/api/send-verification-codes', methods=['POST'])
def send_verification_codes():
    """API endpoint to send verification codes to email and phone"""
    from ..services.verification_service import VerificationService
    
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    business_name = data.get('business_name', '').strip()
    
    if not email or not phone:
        return jsonify({
            'success': False,
            'message': 'Email and phone number are required'
        }), 400
    
    # Send both verification codes
    result = VerificationService.send_both_codes(email, phone, business_name)
    
    return jsonify(result)

@bp.route('/api/verify-codes', methods=['POST'])
def verify_codes():
    """API endpoint to verify email and SMS codes"""
    from ..services.verification_service import VerificationService
    
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    email_code = data.get('email_code', '').strip()
    sms_code = data.get('sms_code', '').strip()
    
    if not all([email, phone, email_code, sms_code]):
        return jsonify({
            'success': False,
            'message': 'All fields are required'
        }), 400
    
    # Verify both codes
    result = VerificationService.verify_both_codes(email, phone, email_code, sms_code)
    
    return jsonify(result)

@bp.route('/plans')
def plans():
    """Subscription plans page"""
    from ..services.subscription_service import SubscriptionService
    
    plans = SubscriptionService.PLAN_PRICING
    periods = SubscriptionService.SUBSCRIPTION_PERIODS
    
    return render_template('tenant/plans.html', 
                         plans=plans, 
                         periods=periods)

