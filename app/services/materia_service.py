from sqlalchemy import select

from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.subject_selection import build_valid_subjects_query_for_group
from app.utils.parsing import coerce_bool, coerce_int
from app.utils.exceptions import ConflictApiError, NotFoundApiError, ValidationApiError
from app.utils.serializers import serialize_subject
from app.validators.materia_validator import validate_subject_payload


class MateriaService:
    @staticmethod
    def list_subjects(filters) -> list[dict]:
        query = select(Materia).order_by(Materia.semestre.asc(), Materia.nombre.asc())

        try:
            if filters.get("plan_estudio_id"):
                query = query.where(Materia.plan_estudio_id == coerce_int(filters["plan_estudio_id"], "plan_estudio_id"))

            if filters.get("semestre"):
                query = query.where(Materia.semestre == coerce_int(filters["semestre"], "semestre"))

            if filters.get("tipo_materia"):
                query = query.where(Materia.tipo_materia == filters["tipo_materia"])

            if filters.get("modalidad"):
                query = query.where(Materia.modalidad == filters["modalidad"])

            if filters.get("activa") is not None:
                activa = coerce_bool(filters.get("activa"))
                query = query.where(Materia.activa.is_(activa))
        except ValueError as error:
            raise ValidationApiError("Filtros invalidos para materias", [str(error)])

        subjects = db.session.scalars(query).all()
        return [serialize_subject(subject) for subject in subjects]

    @staticmethod
    def create_subject(payload: dict) -> dict:
        validated = validate_subject_payload(payload)
        MateriaService._ensure_unique_subject_key(validated["clave"])
        MateriaService._ensure_plan_exists(validated["plan_estudio_id"])

        subject = Materia(**validated)
        db.session.add(subject)
        db.session.commit()
        db.session.refresh(subject)
        return serialize_subject(subject)

    @staticmethod
    def get_subject_detail(subject_id: int) -> dict:
        subject = MateriaService._get_subject_or_404(subject_id)
        return serialize_subject(subject)

    @staticmethod
    def update_subject(subject_id: int, payload: dict) -> dict:
        subject = MateriaService._get_subject_or_404(subject_id)
        validated = validate_subject_payload(payload, partial=True)

        if "clave" in validated and validated["clave"] != subject.clave:
            MateriaService._ensure_unique_subject_key(validated["clave"])

        if "plan_estudio_id" in validated:
            MateriaService._ensure_plan_exists(validated["plan_estudio_id"])

        for field_name, value in validated.items():
            setattr(subject, field_name, value)

        db.session.commit()
        db.session.refresh(subject)
        return serialize_subject(subject)

    @staticmethod
    def delete_subject(subject_id: int) -> None:
        subject = MateriaService._get_subject_or_404(subject_id)
        if subject.bloques_horario:
            raise ConflictApiError(
                "No se puede eliminar la materia",
                ["La materia tiene bloques de horario asociados"],
            )

        db.session.delete(subject)
        db.session.commit()

    @staticmethod
    def list_subjects_for_group(group_id: int, filters) -> list[dict]:
        group = db.session.get(Grupo, group_id)
        if group is None:
            raise NotFoundApiError("Grupo no encontrado", [f"No existe un grupo con id {group_id}"])

        query = build_valid_subjects_query_for_group(group)

        if filters.get("tipo_materia"):
            query = query.where(Materia.tipo_materia == filters["tipo_materia"])

        if filters.get("etapa"):
            query = query.where(Materia.etapa == filters["etapa"])

        subjects = db.session.scalars(query).all()
        return [serialize_subject(subject) for subject in subjects]

    @staticmethod
    def _get_subject_or_404(subject_id: int) -> Materia:
        subject = db.session.get(Materia, subject_id)
        if subject is None:
            raise NotFoundApiError("Materia no encontrada", [f"No existe una materia con id {subject_id}"])
        return subject

    @staticmethod
    def _ensure_plan_exists(plan_estudio_id: int) -> None:
        plan = db.session.get(PlanEstudio, plan_estudio_id)
        if plan is None:
            raise NotFoundApiError(
                "Plan de estudio no encontrado",
                [f"No existe un plan con id {plan_estudio_id}"],
            )

    @staticmethod
    def _ensure_unique_subject_key(clave: str) -> None:
        existing_subject = db.session.scalar(select(Materia).where(Materia.clave == clave))
        if existing_subject is not None:
            raise ConflictApiError("La materia ya existe", [f"La clave {clave} ya fue registrada"])