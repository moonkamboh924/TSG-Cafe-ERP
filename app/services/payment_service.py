"""
Payment Service - Stripe Integration
Handles all payment processing operations including:
- Customer management
- Payment method handling
- Subscription billing
- Webhook processing
- Invoice generation
"""

import stripe
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import current_app, url_for
from sqlalchemy import and_
from ..extensions import db
from ..models import Business, Subscription, Invoice, PaymentMethod, User
from .subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class PaymentService:
    """Service class for payment processing via Stripe"""
    
    @classmethod
    def initialize_stripe(cls):
        """Initialize Stripe with API key from config"""
        stripe.api_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            logger.warning('STRIPE_SECRET_KEY not configured')
    
    @classmethod
    def create_customer(cls, business_id, email, name=None):
        """Create a Stripe customer for a business"""
        cls.initialize_stripe()
        
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        # Check if customer already exists
        if business.stripe_customer_id:
            return business.stripe_customer_id
        
        try:
            # Create Stripe customer
            customer = stripe.Customer.create(
                email=email,
                name=name or business.business_name,
                metadata={
                    'business_id': business_id,
                    'business_name': business.business_name
                }
            )
            
            # Save customer ID to business
            business.stripe_customer_id = customer.id
            db.session.commit()
            
            logger.info(f'Stripe customer created: {customer.id} for business {business_id}')
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f'Error creating Stripe customer: {str(e)}')
            raise Exception(f'Payment service error: {str(e)}')
    
    @classmethod
    def add_payment_method(cls, business_id, payment_method_id, set_default=True):
        """Add a payment method to a business"""
        cls.initialize_stripe()
        
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        # Ensure customer exists
        if not business.stripe_customer_id:
            owner = User.query.filter_by(business_id=business_id, role='owner').first()
            cls.create_customer(business_id, owner.email if owner else business.contact_email)
        
        try:
            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=business.stripe_customer_id
            )
            
            # Set as default if requested
            if set_default:
                stripe.Customer.modify(
                    business.stripe_customer_id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )
                
                # Mark all other payment methods as not default
                PaymentMethod.query.filter_by(business_id=business_id).update({'is_default': False})
            
            # Save payment method to database
            pm = PaymentMethod(
                business_id=business_id,
                type=payment_method.type,
                provider='stripe',
                provider_payment_method_id=payment_method_id,
                last4=payment_method.card.last4 if payment_method.type == 'card' else None,
                brand=payment_method.card.brand if payment_method.type == 'card' else None,
                exp_month=payment_method.card.exp_month if payment_method.type == 'card' else None,
                exp_year=payment_method.card.exp_year if payment_method.type == 'card' else None,
                is_default=set_default,
                is_active=True
            )
            
            db.session.add(pm)
            db.session.commit()
            
            logger.info(f'Payment method added for business {business_id}')
            return pm
            
        except stripe.error.StripeError as e:
            logger.error(f'Error adding payment method: {str(e)}')
            db.session.rollback()
            raise Exception(f'Payment service error: {str(e)}')
    
    @classmethod
    def create_subscription_checkout(cls, business_id, plan, subscription_months):
        """Create a Stripe subscription for a business"""
        cls.initialize_stripe()
        
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        # Ensure customer exists
        if not business.stripe_customer_id:
            owner = User.query.filter_by(business_id=business_id, role='owner').first()
            cls.create_customer(business_id, owner.email if owner else business.contact_email)
        
        # Get pricing
        amount = SubscriptionService.get_plan_pricing(plan, subscription_months)
        plan_info = SubscriptionService.PLAN_PRICING.get(plan, {})
        
        # Calculate trial period
        trial_days = plan_info.get('trial_days', 0)
        
        try:
            # Create Stripe subscription
            subscription = stripe.Subscription.create(
                customer=business.stripe_customer_id,
                items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'{plan_info.get("name")} Plan - {subscription_months} Month(s)',
                            'description': plan_info.get('description', ''),
                        },
                        'unit_amount': int(amount * 100),  # Convert to cents
                        'recurring': {
                            'interval': 'month',
                            'interval_count': subscription_months
                        }
                    },
                }],
                trial_period_days=trial_days if trial_days > 0 else None,
                metadata={
                    'business_id': business_id,
                    'plan': plan,
                    'subscription_months': subscription_months
                }
            )
            
            # Create subscription in database
            db_subscription = SubscriptionService.create_subscription(
                business_id=business_id,
                plan=plan,
                subscription_months=subscription_months,
                payment_method_id=subscription.default_payment_method
            )
            
            # Update with Stripe subscription ID
            db_subscription.payment_method = 'stripe'
            db_subscription.payment_method_id = subscription.id
            db.session.commit()
            
            logger.info(f'Subscription created for business {business_id}: {subscription.id}')
            return subscription
            
        except stripe.error.StripeError as e:
            logger.error(f'Error creating subscription: {str(e)}')
            raise Exception(f'Payment service error: {str(e)}')
    
    @classmethod
    def create_payment_intent(cls, business_id, amount, currency='usd', description=None):
        """Create a one-time payment intent"""
        cls.initialize_stripe()
        
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        # Ensure customer exists
        if not business.stripe_customer_id:
            owner = User.query.filter_by(business_id=business_id, role='owner').first()
            cls.create_customer(business_id, owner.email if owner else business.contact_email)
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                customer=business.stripe_customer_id,
                description=description or f'Payment for {business.business_name}',
                metadata={
                    'business_id': business_id
                }
            )
            
            return intent
            
        except stripe.error.StripeError as e:
            logger.error(f'Error creating payment intent: {str(e)}')
            raise Exception(f'Payment service error: {str(e)}')
    
    @classmethod
    def cancel_subscription(cls, business_id):
        """Cancel a business subscription"""
        cls.initialize_stripe()
        
        subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).first()
        
        if not subscription:
            raise ValueError('No active subscription found')
        
        try:
            # Cancel in Stripe if payment_method_id exists (Stripe subscription ID)
            if subscription.payment_method == 'stripe' and subscription.payment_method_id:
                stripe.Subscription.cancel(subscription.payment_method_id)
            
            # Update database
            subscription.status = 'cancelled'
            subscription.cancelled_at = datetime.now(timezone.utc)
            subscription.end_date = datetime.now(timezone.utc) + timedelta(days=30)  # Grace period
            
            business = Business.query.get(business_id)
            business.subscription_status = 'cancelled'
            
            db.session.commit()
            
            logger.info(f'Subscription cancelled for business {business_id}')
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f'Error cancelling subscription: {str(e)}')
            db.session.rollback()
            raise Exception(f'Payment service error: {str(e)}')
    
    @classmethod
    def process_webhook(cls, payload, sig_header):
        """Process Stripe webhook events"""
        cls.initialize_stripe()
        
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            
            logger.info(f'Processing webhook event: {event.type}')
            
            # Handle different event types
            if event.type == 'payment_intent.succeeded':
                cls._handle_payment_succeeded(event.data.object)
            
            elif event.type == 'invoice.paid':
                cls._handle_invoice_paid(event.data.object)
            
            elif event.type == 'invoice.payment_failed':
                cls._handle_payment_failed(event.data.object)
            
            elif event.type == 'customer.subscription.updated':
                cls._handle_subscription_updated(event.data.object)
            
            elif event.type == 'customer.subscription.deleted':
                cls._handle_subscription_deleted(event.data.object)
            
            return True
            
        except ValueError as e:
            logger.error(f'Invalid webhook payload: {str(e)}')
            raise
        except stripe.error.SignatureVerificationError as e:
            logger.error(f'Invalid webhook signature: {str(e)}')
            raise
    
    @classmethod
    def _handle_payment_succeeded(cls, payment_intent):
        """Handle successful payment"""
        business_id = payment_intent.metadata.get('business_id')
        if not business_id:
            return
        
        logger.info(f'Payment succeeded for business {business_id}: {payment_intent.id}')
        
        # Update subscription status
        subscription = Subscription.query.filter_by(business_id=business_id, status='active').first()
        if subscription:
            subscription.last_payment_date = datetime.now(timezone.utc)
            
            business = Business.query.get(business_id)
            business.subscription_status = 'active'
            
            db.session.commit()
    
    @classmethod
    def _handle_invoice_paid(cls, invoice):
        """Handle paid invoice"""
        subscription_id = invoice.subscription
        if not subscription_id:
            return
        
        # Find subscription by Stripe subscription ID
        subscription = Subscription.query.filter_by(payment_method_id=subscription_id).first()
        if not subscription:
            return
        
        logger.info(f'Invoice paid for subscription {subscription.id}')
        
        # Create invoice record
        db_invoice = Invoice(
            subscription_id=subscription.id,
            business_id=subscription.business_id,
            invoice_number=invoice.number or f'INV-{datetime.now().strftime("%Y%m%d")}-{subscription.id}',
            amount=Decimal(str(invoice.amount_due / 100)),  # Convert from cents
            currency=invoice.currency.upper(),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal(str(invoice.amount_paid / 100)),
            status='paid',
            payment_status='paid',
            billing_period_start=datetime.fromtimestamp(invoice.period_start, tz=timezone.utc),
            billing_period_end=datetime.fromtimestamp(invoice.period_end, tz=timezone.utc),
            due_date=datetime.fromtimestamp(invoice.due_date, tz=timezone.utc) if invoice.due_date else datetime.now(timezone.utc),
            paid_at=datetime.now(timezone.utc),
            payment_method='stripe',
            transaction_id=invoice.payment_intent
        )
        
        db.session.add(db_invoice)
        
        # Update subscription
        subscription.status = 'active'
        subscription.last_payment_date = datetime.now(timezone.utc)
        
        # Calculate next billing date
        period_info = SubscriptionService.SUBSCRIPTION_PERIODS.get(
            int(subscription.billing_cycle.replace('_months', '')), {}
        )
        billing_days = period_info.get('days', 30)
        subscription.next_billing_date = datetime.now(timezone.utc) + timedelta(days=billing_days)
        
        # Update business status
        business = Business.query.get(subscription.business_id)
        business.subscription_status = 'active'
        
        db.session.commit()
    
    @classmethod
    def _handle_payment_failed(cls, invoice):
        """Handle failed payment"""
        subscription_id = invoice.subscription
        if not subscription_id:
            return
        
        subscription = Subscription.query.filter_by(payment_method_id=subscription_id).first()
        if not subscription:
            return
        
        logger.warning(f'Payment failed for subscription {subscription.id}')
        
        # Update subscription status
        subscription.status = 'past_due'
        
        business = Business.query.get(subscription.business_id)
        business.subscription_status = 'past_due'
        
        db.session.commit()
        
        # TODO: Send email notification to business owner
    
    @classmethod
    def _handle_subscription_updated(cls, stripe_subscription):
        """Handle subscription update"""
        subscription = Subscription.query.filter_by(
            payment_method_id=stripe_subscription.id
        ).first()
        
        if not subscription:
            return
        
        logger.info(f'Subscription updated: {subscription.id}')
        
        # Update subscription details
        subscription.status = stripe_subscription.status
        db.session.commit()
    
    @classmethod
    def _handle_subscription_deleted(cls, stripe_subscription):
        """Handle subscription cancellation"""
        subscription = Subscription.query.filter_by(
            payment_method_id=stripe_subscription.id
        ).first()
        
        if not subscription:
            return
        
        logger.info(f'Subscription cancelled: {subscription.id}')
        
        subscription.status = 'cancelled'
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.end_date = datetime.now(timezone.utc)
        
        business = Business.query.get(subscription.business_id)
        business.subscription_status = 'cancelled'
        
        db.session.commit()
    
    @classmethod
    def get_publishable_key(cls):
        """Get Stripe publishable key for frontend"""
        return current_app.config.get('STRIPE_PUBLISHABLE_KEY', '')
