import os
import hashlib
from app import create_app
from app.models import db, User
from app.utils.security_utils import SecureCredentials
from werkzeug.security import generate_password_hash

app = create_app()

# Initialize database tables on startup (for production deployment)
with app.app_context():
    db.create_all()
    
    # Seed initial data
    try:
        from seed_data import seed_database
        print("Starting seed data initialization...")
        # Pass 'Sangat Cafe' as default for this deployment
        # Users can change it in Global Settings after login
        seed_database(default_business_name='Sangat Cafe')
        print("Seed data initialization completed!")
    except Exception as e:
        print(f"ERROR: Seed data initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Create/update default admin user
    try:
        # Use secure credential system instead of environment variables
        verification_code = SecureCredentials.get_verification_code()
        admin_password = SecureCredentials.get_admin_password()
        
        # Check for old username first, then new username
        admin = User.query.filter_by(username='MMamoon001').first()
        if admin:
            # Update existing user to new username format and full permissions
            admin.username = 'MM001'
            admin.role = 'system_administrator'
            admin.is_protected = True
            admin.verification_code = verification_code
            admin.set_password(admin_password)
            admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
            db.session.commit()
        else:
            # Remove protected status from all other users first
            other_users = User.query.filter(User.username != 'MM001').all()
            for user in other_users:
                if user.is_protected:
                    user.is_protected = False
            
            admin = User.query.filter_by(username='MM001').first()
            if not admin:
                admin = User(
                    employee_id='EMP001',
                    username='MM001',
                    email='muhammad.mamoon@tsgcafe.com',
                    first_name='Muhammad',
                    last_name='Mamoon',
                    full_name='Muhammad Mamoon',
                    role='system_administrator',
                    is_active=True,
                    is_protected=True,
                    verification_code=verification_code,
                    requires_password_change=False,
                )
                admin.set_password(admin_password)
                admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
                db.session.add(admin)
                db.session.commit()
            else:
                # Update existing MM001 user with full permissions and protected status
                admin.role = 'system_administrator'
                admin.is_protected = True
                admin.verification_code = verification_code
                admin.set_password(admin_password)
                admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
                db.session.commit()
    except Exception as e:
        print(f"Error creating/updating admin user: {str(e)}")
        db.session.rollback()

# User loader is defined in app/__init__.py to avoid duplication

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create/update default admin user with proper error handling
        try:
            # Use secure credential system instead of environment variables
            verification_code = SecureCredentials.get_verification_code()
            admin_password = SecureCredentials.get_admin_password()
            
            # Check for old username first, then new username
            admin = User.query.filter_by(username='MMamoon001').first()
            if admin:
                # Update existing user to new username format and full permissions
                admin.username = 'MM001'
                admin.role = 'system_administrator'
                admin.is_protected = True
                admin.verification_code = verification_code
                admin.set_password(admin_password)
                admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
                db.session.commit()
                print("Updated admin username from MMamoon001 to MM001 with enhanced security")
            else:
                # Remove protected status from all other users first
                other_users = User.query.filter(User.username != 'MM001').all()
                for user in other_users:
                    if user.is_protected:
                        user.is_protected = False
                        print(f"Removed protected status from user: {user.username}")
                
                admin = User.query.filter_by(username='MM001').first()
                if not admin:
                    admin = User(
                        employee_id='EMP001',
                        username='MM001',
                        email='muhammad.mamoon@tsgcafe.com',
                        first_name='Muhammad',
                        last_name='Mamoon',
                        full_name='Muhammad Mamoon',
                        role='system_administrator',
                        is_active=True,
                        is_protected=True,
                        verification_code=verification_code,
                        requires_password_change=False,
                    )
                    admin.set_password(admin_password)
                    admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
                    db.session.add(admin)
                    db.session.commit()
                    print("Default system administrator created with enhanced security credentials")
                else:
                    # Update existing MM001 user with full permissions and protected status
                    admin.role = 'system_administrator'
                    admin.is_protected = True
                    admin.verification_code = verification_code
                    admin.set_password(admin_password)
                    admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
                    db.session.commit()
                    print("Updated MM001 to system administrator with enhanced security")
        except Exception as e:
            print(f"Error creating/updating admin user: {str(e)}")
            db.session.rollback()
            
            # Fallback to default credentials if secure system fails
            try:
                verification_code = "Ma!1311"
                admin_password = "Sangat@1311"
                admin = User.query.filter_by(username='MM001').first()
                if admin:
                    admin.verification_code = verification_code
                    admin.set_password(admin_password)
                    db.session.commit()
                    print("Fallback: Admin credentials set to default values")
            except Exception as fallback_error:
                print(f"Fallback failed: {str(fallback_error)}")
                db.session.rollback()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
