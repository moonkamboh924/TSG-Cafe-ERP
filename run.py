import os
import sys
import io
import hashlib

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from app import create_app
from app.models import db, User
from app.utils.security_utils import SecureCredentials
from werkzeug.security import generate_password_hash

print("=" * 60)
print("Starting TSG Cafe ERP System v1.0...")
print("=" * 60)

try:
    app = create_app()
    print("✓ Flask app created successfully")
except Exception as e:
    print(f"✗ ERROR creating Flask app: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Initialize database tables on startup (for production deployment)
print("Initializing database...")
try:
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")
        
        # Seed initial data (must be inside app context)
        try:
            from seed_data import seed_database
            print("Starting seed data initialization...")
            # Pass 'Sangat Cafe' as default for this deployment
            # Users can change it in Global Settings after login
            seed_database(default_business_name='Sangat Cafe')
            print("✓ Seed data initialization completed!")
        except Exception as e:
            print(f"WARNING: Seed data initialization failed: {str(e)}")
            # Don't exit on seed data failure, app can still work
        
        # Create/update default admin user (must be inside app context)
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
                        username='MM001',
                        email='admin@tsgcafe.com',
                        first_name='System',
                        last_name='Administrator',
                        full_name='System Administrator',
                        role='system_administrator',
                        is_protected=True,
                        business_id=1,
                        is_owner=True,
                        verification_code=verification_code
                    )
                    admin.set_password(admin_password)
                    admin.set_navigation_permissions(['dashboard', 'pos', 'menu', 'inventory', 'finance', 'reports', 'admin'])
                    db.session.add(admin)
                    db.session.commit()
                    print("Created MM001 system administrator with enhanced security")
                else:
                    # Update existing MM001 user with full permissions and protected status
                    # MULTI-TENANT: Ensure business_id is set
                    if not admin.business_id:
                        admin.business_id = 1  # Assign to Legacy Business
                        admin.is_owner = True
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

except Exception as e:
    print(f"✗ CRITICAL ERROR during database initialization: {str(e)}")
    import traceback
    traceback.print_exc()
    # Still expose the app object even if database init fails
    # This allows the health check to work

# For Gunicorn deployment, we don't call app.run()
# The app object is exposed for Gunicorn to use
print("✓ Application initialized successfully for production deployment")

# For direct execution (development)
if __name__ == '__main__':
    # Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
