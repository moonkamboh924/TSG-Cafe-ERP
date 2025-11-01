from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(10), unique=True, nullable=True, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    
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
        """Check if this user can be edited by the given user"""
        # Muhammad Mamoon (MM001) can edit any user including protected users
        if user.username == 'MM001':
            return True
        if self.is_protected:
            # Protected users can only edit themselves
            return self.id == user.id
        # Non-protected users can be edited by admins or themselves
        return user.role == 'admin' or self.id == user.id
    
    def verify_identity(self, code):
        """Verify identity for protected user operations"""
        return self.verification_code == code if self.verification_code else False
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            if datetime.now(timezone.utc) < self.account_locked_until:
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
    
    @staticmethod
    def generate_next_employee_id():
        """Generate the next employee ID in format EMP001, EMP002, etc."""
        # Get the highest employee ID number
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
    name = db.Column(db.String(100), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
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
    def generate_next_sku():
        """Generate the next SKU in format MENU001, MENU002, etc."""
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
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='draft', nullable=False)  # draft, submitted, received
    total = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    lines = db.relationship('PurchaseOrderLine', backref='purchase_order', lazy=True, cascade='all, delete-orphan')

class PurchaseOrderLine(db.Model):
    __tablename__ = 'purchase_order_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    qty = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    line_total = db.Column(db.Numeric(10, 2), nullable=False)
    
    item = db.relationship('MenuItem', backref='po_lines')

class InventoryLot(db.Model):
    __tablename__ = 'inventory_lots'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    qty_on_hand = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    received_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    item = db.relationship('MenuItem', backref='inventory_lots')

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    table_number = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax = db.Column(db.Numeric(10, 2), nullable=False)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    lines = db.relationship('SaleLine', backref='sale', lazy=True, cascade='all, delete-orphan')
    user = db.relationship('User', backref='sales')
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_no': self.invoice_no,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'table_number': self.table_number,
            'created_at': self.created_at.isoformat(),
            'subtotal': float(self.subtotal),
            'tax': float(self.tax),
            'total': float(self.total),
            'payment_method': self.payment_method,
            'lines': [line.to_dict() for line in self.lines]
        }

class SaleLine(db.Model):
    __tablename__ = 'sale_lines'
    
    id = db.Column(db.Integer, primary_key=True)
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
    category = db.Column(db.String(50), nullable=False)
    note = db.Column(db.String(255))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    incurred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
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
    date = db.Column(db.Date, unique=True, nullable=False, index=True)
    opening_cash = db.Column(db.Numeric(10, 2), nullable=False)
    sales_total = db.Column(db.Numeric(10, 2), nullable=False)
    expense_total = db.Column(db.Numeric(10, 2), nullable=False)
    closing_cash = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
    template_type = db.Column(db.String(20), nullable=False, default='receipt')  # receipt, invoice, kitchen
    header_name = db.Column(db.String(100), default='My Business')
    header_tagline = db.Column(db.String(200), default='Authentic Pakistani Cuisine')
    logo_filename = db.Column(db.String(255))  # Store logo file path
    show_logo = db.Column(db.Boolean, default=True)
    show_order_number = db.Column(db.Boolean, default=True)
    show_date_time = db.Column(db.Boolean, default=True)
    show_cashier = db.Column(db.Boolean, default=True)
    show_table = db.Column(db.Boolean, default=True)
    show_tax = db.Column(db.Boolean, default=True)
    footer_message = db.Column(db.Text, default='Thank you for dining with us!\nVisit us again soon.\nFollow us on social media @sangatcafe')
    show_qr_code = db.Column(db.Boolean, default=False)
    paper_size = db.Column(db.String(10), default='80mm')
    font_size = db.Column(db.String(10), default='medium')
    auto_cut = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def get_template(cls, template_type='receipt'):
        template = cls.query.filter_by(template_type=template_type).first()
        if not template:
            # Create default template if none exists
            template = cls(template_type=template_type)
            db.session.add(template)
            db.session.commit()
        return template
    
    def to_dict(self):
        return {
            'id': self.id,
            'template_type': self.template_type,
            'header_name': self.header_name,
            'header_tagline': self.header_tagline,
            'logo_filename': self.logo_filename,
            'show_logo': self.show_logo,
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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def get_setting(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @classmethod
    def set_setting(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
        else:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting

class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
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
    def generate_next_sku():
        """Generate the next SKU in format INV001, INV002, etc."""
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
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False, unique=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    credit_amount = db.Column(db.Numeric(10, 2), nullable=False)
    paid_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    remaining_amount = db.Column(db.Numeric(10, 2), nullable=False)
    credit_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, partial, paid
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
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
    credit_sale_id = db.Column(db.Integer, db.ForeignKey('credit_sales.id'), nullable=False)
    payment_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, online
    payment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = db.Column(db.Text)
    received_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
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
