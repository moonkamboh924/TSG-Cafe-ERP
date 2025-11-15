"""
Update MM001 System Administrator Permissions
Updates the default system administrator account with new system admin permissions
"""
import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.extensions import db
from app.models import User

def update_mm001_permissions():
    """Update MM001 account with new system administrator permissions"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("UPDATING MM001 SYSTEM ADMINISTRATOR PERMISSIONS")
        print("=" * 60)
        
        try:
            # Find MM001 user
            mm001_user = User.query.filter_by(username='MM001').first()
            
            if not mm001_user:
                print("[ERROR] MM001 user not found!")
                return False
            
            print(f"[FOUND] User: {mm001_user.username} ({mm001_user.email})")
            
            # Get current permissions
            current_permissions = mm001_user.get_navigation_permissions()
            print(f"[CURRENT] Permissions: {current_permissions}")
            
            # New system administrator permissions
            new_permissions = [
                'system_dashboard',
                'user_management', 
                'business_management',
                'subscription_management',
                'system_settings', 
                'system_analytics', 
                'monitoring', 
                'reports'
            ]
            
            # Update permissions
            mm001_user.set_navigation_permissions(new_permissions)
            
            # Commit changes
            db.session.commit()
            
            # Verify update
            updated_permissions = mm001_user.get_navigation_permissions()
            
            print(f"\n[SUCCESS] MM001 permissions updated successfully!")
            print("=" * 60)
            print("UPDATED PERMISSIONS:")
            for perm in updated_permissions:
                print(f"   [OK] {perm}")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] {str(e)}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = update_mm001_permissions()
    if success:
        print("\n[SUCCESS] MM001 permissions update completed successfully!")
    else:
        print("\n[FAILED] MM001 permissions update failed!")
        sys.exit(1)
