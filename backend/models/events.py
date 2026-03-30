from sqlalchemy import event, select, inspect as sa_inspect
from sqlalchemy.orm import Session, with_loader_criteria
from .base import BaseModel

@event.listens_for(Session, "do_orm_execute")
def _add_soft_delete_filter(execute_state):
    if (
        execute_state.is_select
        and not execute_state.is_column_load
        and not execute_state.execution_options.get("include_deleted", False)
    ):
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                BaseModel, 
                lambda cls: cls.deleted_at.is_(None)
                # Removed include_subclasses=True here
            )
        )

@event.listens_for(Session, 'before_flush')
def update_project_counters(session, flush_context, instances):
    from sqlalchemy import update
    from .base import Project, Organization # Prevent circularity
    
    # 1. NEW Active Projects
    for obj in list(session.new):
        if isinstance(obj, Project) and obj.status == "active":
            session.execute(
                update(Organization)
                .where(Organization.id == obj.organization_id)
                .values(active_projects=Organization.active_projects + 1)
            )
    
    # 2. DELETED Active Projects
    for obj in list(session.deleted):
        if isinstance(obj, Project) and obj.status == "active":
            session.execute(
                update(Organization)
                .where(Organization.id == obj.organization_id)
                .values(active_projects=db.func.max(0, Organization.active_projects - 1))
            )

    # 3. UPDATED Status
    for obj in list(session.dirty):
        if isinstance(obj, Project):
            state = sa_inspect(obj)
            if state.attrs.status.history.has_changes():
                hist = state.attrs.status.history
                old, new = (hist.deleted[0] if hist.deleted else None), (hist.added[0] if hist.added else None)
                if old != new:
                    if old == "active":
                        session.execute(update(Organization).where(Organization.id == obj.organization_id).values(active_projects=db.func.max(0, Organization.active_projects - 1)))
                    if new == "active":
                        session.execute(update(Organization).where(Organization.id == obj.organization_id).values(active_projects=Organization.active_projects + 1))

@event.listens_for(Session, 'before_flush')
def validate_usage_limits_global(session, flush_context, instances):
    from .base import User, Organization, Project # Prevent circularity
    
    # 1. Validate User Limit (Requirement 4: Measurable limit enforcement)
    for obj in list(session.new):
        if isinstance(obj, User):
            org = session.get(Organization, obj.organization_id)
            if org and org.plan:
                if org.active_students >= org.plan.max_students:
                    raise ValueError(f"User limit reached for {org.plan.name} ({org.plan.max_students}). Please upgrade.")

    # 2. Multi-tenant violation check
    from .base import Submission
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, Submission) and obj.project_id and obj.organization_id:
            proj_org_id = session.query(Project.organization_id).filter(Project.id == obj.project_id).scalar()
            if proj_org_id and proj_org_id != obj.organization_id:
                raise ValueError("Multi-tenant violation: Submission organization mismatch.")

@event.listens_for(Session, 'before_flush')
def update_user_counters(session, flush_context, instances):
    from sqlalchemy import update
    from .base import User, Organization
    for obj in list(session.new):
        if isinstance(obj, User):
            session.execute(update(Organization).where(Organization.id == obj.organization_id).values(active_students=Organization.active_students + 1))
    
    for obj in list(session.deleted):
        if isinstance(obj, User):
            session.execute(update(Organization).where(Organization.id == obj.organization_id).values(active_students=db.func.max(0, Organization.active_students - 1)))
