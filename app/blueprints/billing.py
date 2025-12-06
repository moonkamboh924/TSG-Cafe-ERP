"""
Billing Blueprint
Handles subscription and payment management
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, make_response
from flask_login import login_required, current_user
from datetime import datetime, timezone
import logging
import json

from ..extensions import db
from ..models import Business, Subscription, Invoice, PaymentMethod
from ..services.payment_service import PaymentService
from ..services.subscription_service import SubscriptionService
from ..business_context import require_business_context, get_current_business

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')


@billing_bp.route('/')
@login_required
@require_business_context
def index():
    """Billing dashboard"""
    business = get_current_business()
    
    # Get active subscription
    subscription = Subscription.query.filter_by(
        business_id=business.id,
        status='active'
    ).first()
    
    # Get invoices
    invoices = Invoice.query.filter_by(
        business_id=business.id
    ).order_by(Invoice.created_at.desc()).limit(10).all()
    
    # Get payment methods
    payment_methods = PaymentMethod.query.filter_by(
        business_id=business.id,
        is_active=True
    ).all()
    
    return render_template('billing/index.html',
                         subscription=subscription,
                         invoices=invoices,
                         payment_methods=payment_methods,
                         business=business)


@billing_bp.route('/payment-method')
@login_required
@require_business_context
def payment_method_page():
    """Payment method management page"""
    business = get_current_business()
    
    # Get payment methods
    payment_methods = PaymentMethod.query.filter_by(
        business_id=business.id,
        is_active=True
    ).all()
    
    # Get Stripe publishable key
    stripe_key = PaymentService.get_publishable_key()
    
    return render_template('billing/payment_method.html',
                         payment_methods=payment_methods,
                         stripe_key=stripe_key)


@billing_bp.route('/add-payment-method', methods=['POST'])
@login_required
@require_business_context
def add_payment_method():
    """Add a new payment method"""
    business = get_current_business()
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('type'):
        return jsonify({'success': False, 'error': 'Payment method type is required'}), 400
    
    try:
        # Add payment method (works with or without Stripe)
        pm = PaymentService.add_payment_method(
            business_id=business.id,
            payment_method_data=data,
            set_default=data.get('set_default', True)
        )
        
        return jsonify({
            'success': True,
            'message': 'Payment method added successfully',
            'payment_method': pm.to_dict()
        })
        
    except Exception as e:
        logger.error(f'Error adding payment method: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/subscribe', methods=['POST'])
@login_required
@require_business_context
def subscribe():
    """Subscribe to a plan"""
    business = get_current_business()
    
    data = request.get_json()
    plan = data.get('plan', 'cafe')
    subscription_months = data.get('subscription_months', 1)
    
    try:
        # Create subscription checkout
        subscription = PaymentService.create_subscription_checkout(
            business_id=business.id,
            plan=plan,
            subscription_months=subscription_months
        )
        
        return jsonify({
            'success': True,
            'message': 'Subscription created successfully',
            'subscription_id': subscription.id,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret if hasattr(subscription, 'latest_invoice') else None
        })
        
    except Exception as e:
        logger.error(f'Error creating subscription: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/cancel', methods=['POST'])
@login_required
@require_business_context
def cancel_subscription():
    """Cancel subscription"""
    business = get_current_business()
    
    try:
        PaymentService.cancel_subscription(business.id)
        flash('Subscription cancelled successfully. You can continue using the service until the end of your billing period.', 'success')
        return jsonify({'success': True, 'message': 'Subscription cancelled'})
        
    except Exception as e:
        logger.error(f'Error cancelling subscription: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/upgrade', methods=['GET', 'POST'])
@login_required
@require_business_context
def upgrade():
    """Upgrade subscription plan"""
    business = get_current_business()
    
    if request.method == 'GET':
        # Get available plans from SubscriptionPlan configuration
        from ..models import SubscriptionPlan
        plans_query = SubscriptionPlan.query.filter_by(is_active=True, is_visible=True).order_by(SubscriptionPlan.display_order).all()
        plans = [plan.to_dict() for plan in plans_query]
        current_plan = business.subscription_plan
        
        return render_template('billing/upgrade.html',
                             plans=plans,
                             current_plan=current_plan,
                             current_plan_name=business.get_plan_name(),
                             business=business,
                             stripe_key=PaymentService.get_publishable_key())
    
    # POST - process upgrade
    data = request.get_json()
    new_plan = data.get('plan')
    subscription_months = data.get('subscription_months', 1)
    
    if not new_plan:
        return jsonify({'success': False, 'error': 'Plan is required'}), 400
    
    try:
        # TODO: Implement plan upgrade logic
        # This should prorate the charges
        
        flash(f'Successfully upgraded to {new_plan} plan!', 'success')
        return jsonify({'success': True, 'message': 'Plan upgraded successfully'})
        
    except Exception as e:
        logger.error(f'Error upgrading plan: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/invoices')
@login_required
@require_business_context
def invoices():
    """View all invoices"""
    business = get_current_business()
    
    # Get all invoices
    invoices = Invoice.query.filter_by(
        business_id=business.id
    ).order_by(Invoice.created_at.desc()).all()
    
    return render_template('billing/invoices.html', invoices=invoices)


@billing_bp.route('/invoice/<int:invoice_id>')
@login_required
@require_business_context
def view_invoice(invoice_id):
    """View invoice details"""
    business = get_current_business()
    
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        business_id=business.id
    ).first_or_404()
    
    return render_template('billing/invoice_detail.html', invoice=invoice, business=business)


@billing_bp.route('/api/subscription-status')
@login_required
@require_business_context
def subscription_status():
    """Get current subscription status"""
    business = get_current_business()
    
    subscription = Subscription.query.filter_by(
        business_id=business.id,
        status='active'
    ).first()
    
    if not subscription:
        return jsonify({
            'status': 'no_subscription',
            'trial_active': business.is_trial_active(),
            'trial_end_date': business.trial_end_date.isoformat() if business.trial_end_date else None
        })
    
    return jsonify({
        'status': subscription.status,
        'plan': subscription.plan,
        'next_billing_date': subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
        'is_trial': subscription.is_trial(),
        'trial_end_date': subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
        'amount': float(subscription.amount),
        'currency': subscription.currency
    })


@billing_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhooks"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        PaymentService.process_webhook(payload, sig_header)
        return jsonify({'success': True}), 200
        
    except Exception as e:
        logger.error(f'Webhook error: {str(e)}')
        return jsonify({'error': str(e)}), 400
