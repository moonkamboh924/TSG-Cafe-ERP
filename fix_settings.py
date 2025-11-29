"""
Fix System Settings - Update company name from Trisync Global to TSG Cafe ERP
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.models import SystemSetting

def fix_system_settings():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Fixing System Settings")
        print("=" * 60)
        
        # Update company_name if it exists
        setting = SystemSetting.query.filter_by(
            key='company_name',
            business_id=None
        ).first()
        
        if setting:
            old_value = setting.value
            setting.value = 'TSG Cafe ERP'
            print(f"\n✓ Updated company_name:")
            print(f"  Old: {old_value}")
            print(f"  New: TSG Cafe ERP")
        else:
            # Create new setting
            setting = SystemSetting(
                key='company_name',
                value='TSG Cafe ERP',
                business_id=None
            )
            db.session.add(setting)
            print(f"\n✓ Created company_name: TSG Cafe ERP")
        
        # Commit changes
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("✅ System settings updated successfully!")
        print("=" * 60)
        print("\nChanges made:")
        print("• Company Name: TSG Cafe ERP")
        print("• This will appear in the top-left corner of the welcome page")
        print("\nRestart your Flask server and refresh the browser to see changes.")

if __name__ == "__main__":
    fix_system_settings()
