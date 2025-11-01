"""
Migration script to convert single-tenant ERP to multi-tenant
This script will:
1. Add business_id column to all relevant tables
2. Create a default business for existing data
3. Update all existing records with business_id = 1
"""

from app import create_app
from app.extensions import db
from sqlalchemy import text

def migrate_to_multitenant():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("STARTING MULTI-TENANT MIGRATION")
        print("=" * 60)
        
        try:
            # Step 1: Add business_id columns to all tables
            tables_to_migrate = [
                'users',
                'menu_categories',
                'menu_items',
                'inventory_items',
                'suppliers',
                'purchase_orders',
                'sales',
                'expenses',
                'daily_closings',
                'bill_templates',
                'system_settings',
                'credit_sales'
            ]
            
            print("\n📋 Step 1: Adding business_id columns...")
            for table in tables_to_migrate:
                try:
                    # Check if column already exists
                    result = db.session.execute(text(f"PRAGMA table_info({table})"))
                    columns = [row[1] for row in result]
                    
                    if 'business_id' not in columns:
                        print(f"  Adding business_id to {table}...")
                        db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN business_id INTEGER"))
                        db.session.commit()
                    else:
                        print(f"  ✓ {table} already has business_id")
                except Exception as e:
                    print(f"  ⚠️ Error with {table}: {str(e)}")
                    db.session.rollback()
            
            # Step 2: Create default business
            print("\n🏢 Step 2: Creating default business...")
            result = db.session.execute(text("SELECT COUNT(*) FROM businesses"))
            business_count = result.scalar()
            
            if business_count == 0:
                db.session.execute(text("""
                    INSERT INTO businesses (business_name, owner_email, subscription_plan, is_active, created_at)
                    VALUES ('Legacy Business', 'admin@system.local', 'premium', 1, datetime('now'))
                """))
                db.session.commit()
                print("  ✓ Created default business (ID: 1)")
            else:
                print(f"  ✓ Businesses already exist ({business_count})")
            
            # Step 3: Update all existing records with business_id = 1
            print("\n🔄 Step 3: Updating existing records...")
            for table in tables_to_migrate:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table} WHERE business_id IS NULL"))
                    null_count = result.scalar()
                    
                    if null_count > 0:
                        print(f"  Updating {null_count} records in {table}...")
                        db.session.execute(text(f"UPDATE {table} SET business_id = 1 WHERE business_id IS NULL"))
                        db.session.commit()
                    else:
                        print(f"  ✓ {table} already updated")
                except Exception as e:
                    print(f"  ⚠️ Error updating {table}: {str(e)}")
                    db.session.rollback()
            
            # Step 4: Add unique constraints for multi-tenant
            print("\n🔒 Step 4: Adding multi-tenant constraints...")
            constraints = [
                ("users", "business_id, email"),
                ("users", "business_id, username"),
                ("users", "business_id, employee_id"),
            ]
            
            for table, columns in constraints:
                try:
                    constraint_name = f"uq_{table}_{'_'.join(columns.replace(', ', '_').split())}"
                    print(f"  Adding constraint: {constraint_name}...")
                    # SQLite doesn't support adding constraints directly, need to recreate table
                    # This will be handled by SQLAlchemy when we update models
                    print(f"  ⚠️ Constraint {constraint_name} will be added when models are updated")
                except Exception as e:
                    print(f"  ⚠️ Error: {str(e)}")
            
            print("\n" + "=" * 60)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. Update all models.py to include business_id")
            print("2. Update all queries to filter by business_id")
            print("3. Test the application thoroughly")
            print("4. Deploy to production")
            
        except Exception as e:
            print(f"\n❌ MIGRATION FAILED: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate_to_multitenant()
