from marshmallow import Schema, fields, validate

# --- USER SCHEMAS ---
class UserSchema(Schema):
    id = fields.String(dump_only=True) # Only sent OUT, never accepted IN
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    # load_only=True ensures the password is NEVER sent back in a JSON response!
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8))
    organization_id = fields.String(required=True)
    active = fields.Boolean(dump_only=True)
    roles = fields.List(fields.Nested(lambda: RoleSchema()), dump_only=True)

class RoleSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(dump_only=True)
    description = fields.String(dump_only=True)

# --- PROJECT SCHEMAS ---
class ProjectSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=3, max=100))
    description = fields.String(allow_none=True)
    problem_statement_file_url = fields.String(allow_none=True, dump_only=True)
    
    # Strict validation for your join codes using Marshmallow's Regexp
    join_code = fields.String(
        required=True, 
        validate=[
            validate.Length(min=6, max=10),
            validate.Regexp(r'^[A-Z0-9]+$', error="Join code must be uppercase and alphanumeric.")
        ]
    )
    professor_id = fields.String(required=True)
    organization_id = fields.String(required=True)
    status = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

# --- MILESTONE SCHEMA ---
class MilestoneSchema(Schema):
    id = fields.String(dump_only=True)
    project_id = fields.String(dump_only=True)
    title = fields.String(required=True, validate=validate.Length(min=1, max=150))
    description = fields.String(allow_none=True)
    order_num = fields.Integer(dump_only=True)
    starts_at = fields.DateTime(required=True)
    deadline = fields.DateTime(required=True)
    created_at = fields.DateTime(dump_only=True)

# --- ORGANIZATION SCHEMAS ---
class OrganizationSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    domain = fields.String(allow_none=True, validate=validate.Length(max=100))
    plan_id = fields.String(required=True)
    active_projects = fields.Integer(dump_only=True)
    status = fields.String(dump_only=True)


# Usually read-only for the frontend (used to display pricing pages)
class PlanSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(dump_only=True) # e.g., "Free", "Pro"
    max_active_projects = fields.Integer(dump_only=True)
    has_ai_feature = fields.Boolean(dump_only=True)

# --- SUBMISSION SCHEMA (Professor / Admin full view) ---
class SubmissionSchema(Schema):
    id = fields.String(dump_only=True)
    file_url = fields.String(required=True, validate=validate.Length(max=512))
    status = fields.String(dump_only=True)  # AI processing status

    # AI-generated fields (read-only)
    ai_evaluation = fields.Dict(allow_none=True, dump_only=True)
    ai_score = fields.Integer(allow_none=True, dump_only=True)
    ai_feedback = fields.String(allow_none=True, dump_only=True)

    # Professor-owned review fields
    grade = fields.String(allow_none=True, validate=validate.Length(max=10))
    remarks = fields.String(allow_none=True)
    review_status = fields.String(allow_none=True)
    rejection_extension_days = fields.Integer(allow_none=True)
    resubmission_deadline = fields.DateTime(allow_none=True)

    project_id = fields.String(required=True)
    student_id = fields.String(required=True)
    organization_id = fields.String(required=True)

    # Nested student info for easy UI display
    student = fields.Nested(UserSchema, only=('id', 'name', 'email'), dump_only=True)
    project_name = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


# --- STUDENT-FACING SCHEMA (limited — no AI internals) ---
class StudentSubmissionSchema(Schema):
    """Students only see the professor's decision — not the AI data."""
    id = fields.String(dump_only=True)
    file_url = fields.String(dump_only=True)
    grade = fields.String(dump_only=True)
    remarks = fields.String(dump_only=True)
    review_status = fields.String(dump_only=True)
    rejection_extension_days = fields.Integer(dump_only=True, allow_none=True)
    resubmission_deadline = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    project_id = fields.String(dump_only=True)


# Initialize instances to use in your routes
user_schema = UserSchema()
project_schema = ProjectSchema()
organization_schema = OrganizationSchema()
plan_schema = PlanSchema()
submission_schema = SubmissionSchema()
student_submission_schema = StudentSubmissionSchema()
milestone_schema = MilestoneSchema()


