"""
Seed data for initial database setup
"""
from app.models import (
    MenuCategory, InventoryItem, Supplier, SystemSetting,
    BillTemplate, db
)
from datetime import datetime, timezone

def seed_database():
    """Add initial seed data to the database"""
    
    # Check if data already exists
    if MenuCategory.query.first() is not None:
        print("Database already has data, skipping seed...")
        return
    
    print("Seeding database with initial data...")
    
    # System Settings
    settings = [
        ('restaurant_name', 'TSG Cafe ERP', 'Restaurant/Business Name'),
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
    categories = [
        ('Beverages', 'Hot and cold drinks', 1),
        ('Food', 'Main dishes and snacks', 2),
        ('Desserts', 'Sweet items', 3),
        ('Breakfast', 'Morning items', 4),
    ]
    
    for name, description, sort_order in categories:
        category = MenuCategory(
            name=name,
            description=description,
            sort_order=sort_order,
            is_active=True
        )
        db.session.add(category)
    
    # Inventory Units
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
    bill_template = BillTemplate(
        name='Default Template',
        header_text='TSG Cafe ERP',
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
        print("✅ Database seeded successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error seeding database: {str(e)}")
        raise
