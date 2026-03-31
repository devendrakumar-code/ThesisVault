# ThesisVault

ThesisVault is a multi-tenant SaaS application built to demonstrate a **Subscription & Feature Entitlement System** for a production-oriented use case.  
The platform models how organizations subscribe to plans, access entitled features, and are restricted by usage limits at the **API level**.

## Problem Statement

Modern SaaS applications need more than login and roles. They must also decide whether a tenant is allowed to perform an action based on:

- Active subscription status
- Enabled plan features
- Usage limits
- Tenant isolation rules

ThesisVault implements these ideas in a thesis/project management domain.

## Core Features

- Multi-tenant architecture with organization-level isolation
- Database-driven subscription plans
- API-level entitlement enforcement through centralized middleware/decorators
- Feature access control based on plan entitlements
- Usage limit enforcement for resources and AI operations
- Subscription lifecycle handling: active, expired, grace period, maintenance mode
- Plan upgrade/downgrade support with subscription history tracking
- Audit trail using activity logs and subscription history
- Admin dashboard to monitor plans, limits, and organization state

## Tech Stack

### Backend
- Flask
- SQLAlchemy
- Flask-Security
- MySQL
- Celery

### Frontend
- Vue 3
- Vite
- Tailwind CSS

## Subscription Model

Plans are stored in the database and can define:

- Plan name
- Enabled features
- Maximum active projects
- Maximum students
- Monthly AI usage limit
- Validity duration

This makes the system extensible without changing business logic for every new plan.

## Entitlement Enforcement

The system enforces subscription rules at the backend using centralized decorators/middleware:

- Subscription validation
- Feature entitlement validation
- Usage limit validation

This ensures restricted actions are blocked at the API layer, not just hidden in the UI.

## Multi-Tenant Design

Each organization acts as a tenant and has:

- Users
- Projects
- One active subscription plan
- Usage counters and lifecycle state

Tenant boundaries are enforced using `organizationId` scoping and backend validation checks to prevent cross-tenant access.

## Auditability

ThesisVault maintains:

- `SubscriptionHistory` for plan changes
- `ActivityLog` for key administrative actions

This supports traceability, compliance review, and easier debugging of subscription events.

## Local Setup

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd thesisvault
```

### 2. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment
Create your environment/config file and update database, mail, and app settings as needed.

### 4. Run migrations / seed data
```bash
flask db upgrade
python seed.py
```

### 5. Start backend
```bash
python app.py
```

### 6. Start frontend
```bash
cd ../frontend
npm install
npm run dev
```

## Deliverables Covered

This project includes:

- Public GitHub repository with source code
- README
- Multi-tenant SaaS implementation
- Subscription & feature entitlement enforcement
- Usage tracking and auditability support
- Architecture and schema documentation for presentation

## Notes

This project was developed as part of a **Full Stack Development Apprentice assessment**, focused on building a scalable and extensible subscription enforcement system for a SaaS application.

## Author

Developed by **Devendra Kumar**
