from sqlalchemy import func, select

from app.extensions import db
from app.models import BloqueHorario, Docente, Grupo, Materia, PlanEstudio
from app.services.group_rules import is_manual_selection_group, resolve_group_modality
from app.services.subject_selection import build_valid_subjects_query_for_group
from app.services.vacancy_teacher import VACANCY_TEACHER_KEY
from app.utils.exceptions import NotFoundApiError, ValidationApiError
from app.utils.parsing import coerce_int
from app.utils.serializers import serialize_block, serialize_group, serialize_plan, serialize_subject
from app.utils.time_utils import calculate_hours_from_blocks, day_sort_key


class SummaryService:
    @staticmethod
    def get_group_summary(group_id: int) -> dict:
        group = db.session.get(Grupo, group_id)
        if group is None:
            raise NotFoundApiError("Grupo no encontrado", [f"No existe un grupo con id {group_id}"])

        blocks = SummaryService._get_sorted_blocks_for_group(group.id)
        if SummaryService._is_manual_schedule_group(group):
            missing_subjects = SummaryService._compute_missing_subjects_for_manual_group(group, blocks)
            assigned_subject_ids = {
                block.materia_id
                for block in blocks
                if block.docente and block.docente.clave_docente != VACANCY_TEACHER_KEY
            }
            vacancy_teacher_ids = SummaryService._get_vacancy_teacher_ids()
            assigned_teacher_ids = {
                block.docente_id
                for block in blocks
                if block.docente_id not in vacancy_teacher_ids
            }

            return {
                "grupo": serialize_group(group),
                "plan_estudio": serialize_plan(group.plan_estudio),
                "capacidad": group.capacidad_alumnos,
                "total_bloques": len(blocks),
                "total_materias_asignadas": len(assigned_subject_ids),
                "total_docentes_asignados": len(assigned_teacher_ids),
                "horas_programadas": calculate_hours_from_blocks(blocks),
                "materias_sin_docente": [serialize_subject(subject) for subject in missing_subjects],
                "bloques_horario": [serialize_block(block) for block in blocks],
            }

        valid_subjects = SummaryService._get_valid_subjects_for_group(group)
        vacancy_teacher_ids = SummaryService._get_vacancy_teacher_ids()
        assigned_subject_ids = {
            subject_id
            for subject_id in db.session.scalars(
                select(BloqueHorario.materia_id)
                .where(BloqueHorario.grupo_id == group.id)
                .where(BloqueHorario.docente_id.not_in(vacancy_teacher_ids))
                .distinct()
            ).all()
        }
        globally_assigned_subject_ids = SummaryService._get_globally_assigned_subject_ids(vacancy_teacher_ids)
        missing_subjects = SummaryService._compute_missing_subjects(
            valid_subjects,
            assigned_subject_ids,
            globally_assigned_subject_ids,
        )
        assigned_teacher_ids = {
            block.docente_id
            for block in blocks
            if block.docente_id not in vacancy_teacher_ids
        }

        return {
            "grupo": serialize_group(group),
            "plan_estudio": serialize_plan(group.plan_estudio),
            "capacidad": group.capacidad_alumnos,
            "total_bloques": len(blocks),
            "total_materias_asignadas": len(assigned_subject_ids),
            "total_docentes_asignados": len(assigned_teacher_ids),
            "horas_programadas": calculate_hours_from_blocks(blocks),
            "materias_sin_docente": [serialize_subject(subject) for subject in missing_subjects],
            "bloques_horario": [serialize_block(block) for block in blocks],
        }

    @staticmethod
    def get_plan_summary(plan_id: int) -> dict:
        plan = db.session.get(PlanEstudio, plan_id)
        if plan is None:
            raise NotFoundApiError("Plan de estudio no encontrado", [f"No existe un plan con id {plan_id}"])

        groups = db.session.scalars(
            select(Grupo).where(Grupo.plan_estudio_id == plan.id).order_by(Grupo.numero_grupo.asc())
        ).all()
        group_ids = [group.id for group in groups]

        blocks = []
        distinct_teacher_count = 0
        if group_ids:
            blocks = db.session.scalars(
                select(BloqueHorario).where(BloqueHorario.grupo_id.in_(group_ids))
            ).all()
            distinct_teacher_count = len({block.docente_id for block in blocks})

        subject_count = db.session.scalar(
            select(func.count(Materia.id)).where(Materia.plan_estudio_id == plan.id)
        ) or 0

        return {
            "plan_estudio": serialize_plan(plan),
            "total_grupos": len(groups),
            "total_materias": subject_count,
            "total_bloques": len(blocks),
            "total_docentes_asignados": distinct_teacher_count,
            "horas_programadas": calculate_hours_from_blocks(blocks),
            "grupos": [
                {
                    "id": group.id,
                    "numero_grupo": group.numero_grupo,
                    "semestre": group.semestre,
                    "capacidad_alumnos": group.capacidad_alumnos,
                    "tipo_grupo": group.tipo_grupo,
                    "total_bloques": sum(1 for block in blocks if block.grupo_id == group.id),
                    "materias_asignadas": len({block.materia_id for block in blocks if block.grupo_id == group.id}),
                }
                for group in groups
            ],
        }

    @staticmethod
    def list_subjects_without_teacher(group_id=None):
        if group_id is not None:
            try:
                parsed_group_id = coerce_int(group_id, "group_id")
            except ValueError as error:
                raise ValidationApiError("Parametro invalido", [str(error)])
            group_summary = SummaryService.get_group_summary(parsed_group_id)
            return {
                "scope": "group",
                "group_id": parsed_group_id,
                "materias": group_summary["materias_sin_docente"],
            }

        groups = db.session.scalars(select(Grupo).order_by(Grupo.numero_grupo.asc())).all()
        return {
            "scope": "all_groups",
            "items": [
                {
                    "grupo": serialize_group(group),
                    "materias": SummaryService.get_group_summary(group.id)["materias_sin_docente"],
                }
                for group in groups
            ],
        }

    @staticmethod
    def _get_valid_subjects_for_group(group: Grupo) -> list[Materia]:
        return db.session.scalars(
            build_valid_subjects_query_for_group(group)
        ).all()

    @staticmethod
    def _compute_missing_subjects(
        valid_subjects: list[Materia],
        assigned_subject_ids: set[int],
        globally_assigned_subject_ids: set[int],
    ) -> list[Materia]:
        valid_optativa_ids = {subject.id for subject in valid_subjects if subject.tipo_materia == "optativa"}
        has_assigned_optativa = bool(valid_optativa_ids.intersection(assigned_subject_ids))
        has_globally_assigned_optativa = bool(valid_optativa_ids.intersection(globally_assigned_subject_ids))

        missing_subjects: list[Materia] = []
        for subject in valid_subjects:
            if subject.id in assigned_subject_ids:
                continue
            if (has_assigned_optativa or has_globally_assigned_optativa) and subject.tipo_materia == "optativa":
                continue
            missing_subjects.append(subject)

        return missing_subjects

    @staticmethod
    def _compute_missing_subjects_for_manual_group(group: Grupo, blocks: list[BloqueHorario]) -> list[Materia]:
        subject_ids_in_group = {block.materia_id for block in blocks}
        if not subject_ids_in_group:
            return []

        subject_ids_with_real_teacher = {
            block.materia_id
            for block in blocks
            if block.docente and block.docente.clave_docente != VACANCY_TEACHER_KEY
        }
        missing_subject_ids = subject_ids_in_group - subject_ids_with_real_teacher
        if not missing_subject_ids:
            return []

        subjects = db.session.scalars(
            select(Materia)
            .where(Materia.id.in_(missing_subject_ids))
            .order_by(Materia.nombre.asc())
        ).all()
        return subjects

    @staticmethod
    def _is_manual_schedule_group(group: Grupo) -> bool:
        if resolve_group_modality(group.numero_grupo, group.tipo_grupo) == "maestria":
            return True
        return is_manual_selection_group(int(group.numero_grupo), group.tipo_grupo)

    @staticmethod
    def _get_globally_assigned_subject_ids(vacancy_teacher_ids: set[int]) -> set[int]:
        return {
            subject_id
            for subject_id in db.session.scalars(
                select(BloqueHorario.materia_id)
                .where(BloqueHorario.docente_id.not_in(vacancy_teacher_ids))
                .distinct()
            ).all()
        }

    @staticmethod
    def _get_vacancy_teacher_ids() -> set[int]:
        return {
            teacher_id
            for teacher_id in db.session.scalars(
                select(Docente.id).where(Docente.clave_docente == VACANCY_TEACHER_KEY)
                .distinct()
            ).all()
            if teacher_id is not None
        }

    @staticmethod
    def _get_sorted_blocks_for_group(group_id: int) -> list[BloqueHorario]:
        blocks = db.session.scalars(select(BloqueHorario).where(BloqueHorario.grupo_id == group_id)).all()
        return sorted(blocks, key=lambda block: (day_sort_key(block.dia), block.hora_inicio, block.hora_fin))