from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

# ============================================================================
# MULTI-TENANT: BUSINESS MODEL
# ============================================================================

class Business(db.Model):
    """Business/Tenant model - each registered business is isolated"""
    __tablename__ = 'businesses'
    
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(200), unique=True, nullable=False, index=True)
    owner_email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, nullable=True)  # Will be set after user creation
    
    # Subscription & Status
    subscription_plan = db.Column(db.String(20), default='free', nullable=False)  # free, basic, premium
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    trial_end_date = db.Column(db.DateTime, nullable=True)  # Trial period expiration
    subscription_status = db.Column(db.String(20), default='trial', nullable=False)  # trial, active, past_due, cancelled, suspended
    stripe_customer_id = db.Column(db.String(100), nullable=True, index=True)  # Stripe customer ID
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships with CASCADE DELETE
    users = db.relationship('User', backref='business', lazy=True, foreign_keys='User.business_id', cascade='all, delete-orphan')
    menu_categories = db.relationship('MenuCategory', backref='business_ref', lazy=True, cascade='all, delete-orphan')
    menu_items = db.relationship('MenuItem', backref='business_ref', lazy=True, cascade='all, delete-orphan')
    inventory_items = db.relationship('InventoryItem', backref='business_ref', lazy=True, cascade='all, delete-orphan')
    sales = db.relationship('Sale', backref='business_ref', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='business_ref', lazy=True, cascade='all, delete-orphan')
    credit_sales = db.relationship('CreditSale', backref='business_ref', lazy=True, cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='business_sub', lazy=True, cascade='all, delete-orphan')
    
    def is_trial_active(self):
        """Check if business is still in trial period"""
        if self.subscription_status == 'trial' and self.trial_end_date:
            return datetime.now(timezone.utc) < self.trial_end_date
        return False
    
    def is_subscription_active(self):
        """Check if subscription is active and business can use the system"""
        if self.subscription_status in ['trial', 'active']:
            if self.subscription_status == 'trial':
                return self.is_trial_active()
            return True
        return False
    
    def get_plan_limits(self):
        """Get plan limits based on subscription plan"""
        from .services.subscription_service import SubscriptionService
        return SubscriptionService.get_plan_limits(self.subscription_plan)
    
    def get_plan_name(self):
        """Get current plan name from SubscriptionPlan configuration"""
        plan_config = SubscriptionPlan.query.filter_by(plan_code=self.subscription_plan).first()
        return plan_config.plan_name if plan_config else self.subscription_plan.capitalize()
    
    def get_plan_details(self):
        """Get full plan details from SubscriptionPlan configuration"""
        return SubscriptionPlan.query.filter_by(plan_code=self.subscription_plan).first()
    
    def get_plan_pricing(self):
        """Get pricing details from plan configuration"""
        plan_config = self.get_plan_details()
        if plan_config:
            return {
                'monthly_price': float(plan_config.monthly_price),
                'yearly_price': float(plan_config.yearly_price),
                'currency': plan_config.currency,
                'yearly_discount': plan_config.calculate_yearly_discount()
            }
        return None
    
    def get_plan_features(self):
        """Get features list from plan configuration"""
        plan_config = self.get_plan_details()
        return plan_config.get_features_list() if plan_config else []
    
    def get_plan_limits_detailed(self):
        """Get detailed limits from plan configuration"""
        plan_config = self.get_plan_details()
        if plan_config:
            return {
                'max_users': plan_config.max_users,
                'max_menu_items': plan_config.max_menu_items,
                'max_inventory_items': plan_config.max_inventory_items,
                'max_monthly_sales': plan_config.max_monthly_sales,
                'max_storage_mb': plan_config.max_storage_mb,
                'advanced_reports': plan_config.advanced_reports,
                'multi_location': plan_config.multi_location,
                'api_access': plan_config.api_access,
                'priority_support': plan_config.priority_support,
                'custom_branding': plan_config.custom_branding,
                'data_export': plan_config.data_export
            }
        return None
    
    def to_dict(self):
        plan_config = self.get_plan_details()
        result = {
            'id': self.id,
            'business_name': self.business_name,
            'owner_email': self.owner_email,
            'subscription_plan': self.subscription_plan,
            'plan_name': self.get_plan_name(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
        
        # Add plan details if available
        if plan_config:
            result.update({
                'plan_details': {
                    'name': plan_config.plan_name,
                    'description': plan_config.description,
                    'pricing': self.get_plan_pricing(),
                    'features': self.get_plan_features(),
                    'limits': self.get_plan_limits_detailed(),
                    'has_trial': plan_config.has_trial,
                    'trial_days': plan_config.trial_days,
                    'is_featured': plan_config.is_featured,
                    'badge_text': plan_config.badge_text,
                    'badge_color': plan_config.badge_color
                }
            })
        
        return result

# ============================================================================
# USER & AUTHENTICATION MODELS
# ============================================================================

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    employee_id = db.Column(db.String(10), nullable=True, index=True)  # Unique per business
    username = db.Column(db.String(80), nullable=False, index=True)  # Unique per business
    email = db.Column(db.String(120), nullable=False, index=True)  # Unique per business
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    is_owner = db.Column(db.Boolean, default=False, nullable=False)  # First user of business
    
    # Enhanced employee fields
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(50))
    designation = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    
    # System fields
    profile_picture = db.Column(db.String(255))
    is_protected = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    requires_password_change = db.Column(db.Boolean, default=True, nullable=False)
    verification_code = db.Column(db.String(20))  # For protected user verification
    
    # Security fields
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    account_locked_until = db.Column(db.DateTime, nullable=True)
    last_login = db.Column(db.DateTime, nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(100), nullable=True)
    
    # OAuth fields
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', 'facebook', etc.
    
    # Navigation permissions (JSON string)
    navigation_permissions = db.Column(db.Text)  # JSON array of allowed navigation items
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission):
        """Check if user has specific permission based on role and navigation permissions"""
        # Admin and system_administrator always have all permissions
        if self.role in ['admin', 'system_administrator']:
            return True
            
        # Check navigation permissions for specific tabs
        if self.navigation_permissions:
            try:
                import json
                nav_perms = json.loads(self.navigation_permissions)
                # If user has access to a navigation tab, they get full access to that functionality
                for nav_perm in nav_perms:
                    if permission.startswith(nav_perm):
                        return True
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Fallback to role-based permissions
        role_permissions = {
            'manager': ['pos.view', 'pos.create', 'menu.view', 'menu.create', 'menu.edit', 
                       'inventory.view', 'finance.view', 'reports.view'],
            'cashier': ['pos.view', 'pos.create', 'menu.view'],
            'inventory': ['inventory.view', 'inventory.create', 'inventory.edit', 'menu.view'],
            'finance': ['finance.view', 'finance.create', 'finance.edit', 'reports.view'],
            'viewer': ['dashboard.view', 'reports.view']
        }
        
        user_perms = role_permissions.get(self.role, [])
        return permission in user_perms
    
    def can_be_edited_by(self, user):
        """Check if this user can be edited by another user"""
        # MM001 account cannot be edited by anyone (including itself)
        if self.username == 'MM001':
            return False
        
        # Muhammad Mamoon (MM001) can edit any other user including protected users
        if user.username == 'MM001':
            return True
        
        # Protected users can only be edited by MM001
        if self.is_protected:
            return False
        
        # System administrators can edit other system administrators (except protected ones)
        if user.role == 'system_administrator' and self.role == 'system_administrator':
            return True
        
        # Users can edit themselves (if not protected)
        if user.id == self.id:
            return True
        
        return False
    
    def verify_identity(self, code):
        """Verify identity for protected user operations"""
        return self.verification_code == code if self.verification_code else False
    
    def is_system_administrator(self):
        """Check if user is the system administrator"""
        return self.role == 'system_administrator' and self.username == 'MM001'
    
    def has_super_admin_privileges(self):
        """Check if user has super admin privileges"""
        return self.is_system_administrator() and self.is_protected
    
    def can_access_system_admin_panel(self):
        """Check if user can access system admin panel"""
        return self.role == 'system_administrator' and self.is_active
    
    def generate_verification_code(self):
        """Generate a new verification code for protected operations"""
        import secrets
        import string
        self.verification_code = ''.join(secrets.choice(string.digits) for _ in range(6))
        return self.verification_code
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            # Ensure both datetimes are timezone-aware for comparison
            current_time = datetime.now(timezone.utc)
            lock_until = self.account_locked_until
            
            # If lock_until is timezone-naive, assume it's UTC
            if lock_until.tzinfo is None:
                lock_until = lock_until.replace(tzinfo=timezone.utc)
            
            if current_time < lock_until:
                return True
            else:
                # Lock period expired, reset
                self.account_locked_until = None
                self.failed_login_attempts = 0
                return False
        return False
    
    def increment_failed_login(self):
        """Increment failed login attempts and lock account if threshold reached"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:  # Lock after 5 failed attempts
            self.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    def reset_failed_login(self):
        """Reset failed login attempts on successful login"""
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login = datetime.now(timezone.utc)
    
    def set_navigation_permissions(self, permissions_list):
        """Set navigation permissions as JSON"""
        import json
        self.navigation_permissions = json.dumps(permissions_list) if permissions_list else None
    
    def get_navigation_permissions(self):
        """Get navigation permissions as list"""
        if self.navigation_permissions:
            try:
                import json
                return json.loads(self.navigation_permissions)
            except (ValueError, TypeError, json.JSONDecodeError):
                return []
        return []
    
    def has_navigation_permission(self, permission):
        """Check if user has a specific navigation permission"""
        # System administrators have access to all system admin navigation areas
        if self.role == 'system_administrator':
            return True
        
        # Get user's navigation permissions
        user_permissions = self.get_navigation_permissions()
        return permission in user_permissions
    
    @staticmethod
    def generate_next_employee_id(business_id=None):
        """Generate the next employee ID in format EMP001, EMP002, etc."""
        # MULTI-TENANT: Get the highest employee ID number for this business
        if business_id:
            last_user = User.query.filter(
                User.business_id == business_id,
                User.employee_id.like('EMP%')
            ).order_by(User.employee_id.desc()).first()
        else:
            last_user = User.query.filter(User.employee_id.like('EMP%')).order_by(User.employee_id.desc()).first()
        
        if last_user and last_user.employee_id:
            try:
                last_num = int(last_user.employee_id[3:])  # Extract number after 'EMP'
                next_id = last_num + 1
            except (ValueError, IndexError):
                next_id = 1
        else:
            next_id = 1
        
        return f"EMP{next_id:03d}"
    
    @staticmethod
    def generate_username(first_name, last_name, employee_id):
        """Generate username: FirstChar + FirstChar + EmpID (e.g., MM001)"""
        first_char = first_name[0].upper() if first_name else 'X'
        last_char = last_name[0].upper() if last_name else 'X'
        emp_num = employee_id[3:] if employee_id.startswith('EMP') else employee_id
        return f"{first_char}{last_char}{emp_num}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'department': self.department,
            'designation': self.designation,
            'phone': self.phone,
            'address': self.address,
            'profile_picture': self.profile_picture,
            'is_protected': self.is_protected,
            'is_active': self.is_active,
            'requires_password_change': self.requires_password_change,
            'navigation_permissions': self.get_navigation_permissions(),
            'created_at': self.created_at.isoformat()
        }

class MenuCategory(db.Model):
    __tablename__ = 'menu_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    name = db.Column(db.String(100), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    items = db.relationship('MenuItem', backref='category', lazy=True, cascade='all, delete-orphan')

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    sku = db.Column(db.String(50), nullable=False, index=True)  # Unique per business
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), default=0.16)  # 16% default tax
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    recipe_items = db.relationship('MenuRecipe', backref='menu_item', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_next_sku(business_id=None):
        """Generate the next SKU in format MENU001, MENU002, etc."""
        # MULTI-TENANT: Get the highest SKU for this business
        if business_id:
            last_item = MenuItem.query.filter(
                MenuItem.business_id == business_id,
                MenuItem.sku.like('MENU%')
            ).order_by(MenuItem.sku.desc()).first()
        else:
            last_item = MenuItem.query.filter(MenuItem.sku.like('MENU%')).order_by(MenuItem.sku.desc()).first()
        
        if last_item and last_item.sku:
            try:
                last_num = int(last_item.sku[4:])  # Extract number after 'MENU'
                next_id = last_num + 1
            except (ValueError, IndexError):
                next_id = 1
        else:
            next_id = 1
        
        return f"MENU{next_id:03d}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'category_id': self.category_id,
            'category': self.category.name if self.category else None,
            'price': float(self.price),
            'tax_rate': float(self.tax_rate * 100),  # Convert to percentage
            'is_active': self.is_active,
            'recipe_items': [recipe.to_dict() for recipe in self.recipe_items],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    po_number = db.Column(db.String(50), nullable=False, index=True)  # Unique per business
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft, submitted, received
    total = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    lines = db.relationship('PurchaseOrderLine', backref='purchase_order', lazy=True, cascade='all, delete-orphan')

class PurchaseOrderLine(db.Model):
    __tablename__ = 'purchase_order_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    qty = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    
    item = db.relationship('MenuItem', backref='po_lines')

class InventoryLot(db.Model):
    __tablename__ = 'inventory_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id', ondelete='CASCADE'), nullable=False)
    qty_on_hand = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    received_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    item = db.relationship('MenuItem', backref='inventory_lots')

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    invoice_no = db.Column(db.String(50), nullable=False, index=True)  # Unique per business
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    table_number = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    service_charge = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    tax = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    lines = db.relationship('SaleLine', backref='sale', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='sales')
    
    def to_dict(self):
        from app.utils.timezone_utils import convert_utc_to_local
        # Convert UTC timestamp to local timezone for display
        local_time = convert_utc_to_local(self.created_at) if self.created_at else None
        
        return {
            'id': self.id,
            'invoice_no': self.invoice_no,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'table_number': self.table_number,
            'created_at': local_time.isoformat() if local_time else None,
            'subtotal': float(self.subtotal),
            'service_charge': float(self.service_charge) if self.service_charge else 0,
            'tax': float(self.tax),
            'total': float(self.total),
            'payment_method': self.payment_method,
            'lines': [line.to_dict() for line in self.lines]
        }

class SaleLine(db.Model):
    __tablename__ = 'sale_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    qty = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    
    item = db.relationship('MenuItem', backref='sale_lines')
    
    def to_dict(self):
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.item.name,
            'qty': float(self.qty),
            'unit_price': float(self.unit_price),
            'line_total': float(self.line_total)
        }

class Expense(db.Model):
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    category = db.Column(db.String(50), nullable=False)
    note = db.Column(db.String(255))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    incurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    user = db.relationship('User', backref='expenses')
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'note': self.note,
            'amount': float(self.amount),
            'incurred_at': self.incurred_at.isoformat(),
            'user': self.user.full_name
        }

class DailyClosing(db.Model):
    __tablename__ = 'daily_closings'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    opening_cash = db.Column(db.Numeric(10, 2), nullable=False)
    sales_total = db.Column(db.Numeric(10, 2), nullable=False)
    expense_total = db.Column(db.Numeric(10, 2), nullable=False)
    closing_cash = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    user = db.relationship('User', backref='daily_closings')
    
    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'opening_cash': float(self.opening_cash),
            'sales_total': float(self.sales_total),
            'expense_total': float(self.expense_total),
            'closing_cash': float(self.closing_cash),
            'notes': self.notes,
            'user': self.user.full_name,
            'created_at': self.created_at.isoformat()
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50), nullable=False)
    entity = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    meta_json = db.Column(db.Text)  # JSON string for additional metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    user = db.relationship('User', backref='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user.full_name if self.user else 'System',
            'action': self.action,
            'entity': self.entity,
            'entity_id': self.entity_id,
            'created_at': self.created_at.isoformat()
        }

class BillTemplate(db.Model):
    __tablename__ = 'bill_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    template_type = db.Column(db.String(20), nullable=False, default='receipt')  # receipt, invoice, kitchen
    header_name = db.Column(db.String(100), default='My Business')
    header_tagline = db.Column(db.String(200), default='Authentic Pakistani Cuisine')
    logo_filename = db.Column(db.String(255))  # Store logo file path
    show_logo = db.Column(db.Boolean, default=True)
    show_restaurant_name = db.Column(db.Boolean, default=True)
    show_order_number = db.Column(db.Boolean, default=True)
    show_date_time = db.Column(db.Boolean, default=True)
    show_cashier = db.Column(db.Boolean, default=True)
    show_table = db.Column(db.Boolean, default=True)
    show_tax = db.Column(db.Boolean, default=True)
    footer_message = db.Column(db.Text, default='')
    show_qr_code = db.Column(db.Boolean, default=False)
    paper_size = db.Column(db.String(10), default='80mm')
    font_size = db.Column(db.String(10), default='medium')
    auto_cut = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def get_template(cls, template_type='receipt', business_id=None):
        """Get bill template for specific business or current user's business"""
        # Determine business_id to use
        if business_id is None:
            try:
                from flask_login import current_user
                if current_user.is_authenticated and hasattr(current_user, 'business_id'):
                    business_id = current_user.business_id
            except:
                pass
        
        # Ensure business_id is an integer or None
        if business_id is not None:
            try:
                business_id = int(business_id)
            except (ValueError, TypeError):
                print(f"ERROR: Cannot convert business_id to int: {business_id}, type: {type(business_id)}")
                business_id = None
        
        # Use ORM query (SQLAlchemy should handle this correctly)
        try:
            if business_id is not None:
                template = cls.query.filter_by(
                    template_type=template_type,
                    business_id=business_id
                ).first()
            else:
                template = cls.query.filter_by(
                    template_type=template_type
                ).filter(cls.business_id.is_(None)).first()
            
            if template:
                return template
            else:
                # Create default template if none exists
                template = cls(
                    template_type=template_type,
                    business_id=business_id,
                    header_name='My Business',
                    header_tagline='Authentic Pakistani Cuisine',
                    show_logo=True,
                    show_restaurant_name=True,
                    show_order_number=True,
                    show_date_time=True,
                    show_cashier=True,
                    show_table=True,
                    show_tax=True,
                    footer_message='',
                    show_qr_code=False,
                    paper_size='80mm',
                    font_size='medium',
                    auto_cut=True
                )
                db.session.add(template)
                db.session.commit()
                return template
                
        except Exception as e:
            db.session.rollback()
            print(f"Error in get_template: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return a default template object even if there's an error
            return cls(
                template_type=template_type,
                business_id=business_id,
                header_name='My Business',
                header_tagline='Authentic Pakistani Cuisine',
                show_restaurant_name=True
            )
    
    def to_dict(self):
        return {
            'id': self.id,
            'template_type': self.template_type,
            'header_name': self.header_name,
            'header_tagline': self.header_tagline,
            'logo_filename': self.logo_filename,
            'show_logo': self.show_logo,
            'show_restaurant_name': self.show_restaurant_name,
            'show_order_number': self.show_order_number,
            'show_date_time': self.show_date_time,
            'show_cashier': self.show_cashier,
            'show_table': self.show_table,
            'show_tax': self.show_tax,
            'footer_message': self.footer_message,
            'show_qr_code': self.show_qr_code,
            'paper_size': self.paper_size,
            'font_size': self.font_size,
            'auto_cut': self.auto_cut,
            'updated_at': self.updated_at.isoformat() if self.updated_at and hasattr(self.updated_at, 'isoformat') else None
        }

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    key = db.Column(db.String(100), nullable=False, index=True)  # Unique per business
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def get_setting(cls, key, default=None, business_id=None):
        """Get setting value, optionally filtered by business_id"""
        # If business_id provided, filter by it
        if business_id is not None:
            setting = cls.query.filter_by(key=key, business_id=business_id).first()
        else:
            # Try to get from current user's business first
            try:
                from flask_login import current_user
                if current_user.is_authenticated and hasattr(current_user, 'business_id') and current_user.business_id:
                    setting = cls.query.filter_by(key=key, business_id=current_user.business_id).first()
                else:
                    setting = cls.query.filter_by(key=key).first()
            except:
                # Fallback to any setting with this key
                setting = cls.query.filter_by(key=key).first()
        
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, key, value, description=None, business_id=None):
        """Set setting value, optionally for specific business"""
        # If business_id provided, use it
        if business_id is not None:
            setting = cls.query.filter_by(key=key, business_id=business_id).first()
        else:
            # Try to use current user's business
            try:
                from flask_login import current_user
                if current_user.is_authenticated and hasattr(current_user, 'business_id') and current_user.business_id:
                    business_id = current_user.business_id
                    setting = cls.query.filter_by(key=key, business_id=business_id).first()
                else:
                    setting = cls.query.filter_by(key=key).first()
            except:
                setting = cls.query.filter_by(key=key).first()
        
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = cls(key=key, value=value, description=description, business_id=business_id)
            db.session.add(setting)
        db.session.commit()
        return setting

class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    sku = db.Column(db.String(50), nullable=False, index=True)  # Unique per business
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Raw Materials, Packaging, etc.
    unit = db.Column(db.String(20), nullable=False)  # kg, grams, ml, liters, pcs
    current_stock = db.Column(db.Numeric(10, 3), default=0, nullable=False)
    min_stock_level = db.Column(db.Numeric(10, 3), default=0)
    max_stock_level = db.Column(db.Numeric(10, 3), default=0)
    unit_cost = db.Column(db.Numeric(10, 2), default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    recipe_usages = db.relationship('MenuRecipe', backref='inventory_item', lazy=True)
    
    @staticmethod
    def generate_next_sku(business_id=None):
        """Generate the next SKU in format INV001, INV002, etc."""
        # MULTI-TENANT: Get the highest SKU for this business
        if business_id:
            last_item = InventoryItem.query.filter(
                InventoryItem.business_id == business_id,
                InventoryItem.sku.like('INV%')
            ).order_by(InventoryItem.sku.desc()).first()
        else:
            last_item = InventoryItem.query.filter(InventoryItem.sku.like('INV%')).order_by(InventoryItem.sku.desc()).first()
        
        if last_item and last_item.sku:
            try:
                last_num = int(last_item.sku[3:])  # Extract number after 'INV'
                next_id = last_num + 1
            except (ValueError, IndexError):
                next_id = 1
        else:
            next_id = 1
        
        return f"INV{next_id:03d}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'category': self.category,
            'unit': self.unit,
            'current_stock': float(self.current_stock),
            'min_stock_level': float(self.min_stock_level),
            'max_stock_level': float(self.max_stock_level),
            'unit_cost': float(self.unit_cost),
            'is_active': self.is_active,
            'stock_status': 'low' if self.current_stock <= self.min_stock_level else 'normal',
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class MenuRecipe(db.Model):
    __tablename__ = 'menu_recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_items.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)  # Quantity needed per menu item
    unit = db.Column(db.String(20), nullable=False)  # Unit of measurement
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'inventory_item_id': self.inventory_item_id,
            'inventory_item_name': self.inventory_item.name if self.inventory_item else None,
            'inventory_item_sku': self.inventory_item.sku if self.inventory_item else None,
            'quantity': float(self.quantity),
            'unit': self.unit,
            'current_stock': float(self.inventory_item.current_stock) if self.inventory_item else 0
        }

class CreditSale(db.Model):
    __tablename__ = 'credit_sales'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    credit_amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    remaining_amount = db.Column(db.Numeric(10, 2), nullable=False)
    credit_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, partial, paid
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    sale = db.relationship('Sale', backref=db.backref('credit_sale', uselist=False))
    creator = db.relationship('User', backref='created_credit_sales')
    payments = db.relationship('CreditPayment', backref='credit_sale', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'invoice_no': self.sale.invoice_no if self.sale else None,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'credit_amount': float(self.credit_amount),
            'paid_amount': float(self.paid_amount),
            'remaining_amount': float(self.remaining_amount),
            'credit_date': self.credit_date.isoformat(),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'notes': self.notes,
            'created_by': self.creator.full_name if self.creator else None,
            'payments': [payment.to_dict() for payment in self.payments]
        }

class CreditPayment(db.Model):
    __tablename__ = 'credit_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    credit_sale_id = db.Column(db.Integer, db.ForeignKey('credit_sales.id'), nullable=False)
    payment_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, online
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = db.Column(db.Text)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    receiver = db.relationship('User', backref='received_credit_payments')
    
    def to_dict(self):
        return {
            'id': self.id,
            'credit_sale_id': self.credit_sale_id,
            'payment_amount': float(self.payment_amount),
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat(),
            'notes': self.notes,
            'received_by': self.receiver.full_name if self.receiver else None
        }

class PasswordResetRequest(db.Model):
    """Password reset requests - admin manually approves and sets new password"""
    __tablename__ = 'password_reset_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Request details
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, completed
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Admin response
    admin_notes = db.Column(db.Text)
    new_password_set = db.Column(db.Boolean, default=False, nullable=False)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Notification for user
    user_notified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='password_requests', foreign_keys=[user_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user.email if self.user else None,
            'user_name': self.user.full_name if self.user else None,
            'status': self.status,
            'requested_at': self.requested_at.isoformat(),
            'admin_notes': self.admin_notes,
            'new_password_set': self.new_password_set,
            'user_notified': self.user_notified,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by.full_name if self.approved_by else None
        }

class AccountDeletionRequest(db.Model):
    """Account deletion requests - system administrator approves and deletes account"""
    __tablename__ = 'account_deletion_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=True, index=True)  # MULTI-TENANT
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Request details
    reason = db.Column(db.Text)  # Why user wants to delete account
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Admin response
    admin_notes = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    user = db.relationship('User', backref='deletion_requests', foreign_keys=[user_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user.email if self.user else None,
            'user_name': self.user.full_name if self.user else None,
            'reason': self.reason,
            'status': self.status,
            'requested_at': self.requested_at.isoformat(),
            'admin_notes': self.admin_notes,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by.full_name if self.approved_by else None
        }

# ============================================================================
# SYSTEM MONITORING & METRICS
# ============================================================================

class SystemMetric(db.Model):
    """Track system-wide metrics for monitoring dashboard"""
    __tablename__ = 'system_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), nullable=False, index=True)  # daily_logins, api_requests, db_queries
    metric_value = db.Column(db.Integer, default=0, nullable=False)
    metric_date = db.Column(db.Date, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Composite unique constraint to prevent duplicates
    __table_args__ = (
        db.UniqueConstraint('metric_type', 'metric_date', name='unique_metric_per_day'),
    )
    
    @classmethod
    def increment_metric(cls, metric_type, value=1):
        """Increment a metric for today"""
        today = datetime.now(timezone.utc).date()
        
        metric = cls.query.filter_by(
            metric_type=metric_type,
            metric_date=today
        ).first()
        
        if metric:
            metric.metric_value += value
        else:
            metric = cls(
                metric_type=metric_type,
                metric_value=value,
                metric_date=today
            )
            db.session.add(metric)
        
        db.session.commit()
        return metric
    
    @classmethod
    def get_metric(cls, metric_type, days=1):
        """Get metric value for the last N days"""
        start_date = datetime.now(timezone.utc).date() - timedelta(days=days-1)
        
        metrics = cls.query.filter(
            cls.metric_type == metric_type,
            cls.metric_date >= start_date
        ).all()
        
        return sum(m.metric_value for m in metrics)
    
    def to_dict(self):
        return {
            'id': self.id,
            'metric_type': self.metric_type,
            'metric_value': self.metric_value,
            'metric_date': self.metric_date.isoformat(),
            'created_at': self.created_at.isoformat()
        }

# ============================================================================
# SUBSCRIPTION & BILLING MODELS
# ============================================================================

class Subscription(db.Model):
    """Subscription records for businesses"""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    plan = db.Column(db.String(20), nullable=False)  # free, basic, premium
    status = db.Column(db.String(20), default='active', nullable=False)  # active, cancelled, past_due, suspended
    
    # Billing cycle
    billing_cycle = db.Column(db.String(20), default='monthly', nullable=False)  # monthly, yearly
    amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    
    # Dates
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)  # For cancelled subscriptions
    next_billing_date = db.Column(db.DateTime, nullable=True)
    trial_end_date = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    # Payment info
    payment_method = db.Column(db.String(50), nullable=True)  # stripe, paypal, etc.
    payment_method_id = db.Column(db.String(100), nullable=True)  # External payment method ID
    last_payment_date = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    invoices = db.relationship('Invoice', backref='subscription', lazy=True, cascade='all, delete-orphan')
    
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status == 'active' and (self.end_date is None or datetime.now(timezone.utc) < self.end_date)
    
    def is_trial(self):
        """Check if subscription is in trial period"""
        if self.trial_end_date:
            return datetime.now(timezone.utc) < self.trial_end_date
        return False
    
    def days_until_renewal(self):
        """Calculate days until next billing"""
        if self.next_billing_date:
            delta = self.next_billing_date - datetime.now(timezone.utc)
            return max(0, delta.days)
        return None
    
    def get_plan_name(self):
        """Get current plan name from SubscriptionPlan configuration"""
        plan_config = SubscriptionPlan.query.filter_by(plan_code=self.plan).first()
        return plan_config.plan_name if plan_config else self.plan.capitalize()
    
    def get_plan_details(self):
        """Get full plan details from SubscriptionPlan configuration"""
        return SubscriptionPlan.query.filter_by(plan_code=self.plan).first()
    
    def get_plan_pricing(self):
        """Get pricing from plan configuration"""
        plan_config = self.get_plan_details()
        if plan_config:
            return {
                'monthly_price': float(plan_config.monthly_price),
                'yearly_price': float(plan_config.yearly_price),
                'currency': plan_config.currency
            }
        return None
    
    def to_dict(self):
        plan_config = self.get_plan_details()
        result = {
            'id': self.id,
            'business_id': self.business_id,
            'plan': self.plan,
            'plan_name': self.get_plan_name(),
            'subscription_plan': self.plan,
            'status': self.status,
            'billing_cycle': self.billing_cycle,
            'amount': float(self.amount),
            'currency': self.currency,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'next_billing_date': self.next_billing_date.isoformat() if self.next_billing_date else None,
            'trial_end_date': self.trial_end_date.isoformat() if self.trial_end_date else None,
            'is_active': self.is_active(),
            'is_trial': self.is_trial(),
            'days_until_renewal': self.days_until_renewal()
        }
        
        # Add plan details if available
        if plan_config:
            result.update({
                'plan_description': plan_config.description,
                'plan_features': plan_config.get_features_list(),
                'plan_badge_text': plan_config.badge_text,
                'plan_badge_color': plan_config.badge_color,
                'plan_is_featured': plan_config.is_featured
            })
        
        return result

class Invoice(db.Model):
    """Invoice/billing history for subscriptions"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False, index=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Billing details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, paid, failed, refunded
    payment_status = db.Column(db.String(20), default='unpaid', nullable=False)  # unpaid, paid, partial, refunded
    
    # Dates
    billing_period_start = db.Column(db.DateTime, nullable=False)
    billing_period_end = db.Column(db.DateTime, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Payment info
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)  # External payment processor transaction ID
    payment_details = db.Column(db.Text, nullable=True)  # JSON string with additional payment details
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status != 'paid':
            return datetime.now(timezone.utc) > self.due_date
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'amount': float(self.amount),
            'currency': self.currency,
            'tax_amount': float(self.tax_amount),
            'total_amount': float(self.total_amount),
            'status': self.status,
            'payment_status': self.payment_status,
            'billing_period_start': self.billing_period_start.isoformat(),
            'billing_period_end': self.billing_period_end.isoformat(),
            'due_date': self.due_date.isoformat(),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'is_overdue': self.is_overdue(),
            'created_at': self.created_at.isoformat()
        }

class PaymentMethod(db.Model):
    """Stored payment methods for businesses"""
    __tablename__ = 'payment_methods'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Payment method details
    type = db.Column(db.String(20), nullable=False)  # card, bank_account, paypal, cash, manual
    provider = db.Column(db.String(50), nullable=False)  # stripe, paypal, manual, etc.
    provider_payment_method_id = db.Column(db.String(100), nullable=True)  # External ID from payment provider
    
    # Card/account details (masked)
    last4 = db.Column(db.String(4), nullable=True)  # Last 4 digits
    brand = db.Column(db.String(20), nullable=True)  # visa, mastercard, etc.
    exp_month = db.Column(db.Integer, nullable=True)
    exp_year = db.Column(db.Integer, nullable=True)
    cardholder_name = db.Column(db.String(100), nullable=True)
    billing_address = db.Column(db.Text, nullable=True)  # JSON or text address
    
    # Status
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def is_expired(self):
        """Check if card is expired"""
        if self.exp_month and self.exp_year:
            now = datetime.now(timezone.utc)
            return now.year > self.exp_year or (now.year == self.exp_year and now.month > self.exp_month)
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'provider': self.provider,
            'last4': self.last4,
            'brand': self.brand,
            'exp_month': self.exp_month,
            'exp_year': self.exp_year,
            'cardholder_name': self.cardholder_name,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'is_expired': self.is_expired()
        }


class SubscriptionPlan(db.Model):
    """Subscription plan configuration - manage all plan types and their features"""
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Plan identification
    plan_code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # free, basic, premium, enterprise
    plan_name = db.Column(db.String(100), nullable=False)  # Display name
    description = db.Column(db.Text, nullable=True)
    
    # Pricing (simplified - billing period handled on customer side)
    price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)  # Base monthly price
    discount_percentage = db.Column(db.Numeric(5, 2), default=0.00, nullable=False)  # Discount for longer periods
    currency = db.Column(db.String(3), default='USD', nullable=False)
    
    # Legacy fields for backward compatibility
    monthly_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    yearly_price = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    
    # Trial configuration
    has_trial = db.Column(db.Boolean, default=False, nullable=False)
    trial_days = db.Column(db.Integer, default=0, nullable=False)
    
    # Feature limits (stored as JSON)
    max_users = db.Column(db.Integer, default=-1, nullable=False)  # -1 means unlimited
    max_menu_items = db.Column(db.Integer, default=-1, nullable=False)
    max_inventory_items = db.Column(db.Integer, default=-1, nullable=False)
    max_monthly_sales = db.Column(db.Integer, default=-1, nullable=False)
    max_storage_mb = db.Column(db.Integer, default=1024, nullable=False)  # Storage limit in MB
    
    # Features (stored as JSON string)
    features = db.Column(db.Text, nullable=True)  # JSON array of feature descriptions
    
    # Advanced features flags
    advanced_reports = db.Column(db.Boolean, default=False, nullable=False)
    multi_location = db.Column(db.Boolean, default=False, nullable=False)
    api_access = db.Column(db.Boolean, default=False, nullable=False)
    priority_support = db.Column(db.Boolean, default=False, nullable=False)
    custom_branding = db.Column(db.Boolean, default=False, nullable=False)
    data_export = db.Column(db.Boolean, default=False, nullable=False)
    
    # Display settings
    display_order = db.Column(db.Integer, default=0, nullable=False)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)  # Show on pricing page
    
    # Badge/label
    badge_text = db.Column(db.String(50), nullable=True)  # e.g., "Most Popular", "Best Value"
    badge_color = db.Column(db.String(20), nullable=True)  # CSS color
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def get_features_list(self):
        """Parse features JSON string to list"""
        if self.features:
            import json
            try:
                return json.loads(self.features)
            except:
                return []
        return []
    
    def set_features_list(self, features_list):
        """Convert features list to JSON string"""
        import json
        self.features = json.dumps(features_list)
    
    def calculate_yearly_discount(self):
        """Get discount percentage (backward compatibility)"""
        return float(self.discount_percentage) if self.discount_percentage else 0
    
    def get_price_for_period(self, months=1):
        """Calculate price with discount for given billing period"""
        base_price = float(self.price) if self.price else float(self.monthly_price)
        discount = float(self.discount_percentage) if self.discount_percentage else 0
        
        # Apply discount based on period length
        if months >= 12:
            discount_multiplier = 1.0  # Full discount for 12+ months
        elif months >= 6:
            discount_multiplier = 0.66  # 2/3 discount for 6-11 months
        elif months >= 3:
            discount_multiplier = 0.33  # 1/3 discount for 3-5 months
        else:
            discount_multiplier = 0  # No discount for 1-2 months
        
        applied_discount = discount * discount_multiplier / 100
        total = base_price * months * (1 - applied_discount)
        return round(total, 2)
    
    def to_dict(self):
        base_price = float(self.price) if self.price else float(self.monthly_price)
        return {
            'id': self.id,
            'plan_code': self.plan_code,
            'plan_name': self.plan_name,
            'description': self.description,
            'price': base_price,
            'discount_percentage': float(self.discount_percentage) if self.discount_percentage else 0,
            'currency': self.currency,
            # Backward compatibility
            'monthly_price': base_price,
            'yearly_price': float(self.yearly_price) if self.yearly_price else base_price * 12,
            'has_trial': self.has_trial,
            'trial_days': self.trial_days,
            'max_users': self.max_users,
            'max_menu_items': self.max_menu_items,
            'max_inventory_items': self.max_inventory_items,
            'max_monthly_sales': self.max_monthly_sales,
            'max_storage_mb': self.max_storage_mb,
            'features': self.get_features_list(),
            'advanced_reports': self.advanced_reports,
            'multi_location': self.multi_location,
            'api_access': self.api_access,
            'priority_support': self.priority_support,
            'custom_branding': self.custom_branding,
            'data_export': self.data_export,
            'display_order': self.display_order,
            'is_featured': self.is_featured,
            'is_active': self.is_active,
            'is_visible': self.is_visible,
            'badge_text': self.badge_text,
            'badge_color': self.badge_color,
            'yearly_discount': self.calculate_yearly_discount(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PlanFeature(db.Model):
    """Plan features and limits configuration"""
    __tablename__ = 'plan_features'
    
    id = db.Column(db.Integer, primary_key=True)
    plan = db.Column(db.String(20), nullable=False, index=True)  # free, basic, premium
    feature_key = db.Column(db.String(50), nullable=False)  # max_users, max_locations, etc.
    feature_value = db.Column(db.String(100), nullable=False)  # Limit value or 'unlimited'
    feature_type = db.Column(db.String(20), default='limit', nullable=False)  # limit, boolean, string
    description = db.Column(db.String(255), nullable=True)
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('plan', 'feature_key', name='unique_plan_feature'),
    )
    
    @classmethod
    def get_feature(cls, plan, feature_key):
        """Get feature value for a specific plan"""
        feature = cls.query.filter_by(plan=plan, feature_key=feature_key).first()
        if feature:
            if feature.feature_type == 'limit':
                return int(feature.feature_value) if feature.feature_value != 'unlimited' else -1
            elif feature.feature_type == 'boolean':
                return feature.feature_value.lower() == 'true'
            return feature.feature_value
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'plan': self.plan,
            'feature_key': self.feature_key,
            'feature_value': self.feature_value,
            'feature_type': self.feature_type,
            'description': self.description
        }


