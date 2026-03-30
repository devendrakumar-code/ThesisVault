from datetime import datetime, timedelta, timezone
from app import create_app
from extentions import db
from models import Role, Plan, User, Organization
from flask_security.utils import hash_password

def seed_data():
    app = create_app()
    with app.app_context():
        print("🌱 Starting database seeding...")

        # 1. Create Default Roles
        roles_data = [
            {'name': 'admin', 'description': 'System-wide administrator'},
            {'name': 'professor', 'description': 'Faculty member who manages projects'},
            {'name': 'student', 'description': 'Student who submits theses'}
        ]
        for r_data in roles_data:
            role = Role.query.filter_by(name=r_data['name']).first()
            if not role:
                role = Role(**r_data)
                db.session.add(role)
                print(f"Created role: {r_data['name']}")

        # 2. Create Default Subscription Plans
        # Note: using 'max_projects' and 'has_ai_analysis' to match your middleware
        plans_data = [
            {
                'name': 'Free', 
                'max_active_projects': 3, 
                'max_students': 10, 
                'monthly_ai_limit': 5,
                'validity_days': 30, 
                'features': {'ai_analysis': False, 'premium_support': False}
            },
            {
                'name': 'Pro', 
                'max_active_projects': 50, 
                'max_students': 500, 
                'monthly_ai_limit': 100,
                'validity_days': 30, 
                'features': {'ai_analysis': True, 'premium_support': True}
            },
            {
                'name': 'Enterprise', 
                'max_active_projects': 1000, 
                'max_students': 10000, 
                'monthly_ai_limit': 10000,
                'validity_days': 365, 
                'features': {'ai_analysis': True, 'premium_support': True}
            }
        ]
        for p_data in plans_data:
            plan = Plan.query.filter_by(name=p_data['name']).first()
            if not plan:
                plan = Plan(**p_data)
                db.session.add(plan)
            else:
                # Update existing plan attributes
                for key, val in p_data.items():
                    setattr(plan, key, val)
                print(f"Updated plan attributes: {p_data['name']}")
            print(f"Created/Updated plan: {p_data['name']}")
        
        db.session.flush() # Ensure plans and roles are available for the next steps

        # 3. Create a Test Organization (The Tenant)
        org_name = "IIT Madras"
        test_org = Organization.query.filter_by(name=org_name).first()
        if not test_org:
            pro_plan = Plan.query.filter_by(name='Pro').first()
            test_org = Organization(
                name=org_name,
                domain="iitm.ac.in",
                plan_id=pro_plan.id,
                active_projects=0,
                subscription_status='active',
                # Set expiry based on plan validity (Requirement 5)
                subscription_ends_at=datetime.now(timezone.utc) + timedelta(days=pro_plan.validity_days)
            )
            db.session.add(test_org)
            db.session.flush()
            print(f"Created test organization: {org_name}")

        # 4. Create a Default Admin User for testing
        admin_email = "admin@iitm.ac.in"
        if not User.query.filter_by(email=admin_email).first():
            admin_role = Role.query.filter_by(name='admin').first()
            test_admin = User(
                email=admin_email,
                password=hash_password("admin123"), # Change this in production!
                name="Devendra Kumar",
                active=True,
                organization_id=test_org.id
            )
            test_admin.roles.append(admin_role)
            db.session.add(test_admin)
            print(f"Created test admin: {admin_email}")

        db.session.commit()
        print("✅ Seeding complete! You can now log in with admin@iitm.ac.in / admin123")

if __name__ == "__main__":
    seed_data()
