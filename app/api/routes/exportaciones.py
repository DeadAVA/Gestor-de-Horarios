from flask import Blueprint

from app.services.export_service import ExportService


exportaciones_bp = Blueprint("exportaciones", __name__)


@exportaciones_bp.get("/exportaciones/grupos/<int:group_id>/excel")
def export_group_excel(group_id: int):
    return ExportService.export_group_schedule_excel(group_id)


@exportaciones_bp.get("/exportaciones/grupos/<int:group_id>/word")
def export_group_word(group_id: int):
    return ExportService.export_group_schedule_word(group_id)


@exportaciones_bp.get("/exportaciones/grupos/<int:group_id>/pdf")
def export_group_pdf(group_id: int):
    return ExportService.export_group_schedule_pdf(group_id)


@exportaciones_bp.get("/exportaciones/grupos/todos/<string:format_name>")
def export_all_groups(format_name: str):
    return ExportService.export_all_group_schedules(format_name)


# ──── Historial de docentes ────────────────────────────────────────────────

@exportaciones_bp.get("/exportaciones/historial/excel")
def export_historial_general_excel():
    return ExportService.export_historial_excel()


@exportaciones_bp.get("/exportaciones/historial/word")
def export_historial_general_word():
    return ExportService.export_historial_word()


@exportaciones_bp.get("/exportaciones/historial/pdf")
def export_historial_general_pdf():
    return ExportService.export_historial_pdf()


@exportaciones_bp.get("/exportaciones/historial/<int:teacher_id>/excel")
def export_historial_teacher_excel(teacher_id: int):
    return ExportService.export_historial_excel(teacher_id=teacher_id)


@exportaciones_bp.get("/exportaciones/historial/<int:teacher_id>/word")
def export_historial_teacher_word(teacher_id: int):
    return ExportService.export_historial_word(teacher_id=teacher_id)


@exportaciones_bp.get("/exportaciones/historial/<int:teacher_id>/pdf")
def export_historial_teacher_pdf(teacher_id: int):
    return ExportService.export_historial_pdf(teacher_id=teacher_id)

