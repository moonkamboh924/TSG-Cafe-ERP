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
    
    # Plan pricing configuration by business type
    PLAN_PRICING = {
        'cafe': {
            'name': 'Cafe',
            'icon': 'fa-coffee',
            'description': 'Perfect for coffee shops and small cafes',
            'features': [
                'Up to 10 users',
                'Menu management (100 items)',
                'Basic POS system',
                'Inventory tracking',
                'Daily sales reports',
                'Email support'
            ],
            'pricing': {
                1: 29,    # 1 month
                3: 79,    # 3 months (10% discount)
                6: 149,   # 6 months (15% discount)
                12: 279   # 12 months (20% discount)
            },
            'trial_days': 14
        },
        'restaurant': {
            'name': 'Restaurant',
            'icon': 'fa-utensils',
            'description': 'Complete solution for full-service restaurants',
            'features': [
                'Up to 50 users',
                'Unlimited menu items',
                'Advanced POS with table management',
                'Inventory management',
                'Kitchen display system',
                'Multi-location support (up to 3)',
                'Advanced analytics & reports',
                'Priority support',
                'Custom branding'
            ],
            'pricing': {
                1: 79,    # 1 month
                3: 219,   # 3 months (10% discount)
                6: 409,   # 6 months (15% discount)
                12: 759   # 12 months (20% discount)
            },
            'trial_days': 14
        },
        'hotel': {
            'name': 'Hotel',
            'icon': 'fa-hotel',
            'description': 'Enterprise solution for hotels and resorts',
            'features': [
                'Unlimited users',
                'Unlimited menu items',
                'Multi-restaurant management',
                'Room service integration',
                'Banquet & catering management',
                'Unlimited locations',
                'Advanced inventory & procurement',
                'Real-time analytics dashboard',
                'API access',
                'Dedicated account manager',
                '24/7 priority support',
                'Custom integrations'
            ],
            'pricing': {
                1: 199,   # 1 month
                3: 549,   # 3 months (10% discount)
                6: 1029,  # 6 months (15% discount)
                12: 1909  # 12 months (20% discount)
            },
            'trial_days': 14
        }
    }
    
    # Subscription period configuration
    SUBSCRIPTION_PERIODS = {
        1: {
            'name': '1 Month',
            'display': 'Monthly',
            'days': 30,
            'discount': 0
        },
        3: {
            'name': '3 Months',
            'display': 'Quarterly',
            'days': 90,
            'discount': 10,
            'badge': 'Save 10%'
        },
        6: {
            'name': '6 Months',
            'display': 'Semi-Annual',
            'days': 180,
            'discount': 15,
            'badge': 'Save 15%'
        },
        12: {
            'name': '12 Months',
            'display': 'Annual',
            'days': 365,
            'discount': 20,
            'badge': 'Best Value - Save 20%',
            'popular': True
        }
    }
    
    # Plan limits configuration
    PLAN_LIMITS = {
        'cafe': {
            'max_users': 10,
            'max_menu_items': 100,
            'max_locations': 1,
            'max_tables': 20,
            'max_monthly_sales': -1,  # unlimited
            'inventory_management': True,
            'kitchen_display': False,
            'table_management': False,
            'room_service': False,
            'banquet_management': False,
            'advanced_reports': False,
            'api_access': False,
            'custom_branding': False,
            'priority_support': False,
            'data_retention_days': 180,
            'export_data': True
        },
        'restaurant': {
            'max_users': 50,
            'max_menu_items': -1,  # unlimited
            'max_locations': 3,
            'max_tables': 100,
            'max_monthly_sales': -1,  # unlimited
            'inventory_management': True,
            'kitchen_display': True,
            'table_management': True,
            'room_service': False,
            'banquet_management': False,
            'advanced_reports': True,
            'api_access': False,
            'custom_branding': True,
            'priority_support': True,
            'data_retention_days': 365,
            'export_data': True
        },
        'hotel': {
            'max_users': -1,  # unlimited
            'max_menu_items': -1,  # unlimited
            'max_locations': -1,  # unlimited
            'max_tables': -1,  # unlimited
            'max_monthly_sales': -1,  # unlimited
            'inventory_management': True,
            'kitchen_display': True,
            'table_management': True,
            'room_service': True,
            'banquet_management': True,
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
        return cls.PLAN_LIMITS.get(plan, cls.PLAN_LIMITS['cafe'])
    
    @classmethod
    def get_plan_pricing(cls, plan, subscription_months=1):
        """Get pricing for a specific plan and subscription period"""
        plan_info = cls.PLAN_PRICING.get(plan)
        if not plan_info:
            return 0
        return plan_info['pricing'].get(subscription_months, 0)
    
    @classmethod
    def calculate_monthly_price(cls, plan, subscription_months=1):
        """Calculate monthly price for a subscription period"""
        total_price = cls.get_plan_pricing(plan, subscription_months)
        return round(total_price / subscription_months, 2) if subscription_months > 0 else 0
    
    @classmethod
    def get_discount_percentage(cls, subscription_months):
        """Get discount percentage for subscription period"""
        period_info = cls.SUBSCRIPTION_PERIODS.get(subscription_months, {})
        return period_info.get('discount', 0)
    
    @classmethod
    def create_subscription(cls, business_id, plan='cafe', subscription_months=1, payment_method_id=None):
        """Create a new subscription for a business"""
        business = Business.query.get(business_id)
        if not business:
            raise ValueError('Business not found')
        
        # Get plan pricing
        amount = cls.get_plan_pricing(plan, subscription_months)
        plan_info = cls.PLAN_PRICING.get(plan, {})
        trial_days = plan_info.get('trial_days', 0)
        
        # Calculate dates
        start_date = datetime.now(timezone.utc)
        trial_end_date = start_date + timedelta(days=trial_days) if trial_days > 0 else None
        
        # Calculate next billing date based on subscription months
        period_info = cls.SUBSCRIPTION_PERIODS.get(subscription_months, {})
        billing_days = period_info.get('days', 30)
        next_billing_date = start_date + timedelta(days=billing_days)
        
        # Create subscription
        subscription = Subscription(
            business_id=business_id,
            plan=plan,
            status='active',
            billing_cycle=f'{subscription_months}_months',
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
