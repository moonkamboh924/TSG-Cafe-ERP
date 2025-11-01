"""
Seed data for initial database setup
"""
from app.models import (
    MenuCategory, InventoryItem, Supplier, SystemSetting,
    BillTemplate, db
)
from datetime import datetime, timezone
import os

def seed_database(default_business_name=None):
    """Add initial seed data to the database"""
    
    print("=" * 50)
    print("SEED DATABASE - Starting initialization...")
    print("=" * 50)
    
    # Check if we need to seed each type of data
    settings_count = SystemSetting.query.count()
    categories_count = MenuCategory.query.count()
    suppliers_count = Supplier.query.count()
    template_count = BillTemplate.query.count()
    
    print(f"Current database state:")
    print(f"  - System Settings: {settings_count}")
    print(f"  - Menu Categories: {categories_count}")
    print(f"  - Suppliers: {suppliers_count}")
    print(f"  - Bill Templates: {template_count}")
    
    needs_settings = settings_count == 0
    needs_categories = categories_count == 0
    needs_suppliers = suppliers_count == 0
    needs_template = template_count == 0
    
    if not (needs_settings or needs_categories or needs_suppliers or needs_template):
        print("✅ Database already has all seed data, skipping...")
        print("=" * 50)
        return
    
    print("\n🌱 Seeding database with initial data...")
    
    # Get business name from environment variable or parameter or use generic default
    if default_business_name is None:
        default_business_name = os.environ.get('DEFAULT_BUSINESS_NAME', 'My Business')
    
    print(f"Using business name: {default_business_name}")
    
    # System Settings
    if needs_settings:
        print("Adding system settings...")
        settings = [
            ('restaurant_name', default_business_name, 'Restaurant/Business Name'),
            ('restaurant_subtitle', 'Powered by Trisyns Global', 'Restaurant Subtitle'),
            ('currency', 'PKR', 'Currency Symbol'),
            ('timezone', 'Asia/Karachi', 'System Timezone'),
            ('tax_rate', '0', 'Default Tax Rate (%)'),
            ('backup_frequency', 'daily', 'Automatic Backup Frequency'),
            ('language', 'en', 'System Language'),
        ]
        
        for key, value, description in settings:
            setting = SystemSetting(key=key, value=value, description=description)
            db.session.add(setting)
    
    # Menu Categories
    if needs_categories:
        print("Adding menu categories...")
        categories = [
            ('Beverages', 1),
            ('Food', 2),
            ('Desserts', 3),
            ('Breakfast', 4),
        ]
        
        for name, order_index in categories:
            category = MenuCategory(
                name=name,
                order_index=order_index,
                is_active=True
            )
            db.session.add(category)
    
    # Inventory Units (always check individually)
    print("Adding inventory units...")
    units = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('L', 'Liter'),
        ('ml', 'Milliliter'),
        ('pcs', 'Pieces'),
        ('dozen', 'Dozen'),
        ('pack', 'Pack'),
        ('box', 'Box'),
    ]
    
    for unit_name, unit_desc in units:
        # Check if unit already exists
        existing = InventoryItem.query.filter_by(unit=unit_name, category='Units').first()
        if not existing:
            item = InventoryItem(
                name=f'{unit_name} (Unit)',
                unit=unit_name,
                category='Units',
                current_stock=0,
                minimum_stock=0,
                cost_per_unit=0,
                is_active=True
            )
            db.session.add(item)
    
    # Sample Suppliers
    if needs_suppliers:
        print("Adding sample suppliers...")
        suppliers = [
            ('Local Supplier', 'local@supplier.com', '0300-1234567', 'Local Market'),
            ('Wholesale Supplier', 'wholesale@supplier.com', '0321-9876543', 'Wholesale Market'),
        ]
        
        for name, email, phone, address in suppliers:
            supplier = Supplier(
                name=name,
                email=email,
                phone=phone,
                address=address,
                is_active=True
            )
            db.session.add(supplier)
    
    # Default Bill Template
    if needs_template:
        print("Adding default bill template...")
        bill_template = BillTemplate(
            name='Default Template',
            header_text=default_business_name,
            footer_text='Thank you for your business!',
            show_logo=True,
            show_tax=False,
            is_default=True,
            is_active=True
        )
        db.session.add(bill_template)
    
    # Commit all changes
    try:
        db.session.commit()
        print("\n" + "=" * 50)
        print("✅ DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 50)
        print(f"Added:")
        if needs_settings:
            print(f"  ✓ System Settings")
        if needs_categories:
            print(f"  ✓ Menu Categories (4)")
        if needs_suppliers:
            print(f"  ✓ Suppliers (2)")
        if needs_template:
            print(f"  ✓ Bill Template")
        print(f"  ✓ Inventory Units (8)")
        print("=" * 50)
    except Exception as e:
        db.session.rollback()
        print("\n" + "=" * 50)
        print(f"❌ ERROR SEEDING DATABASE: {str(e)}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        raise
