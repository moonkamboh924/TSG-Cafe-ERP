"""
System Admin Subscription Management Blueprint
Handles subscription management for all businesses
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models import Business, User
from ..decorators import require_system_admin, system_admin_api_required

bp = Blueprint('system_admin_subscriptions', __name__, url_prefix='/system-admin/subscriptions')

@bp.route('/')
@login_required
@require_system_admin
def index():
    """Subscription Management Dashboard"""
    return render_template('system_admin/subscriptions_enhanced.html')


@bp.route('/plans')
@login_required
@require_system_admin
def manage_plans():
    """Subscription Plans Configuration Page"""
    return render_template('system_admin/subscription_plans.html')

@bp.route('/api/subscriptions')
@login_required
@system_admin_api_required
def get_subscriptions():
    """Get subscription data for all businesses"""
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        search = request.args.get('search', '', type=str)
        plan_filter = request.args.get('plan', '', type=str)
        status_filter = request.args.get('status', '', type=str)
        
        # Base query for all businesses
        query = Business.query
        
        # Apply search filter
        if search:
            query = query.filter(
                Business.business_name.ilike(f'%{search}%')
            )
        
        # Apply plan filter
        if plan_filter:
            query = query.filter(Business.subscription_plan == plan_filter)
        
        # Apply status filter
        if status_filter:
            if status_filter == 'active':
                query = query.filter(Business.is_active == True)
            elif status_filter == 'inactive':
                query = query.filter(Business.is_active == False)
        
        # Order by creation date
        query = query.order_by(desc(Business.created_at))
        
        # Paginate results
        businesses = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        business_list = []
        for business in businesses.items:
            # Get business owner
            owner = User.query.filter_by(business_id=business.id, is_owner=True).first()
            
            business_data = {
                'id': business.id,
                'business_name': business.business_name,
                'subscription_plan': business.subscription_plan,
                'is_active': business.is_active,
                'created_at': business.created_at.isoformat(),
                'owner': {
                    'name': owner.full_name if owner else 'No Owner',
                    'email': owner.email if owner else 'N/A',
                    'username': owner.username if owner else 'N/A'
                } if owner else None
            }
            business_list.append(business_data)
        
        # Get summary statistics
        total_businesses = Business.query.count()
        active_businesses = Business.query.filter_by(is_active=True).count()
        
        # Get subscription plan distribution
        plan_stats = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        plan_distribution = {plan: count for plan, count in plan_stats}
        
        return jsonify({
            'businesses': business_list,
            'total': businesses.total,
            'pages': businesses.pages,
            'current_page': page,
            'per_page': per_page,
            'statistics': {
                'total_businesses': total_businesses,
                'active_businesses': active_businesses,
                'plan_distribution': plan_distribution
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/stats')
@login_required
@system_admin_api_required
def subscription_stats():
    """Get subscription statistics"""
    
    try:
        # Basic subscription statistics
        total_subscriptions = Business.query.count()
        active_subscriptions = Business.query.filter_by(is_active=True).count()
        
        # Plan distribution
        plan_stats = db.session.query(
            Business.subscription_plan,
            func.count(Business.id).label('count')
        ).group_by(Business.subscription_plan).all()
        
        plan_distribution = {plan: count for plan, count in plan_stats}
        
        # Recent subscriptions (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_subscriptions = Business.query.filter(
            Business.created_at >= thirty_days_ago
        ).count()
        
        # Calculate Monthly Recurring Revenue (MRR)
        from app.models import Subscription
        mrr = db.session.query(func.sum(Subscription.amount)).filter(
            Subscription.status == 'active',
            Subscription.billing_cycle == 'monthly'
        ).scalar() or 0
        
        # Calculate Annual Recurring Revenue (ARR)
        arr = db.session.query(func.sum(Subscription.amount)).filter(
            Subscription.status == 'active',
            Subscription.billing_cycle == 'yearly'
        ).scalar() or 0
        
        total_mrr = float(mrr) + (float(arr) / 12)
        
        return jsonify({
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'plan_distribution': plan_distribution,
            'recent_subscriptions': recent_subscriptions,
            'mrr': float(mrr),
            'arr': float(arr),
            'total_mrr': total_mrr
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/businesses/<int:business_id>/subscription')
@login_required
@system_admin_api_required
def get_business_subscription(business_id):
    """Get detailed subscription info for a business"""
    
    try:
        from app.models import Subscription, Invoice
        
        business = Business.query.get_or_404(business_id)
        
        # Get active subscription
        subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).order_by(desc(Subscription.created_at)).first()
        
        # Get subscription history
        all_subscriptions = Subscription.query.filter_by(
            business_id=business_id
        ).order_by(desc(Subscription.created_at)).limit(10).all()
        
        # Get recent invoices
        invoices = Invoice.query.filter_by(
            business_id=business_id
        ).order_by(desc(Invoice.created_at)).limit(10).all()
        
        return jsonify({
            'business': {
                'id': business.id,
                'name': business.business_name,
                'email': business.owner_email,
                'is_active': business.is_active
            },
            'current_subscription': subscription.to_dict() if subscription else None,
            'subscription_history': [s.to_dict() for s in all_subscriptions],
            'recent_invoices': [inv.to_dict() for inv in invoices] if hasattr(invoices[0] if invoices else None, 'to_dict') else []
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/businesses/<int:business_id>/subscription/upgrade', methods=['POST'])
@login_required
@system_admin_api_required
def upgrade_subscription(business_id):
    """Upgrade a business subscription plan"""
    
    try:
        from app.models import Subscription
        
        data = request.get_json()
        new_plan = data.get('plan')
        
        # Validate plan exists in SubscriptionPlan table
        if not new_plan:
            return jsonify({'error': 'Subscription plan is required'}), 400
        
        from ...models import SubscriptionPlan
        plan_config = SubscriptionPlan.query.filter_by(plan_code=new_plan, is_active=True).first()
        if not plan_config:
            return jsonify({'error': 'Invalid subscription plan'}), 400
        
        business = Business.query.get_or_404(business_id)
        
        # Update business subscription plan
        old_plan = business.subscription_plan
        business.subscription_plan = new_plan
        business.updated_at = datetime.now(timezone.utc)
        
        # Get or create active subscription record
        subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).first()
        
        if subscription:
            subscription.plan = new_plan
            subscription.updated_at = datetime.now(timezone.utc)
        else:
            # Create new subscription record
            subscription = Subscription(
                business_id=business_id,
                plan=new_plan,
                status='active',
                billing_cycle=data.get('billing_cycle', 'monthly'),
                amount=data.get('amount', 0.00),
                currency=data.get('currency', 'USD'),
                start_date=datetime.now(timezone.utc)
            )
            db.session.add(subscription)
        
        db.session.commit()
        
        # Log the upgrade
        from app.auth import log_audit
        log_audit('upgrade_subscription', 'business', business_id, {
            'old_plan': old_plan,
            'new_plan': new_plan,
            'business_name': business.business_name
        })
        
        return jsonify({
            'success': True,
            'message': f'Subscription upgraded from {old_plan} to {new_plan}',
            'subscription': subscription.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/businesses/<int:business_id>/subscription/suspend', methods=['POST'])
@login_required
@system_admin_api_required
def suspend_subscription(business_id):
    """Suspend a business subscription"""
    
    try:
        from app.models import Subscription
        
        data = request.get_json()
        reason = data.get('reason', 'Administrative action')
        
        business = Business.query.get_or_404(business_id)
        
        # Update business status
        business.is_active = False
        business.subscription_status = 'suspended'
        business.updated_at = datetime.now(timezone.utc)
        
        # Update subscription record
        subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).first()
        
        if subscription:
            subscription.status = 'suspended'
            subscription.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log the suspension
        from app.auth import log_audit
        log_audit('suspend_subscription', 'business', business_id, {
            'reason': reason,
            'business_name': business.business_name
        })
        
        return jsonify({
            'success': True,
            'message': f'Subscription suspended for {business.business_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/businesses/<int:business_id>/subscription/reactivate', methods=['POST'])
@login_required
@system_admin_api_required
def reactivate_subscription(business_id):
    """Reactivate a suspended business subscription"""
    
    try:
        from app.models import Subscription
        
        business = Business.query.get_or_404(business_id)
        
        # Update business status
        business.is_active = True
        business.subscription_status = 'active'
        business.updated_at = datetime.now(timezone.utc)
        
        # Update subscription record
        subscription = Subscription.query.filter_by(
            business_id=business_id
        ).order_by(desc(Subscription.created_at)).first()
        
        if subscription:
            subscription.status = 'active'
            subscription.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Log the reactivation
        from app.auth import log_audit
        log_audit('reactivate_subscription', 'business', business_id, {
            'business_name': business.business_name
        })
        
        return jsonify({
            'success': True,
            'message': f'Subscription reactivated for {business.business_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/invoices')
@login_required
@system_admin_api_required
def get_all_invoices():
    """Get all invoices across all businesses"""
    
    try:
        from app.models import Invoice
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        status_filter = request.args.get('status', '', type=str)
        
        query = Invoice.query
        
        if status_filter:
            query = query.filter(Invoice.payment_status == status_filter)
        
        invoices = query.order_by(desc(Invoice.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        invoice_list = []
        for invoice in invoices.items:
            business = Business.query.get(invoice.business_id)
            invoice_data = invoice.to_dict() if hasattr(invoice, 'to_dict') else {
                'id': invoice.id,
                'invoice_number': invoice.invoice_number,
                'amount': float(invoice.total_amount),
                'status': invoice.payment_status,
                'due_date': invoice.due_date.isoformat()
            }
            invoice_data['business_name'] = business.business_name if business else 'Unknown'
            invoice_list.append(invoice_data)
        
        return jsonify({
            'invoices': invoice_list,
            'total': invoices.total,
            'pages': invoices.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== SUBSCRIPTION PLAN MANAGEMENT APIs =====

@bp.route('/api/plans')
@login_required
@system_admin_api_required
def get_all_plans():
    """Get all subscription plans"""
    
    try:
        from app.models import SubscriptionPlan
        
        plans = SubscriptionPlan.query.order_by(SubscriptionPlan.display_order).all()
        
        return jsonify({
            'success': True,
            'plans': [plan.to_dict() for plan in plans]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plans/<int:plan_id>')
@login_required
@system_admin_api_required
def get_plan(plan_id):
    """Get a specific subscription plan"""
    
    try:
        from app.models import SubscriptionPlan
        
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        
        return jsonify({
            'success': True,
            'plan': plan.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plans', methods=['POST'])
@login_required
@system_admin_api_required
def create_plan():
    """Create a new subscription plan"""
    
    try:
        from app.models import SubscriptionPlan
        import json
        
        data = request.get_json()
        
        # Check if plan code already exists
        existing = SubscriptionPlan.query.filter_by(plan_code=data['plan_code']).first()
        if existing:
            return jsonify({'error': 'Plan code already exists'}), 400
        
        # Parse features if provided as array
        features = data.get('features', [])
        if isinstance(features, list):
            features = json.dumps(features)
        
        plan = SubscriptionPlan(
            plan_code=data['plan_code'],
            plan_name=data['plan_name'],
            description=data.get('description'),
            price=data.get('price', 0),
            discount_percentage=data.get('discount_percentage', 0),
            currency=data.get('currency', '$'),
            # Backward compatibility
            monthly_price=data.get('price', 0),
            yearly_price=data.get('price', 0) * 12 if data.get('price') else 0,
            has_trial=data.get('has_trial', False),
            trial_days=data.get('trial_days', 0),
            max_users=data.get('max_users', -1),
            max_menu_items=data.get('max_menu_items', -1),
            max_inventory_items=data.get('max_inventory_items', -1),
            max_monthly_sales=data.get('max_monthly_sales', -1),
            max_storage_mb=data.get('max_storage_mb', 1024),
            features=features,
            advanced_reports=data.get('advanced_reports', False),
            multi_location=data.get('multi_location', False),
            api_access=data.get('api_access', False),
            priority_support=data.get('priority_support', False),
            custom_branding=data.get('custom_branding', False),
            data_export=data.get('data_export', False),
            display_order=data.get('display_order', 0),
            is_featured=data.get('is_featured', False),
            is_active=data.get('is_active', True),
            is_visible=data.get('is_visible', True),
            badge_text=data.get('badge_text'),
            badge_color=data.get('badge_color')
        )
        
        db.session.add(plan)
        db.session.commit()
        
        # Log the action
        from app.auth import log_audit
        log_audit('create', 'subscription_plan', plan.id, {
            'plan_code': plan.plan_code,
            'plan_name': plan.plan_name
        })
        
        return jsonify({
            'success': True,
            'message': 'Subscription plan created successfully',
            'plan': plan.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plans/<int:plan_id>', methods=['PUT'])
@login_required
@system_admin_api_required
def update_plan(plan_id):
    """Update a subscription plan"""
    
    try:
        from app.models import SubscriptionPlan
        import json
        
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        data = request.get_json()
        
        # Check if plan code is being changed and if it already exists
        if 'plan_code' in data and data['plan_code'] != plan.plan_code:
            existing = SubscriptionPlan.query.filter_by(plan_code=data['plan_code']).first()
            if existing:
                return jsonify({'error': 'Plan code already exists'}), 400
        
        # Update fields
        if 'plan_code' in data:
            plan.plan_code = data['plan_code']
        if 'plan_name' in data:
            plan.plan_name = data['plan_name']
        if 'description' in data:
            plan.description = data['description']
        if 'price' in data:
            plan.price = data['price']
            plan.monthly_price = data['price']  # Backward compatibility
            plan.yearly_price = data['price'] * 12
        if 'discount_percentage' in data:
            plan.discount_percentage = data['discount_percentage']
        if 'currency' in data:
            plan.currency = data['currency']
        if 'has_trial' in data:
            plan.has_trial = data['has_trial']
        if 'trial_days' in data:
            plan.trial_days = data['trial_days']
        if 'max_users' in data:
            plan.max_users = data['max_users']
        if 'max_menu_items' in data:
            plan.max_menu_items = data['max_menu_items']
        if 'max_inventory_items' in data:
            plan.max_inventory_items = data['max_inventory_items']
        if 'max_monthly_sales' in data:
            plan.max_monthly_sales = data['max_monthly_sales']
        if 'max_storage_mb' in data:
            plan.max_storage_mb = data['max_storage_mb']
        
        # Handle features
        if 'features' in data:
            features = data['features']
            if isinstance(features, list):
                plan.features = json.dumps(features)
            else:
                plan.features = features
        
        # Boolean flags
        if 'advanced_reports' in data:
            plan.advanced_reports = data['advanced_reports']
        if 'multi_location' in data:
            plan.multi_location = data['multi_location']
        if 'api_access' in data:
            plan.api_access = data['api_access']
        if 'priority_support' in data:
            plan.priority_support = data['priority_support']
        if 'custom_branding' in data:
            plan.custom_branding = data['custom_branding']
        if 'data_export' in data:
            plan.data_export = data['data_export']
        if 'display_order' in data:
            plan.display_order = data['display_order']
        if 'is_featured' in data:
            plan.is_featured = data['is_featured']
        if 'is_active' in data:
            plan.is_active = data['is_active']
        if 'is_visible' in data:
            plan.is_visible = data['is_visible']
        if 'badge_text' in data:
            plan.badge_text = data['badge_text']
        if 'badge_color' in data:
            plan.badge_color = data['badge_color']
        
        plan.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log the action
        from app.auth import log_audit
        log_audit('update', 'subscription_plan', plan.id, {
            'plan_code': plan.plan_code,
            'plan_name': plan.plan_name
        })
        
        return jsonify({
            'success': True,
            'message': 'Subscription plan updated successfully',
            'plan': plan.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plans/<int:plan_id>', methods=['DELETE'])
@login_required
@system_admin_api_required
def delete_plan(plan_id):
    """Delete a subscription plan"""
    
    try:
        from app.models import SubscriptionPlan
        
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        
        # Check if any businesses are using this plan
        businesses_count = Business.query.filter_by(subscription_plan=plan.plan_code).count()
        if businesses_count > 0:
            return jsonify({
                'error': f'Cannot delete plan. {businesses_count} business(es) are currently using this plan.'
            }), 400
        
        plan_code = plan.plan_code
        plan_name = plan.plan_name
        
        db.session.delete(plan)
        db.session.commit()
        
        # Log the action
        from app.auth import log_audit
        log_audit('delete', 'subscription_plan', plan_id, {
            'plan_code': plan_code,
            'plan_name': plan_name
        })
        
        return jsonify({
            'success': True,
            'message': 'Subscription plan deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/api/plans/<int:plan_id>/toggle-status', methods=['POST'])
@login_required
@system_admin_api_required
def toggle_plan_status(plan_id):
    """Toggle plan active status"""
    
    try:
        from app.models import SubscriptionPlan
        
        plan = SubscriptionPlan.query.get_or_404(plan_id)
        plan.is_active = not plan.is_active
        plan.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Plan {"activated" if plan.is_active else "deactivated"} successfully',
            'is_active': plan.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
