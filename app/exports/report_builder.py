from collections import OrderedDict
from datetime import datetime

from sqlalchemy import select

from app.extensions import db
from app.exports.institutional_layout import (
    CAREER_CODE,
    CAREER_NAME,
    COORDINATION_NAME,
    DAY_KEYS,
    DEFAULT_PERIOD,
    INSTITUTION_NAME,
    REPORT_CODE,
    REPORT_TITLE,
    UNIT_CODE,
    UNIT_NAME,
)
from app.models import BloqueHorario, Grupo
from app.utils.exceptions import NotFoundApiError
from app.utils.time_utils import calculate_duration_hours, day_sort_key, format_time_value


class ReportBuilder:
    @staticmethod
    def build_group_report_context(group_id: int) -> dict:
        group = db.session.get(Grupo, group_id)
        if group is None:
            raise NotFoundApiError("Grupo no encontrado", [f"No existe un grupo con id {group_id}"])

        blocks = db.session.scalars(
            select(BloqueHorario).where(BloqueHorario.grupo_id == group.id)
        ).all()
        sorted_blocks = sorted(
            blocks,
            key=lambda block: (day_sort_key(block.dia), block.hora_inicio, block.hora_fin, block.materia.nombre),
        )

        rows = OrderedDict()
        for block in sorted_blocks:
            teacher_code = block.docente.clave_docente if block.docente else "VACANTE-SISTEMA"
            teacher_name = block.docente.nombre if block.docente else "Vacante"
            row_key = (block.materia_id, block.docente_id or 0)
            if row_key not in rows:
                rows[row_key] = {
                    "subject_code": block.materia.clave,
                    "teacher_code": teacher_code,
                    "subject_name": block.materia.nombre,
                    "teacher_name": teacher_name,
                    "edificio": "",
                    "salon": "0",
                    "capacidad": group.capacidad_alumnos,
                    "tipo_sgp": "N",
                    "days": {key: [] for key, _ in DAY_KEYS},
                    "weekly_hours": 0.0,
                    "virtual": False,
                }

            rows[row_key]["days"][block.dia].append(
                _format_export_schedule_label(block.hora_inicio, block.hora_fin, block.modalidad)
            )
            rows[row_key]["weekly_hours"] += calculate_duration_hours(block.hora_inicio, block.hora_fin)
            if block.modalidad == "virtual":
                rows[row_key]["virtual"] = True
                rows[row_key]["salon"] = "VIR"

        rendered_rows = []
        for row in rows.values():
            rendered_rows.append(
                {
                    "clave_control": f"{row['subject_code']}\n{row['teacher_code']}",
                    "descripcion_maestro": (
                        f"{row['subject_name'].upper()}"
                        f"{' (VIR)' if row['virtual'] else ''}\n{row['teacher_name'].upper()}"
                    ),
                    "edificio": row["edificio"],
                    "salon": row["salon"],
                    "cap_asg": row["capacidad"],
                    "tpo_sgp": row["tipo_sgp"],
                    "lunes": _join_schedule_values(row["days"]["lunes"]),
                    "martes": _join_schedule_values(row["days"]["martes"]),
                    "miercoles": _join_schedule_values(row["days"]["miercoles"]),
                    "jueves": _join_schedule_values(row["days"]["jueves"]),
                    "viernes": _join_schedule_values(row["days"]["viernes"]),
                    "sabado": _join_schedule_values(row["days"]["sabado"]),
                    "domingo": _join_schedule_values(row["days"]["domingo"]),
                    "es": int(row["weekly_hours"]) if row["weekly_hours"].is_integer() else row["weekly_hours"],
                }
            )

        if not rendered_rows:
            rendered_rows.append(
                {
                    "clave_control": "-",
                    "descripcion_maestro": "SIN BLOQUES PROGRAMADOS",
                    "edificio": "",
                    "salon": "",
                    "cap_asg": group.capacidad_alumnos,
                    "tpo_sgp": "N",
                    "lunes": "",
                    "martes": "",
                    "miercoles": "",
                    "jueves": "",
                    "viernes": "",
                    "sabado": "",
                    "domingo": "",
                    "es": 0,
                }
            )

        now = datetime.now()
        return {
            "report_code": REPORT_CODE,
            "generated_time": now.strftime("%H:%M:%S"),
            "generated_date": now.strftime("%d-%b-%Y"),
            "institution_name": INSTITUTION_NAME,
            "coordination_name": COORDINATION_NAME,
            "report_title": REPORT_TITLE,
            "period": DEFAULT_PERIOD,
            "unit_code": UNIT_CODE,
            "unit_name": UNIT_NAME,
            "career_code": CAREER_CODE,
            "career_name": CAREER_NAME,
            "plan_key": _display_plan_key(group.plan_estudio.clave),
            "group_number": group.numero_grupo,
            "group_type_label": _group_type_label(group.tipo_grupo),
            "semester": group.semestre,
            "group_capacity": group.capacidad_alumnos,
            "rows": rendered_rows,
        }


def _join_schedule_values(values: list[str]) -> str:
    return "\n\n".join(values)


def _display_plan_key(plan_key: str) -> str:
    return "2015-2" if plan_key == "2025-2" else plan_key


def _group_type_label(group_type: str) -> str:
    return "SEMIESCOLARIZADO" if group_type == "semi" else "ESCOLARIZADO"


def _format_export_schedule_label(start_time, end_time, modalidad: str) -> str:
    start_label = format_time_value(start_time)
    end_label = format_time_value(end_time)
    if modalidad == "virtual":
        return f"{start_label}\n{end_label}\nVIR"
    return f"{start_label}\n{end_label}"
