from sqlalchemy import select

from app.extensions import db
from app.models import Docente
from app.models.horario_juez import HorarioJuez
from app.utils.exceptions import ConflictApiError, NotFoundApiError, ValidationApiError
from app.utils.parsing import coerce_bool
from app.utils.serializers import serialize_teacher
from app.utils.time_utils import calculate_hours_from_blocks
from app.validators.docente_validator import validate_teacher_payload


ALLOWED_DAYS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado"}

MAX_TEACHER_HOURS = 25


class DocenteService:
    @staticmethod
    def list_teachers(filters) -> list[dict]:
        query = select(Docente).order_by(Docente.nombre.asc())

        try:
            if filters.get("activo") is not None:
                activo = coerce_bool(filters.get("activo"))
                query = query.where(Docente.activo.is_(activo))

            if filters.get("foraneo") is not None:
                foraneo = coerce_bool(filters.get("foraneo"))
                query = query.where(Docente.foraneo.is_(foraneo))
        except ValueError as error:
            raise ValidationApiError("Filtros invalidos para docentes", [str(error)])

        teachers = db.session.scalars(query).all()
        return [serialize_teacher(teacher) for teacher in teachers]

    @staticmethod
    def create_teacher(payload: dict) -> dict:
        validated = validate_teacher_payload(payload)
        DocenteService._ensure_unique_teacher_key(validated["clave_docente"])

        teacher = Docente(**validated)
        db.session.add(teacher)
        db.session.commit()
        db.session.refresh(teacher)
        return serialize_teacher(teacher)

    @staticmethod
    def get_teacher_detail(teacher_id: int) -> dict:
        teacher = DocenteService._get_teacher_or_404(teacher_id)
        return serialize_teacher(teacher)

    @staticmethod
    def update_teacher(teacher_id: int, payload: dict) -> dict:
        teacher = DocenteService._get_teacher_or_404(teacher_id)
        validated = validate_teacher_payload(payload, partial=True)

        if "clave_docente" in validated and validated["clave_docente"] != teacher.clave_docente:
            DocenteService._ensure_unique_teacher_key(validated["clave_docente"])

        for field_name, value in validated.items():
            setattr(teacher, field_name, value)

        db.session.commit()
        db.session.refresh(teacher)
        return serialize_teacher(teacher)

    @staticmethod
    def delete_teacher(teacher_id: int) -> None:
        teacher = DocenteService._get_teacher_or_404(teacher_id)
        if teacher.bloques_horario:
            raise ConflictApiError(
                "No se puede eliminar el docente",
                ["El docente tiene bloques de horario asociados"],
            )

        db.session.delete(teacher)
        db.session.commit()

    @staticmethod
    def get_teacher_hours(teacher_id: int) -> dict:
        teacher = DocenteService._get_teacher_or_404(teacher_id)
        hours = calculate_hours_from_blocks(teacher.bloques_horario)
        return {
            "docente": serialize_teacher(teacher, include_hours=False),
            "horas_acumuladas": hours,
            "limite_horas": MAX_TEACHER_HOURS,
            "disponible_horas": round(MAX_TEACHER_HOURS - hours, 2),
        }

    @staticmethod
    def _get_teacher_or_404(teacher_id: int) -> Docente:
        teacher = db.session.get(Docente, teacher_id)
        if teacher is None:
            raise NotFoundApiError("Docente no encontrado", [f"No existe un docente con id {teacher_id}"])
        return teacher

    @staticmethod
    def _ensure_unique_teacher_key(clave_docente: str) -> None:
        existing_teacher = db.session.scalar(
            select(Docente).where(Docente.clave_docente == clave_docente)
        )
        if existing_teacher is not None:
            raise ConflictApiError(
                "El docente ya existe",
                [f"La clave {clave_docente} ya fue registrada"],
            )

    @staticmethod
    def set_judge_schedule(teacher_id: int, slots: list[dict]) -> dict:
        """Reemplaza el horario predefinido de juez del docente con los slots dados."""
        teacher = DocenteService._get_teacher_or_404(teacher_id)

        cleaned_slots = []
        for i, slot in enumerate(slots):
            n = i + 1
            day = str(slot.get("dia", "")).strip().lower()
            if day not in ALLOWED_DAYS:
                raise ValidationApiError(
                    "Horario de juez inválido",
                    [f"Slot {n}: el día '{day}' no es válido. Usa lunes/martes/miercoles/jueves/viernes/sabado"],
                )

            try:
                hora_inicio = int(slot.get("hora_inicio", ""))
                hora_fin = int(slot.get("hora_fin", ""))
            except (TypeError, ValueError):
                raise ValidationApiError("Horario de juez inválido", [f"Slot {n}: hora_inicio y hora_fin deben ser enteros"])

            if not (7 <= hora_inicio <= 23):
                raise ValidationApiError("Horario de juez inválido", [f"Slot {n}: hora_inicio fuera de rango (7-23)"])

            if hora_fin <= hora_inicio or hora_fin > 24:
                raise ValidationApiError(
                    "Horario de juez inválido",
                    [f"Slot {n}: hora_fin debe ser mayor que hora_inicio y no mayor a 24"],
                )

            cleaned_slots.append({"dia": day, "hora_inicio": hora_inicio, "hora_fin": hora_fin})

        # Eliminar slots anteriores y reemplazar
        for existing in list(teacher.horario_juez):
            db.session.delete(existing)

        for s in cleaned_slots:
            teacher.horario_juez.append(HorarioJuez(docente_id=teacher_id, **s))

        db.session.commit()
        db.session.refresh(teacher)
        return serialize_teacher(teacher)