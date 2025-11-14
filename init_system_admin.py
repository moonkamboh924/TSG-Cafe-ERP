"""
Initialize System Administrator Account
Creates or updates the default system administrator account with enhanced security
"""
import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.extensions import db
from app.models import User, Business, SystemSetting

def init_system_admin():
    """Initialize or update the system administrator account"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("INITIALIZING SYSTEM ADMINISTRATOR ACCOUNT")
        print("=" * 60)
        
        # System Admin Details
        admin_details = {
            'username': 'MM001',
            'email': 'm.mamoon924@gmail.com',
            'password': 'TSG@1311!',
            'first_name': 'Muhammad',
            'last_name': 'Mamoon',
            'full_name': 'Muhammad Mamoon',
            'designation': 'ERP Owner',
            'department': 'Management',
            'phone': '03176933508',
            'role': 'system_administrator',
            'employee_id': 'SYS001'
        }
        
        try:
            # Check if system admin already exists
            existing_admin = User.query.filter_by(username='MM001').first()
            
            if existing_admin:
                print(f"[OK] Found existing system admin: {existing_admin.username}")
                print("[UPDATE] Updating system administrator details...")
                
                # Update existing admin
                existing_admin.email = admin_details['email']
                existing_admin.first_name = admin_details['first_name']
                existing_admin.last_name = admin_details['last_name']
                existing_admin.full_name = admin_details['full_name']
                existing_admin.designation = admin_details['designation']
                existing_admin.department = admin_details['department']
                existing_admin.phone = admin_details['phone']
                existing_admin.role = admin_details['role']
                existing_admin.employee_id = admin_details['employee_id']
                existing_admin.set_password(admin_details['password'])
                
                # Enhanced Security Settings
                existing_admin.is_protected = True
                existing_admin.is_active = True
                existing_admin.requires_password_change = False
                existing_admin.email_verified = True
                existing_admin.failed_login_attempts = 0
                existing_admin.account_locked_until = None
                
                # Set full navigation permissions
                existing_admin.set_navigation_permissions([
                    'dashboard', 'pos', 'menu', 'inventory', 
                    'finance', 'reports', 'admin'
                ])
                
                user = existing_admin
                action = "UPDATED"
                
            else:
                print("[NEW] Creating new system administrator account...")
                
                # Create new system admin
                user = User(
                    business_id=None,  # System admin doesn't belong to any specific business
                    employee_id=admin_details['employee_id'],
                    username=admin_details['username'],
                    email=admin_details['email'],
                    first_name=admin_details['first_name'],
                    last_name=admin_details['last_name'],
                    full_name=admin_details['full_name'],
                    designation=admin_details['designation'],
                    department=admin_details['department'],
                    phone=admin_details['phone'],
                    role=admin_details['role'],
                    is_owner=False,
                    is_protected=True,  # Enhanced Security
                    is_active=True,
                    requires_password_change=False,
                    email_verified=True,
                    failed_login_attempts=0,
                    account_locked_until=None
                )
                
                user.set_password(admin_details['password'])
                user.set_navigation_permissions([
                    'dashboard', 'pos', 'menu', 'inventory', 
                    'finance', 'reports', 'admin'
                ])
                
                db.session.add(user)
                action = "CREATED"
            
            # Create system-wide settings if they don't exist
            create_system_settings()
            
            # Commit changes
            db.session.commit()
            
            print(f"\n[SUCCESS] System Administrator Account {action} Successfully!")
            print("=" * 60)
            print("ACCOUNT DETAILS:")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Password: {admin_details['password']}")
            print(f"   Full Name: {user.full_name}")
            print(f"   Designation: {user.designation}")
            print(f"   Department: {user.department}")
            print(f"   Phone: {user.phone}")
            print(f"   Employee ID: {user.employee_id}")
            print(f"   Role: {user.role}")
            print("=" * 60)
            print("SECURITY FEATURES:")
            print(f"   Protected Account: {user.is_protected}")
            print(f"   Email Verified: {user.email_verified}")
            print(f"   Account Active: {user.is_active}")
            print(f"   Password Change Required: {user.requires_password_change}")
            print(f"   Failed Login Attempts: {user.failed_login_attempts}")
            print("=" * 60)
            print("NAVIGATION PERMISSIONS:")
            nav_perms = user.get_navigation_permissions()
            for perm in nav_perms:
                print(f"   [OK] {perm.title()}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] {str(e)}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False

def create_system_settings():
    """Create system-wide settings"""
    
    system_settings = [
        ('system_name', 'TSG Cafe ERP', 'System Name'),
        ('system_version', '1.0.0', 'System Version'),
        ('company_name', 'Trisyns Global', 'Company Name'),
        ('support_email', 'm.mamoon924@gmail.com', 'Support Email'),
        ('support_phone', '03176933508', 'Support Phone'),
        ('max_login_attempts', '5', 'Maximum Login Attempts'),
        ('account_lockout_duration', '30', 'Account Lockout Duration (minutes)'),
        ('session_timeout', '60', 'Session Timeout (minutes)'),
        ('password_min_length', '8', 'Minimum Password Length'),
        ('require_password_complexity', 'true', 'Require Password Complexity'),
        ('backup_retention_days', '30', 'Backup Retention Days'),
        ('audit_log_retention_days', '90', 'Audit Log Retention Days')
    ]
    
    for key, value, description in system_settings:
        existing_setting = SystemSetting.query.filter_by(
            key=key, 
            business_id=None
        ).first()
        
        if not existing_setting:
            setting = SystemSetting(
                business_id=None,  # System-wide setting
                key=key,
                value=value,
                description=description
            )
            db.session.add(setting)
            print(f"   [ADD] Added system setting: {key}")

if __name__ == '__main__':
    success = init_system_admin()
    if success:
        print("\n[SUCCESS] System Administrator initialization completed successfully!")
        print("[INFO] You can now login with the credentials shown above.")
    else:
        print("\n[FAILED] System Administrator initialization failed!")
        sys.exit(1)
