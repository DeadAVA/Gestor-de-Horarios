from sqlalchemy import select

from app.extensions import db
from app.models import BloqueHorario, Docente, Grupo, Materia
from app.services.candado_service import CandadoService
from app.services.docente_service import MAX_TEACHER_HOURS
from app.services.subject_selection import build_valid_subjects_query_for_group
from app.services.vacancy_teacher import get_or_create_vacancy_teacher, is_vacancy_teacher
from app.utils.exceptions import ConflictApiError, NotFoundApiError, ValidationApiError
from app.utils.serializers import serialize_block, serialize_group, serialize_plan, serialize_subject, serialize_teacher
from app.utils.time_utils import END_OF_DAY_SENTINEL, calculate_duration_hours, calculate_hours_from_blocks, day_sort_key, format_time_value
from app.validators.horario_validator import validate_schedule_block_payload


class HorarioService:
    @staticmethod
    def get_group_schedule(group_id: int) -> dict:
        group = HorarioService._get_group_or_404(group_id)
        valid_subjects = HorarioService._get_valid_subjects_for_group(group)
        blocks = HorarioService._get_sorted_group_blocks(group.id)

        return {
            "grupo": serialize_group(group),
            "semestre": group.semestre,
            "plan_estudio": serialize_plan(group.plan_estudio),
            "capacidad": group.capacidad_alumnos,
            "materias_disponibles": [serialize_subject(subject) for subject in valid_subjects],
            "bloques_horario": [serialize_block(block) for block in blocks],
        }

    @staticmethod
    def create_block(payload: dict) -> dict:
        validation_result = HorarioService._validate_schedule_rules(payload)

        block = BloqueHorario(
            grupo_id=validation_result["group"].id,
            materia_id=validation_result["subject"].id,
            docente_id=validation_result["teacher"].id,
            dia=validation_result["payload"]["dia"],
            hora_inicio=validation_result["payload"]["hora_inicio"],
            hora_fin=validation_result["payload"]["hora_fin"],
            modalidad=validation_result["payload"]["modalidad"],
        )
        db.session.add(block)
        db.session.commit()
        db.session.refresh(block)
        return serialize_block(block)

    @staticmethod
    def delete_block(block_id: int) -> dict:
        block = db.session.get(BloqueHorario, block_id)
        if block is None:
            raise NotFoundApiError("Bloque no encontrado", [f"No existe un bloque con id {block_id}"])

        serialized = serialize_block(block)
        db.session.delete(block)
        db.session.commit()
        return serialized

    @staticmethod
    def update_block(block_id: int, payload: dict) -> dict:
        block = db.session.get(BloqueHorario, block_id)
        if block is None:
            raise NotFoundApiError("Bloque no encontrado", [f"No existe un bloque con id {block_id}"])

        validation_result = HorarioService._validate_schedule_rules(payload, exclude_block_id=block_id)

        block.grupo_id = validation_result["group"].id
        block.materia_id = validation_result["subject"].id
        block.docente_id = validation_result["teacher"].id
        block.dia = validation_result["payload"]["dia"]
        block.hora_inicio = validation_result["payload"]["hora_inicio"]
        block.hora_fin = validation_result["payload"]["hora_fin"]
        block.modalidad = validation_result["payload"]["modalidad"]

        db.session.commit()
        db.session.refresh(block)
        return serialize_block(block)

    @staticmethod
    def reassign_subject_teacher(group_id: int, subject_id: int, teacher_id: int) -> dict:
        group = HorarioService._get_group_or_404(group_id)
        subject = HorarioService._get_subject_or_404(subject_id)
        HorarioService._ensure_subject_matches_group(group, subject)

        blocks = db.session.scalars(
            select(BloqueHorario)
            .where(BloqueHorario.grupo_id == group.id)
            .where(BloqueHorario.materia_id == subject.id)
            .order_by(BloqueHorario.id.asc())
        ).all()

        if not blocks:
            return {
                "group_id": group.id,
                "materia_id": subject.id,
                "docente_id": int(teacher_id),
                "updated_blocks": 0,
                "bloques": [],
            }

        for block in blocks:
            payload = {
                "group_id": group.id,
                "materia_id": subject.id,
                "docente_id": int(teacher_id),
                "dia": block.dia,
                "hora_inicio": format_time_value(block.hora_inicio),
                "hora_fin": format_time_value(block.hora_fin),
                "modalidad": block.modalidad,
            }

            validation_result = HorarioService._validate_schedule_rules(
                payload,
                exclude_block_id=block.id,
                enforce_single_teacher_rule=False,
            )

            block.docente_id = validation_result["teacher"].id
            db.session.flush()

        db.session.commit()

        refreshed_blocks = HorarioService._get_sorted_group_blocks(group.id)
        affected_blocks = [b for b in refreshed_blocks if b.materia_id == subject.id]
        return {
            "group_id": group.id,
            "materia_id": subject.id,
            "docente_id": int(teacher_id),
            "updated_blocks": len(affected_blocks),
            "bloques": [serialize_block(block) for block in affected_blocks],
        }

    @staticmethod
    def validate_block_payload(payload: dict) -> dict:
        validation_result = HorarioService._validate_schedule_rules(payload)
        teacher_hours = validation_result["teacher_current_hours"]
        assignment_hours = validation_result["assignment_hours"]
        return {
            "valid": True,
            "message": "Bloque valido para persistencia",
            "errors": [],
            "grupo": serialize_group(validation_result["group"]),
            "materia": serialize_subject(validation_result["subject"]),
            "docente": serialize_teacher(validation_result["teacher"]),
            "horas_docente_actuales": teacher_hours,
            "horas_bloque": assignment_hours,
            "horas_docente_resultantes": round(teacher_hours + assignment_hours, 2),
        }

    @staticmethod
    def _validate_schedule_rules(
        payload: dict,
        exclude_block_id: int | None = None,
        enforce_single_teacher_rule: bool = True,
    ) -> dict:
        cleaned_payload = validate_schedule_block_payload(payload)

        group = HorarioService._get_group_or_404(cleaned_payload["group_id"])
        subject = HorarioService._get_subject_or_404(cleaned_payload["materia_id"])
        teacher = HorarioService._resolve_teacher_for_assignment(cleaned_payload["docente_id"])
        vacancy_assignment = is_vacancy_teacher(teacher)

        HorarioService._ensure_subject_matches_group(group, subject)
        if not vacancy_assignment:
            HorarioService._ensure_teacher_is_active(teacher)
            HorarioService._ensure_foraneo_virtual_assignment(teacher, cleaned_payload)
        HorarioService._ensure_not_locked_by_candado(cleaned_payload)

        if not vacancy_assignment:
            conflicting_group_block = HorarioService._find_group_overlap(
                group.id,
                cleaned_payload["dia"],
                cleaned_payload["hora_inicio"],
                cleaned_payload["hora_fin"],
                exclude_block_id=exclude_block_id,
            )
            if conflicting_group_block is not None:
                raise ConflictApiError(
                    f"Conflicto con {conflicting_group_block.materia.nombre} - Prof. {conflicting_group_block.docente.nombre}",
                    [
                        f"El grupo {group.numero_grupo} ya tiene un bloque traslapado en ese horario",
                        f"Bloque en conflicto: grupo {conflicting_group_block.grupo.numero_grupo}",
                        f"Horario en conflicto: {HorarioService._format_schedule_range(conflicting_group_block)}",
                    ],
                )

        if not vacancy_assignment:
            conflicting_teacher_block = HorarioService._find_teacher_overlap(
                teacher.id,
                cleaned_payload["dia"],
                cleaned_payload["hora_inicio"],
                cleaned_payload["hora_fin"],
                exclude_block_id=exclude_block_id,
            )
            if conflicting_teacher_block is not None:
                raise ConflictApiError(
                    f"Conflicto con {conflicting_teacher_block.materia.nombre} - Prof. {conflicting_teacher_block.docente.nombre}",
                    [
                        "El docente ya tiene clases simultaneas en otro grupo",
                        f"Grupo en conflicto: {conflicting_teacher_block.grupo.numero_grupo}",
                        f"Horario en conflicto: {HorarioService._format_schedule_range(conflicting_teacher_block)}",
                    ],
                )

        if not vacancy_assignment and enforce_single_teacher_rule:
            HorarioService._ensure_single_teacher_per_subject(
                group.id,
                subject.id,
                teacher.id,
                exclude_block_id=exclude_block_id,
            )

        teacher_current_hours = 0.0
        assignment_hours = calculate_duration_hours(
            cleaned_payload["hora_inicio"],
            cleaned_payload["hora_fin"],
        )

        if not vacancy_assignment:
            teacher_blocks = teacher.bloques_horario
            if exclude_block_id is not None:
                teacher_blocks = [block for block in teacher_blocks if block.id != exclude_block_id]

            teacher_current_hours = calculate_hours_from_blocks(teacher_blocks)

            if teacher_current_hours >= MAX_TEACHER_HOURS:
                raise ConflictApiError(
                    "El docente ya alcanzó 25 horas",
                    [f"El docente {teacher.nombre} ya tiene {teacher_current_hours} horas asignadas"],
                )

            if teacher_current_hours + assignment_hours > MAX_TEACHER_HOURS:
                raise ConflictApiError(
                    "Esta asignación excede el máximo permitido",
                    [
                        f"El docente {teacher.nombre} sumaria {round(teacher_current_hours + assignment_hours, 2)} horas",
                    ],
                )

        return {
            "payload": cleaned_payload,
            "group": group,
            "subject": subject,
            "teacher": teacher,
            "teacher_current_hours": teacher_current_hours,
            "assignment_hours": assignment_hours,
        }

    @staticmethod
    def _ensure_not_locked_by_candado(cleaned_payload: dict) -> None:
        start_hour = int(cleaned_payload["hora_inicio"].hour)
        end_hour = 24 if cleaned_payload["hora_fin"] == END_OF_DAY_SENTINEL else int(cleaned_payload["hora_fin"].hour)
        conflict = CandadoService.find_conflicting_lock(
            cleaned_payload["dia"],
            start_hour,
            end_hour,
            cleaned_payload["modalidad"],
        )
        if conflict is None:
            return

        alcance = conflict["alcance"]
        if alcance == "ambos":
            alcance_text = "presenciales y virtuales"
        elif alcance == "presencial":
            alcance_text = "presenciales"
        else:
            alcance_text = "virtuales"

        raise ConflictApiError(
            "Horario bloqueado por candado",
            [
                (
                    f"Existe un candado para {conflict['dia']} "
                    f"{str(conflict['hora_inicio']).zfill(2)}:00-"
                    f"{str(conflict['hora_fin']).zfill(2)}:00 "
                    f"aplicable a materias {alcance_text}"
                ),
            ],
        )

    @staticmethod
    def _get_group_or_404(group_id: int) -> Grupo:
        group = db.session.get(Grupo, group_id)
        if group is None:
            raise NotFoundApiError("Grupo no encontrado", [f"No existe un grupo con id {group_id}"])
        return group

    @staticmethod
    def _get_subject_or_404(subject_id: int) -> Materia:
        subject = db.session.get(Materia, subject_id)
        if subject is None:
            raise NotFoundApiError("Materia no encontrada", [f"No existe una materia con id {subject_id}"])
        return subject

    @staticmethod
    def _get_teacher_or_404(teacher_id: int) -> Docente:
        teacher = db.session.get(Docente, teacher_id)
        if teacher is None:
            raise NotFoundApiError("Docente no encontrado", [f"No existe un docente con id {teacher_id}"])
        return teacher

    @staticmethod
    def _resolve_teacher_for_assignment(teacher_id: int) -> Docente:
        if int(teacher_id) == 0:
            return get_or_create_vacancy_teacher()
        return HorarioService._get_teacher_or_404(teacher_id)

    @staticmethod
    def _ensure_subject_matches_group(group: Grupo, subject: Materia) -> None:
        if not subject.activa:
            raise ValidationApiError("La materia no esta activa", [f"La materia {subject.nombre} no puede ser asignada"])

        valid_subject_ids = {
            materia.id
            for materia in HorarioService._get_valid_subjects_for_group(group)
        }

        if subject.id not in valid_subject_ids:
            raise ValidationApiError(
                "La materia no es valida para el grupo",
                [
                    f"La materia {subject.nombre} no corresponde a las opciones disponibles del grupo {group.numero_grupo}",
                ],
            )

    @staticmethod
    def _ensure_teacher_is_active(teacher: Docente) -> None:
        if not teacher.activo:
            raise ValidationApiError(
                "El docente no esta activo",
                [f"El docente {teacher.nombre} no puede recibir nuevas asignaciones"],
            )

    @staticmethod
    def _ensure_foraneo_virtual_assignment(teacher: Docente, cleaned_payload: dict) -> None:
        if not getattr(teacher, "foraneo", False):
            return

        if cleaned_payload.get("modalidad") == "virtual":
            return

        raise ValidationApiError(
            "Asignacion invalida para docente foraneo",
            [f"El docente foraneo {teacher.nombre} solo puede asignarse a clases virtuales"],
        )

    @staticmethod
    def _ensure_single_teacher_per_subject(
        group_id: int,
        subject_id: int,
        teacher_id: int,
        exclude_block_id: int | None = None,
    ) -> None:
        query = (
            select(BloqueHorario)
            .where(BloqueHorario.grupo_id == group_id)
            .where(BloqueHorario.materia_id == subject_id)
            .where(BloqueHorario.docente_id != teacher_id)
        )
        if exclude_block_id is not None:
            query = query.where(BloqueHorario.id != exclude_block_id)

        assigned_subject_block = db.session.scalar(query.limit(1))
        if assigned_subject_block is not None:
            raise ConflictApiError(
                "Esta materia ya tiene docente asignado",
                ["No se permiten dos docentes distintos para la misma materia dentro del mismo grupo"],
            )

    @staticmethod
    def _find_group_overlap(group_id: int, day: str, start_time, end_time, exclude_block_id: int | None = None):
        query = (
            select(BloqueHorario)
            .where(BloqueHorario.grupo_id == group_id)
            .where(BloqueHorario.dia == day)
            .where(BloqueHorario.hora_inicio < end_time)
            .where(BloqueHorario.hora_fin > start_time)
        )
        if exclude_block_id is not None:
            query = query.where(BloqueHorario.id != exclude_block_id)
        return db.session.scalar(query.limit(1))

    @staticmethod
    def _find_teacher_overlap(teacher_id: int, day: str, start_time, end_time, exclude_block_id: int | None = None):
        query = (
            select(BloqueHorario)
            .where(BloqueHorario.docente_id == teacher_id)
            .where(BloqueHorario.dia == day)
            .where(BloqueHorario.hora_inicio < end_time)
            .where(BloqueHorario.hora_fin > start_time)
        )
        if exclude_block_id is not None:
            query = query.where(BloqueHorario.id != exclude_block_id)
        return db.session.scalar(query.limit(1))

    @staticmethod
    def _get_valid_subjects_for_group(group: Grupo) -> list[Materia]:
        return db.session.scalars(
            build_valid_subjects_query_for_group(group)
        ).all()

    @staticmethod
    def _get_sorted_group_blocks(group_id: int) -> list[BloqueHorario]:
        blocks = db.session.scalars(
            select(BloqueHorario).where(BloqueHorario.grupo_id == group_id)
        ).all()
        return sorted(blocks, key=lambda block: (day_sort_key(block.dia), block.hora_inicio, block.hora_fin))

    @staticmethod
    def _format_schedule_range(block: BloqueHorario) -> str:
        return f"{block.dia.capitalize()} {format_time_value(block.hora_inicio)}-{format_time_value(block.hora_fin)}"