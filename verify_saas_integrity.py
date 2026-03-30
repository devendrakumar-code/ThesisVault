from app import create_app
from extentions import db
from models import Organization, Plan, User, Role
from datetime import datetime, timedelta, timezone

def test_saas_enforcement():
    app = create_app()
    with app.app_context():
        print("\n--- SaaS Enforcement Verification ---\n")
        
        # 1. Setup Test Data
        # Ensure we have a Free Plan with limited projects
        free_plan = Plan.query.filter_by(name='Free').first()
        if not free_plan:
            free_plan = Plan(name='Free', max_active_projects=1, max_students=2, features={})
            db.session.add(free_plan)
        else:
            free_plan.max_active_projects = 1
            free_plan.max_students = 2
            free_plan.features = {"ai_analysis": False}
        
        # Ensure we have a Pro Plan
        pro_plan = Plan.query.filter_by(name='Pro').first()
        if not pro_plan:
            pro_plan = Plan(name='Pro', max_active_projects=50, max_students=500, features={"ai_analysis": True})
            db.session.add(pro_plan)
        
        db.session.commit()

        # 2. Test User Limit
        print("Testing User Limit (Max Students: 2)...")
        temp_org = Organization(name="Limit Test Org", plan_id=free_plan.id, active_students=2)
        db.session.add(temp_org)
        db.session.flush()
        
        try:
            extra_user = User(name="Extra student", email="extra@test.com", password="pwd", organization_id=temp_org.id)
            db.session.add(extra_user)
            db.session.commit()
            print("❌ FAIL: Should have blocked user addition.")
        except ValueError as e:
            print(f"✅ PASS: Blocked with error: {e}")
            db.session.rollback()

        # 3. Test Subscription Expiry
        print("\nTesting Subscription Expiry...")
        temp_org.subscription_status = 'expired'
        temp_org.subscription_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.session.commit()
        
        # We can't easily test the decorator here without a request context, 
        # but we can test the property used by the decorator.
        if temp_org.is_subscription_valid is False:
            print("✅ PASS: is_subscription_valid correctly returns False for expired org.")
        else:
            print("❌ FAIL: is_subscription_valid returned True for expired org.")

        # 4. Clean up
        db.session.delete(temp_org)
        db.session.commit()
        print("\n--- Verification Complete ---")

if __name__ == "__main__":
    test_saas_enforcement()
