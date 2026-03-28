import random
import string
from sqlalchemy.exc import IntegrityError
from .base import Project

def create_project_safe(session, **kwargs):
    for _ in range(5):
        try:
            with session.begin_nested():
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                p = Project(join_code=code, **kwargs)
                session.add(p)
                session.flush()
                return p
        except IntegrityError:
            continue
    raise RuntimeError("Unique join_code generation failed.")
