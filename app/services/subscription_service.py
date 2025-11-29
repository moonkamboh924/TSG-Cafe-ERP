"""
Subscription Service
Handles all subscription-related operations including:
- Plan management and limits
- Upgrades and downgrades
- Trial periods
- Billing cycles
- Feature restrictions
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import current_app
from sqlalchemy import func
from ..extensions import db
from ..models import Business, Subscription, Invoice, PaymentMethod, PlanFeature, User

class SubscriptionService:
    """Service class for subscription management"""
    
    # Plan pricing configuration
    PLAN_PRICING = {
        'free': {
            'name': 'Free',
            'monthly_price': 0,
            'yearly_price': 0,
            'trial_days': 0,
            'description': 'Perfect for getting started'
        },
        'basic': {
            'name': 'Basic',
            'monthly_price': 29,
            'yearly_price': 290,  # 2 months free
            'trial_days': 14,
            'description': 'Ideal for small restaurants'
        },
        'premium': {
            'name': 'Premium',
            'monthly_price': 99,
            'yearly_price': 990,  # 2 months free
            'trial_days': 14,
            'description': 'Complete solution for growing businesses'
        }
    }
    
    # Plan limits configuration
    PLAN_LIMITS = {
        'free': {
            'max_users': 5,
            'max_menu_items': 50,
            'max_locations': 1,
            'max_monthly_sales': 1000,
            'inventory_management': True,
            'advanced_reports': False,
            'api_access': False,
            'custom_branding': False,
            'priority_support': False,
            'data_retention_days': 90,
            'export_data': False
        },
        'basic': {
            'max_users': 25,
            'max_menu_items': 500,
            'max_locations': 3,
            'max_monthly_sales': -1,  # unlimited
            'inventory_management': True,
            'advanced_reports': True,
            'api_access': False,
            'custom_branding': True,
            'priority_support': True,
            'data_retention_days': 365,
            'export_data': True
        },
        'premium': {
            'max_users': -1,  # unlimited
            'max_menu_items': -1,  # unlimited
            'max_locations': -1,  # unlimited
            'max_monthly_sales': -1,  # unlimited
            'inventory_management': True,
            'advanced_reports': True,
            'api_access': True,
            'custom_branding': True,
            'priority_support': True,
            'data_retention_days': -1,  # unlimited
            'export_data': True
        }
    }
    
    @classmethod
    def get_plan_limits(cls, plan):
        """Get limits for a specific plan"""
        return cls.PLAN_LIMITS.get(plan, cls.PLAN_LIMITS['free'])
    
    @classmethod
    def get_plan_pricing(cls, plan, billing_cycle='monthly'):
        """Get pricing for a specific plan"""
        plan_info = cls.PLAN_PRICING.get(plan, cls.PLAN_PRICING['free'])
        price_key = 'monthly_price' if billing_cycle == 'monthly' else 'yearly_price'
        return plan_info.get(price_key, 0)
    
    @classmethod
    def create_subscription(cls, business_id, plan='free', billing_cycle='monthly', payment_method_id=None):
        """Create a new subscription for a business"""
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        # Get plan pricing
        amount = cls.get_plan_pricing(plan, billing_cycle)
        trial_days = cls.PLAN_PRICING.get(plan, {}).get('trial_days', 0)
        
        # Calculate dates
        start_date = datetime.now(timezone.utc)
        trial_end_date = start_date + timedelta(days=trial_days) if trial_days > 0 else None
        
        if billing_cycle == 'monthly':
            next_billing_date = start_date + timedelta(days=30)
        else:  # yearly
            next_billing_date = start_date + timedelta(days=365)
        
        # Create subscription
        subscription = Subscription(
            business_id=business_id,
            plan=plan,
            status='active',
            billing_cycle=billing_cycle,
            amount=Decimal(str(amount)),
            currency='USD',
            start_date=start_date,
            next_billing_date=next_billing_date if amount > 0 else None,
            trial_end_date=trial_end_date,
            payment_method_id=payment_method_id
        )
        
        db.session.add(subscription)
        
        # Update business subscription info
        business.subscription_plan = plan
        business.subscription_status = 'trial' if trial_days > 0 else 'active'
        business.trial_end_date = trial_end_date
        
        db.session.commit()
        
        return subscription
    
    @classmethod
    def upgrade_subscription(cls, business_id, new_plan, billing_cycle='monthly'):
        """Upgrade a business subscription to a higher plan"""
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        current_subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).order_by(Subscription.created_at.desc()).first()
        
        if not current_subscription:
            # No active subscription, create new one
            return cls.create_subscription(business_id, new_plan, billing_cycle)
        
        # Validate upgrade
        plan_order = ['free', 'basic', 'premium']
        current_plan_index = plan_order.index(current_subscription.plan)
        new_plan_index = plan_order.index(new_plan)
        
        if new_plan_index <= current_plan_index:
            raise ValueError('Can only upgrade to a higher plan')
        
        # Calculate prorated amount if applicable
        # For simplicity, start new subscription immediately
        current_subscription.status = 'cancelled'
        current_subscription.cancelled_at = datetime.now(timezone.utc)
        current_subscription.end_date = datetime.now(timezone.utc)
        
        # Create new subscription
        new_subscription = cls.create_subscription(business_id, new_plan, billing_cycle)
        
        return new_subscription
    
    @classmethod
    def downgrade_subscription(cls, business_id, new_plan):
        """Downgrade a business subscription to a lower plan"""
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        current_subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).order_by(Subscription.created_at.desc()).first()
        
        if not current_subscription:
            raise ValueError('No active subscription found')
        
        # Validate downgrade
        plan_order = ['free', 'basic', 'premium']
        current_plan_index = plan_order.index(current_subscription.plan)
        new_plan_index = plan_order.index(new_plan)
        
        if new_plan_index >= current_plan_index:
            raise ValueError('Can only downgrade to a lower plan')
        
        # Schedule downgrade for end of current billing period
        current_subscription.end_date = current_subscription.next_billing_date
        
        # Update business plan (will take effect at end of billing period)
        business.subscription_plan = new_plan
        
        db.session.commit()
        
        return current_subscription
    
    @classmethod
    def cancel_subscription(cls, business_id, immediate=False):
        """Cancel a business subscription"""
        current_subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).order_by(Subscription.created_at.desc()).first()
        
        if not current_subscription:
            raise ValueError('No active subscription found')
        
        current_subscription.status = 'cancelled'
        current_subscription.cancelled_at = datetime.now(timezone.utc)
        
        if immediate:
            current_subscription.end_date = datetime.now(timezone.utc)
        else:
            # Cancel at end of billing period
            current_subscription.end_date = current_subscription.next_billing_date
        
        db.session.commit()
        
        return current_subscription
    
    @classmethod
    def check_plan_limit(cls, business_id, limit_key):
        """Check if business has reached a specific plan limit"""
        business = Business.query.get(business_id)
        if not business:
            return False
        
        limits = cls.get_plan_limits(business.subscription_plan)
        limit_value = limits.get(limit_key)
        
        # If limit is -1, it's unlimited
        if limit_value == -1:
            return True
        
        # Check current usage against limit
        if limit_key == 'max_users':
            current_count = User.query.filter_by(business_id=business_id).count()
            return current_count < limit_value
        
        elif limit_key == 'max_menu_items':
            from ..models import MenuItem
            current_count = MenuItem.query.filter_by(business_id=business_id).count()
            return current_count < limit_value
        
        elif limit_key == 'max_monthly_sales':
            from ..models import Sale
            first_day = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_count = Sale.query.filter(
                Sale.business_id == business_id,
                Sale.sale_date >= first_day
            ).count()
            return current_count < limit_value
        
        # For boolean features
        elif isinstance(limit_value, bool):
            return limit_value
        
        return True
    
    @classmethod
    def has_feature(cls, business_id, feature_key):
        """Check if business plan has a specific feature"""
        business = Business.query.get(business_id)
        if not business:
            return False
        
        limits = cls.get_plan_limits(business.subscription_plan)
        return limits.get(feature_key, False)
    
    @classmethod
    def generate_invoice(cls, subscription_id):
        """Generate an invoice for a subscription billing cycle"""
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            raise ValueError('Subscription not found')
        
        # Generate unique invoice number
        invoice_number = f"INV-{subscription.business_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Calculate billing period
        if subscription.billing_cycle == 'monthly':
            billing_end = subscription.next_billing_date
            billing_start = billing_end - timedelta(days=30)
        else:
            billing_end = subscription.next_billing_date
            billing_start = billing_end - timedelta(days=365)
        
        # Calculate tax (10% for example)
        tax_rate = Decimal('0.10')
        tax_amount = subscription.amount * tax_rate
        total_amount = subscription.amount + tax_amount
        
        # Create invoice
        invoice = Invoice(
            subscription_id=subscription_id,
            business_id=subscription.business_id,
            invoice_number=invoice_number,
            amount=subscription.amount,
            currency=subscription.currency,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status='pending',
            payment_status='unpaid',
            billing_period_start=billing_start,
            billing_period_end=billing_end,
            due_date=subscription.next_billing_date
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        return invoice
    
    @classmethod
    def process_payment(cls, invoice_id, payment_method, transaction_id):
        """Process payment for an invoice"""
        invoice = Invoice.query.get(invoice_id)
        if not invoice:
            raise ValueError('Invoice not found')
        
        invoice.status = 'paid'
        invoice.payment_status = 'paid'
        invoice.paid_at = datetime.now(timezone.utc)
        invoice.payment_method = payment_method
        invoice.transaction_id = transaction_id
        
        # Update subscription last payment date
        subscription = invoice.subscription
        subscription.last_payment_date = datetime.now(timezone.utc)
        
        # Update next billing date
        if subscription.billing_cycle == 'monthly':
            subscription.next_billing_date = subscription.next_billing_date + timedelta(days=30)
        else:
            subscription.next_billing_date = subscription.next_billing_date + timedelta(days=365)
        
        db.session.commit()
        
        return invoice
    
    @classmethod
    def get_subscription_status(cls, business_id):
        """Get detailed subscription status for a business"""
        business = Business.query.get(business_id)
        if not business:
            return None
        
        subscription = Subscription.query.filter_by(
            business_id=business_id,
            status='active'
        ).order_by(Subscription.created_at.desc()).first()
        
        if not subscription:
            return {
                'has_subscription': False,
                'plan': 'free',
                'status': 'inactive'
            }
        
        return {
            'has_subscription': True,
            'plan': subscription.plan,
            'status': subscription.status,
            'is_trial': subscription.is_trial(),
            'trial_ends_at': subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
            'next_billing_date': subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
            'amount': float(subscription.amount),
            'currency': subscription.currency,
            'billing_cycle': subscription.billing_cycle,
            'days_until_renewal': subscription.days_until_renewal(),
            'limits': cls.get_plan_limits(subscription.plan)
        }
    
    @classmethod
    def get_usage_stats(cls, business_id):
        """Get current usage stats compared to plan limits"""
        business = Business.query.get(business_id)
        if not business:
            return None
        
        limits = cls.get_plan_limits(business.subscription_plan)
        
        # Get current usage
        from ..models import MenuItem, Sale
        
        user_count = User.query.filter_by(business_id=business_id).count()
        menu_item_count = MenuItem.query.filter_by(business_id=business_id).count()
        
        # Monthly sales
        first_day = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_sales = Sale.query.filter(
            Sale.business_id == business_id,
            Sale.sale_date >= first_day
        ).count()
        
        return {
            'users': {
                'current': user_count,
                'limit': limits['max_users'],
                'percentage': (user_count / limits['max_users'] * 100) if limits['max_users'] > 0 else 0
            },
            'menu_items': {
                'current': menu_item_count,
                'limit': limits['max_menu_items'],
                'percentage': (menu_item_count / limits['max_menu_items'] * 100) if limits['max_menu_items'] > 0 else 0
            },
            'monthly_sales': {
                'current': monthly_sales,
                'limit': limits['max_monthly_sales'],
                'percentage': (monthly_sales / limits['max_monthly_sales'] * 100) if limits['max_monthly_sales'] > 0 else 0
            }
        }
