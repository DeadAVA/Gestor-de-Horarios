from sqlalchemy import and_, func, or_, select

from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.group_rules import is_manual_selection_group, resolve_group_modality


def _resolve_optativa_stages(group: Grupo) -> list[str]:
    plan_key = group.plan_estudio.clave if getattr(group, "plan_estudio", None) else None

    # En ambos planes de licenciatura las optativas se muestran de forma acumulativa:
    # disciplinaria incluye basica + disciplinaria; terminal incluye todas.
    if plan_key in {"2015-2", "2025-2", "2025-1"}:
        if 2 <= group.semestre <= 3:
            return ["basica"]
        if 4 <= group.semestre <= 6:
            return ["basica", "disciplinaria"]
        if 7 <= group.semestre <= 8:
            return ["basica", "disciplinaria", "terminal"]
        return []

    # Fallback conservador para cualquier otro plan.
    if 3 <= group.semestre <= 6:
        return ["disciplinaria"]
    if 7 <= group.semestre <= 8:
        return ["disciplinaria", "terminal"]
    return []


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

    # Grupos manuales x5-x9: selección libre de materias dentro del plan, sin filtrar por semestre/etapa.
    if is_manual_selection_group(int(group.numero_grupo), group.tipo_grupo):
        return query.order_by(Materia.semestre.asc(), Materia.nombre.asc())

    optativa_stages = _resolve_optativa_stages(group)
    if optativa_stages:
        query = query.where(
            or_(
                Materia.semestre == group.semestre,
                and_(
                    Materia.tipo_materia == "optativa",
                    Materia.etapa.in_(optativa_stages),
                ),
            )
        )
    else:
        query = query.where(Materia.semestre == group.semestre)

    return query.order_by(Materia.nombre.asc())
