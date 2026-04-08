from sqlalchemy import select

from app.extensions import db
from app.models import Docente


VACANCY_TEACHER_KEY = "VACANTE-SISTEMA"
VACANCY_TEACHER_NAME = "Vacante"


def get_or_create_vacancy_teacher() -> Docente:
    teacher = db.session.scalar(
        select(Docente).where(Docente.clave_docente == VACANCY_TEACHER_KEY)
    )
    if teacher is not None:
        return teacher

    teacher = Docente(
        clave_docente=VACANCY_TEACHER_KEY,
        nombre=VACANCY_TEACHER_NAME,
        activo=False,
        foraneo=False,
        es_juez=False,
    )
    db.session.add(teacher)
    db.session.flush()
    return teacher


def is_vacancy_teacher(teacher: Docente | None) -> bool:
    return bool(teacher and teacher.clave_docente == VACANCY_TEACHER_KEY)
