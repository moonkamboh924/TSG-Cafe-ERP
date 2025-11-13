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
        subscription_plan = request.form.get('subscription_plan', 'free')
        
        # Validation
        errors = []
        
        if not business_name or len(business_name) < 2:
            errors.append('Business name must be at least 2 characters long')
        
        if not owner_email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', owner_email):
            errors.append('Please enter a valid email address')
        
        if not owner_name or len(owner_name) < 2:
            errors.append('Owner name must be at least 2 characters long')
        
        if subscription_plan not in ['free', 'basic', 'premium']:
            subscription_plan = 'free'
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('tenant/register.html', 
                                 business_name=business_name,
                                 owner_email=owner_email,
                                 owner_name=owner_name,
                                 subscription_plan=subscription_plan)
        
        try:
            # Create new tenant
            result = TenantService.create_tenant(
                business_name=business_name,
                owner_email=owner_email,
                owner_name=owner_name,
                subscription_plan=subscription_plan
            )
            
            # Show success page with credentials
            return render_template('tenant/registration_success.html', 
                                 tenant_info=result)
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('tenant/register.html',
                                 business_name=business_name,
                                 owner_email=owner_email,
                                 owner_name=owner_name,
                                 subscription_plan=subscription_plan)
        except Exception as e:
            # Show actual error for debugging
            flash(f'Registration failed: {str(e)}', 'error')
            # Also log the error
            import traceback
            print(f"Registration error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return render_template('tenant/register.html',
                                 business_name=business_name,
                                 owner_email=owner_email,
                                 owner_name=owner_name,
                                 subscription_plan=subscription_plan)
    
    return render_template('tenant/register.html')

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

@bp.route('/plans')
def plans():
    """Subscription plans page"""
    plans = {
        'free': {
            'name': 'Free',
            'price': 0,
            'features': [
                'Up to 5 users',
                'Basic POS system',
                'Menu management',
                'Basic reports',
                'Email support'
            ]
        },
        'basic': {
            'name': 'Basic',
            'price': 29,
            'features': [
                'Up to 25 users',
                'Advanced POS system',
                'Inventory management',
                'Financial reports',
                'Priority support',
                'Data backup'
            ]
        },
        'premium': {
            'name': 'Premium',
            'price': 99,
            'features': [
                'Unlimited users',
                'Multi-location support',
                'Advanced analytics',
                'Custom reports',
                'API access',
                '24/7 support',
                'Custom integrations'
            ]
        }
    }
    return render_template('tenant/plans.html', plans=plans)
