"""
Subscription Management Blueprint
Handles user-facing subscription management
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
from ..extensions import db
from ..models import Business, Subscription, Invoice, PaymentMethod
from ..services.subscription_service import SubscriptionService
from ..business_context import get_current_business

bp = Blueprint('subscriptions', __name__, url_prefix='/subscriptions')

@bp.route('/')
@login_required
def index():
    """Subscription management dashboard"""
    business = get_current_business()
    if not business:
        flash('Business not found', 'error')
        return redirect(url_for('dashboard.index'))
    
    subscription_status = SubscriptionService.get_subscription_status(business.id)
    usage_stats = SubscriptionService.get_usage_stats(business.id)
    
    # Get billing history
    invoices = Invoice.query.filter_by(
        business_id=business.id
    ).order_by(Invoice.created_at.desc()).limit(10).all()
    
    return render_template('subscriptions/index.html',
                         subscription=subscription_status,
                         usage=usage_stats,
                         invoices=invoices,
                         plans=SubscriptionService.get_all_plans())

@bp.route('/api/status')
@login_required
def api_status():
    """Get subscription status via API"""
    business = get_current_business()
    if not business:
        return jsonify({'error': 'Business not found'}), 404
    
    status = SubscriptionService.get_subscription_status(business.id)
    usage = SubscriptionService.get_usage_stats(business.id)
    
    return jsonify({
        'subscription': status,
        'usage': usage
    })

@bp.route('/api/upgrade', methods=['POST'])
@login_required
def api_upgrade():
    """Upgrade subscription plan"""
    business = get_current_business()
    if not business:
        return jsonify({'error': 'Business not found'}), 404
    
    data = request.get_json()
    new_plan = data.get('plan')
    billing_cycle = data.get('billing_cycle', 'monthly')
    
    if new_plan not in ['free', 'basic', 'premium']:
        return jsonify({'error': 'Invalid plan'}), 400
    
    try:
        subscription = SubscriptionService.upgrade_subscription(
            business.id,
            new_plan,
            billing_cycle
        )
        
        return jsonify({
            'success': True,
            'message': f'Successfully upgraded to {new_plan} plan',
            'subscription': subscription.to_dict()
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to upgrade subscription'}), 500

@bp.route('/api/downgrade', methods=['POST'])
@login_required
def api_downgrade():
    """Downgrade subscription plan"""
    business = get_current_business()
    if not business:
        return jsonify({'error': 'Business not found'}), 404
    
    data = request.get_json()
    new_plan = data.get('plan')
    
    if new_plan not in ['free', 'basic', 'premium']:
        return jsonify({'error': 'Invalid plan'}), 400
    
    try:
        subscription = SubscriptionService.downgrade_subscription(
            business.id,
            new_plan
        )
        
        return jsonify({
            'success': True,
            'message': f'Subscription will be downgraded to {new_plan} plan at the end of current billing period',
            'subscription': subscription.to_dict()
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to downgrade subscription'}), 500

@bp.route('/api/cancel', methods=['POST'])
@login_required
def api_cancel():
    """Cancel subscription"""
    business = get_current_business()
    if not business:
        return jsonify({'error': 'Business not found'}), 404
    
    data = request.get_json()
    immediate = data.get('immediate', False)
    
    try:
        subscription = SubscriptionService.cancel_subscription(
            business.id,
            immediate=immediate
        )
        
        message = 'Subscription cancelled immediately' if immediate else 'Subscription will be cancelled at the end of current billing period'
        
        return jsonify({
            'success': True,
            'message': message,
            'subscription': subscription.to_dict()
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to cancel subscription'}), 500

@bp.route('/api/invoices')
@login_required
def api_invoices():
    """Get billing history"""
    business = get_current_business()
    if not business:
        return jsonify({'error': 'Business not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    invoices = Invoice.query.filter_by(
        business_id=business.id
    ).order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'invoices': [inv.to_dict() for inv in invoices.items],
        'total': invoices.total,
        'pages': invoices.pages,
        'current_page': page
    })

@bp.route('/api/invoice/<int:invoice_id>')
@login_required
def api_invoice_detail(invoice_id):
    """Get invoice details"""
    business = get_current_business()
    if not business:
        return jsonify({'error': 'Business not found'}), 404
    
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        business_id=business.id
    ).first()
    
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    return jsonify(invoice.to_dict())

@bp.route('/plans')
@login_required
def plans():
    """View available plans"""
    business = get_current_business()
    current_plan = business.subscription_plan if business else 'free'
    
    return render_template('subscriptions/plans.html',
                         plans=SubscriptionService.get_all_plans(),
                         plan_limits=SubscriptionService.PLAN_LIMITS,
                         current_plan=current_plan)

@bp.route('/change-plan/<plan>')
@login_required
def change_plan(plan):
    """Change subscription plan"""
    business = get_current_business()
    if not business:
        flash('Business not found', 'error')
        return redirect(url_for('dashboard.index'))
    
    if plan not in ['free', 'basic', 'premium']:
        flash('Invalid plan selected', 'error')
        return redirect(url_for('subscriptions.plans'))
    
    return render_template('subscriptions/change_plan.html',
                         plan=plan,
                         pricing=SubscriptionService.get_plan_pricing(plan, 1),
                         current_plan=business.subscription_plan)
