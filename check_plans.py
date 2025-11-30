from app import create_app
from app.models import SubscriptionPlan, Business
from app.extensions import db

app = create_app()

with app.app_context():
    print("=" * 60)
    print("SUBSCRIPTION PLANS IN DATABASE:")
    print("=" * 60)
    
    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.display_order).all()
    
    if plans:
        for plan in plans:
            print(f"\nPlan #{plan.id}:")
            print(f"  Code: {plan.plan_code}")
            print(f"  Name: {plan.plan_name}")
            print(f"  Price: ${plan.price}")
            print(f"  Active: {plan.is_active}")
            print(f"  Visible: {plan.is_visible}")
            print(f"  Display Order: {plan.display_order}")
    else:
        print("\n⚠️  NO SUBSCRIPTION PLANS FOUND IN DATABASE!")
        print("You need to create subscription plans first.")
    
    print("\n" + "=" * 60)
    print("BUSINESSES AND THEIR PLANS:")
    print("=" * 60)
    
    businesses = Business.query.all()
    for business in businesses:
        print(f"\n{business.business_name}:")
        print(f"  Current Plan: {business.subscription_plan}")
        print(f"  Active: {business.is_active}")
        
        # Check if plan exists in SubscriptionPlan table
        plan_config = SubscriptionPlan.query.filter_by(plan_code=business.subscription_plan).first()
        if plan_config:
            print(f"  ✅ Plan exists in config: {plan_config.plan_name}")
        else:
            print(f"  ⚠️  Plan '{business.subscription_plan}' NOT FOUND in SubscriptionPlan table!")
    
    print("\n" + "=" * 60)
