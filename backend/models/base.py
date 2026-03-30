import uuid
import time
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy import JSON, UniqueConstraint, func, update, Index, Computed
from sqlalchemy.dialects.mysql import JSON as MYSQL_JSON
from sqlalchemy.orm import Session
from sqlalchemy import inspect as sa_inspect
from flask_sqlalchemy.query import Query as BaseQuery
from flask_security import UserMixin, RoleMixin
from extentions import db

def generate_uuid_v7():
    try:
        from uuid6 import uuid7
        return str(uuid7())
    except ImportError:
        ms = int(time.time() * 1000)
        rand_a = secrets.randbits(12)
        rand_b = secrets.randbits(62)
        v = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
        return str(uuid.UUID(int=v))

class SoftDeleteQuery(BaseQuery):
    _with_deleted = False

    def with_deleted(self):
        q = self._clone()
        q._with_deleted = True
        return q

    def _entity_model_class(self, ent):
        try:
            if hasattr(ent, "entity_zero") and ent.entity_zero is not None:
                return ent.entity_zero.class_
            if hasattr(ent, "mapper") and ent.mapper is not None:
                return ent.mapper.class_
            insp = sa_inspect(ent)
            if hasattr(insp, "mapper") and insp.mapper is not None:
                return insp.mapper.class_
        except Exception:
            pass
        return None

    def __iter__(self):
        if not getattr(self, "_with_deleted", False):
            filters = []
            entities = getattr(self, "_entities", None) or []
            for ent in entities:
                model_cls = self._entity_model_class(ent)
                if model_cls and hasattr(model_cls, "deleted_at"):
                    filters.append(model_cls.deleted_at.is_(None))
            if filters:
                return super(SoftDeleteQuery, self.filter(*filters)).__iter__()
        return super(SoftDeleteQuery, self).__iter__()

class BaseModel(db.Model):
    __abstract__ = True
    query_class = SoftDeleteQuery

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid_v7)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now(), nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    def soft_delete(self, session: Session):
        session.execute(update(self.__class__).where(self.__class__.id == self.id).values(deleted_at=func.now()))
        session.expire(self)

    def restore(self, session: Session):
        session.execute(update(self.__class__).where(self.__class__.id == self.id).values(deleted_at=None))
        session.expire(self)

# --- RBAC ---
class Role(BaseModel, RoleMixin):
    __tablename__ = 'roles'
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

class UserRole(BaseModel):
    __tablename__ = 'user_roles'
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'), nullable=False, index=True)
    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='uq_user_role'),)

# --- ACCOUNTS ---
class Plan(BaseModel):
    __tablename__ = 'plans'
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    
    # Usage Limits (Requirement 2: Data-Driven Modeling)
    max_active_projects = db.Column(db.Integer, nullable=False, default=10)
    max_students = db.Column(db.Integer, nullable=False, default=100)
    monthly_ai_limit = db.Column(db.Integer, nullable=False, default=50)
    validity_days = db.Column(db.Integer, nullable=False, default=30)

    # Feature Entitlements (Requirement 2: No code change needed for new features)
    # Stores flags like: {"ai_analysis": true, "advanced_reporting": true}
    features = db.Column(db.JSON, nullable=True)
    
    # Legacy flag for backward compat (will be deprecated)
    has_ai_feature = db.Column(db.Boolean, nullable=False, default=False)
    
    organizations = db.relationship('Organization', backref='plan', lazy='select')

class Organization(BaseModel):
    __tablename__ = 'organizations'
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='active', index=True)
    active_projects = db.Column(db.Integer, default=0, nullable=False)
    domain = db.Column(db.String(100), unique=True, nullable=True)
    plan_id = db.Column(db.String(36), db.ForeignKey('plans.id'), nullable=False, index=True)
    subscription_status = db.Column(db.String(20), default='active') # active, expired, trialing
    subscription_ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    trial_ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    grace_period_ends_at = db.Column(db.DateTime(timezone=True), nullable=True) # Requirement 5: Lifecycle (Grace period)
    is_maintenance = db.Column(db.Boolean, default=False) # SaaS Operations: Kill switch
    
    # Usage Tracking (Requirement: Monthly reset logic)
    monthly_ai_count = db.Column(db.Integer, default=0, nullable=False)
    last_usage_reset = db.Column(db.DateTime, default=func.now())
    
    # Denormalized for quick scaling/indexing
    active_projects = db.Column(db.Integer, default=0, nullable=False)
    active_students = db.Column(db.Integer, default=0, nullable=False)

    users = db.relationship('User', backref='organization', cascade="all, delete-orphan")
    projects = db.relationship('Project', backref='organization', cascade="all, delete-orphan")

    @property
    def is_subscription_valid(self):
        now = datetime.now(timezone.utc)
        
        # --- SELF-HEALING: Monthly Usage Reset ---
        # If the last reset was in a different month/year, reset the counter
        # This fulfills the 'Monthly reset logic' requirement automatically.
        last_reset = self.last_usage_reset.replace(tzinfo=timezone.utc) if self.last_usage_reset.tzinfo is None else self.last_usage_reset
        if last_reset.month != now.month or last_reset.year != now.year:
            self.monthly_ai_count = 0
            self.last_usage_reset = func.now()
            # Note: We depend on a subsequent commit in the request lifecycle
        
        # 1. Check explicit suspension or maintenance
        if self.status != 'active' or self.is_maintenance:
            return False
            
        # 2. Check Expiry with Grace Period Support
        if self.subscription_ends_at:
            ends_at = self.subscription_ends_at.replace(tzinfo=timezone.utc) if self.subscription_ends_at.tzinfo is None else self.subscription_ends_at
            
            # If expired, check if we are still in grace period
            if ends_at < now:
                if self.grace_period_ends_at:
                    grace_at = self.grace_period_ends_at.replace(tzinfo=timezone.utc) if self.grace_period_ends_at.tzinfo is None else self.grace_period_ends_at
                    return grace_at > now
                return False
        
        return True
class User(BaseModel, UserMixin):
    __tablename__ = 'users'
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean(), default=True)
    fs_uniquifier = db.Column(db.String(36), unique=True, nullable=False, default=generate_uuid_v7)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False, index=True)
    profile_image = db.Column(db.String(255), nullable=True) # Relative path to profile image

    roles = db.relationship('Role', secondary=UserRole.__table__, backref=db.backref('users', lazy='dynamic'))
    student_profile = db.relationship('StudentProfile', backref='user', uselist=False, cascade="all, delete-orphan", lazy='joined')
    professor_profile = db.relationship('ProfessorProfile', backref='user', uselist=False, cascade="all, delete-orphan", lazy='joined')
    
    # SECURITY CASCADE: If a user is deleted, their submissions are purged.
    submissions = db.relationship('Submission', backref='user_owner', cascade='all, delete-orphan', foreign_keys='Submission.student_id')

class StudentProfile(BaseModel):
    __tablename__ = 'student_profiles'
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False)
    enrollment_number = db.Column(db.String(50), unique=True, nullable=True)
    major = db.Column(db.String(100))
    semester = db.Column(db.Integer, default=1)

class ProfessorProfile(BaseModel):
    __tablename__ = 'professor_profiles'
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), unique=True, nullable=False)
    department = db.Column(db.String(100))

# --- CONTENT ---
class Project(BaseModel):
    __tablename__ = 'projects'
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)  # problem statement summary / notes
    problem_statement_file_url = db.Column(db.String(512), nullable=True)
    join_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='active', index=True)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False, index=True)
    professor_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    milestones = db.relationship('Milestone', backref='project', cascade='all, delete-orphan', order_by='Milestone.order_num')

class Milestone(BaseModel):
    __tablename__ = 'milestones'
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    order_num = db.Column(db.Integer, nullable=False, default=1)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    deadline = db.Column(db.DateTime(timezone=True), nullable=False)
    __table_args__ = (Index('idx_milestone_project', 'project_id', 'order_num'),)

class Submission(BaseModel):
    __tablename__ = 'submissions'
    file_url = db.Column(db.String(512), nullable=False)
    # AI processing status — set by the background worker
    status = db.Column(db.String(20), default='uploaded') # uploaded, pending, processing, completed, failed
    # AI-generated fields — read-only for professor/student
    ai_evaluation = db.Column(MYSQL_JSON, nullable=True)
    ai_score = db.Column(db.Integer, nullable=True)
    ai_feedback = db.Column(db.Text, nullable=True)  # legacy / raw AI text
    # Professor-owned review fields
    grade = db.Column(db.String(10), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    review_status = db.Column(db.String(30), default='pending_review')
    rejection_extension_days = db.Column(db.Integer, nullable=True)
    resubmission_deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    # Milestone link
    milestone_id = db.Column(db.String(36), db.ForeignKey('milestones.id'), nullable=True, index=True)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False, index=True)
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False, index=True)
    
    # Explicit relationships for nested serialization
    student = db.relationship('User', foreign_keys=[student_id], overlaps="submissions,user_owner")
    project = db.relationship('Project', backref=db.backref('submissions', lazy='dynamic'), foreign_keys=[project_id])
    milestone = db.relationship('Milestone', backref=db.backref('submissions', lazy='dynamic'), foreign_keys=[milestone_id])

    @property
    def project_name(self):
        return self.project.name if self.project else "Unknown Project"

    __table_args__ = (
        Index('idx_sub_org_score', 'organization_id', 'ai_score'),
        UniqueConstraint('student_id', 'milestone_id', name='uq_student_milestone'),
    )

class Enrollment(BaseModel):
    __tablename__ = 'enrollments'
    
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False, index=True)
    
    # Track when they joined
    joined_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # Optional: Track if they are active or dropped the project
    is_active = db.Column(db.Boolean, default=True)

    # Performance: Compound index for quick enrollment checks
    __table_args__ = (db.Index('idx_enrollment_student_project', 'student_id', 'project_id'),)

    # Relationship for easy access
    project = db.relationship('Project', backref='enrollments')
    student = db.relationship('User', backref='project_enrollments')

#-------------------------------
#   Functional Tables
#-------------------------------

class RevokedToken(BaseModel):
    __tablename__ = 'revoked_tokens'
    
    # Stores the actual JWT string that is being invalidated [cite: 15]
    token = db.Column(db.String(500), nullable=False, index=True)
    
    # Automatically sets expiry to 60 minutes from the moment of revocation
    expires_at = db.Column(
        db.DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc) + timedelta(minutes=60)
    )
class OneTimeToken(BaseModel):
    __tablename__ = 'one_time_tokens'
    
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    purpose = db.Column(db.String(50), nullable=False) # e.g., 'onboard', 'reset_password'
    
    # Tokens expire after 24 hours by default
    expires_at = db.Column(
        db.DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )

class Invite(BaseModel):
    __tablename__ = 'invites'
    
    email = db.Column(db.String(120), nullable=False, index=True)
    name = db.Column(db.String(100)) # Stores the invited name for pre-filling form
    token = db.Column(db.String(500), unique=True, nullable=False)
    subject = db.Column(db.String(200))
    text_body = db.Column(db.Text)
    html_body = db.Column(db.Text)
    purpose = db.Column(db.String(50)) # e.g., 'professor_onboard'
    status = db.Column(db.String(20), default='queued', index=True) # queued, sent, expired
    
    created_by_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    sent_at = db.Column(db.DateTime(timezone=True))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

class SubscriptionHistory(BaseModel):
    __tablename__ = 'subscription_history'
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False, index=True)
    old_plan_id = db.Column(db.String(36), db.ForeignKey('plans.id'), nullable=True, index=True)
    new_plan_id = db.Column(db.String(36), db.ForeignKey('plans.id'), nullable=False, index=True)
    change_reason = db.Column(db.String(255), nullable=True) # e.g., 'initial_signup', 'upgrade', 'system_adjustment'
    
    # Relationships
    organization = db.relationship('Organization', backref=db.backref('history', order_by='SubscriptionHistory.created_at.desc()'))
    old_plan = db.relationship('Plan', foreign_keys=[old_plan_id])
    new_plan = db.relationship('Plan', foreign_keys=[new_plan_id])

class ActivityLog(BaseModel):
    __tablename__ = 'activity_logs'
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True, index=True)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False) # e.g., 'PROJECT_DELETED', 'PLAN_CHANGED'
    description = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=True) # Any extra context

    user = db.relationship('User', backref='activities')
    organization = db.relationship('Organization', backref='activities')


