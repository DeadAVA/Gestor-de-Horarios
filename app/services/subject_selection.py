from sqlalchemy import and_, or_, select

from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.group_rules import is_manual_selection_group, resolve_group_modality


PLAN_ALIAS_MAP = {
    "2015-2": "2025-2",
    "2025-2": "2015-2",
}


def _resolve_plan_key(group: Grupo) -> str | None:
    if getattr(group, "plan_estudio", None):
        return group.plan_estudio.clave

    plan = db.session.get(PlanEstudio, int(group.plan_estudio_id))
    return plan.clave if plan is not None else None


def _resolve_alias_plan_id(group: Grupo) -> int | None:
    plan_key = _resolve_plan_key(group)
    alias_key = PLAN_ALIAS_MAP.get(plan_key)
    if alias_key is None:
        return None

    alias_plan = db.session.scalar(select(PlanEstudio).where(PlanEstudio.clave == alias_key))
    if alias_plan is None:
        return None

    return int(alias_plan.id)


def _resolve_optativa_stages(group: Grupo) -> list[str]:
    plan_key = _resolve_plan_key(group)

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
    """Los planes aliados (2015-2 ↔ 2025-2) comparten currículo: se incluyen ambos
    para que las obligatorias del plan vigente siempre aparezcan en el selector."""
    primary_plan_id = int(group.plan_estudio_id)
    alias_plan_id = _resolve_alias_plan_id(group)
    if alias_plan_id is None:
        return [primary_plan_id]
    return [primary_plan_id, alias_plan_id]


def _resolve_optativa_plan_ids(group: Grupo, optativa_stages: list[str]) -> list[int]:
    """Igual que _resolve_subject_plan_ids: incluye ambos planes para que las
    optativas del plan vigente aparezcan aunque el plan del grupo no las tenga."""
    primary_plan_id = int(group.plan_estudio_id)
    alias_plan_id = _resolve_alias_plan_id(group)
    if alias_plan_id is None or not optativa_stages:
        return [primary_plan_id]
    return [primary_plan_id, alias_plan_id]


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

    base_plan_ids = _resolve_subject_plan_ids(group)
    query = select(Materia).where(Materia.activa.is_(True))

    # Grupos manuales x5-x9: selección libre de materias dentro del plan, sin filtrar por semestre/etapa.
    if is_manual_selection_group(int(group.numero_grupo), group.tipo_grupo):
        return (
            query
            .where(Materia.plan_estudio_id.in_(base_plan_ids))
            .order_by(Materia.semestre.asc(), Materia.nombre.asc())
        )

    optativa_stages = _resolve_optativa_stages(group)
    optativa_plan_ids = _resolve_optativa_plan_ids(group, optativa_stages)
    if optativa_stages:
        query = query.where(
            or_(
                and_(
                    Materia.plan_estudio_id.in_(base_plan_ids),
                    Materia.semestre == group.semestre,
                ),
                and_(
                    Materia.plan_estudio_id.in_(optativa_plan_ids),
                    Materia.tipo_materia == "optativa",
                    Materia.etapa.in_(optativa_stages),
                ),
            )
        )
    else:
        query = query.where(
            and_(
                Materia.plan_estudio_id.in_(base_plan_ids),
                Materia.semestre == group.semestre,
            )
        )

    return query.order_by(Materia.nombre.asc())
