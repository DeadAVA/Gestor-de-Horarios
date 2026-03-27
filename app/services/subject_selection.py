from sqlalchemy import and_, func, or_, select

from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.group_rules import resolve_group_modality


def _resolve_optativa_stage(group: Grupo):
    plan_key = group.plan_estudio.clave if getattr(group, "plan_estudio", None) else None

    if plan_key == "2025-2":
        if 2 <= group.semestre <= 3:
            return "basica"
        if 4 <= group.semestre <= 6:
            return "disciplinaria"
        if 7 <= group.semestre <= 8:
            return "terminal"
        return None

    # Compatibilidad con logica historica de 2025-1
    if 3 <= group.semestre <= 6:
        return "disciplinaria"
    if 7 <= group.semestre <= 8:
        return "terminal"
    return None


def _resolve_subject_plan_ids(group: Grupo) -> list[int]:
    """Return plan ids to use for subject lookup, with alias fallback when needed."""
    primary_plan_id = int(group.plan_estudio_id)
    primary_count = db.session.scalar(
        select(func.count(Materia.id)).where(Materia.plan_estudio_id == primary_plan_id)
    ) or 0
    if primary_count > 0:
        return [primary_plan_id]

    plan_key = group.plan_estudio.clave if getattr(group, "plan_estudio", None) else None
    alias_key = None
    if plan_key == "2015-2":
        alias_key = "2025-2"
    elif plan_key == "2025-2":
        alias_key = "2015-2"

    if not alias_key:
        return [primary_plan_id]

    alias_plan = db.session.scalar(select(PlanEstudio).where(PlanEstudio.clave == alias_key))
    if alias_plan is None:
        return [primary_plan_id]

    alias_count = db.session.scalar(
        select(func.count(Materia.id)).where(Materia.plan_estudio_id == alias_plan.id)
    ) or 0
    if alias_count == 0:
        return [primary_plan_id]

    return [primary_plan_id, alias_plan.id]


def build_valid_subjects_query_for_group(group: Grupo):
    modality = resolve_group_modality(group.numero_grupo, group.tipo_grupo)

    MAESTRIA_PLAN_KEY = "maestria"

    if modality == "maestria":
        maestria_plan = db.session.scalar(
            select(PlanEstudio).where(PlanEstudio.clave == MAESTRIA_PLAN_KEY)
        )
        if maestria_plan is not None:
            return (
                select(Materia)
                .where(Materia.activa.is_(True))
                .where(Materia.plan_estudio_id == maestria_plan.id)
                .order_by(Materia.nombre.asc())
            )
        # Fallback si el plan maestria aún no existe (compatibilidad)
        return (
            select(Materia)
            .where(Materia.activa.is_(True))
            .order_by(Materia.nombre.asc())
        )

    plan_ids = _resolve_subject_plan_ids(group)
    query = (
        select(Materia)
        .where(Materia.plan_estudio_id.in_(plan_ids))
        .where(Materia.activa.is_(True))
    )

    # Grupos 505-509: selección libre de materias dentro del plan, sin filtrar por semestre/etapa.
    if 505 <= int(group.numero_grupo) <= 509:
        return query.order_by(Materia.semestre.asc(), Materia.nombre.asc())

    optativa_stage = _resolve_optativa_stage(group)
    if optativa_stage:
        query = query.where(
            or_(
                Materia.semestre == group.semestre,
                and_(
                    Materia.tipo_materia == "optativa",
                    Materia.etapa == optativa_stage,
                ),
            )
        )
    else:
        query = query.where(Materia.semestre == group.semestre)

    return query.order_by(Materia.nombre.asc())
