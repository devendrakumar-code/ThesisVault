from marshmallow import Schema, fields, validate

# --- USER SCHEMAS ---
class UserSchema(Schema):
    id = fields.String(dump_only=True) # Only sent OUT, never accepted IN
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    # load_only=True ensures the password is NEVER sent back in a JSON response!
    password = fields.String(required=True, load_only=True, validate=validate.Length(min=8))
    organization_id = fields.String(required=True)
    role = fields.String(dump_only=True) # Set by backend, not frontend

# --- PROJECT SCHEMAS ---
class ProjectSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=3, max=100))
    
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

# --- ORGANIZATION SCHEMAS ---
class OrganizationSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    plan_id = fields.String(required=True)
    active_projects = fields.Integer(dump_only=True)
    status = fields.String(dump_only=True)


# Usually read-only for the frontend (used to display pricing pages)
class PlanSchema(Schema):
    id = fields.String(dump_only=True)
    name = fields.String(dump_only=True) # e.g., "Free", "Pro"
    max_active_projects = fields.Integer(dump_only=True)
    has_ai_feature = fields.Boolean(dump_only=True)

# --- SUBMISSION SCHEMA ---
class SubmissionSchema(Schema):
    id = fields.String(dump_only=True)
    file_url = fields.String(required=True, validate=validate.Length(max=512))
    grade = fields.String(allow_none=True, validate=validate.Length(max=10))
    remarks = fields.String(allow_none=True)
    
    # Marshmallow handles your Gemini JSON output perfectly using fields.Dict()
    ai_evaluation = fields.Dict(allow_none=True, dump_only=True) 
    
    project_id = fields.String(required=True)
    student_id = fields.String(required=True)
    organization_id = fields.String(required=True)
    
    created_at = fields.DateTime(dump_only=True)

# Initialize instances to use in your routes
user_schema = UserSchema()
project_schema = ProjectSchema()
organization_schema = OrganizationSchema()
plan_schema = PlanSchema()
submission_schema = SubmissionSchema()


