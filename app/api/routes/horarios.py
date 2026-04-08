from flask import Blueprint, request

from app.services.horario_service import HorarioService
from app.services.response_service import success_response
from app.services.summary_service import SummaryService
from app.utils.exceptions import ApiError


horarios_bp = Blueprint("horarios", __name__)


@horarios_bp.get("/grupos/<int:group_id>/horarios")
def get_group_schedule(group_id: int):
    data = HorarioService.get_group_schedule(group_id)
    return success_response("Horario del grupo obtenido correctamente", data)


@horarios_bp.post("/horarios/bloques")
def create_schedule_block():
    data = HorarioService.create_block(request.get_json(silent=True) or {})
    return success_response("Bloque creado correctamente", data, status_code=201)


@horarios_bp.delete("/horarios/bloques/<int:block_id>")
def delete_schedule_block(block_id: int):
    data = HorarioService.delete_block(block_id)
    return success_response("Bloque eliminado correctamente", data)


@horarios_bp.patch("/horarios/bloques/<int:block_id>")
def update_schedule_block(block_id: int):
    data = HorarioService.update_block(block_id, request.get_json(silent=True) or {})
    return success_response("Bloque actualizado correctamente", data)


@horarios_bp.patch("/grupos/<int:group_id>/materias/<int:subject_id>/docente")
def reassign_subject_teacher(group_id: int, subject_id: int):
    payload = request.get_json(silent=True) or {}
    if "docente_id" not in payload:
        payload["docente_id"] = None
    data = HorarioService.reassign_subject_teacher(group_id, subject_id, payload["docente_id"])
    return success_response("Docente de materia reasignado correctamente", data)


@horarios_bp.post("/horarios/validar")
def validate_schedule_block():
    payload = request.get_json(silent=True) or {}
    try:
        data = HorarioService.validate_block_payload(payload)
    except ApiError as error:
        data = {
            "valid": False,
            "message": error.message,
            "errors": error.errors,
        }
    return success_response("Validacion de bloque completada", data)


@horarios_bp.get("/grupos/<int:group_id>/resumen")
def get_group_summary(group_id: int):
    data = SummaryService.get_group_summary(group_id)
    return success_response("Resumen del grupo obtenido correctamente", data)


@horarios_bp.get("/planes/<int:plan_id>/resumen")
def get_plan_summary(plan_id: int):
    data = SummaryService.get_plan_summary(plan_id)
    return success_response("Resumen del plan obtenido correctamente", data)