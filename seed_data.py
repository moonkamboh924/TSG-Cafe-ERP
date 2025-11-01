"""
Seed data for initial database setup
"""
import sys
import io

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
    
    # Sample Inventory Items with different categories and units
    print("Adding sample inventory items...")
    sample_items = [
        # (SKU, Name, Category, Unit, Min Stock, Unit Cost)
        ('INV001', 'Flour', 'Raw Materials', 'kg', 10, 50),
        ('INV002', 'Sugar', 'Raw Materials', 'kg', 5, 60),
        ('INV003', 'Salt', 'Raw Materials', 'kg', 2, 30),
        ('INV004', 'Cooking Oil', 'Raw Materials', 'L', 5, 200),
        ('INV005', 'Milk', 'Raw Materials', 'L', 10, 80),
        ('INV006', 'Eggs', 'Raw Materials', 'dozen', 5, 150),
        ('INV007', 'Chicken', 'Raw Materials', 'kg', 10, 300),
        ('INV008', 'Rice', 'Raw Materials', 'kg', 20, 100),
        ('INV009', 'Disposable Cups', 'Packaging', 'pack', 10, 50),
        ('INV010', 'Napkins', 'Packaging', 'pack', 5, 30),
    ]
    
    for sku, name, category, unit, min_stock, unit_cost in sample_items:
        # Check if item already exists
        existing = InventoryItem.query.filter_by(sku=sku).first()
        if not existing:
            item = InventoryItem(
                sku=sku,
                name=name,
                category=category,
                unit=unit,
                current_stock=0,
                min_stock_level=min_stock,
                max_stock_level=min_stock * 3,
                unit_cost=unit_cost,
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
            print(f"  ✓ System Settings (7)")
        if needs_categories:
            print(f"  ✓ Menu Categories (4)")
        print(f"  ✓ Sample Inventory Items (10)")
        if needs_suppliers:
            print(f"  ✓ Suppliers (2)")
        if needs_template:
            print(f"  ✓ Bill Template")
        print("=" * 50)
    except Exception as e:
        db.session.rollback()
        print("\n" + "=" * 50)
        print(f"❌ ERROR SEEDING DATABASE: {str(e)}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        raise
