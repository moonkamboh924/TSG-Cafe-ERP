"""
Basic seed data for TSG Cafe ERP - Multi-tenant
Creates a demo business and admin user for testing
"""
from app import create_app
from app.models import db, Business, User

def create_demo_data():
    """Create basic demo data for multi-tenant ERP"""
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if demo business exists
        demo_business = Business.query.filter_by(business_name='Demo Restaurant').first()
        if not demo_business:
            # Create demo business
            demo_business = Business(
                business_name='Demo Restaurant',
                owner_email='demo@tsgcafe.com',
                subscription_plan='free',
                is_active=True
            )
            db.session.add(demo_business)
            db.session.commit()
            print("✓ Created demo business")
        
        # Check if demo admin exists
        demo_admin = User.query.filter_by(username='DEMO001').first()
        if not demo_admin:
            # Create demo admin user
            demo_admin = User(
                business_id=demo_business.id,
                employee_id='EMP001',
                username='DEMO001',
                email='demo@tsgcafe.com',
                first_name='Demo',
                last_name='Admin',
                full_name='Demo Admin',
                role='admin',
                is_owner=True,
                is_active=True,
                requires_password_change=False,
                email_verified=True
            )
            demo_admin.set_password('demo123')
            demo_admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
            
            db.session.add(demo_admin)
            db.session.commit()
            
            # Update business owner_id
            demo_business.owner_id = demo_admin.id
            db.session.commit()
            
            print("✓ Created demo admin user")
            print("  Username: DEMO001")
            print("  Password: demo123")
        
        print("✓ Demo data ready!")

if __name__ == '__main__':
    create_demo_data()
