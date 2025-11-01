"""
One-time script to update existing bill templates with business name from settings
"""
from app import create_app
from app.models import db, BillTemplate, SystemSetting

app = create_app()

with app.app_context():
    # Get business name from settings
    business_name = SystemSetting.get_setting('restaurant_name', 'My Business')
    
    print(f"Current business name in settings: {business_name}")
    
    # Update all bill templates
    templates = BillTemplate.query.all()
    
    if not templates:
        print("No bill templates found in database")
    else:
        for template in templates:
            old_name = template.header_name
            template.header_name = business_name
            print(f"Updated template '{template.name}': '{old_name}' -> '{business_name}'")
        
        db.session.commit()
        print(f"\n✅ Successfully updated {len(templates)} bill template(s)")
