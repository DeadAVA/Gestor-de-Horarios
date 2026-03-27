from sqlalchemy import select

from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.group_rules import (
    INTERSEMESTRAL_GROUP_START,
    MAESTRIA_GROUP_START,
    resolve_group_modality,
    validate_group_number_for_type,
)
from app.services.subject_selection import build_valid_subjects_query_for_group
from app.utils.exceptions import ConflictApiError, NotFoundApiError, ValidationApiError
from app.utils.parsing import coerce_int
from app.utils.serializers import serialize_group, serialize_subject
from app.validators.grupo_validator import validate_group_payload


class GroupService:
    @staticmethod
    def list_groups(filters) -> list[dict]:
        query = select(Grupo).order_by(Grupo.numero_grupo.asc())

        try:
            if filters.get("plan_estudio_id"):
                query = query.where(Grupo.plan_estudio_id == coerce_int(filters["plan_estudio_id"], "plan_estudio_id"))

            if filters.get("semestre"):
                query = query.where(Grupo.semestre == coerce_int(filters["semestre"], "semestre"))
        except ValueError as error:
            raise ValidationApiError("Filtros invalidos para grupos", [str(error)])

        groups = db.session.scalars(query).all()
        return [serialize_group(group) for group in groups]

    @staticmethod
    def create_group(payload: dict) -> dict:
        validated = validate_group_payload(payload)
        modalidad = validated["tipo_grupo"]

        if modalidad == "maestria":
            numero_grupo = GroupService._resolve_maestria_group_number(validated.get("numero_grupo"))
            semestre = 1
            tipo_grupo_db = "normal"
            plan = GroupService._get_default_plan_for_maestria()
        elif modalidad == "intersemestral":
            numero_grupo = GroupService._next_virtual_group_number(modalidad)
            semestre = validated["semestre"]
            tipo_grupo_db = "normal"
            plan = GroupService._get_plan_by_key(validated["plan_estudio_clave"])
        else:
            numero_grupo = validated["numero_grupo"]
            GroupService._ensure_unique_group_number(numero_grupo)
            try:
                semestre = validate_group_number_for_type(numero_grupo, modalidad)
            except ValueError as error:
                raise ValidationApiError("El grupo no cumple con el formato institucional", [str(error)])
            tipo_grupo_db = modalidad
            plan = GroupService._get_plan_by_key(validated["plan_estudio_clave"])

        group = Grupo(
            numero_grupo=numero_grupo,
            semestre=semestre,
            plan_estudio_id=plan.id,
            capacidad_alumnos=validated["capacidad_alumnos"],
            tipo_grupo=tipo_grupo_db,
        )
        db.session.add(group)
        db.session.commit()
        db.session.refresh(group)
        return GroupService.get_group_detail(group.id)

    @staticmethod
    def get_group_detail(group_id: int) -> dict:
        group = GroupService._get_group_or_404(group_id)
        payload = serialize_group(group, include_related=True)
        payload["materias_disponibles"] = [
            serialize_subject(subject)
            for subject in db.session.scalars(
                build_valid_subjects_query_for_group(group)
            ).all()
        ]
        return payload

    @staticmethod
    def update_group(group_id: int, payload: dict) -> dict:
        group = GroupService._get_group_or_404(group_id)
        validated = validate_group_payload(payload, partial=True)

        current_modality = resolve_group_modality(group.numero_grupo, group.tipo_grupo)
        target_group_type = validated.get("tipo_grupo", current_modality)
        target_group_number = validated.get("numero_grupo", group.numero_grupo)
        target_plan_key = validated.get("plan_estudio_clave", group.plan_estudio.clave)

        if target_group_type == "maestria":
            requested_visible_number = validated.get("numero_grupo")
            if "tipo_grupo" in validated and target_group_type != current_modality:
                group.numero_grupo = GroupService._resolve_maestria_group_number(requested_visible_number)
            elif requested_visible_number is not None:
                group.numero_grupo = GroupService._resolve_maestria_group_number(
                    requested_visible_number,
                    current_group_number=group.numero_grupo,
                )
            group.tipo_grupo = "normal"
            group.semestre = 1
            group.plan_estudio_id = GroupService._get_default_plan_for_maestria().id
        elif target_group_type == "intersemestral":
            target_semester = validated.get("semestre", group.semestre)
            if "tipo_grupo" in validated and target_group_type != current_modality:
                group.numero_grupo = GroupService._next_virtual_group_number(target_group_type)
            group.tipo_grupo = "normal"
            group.semestre = target_semester

            if (
                "plan_estudio_clave" in validated
                or target_plan_key != group.plan_estudio.clave
            ):
                plan = GroupService._get_plan_by_key(target_plan_key)
                group.plan_estudio_id = plan.id
        else:
            try:
                target_semester = validate_group_number_for_type(target_group_number, target_group_type)
            except ValueError as error:
                raise ValidationApiError("El grupo no cumple con el formato institucional", [str(error)])

            if "numero_grupo" in validated and validated["numero_grupo"] != group.numero_grupo:
                GroupService._ensure_unique_group_number(validated["numero_grupo"])
                group.numero_grupo = validated["numero_grupo"]

            if (
                "numero_grupo" in validated
                or "tipo_grupo" in validated
                or target_semester != group.semestre
            ):
                group.semestre = target_semester

            if "tipo_grupo" in validated:
                group.tipo_grupo = target_group_type

            if (
                "plan_estudio_clave" in validated
                or target_plan_key != group.plan_estudio.clave
            ):
                plan = GroupService._get_plan_by_key(target_plan_key)
                group.plan_estudio_id = plan.id

        if "capacidad_alumnos" in validated:
            group.capacidad_alumnos = validated["capacidad_alumnos"]

        db.session.commit()
        db.session.refresh(group)
        return GroupService.get_group_detail(group.id)

    @staticmethod
    def delete_group(group_id: int) -> None:
        group = GroupService._get_group_or_404(group_id)
        db.session.delete(group)
        db.session.commit()

    @staticmethod
    def _get_group_or_404(group_id: int) -> Grupo:
        group = db.session.get(Grupo, group_id)
        if group is None:
            raise NotFoundApiError("Grupo no encontrado", [f"No existe un grupo con id {group_id}"])
        return group

    @staticmethod
    def _get_plan_by_key(plan_key: str) -> PlanEstudio:
        normalized_key = (plan_key or "").strip()
        plan = db.session.scalar(select(PlanEstudio).where(PlanEstudio.clave == normalized_key))
        if plan is None:
            alias_key = None
            if normalized_key == "2015-2":
                alias_key = "2025-2"
            elif normalized_key == "2025-2":
                alias_key = "2015-2"

            if alias_key is not None:
                plan = db.session.scalar(select(PlanEstudio).where(PlanEstudio.clave == alias_key))

        if plan is None:
            raise NotFoundApiError(
                "Plan de estudio no disponible",
                [f"No existe un plan activo con clave {plan_key}"],
            )
        return plan

    @staticmethod
    def _ensure_unique_group_number(numero_grupo: int) -> None:
        existing_group = db.session.scalar(
            select(Grupo).where(Grupo.numero_grupo == numero_grupo)
        )
        if existing_group is not None:
            raise ConflictApiError("El grupo ya existe", [f"El grupo {numero_grupo} ya fue registrado"])

    @staticmethod
    def _next_virtual_group_number(modality: str) -> int:
        if modality == "intersemestral":
            start = INTERSEMESTRAL_GROUP_START
            end = MAESTRIA_GROUP_START
        elif modality == "maestria":
            start = MAESTRIA_GROUP_START
            end = 10**9
        else:
            raise ValidationApiError("Tipo de grupo invalido", ["La modalidad virtual no es valida"])

        last_group = db.session.scalar(
            select(Grupo)
            .where(Grupo.numero_grupo >= start)
            .where(Grupo.numero_grupo < end)
            .order_by(Grupo.numero_grupo.desc())
        )
        if last_group is None:
            return start
        return int(last_group.numero_grupo) + 1

    @staticmethod
    def _resolve_maestria_group_number(
        requested_visible_number: int | None,
        current_group_number: int | None = None,
    ) -> int:
        if requested_visible_number in (None, ""):
            return GroupService._next_virtual_group_number("maestria")

        visible_number = int(requested_visible_number)
        if visible_number <= 0:
            raise ValidationApiError(
                "Numero de grupo invalido",
                ["Para maestria el numero visible debe ser mayor a cero"],
            )

        internal_number = MAESTRIA_GROUP_START + visible_number - 1
        if current_group_number is not None and internal_number == int(current_group_number):
            return internal_number

        GroupService._ensure_unique_group_number(internal_number)
        return internal_number

    @staticmethod
    def _get_default_plan_for_maestria() -> PlanEstudio:
        plan = db.session.scalar(
            select(PlanEstudio)
            .where(PlanEstudio.clave == "maestria")
            .where(PlanEstudio.activo.is_(True))
        )
        if plan is not None:
            return plan

        # Fallback: primer plan activo si el plan maestria aun no existe
        plan = db.session.scalar(
            select(PlanEstudio)
            .where(PlanEstudio.activo.is_(True))
            .order_by(PlanEstudio.id.asc())
        )
        if plan is None:
            plan = db.session.scalar(select(PlanEstudio).order_by(PlanEstudio.id.asc()))
        if plan is None:
            raise NotFoundApiError(
                "Plan de estudio no disponible",
                ["No existe ningun plan para registrar el grupo de maestria"],
            )
        return plan