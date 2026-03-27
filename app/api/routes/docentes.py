from flask import Blueprint, request

from app.services.docente_service import DocenteService
from app.services.historial_service import HistorialService
from app.services.response_service import success_response


docentes_bp = Blueprint("docentes", __name__)


@docentes_bp.get("/docentes")
def list_teachers():
    data = DocenteService.list_teachers(request.args)
    return success_response("Docentes obtenidos correctamente", data)


@docentes_bp.post("/docentes")
def create_teacher():
    data = DocenteService.create_teacher(request.get_json(silent=True) or {})
    return success_response("Docente creado correctamente", data, status_code=201)


@docentes_bp.get("/docentes/<int:teacher_id>")
def get_teacher(teacher_id: int):
    data = DocenteService.get_teacher_detail(teacher_id)
    return success_response("Docente obtenido correctamente", data)


@docentes_bp.patch("/docentes/<int:teacher_id>")
def update_teacher(teacher_id: int):
    data = DocenteService.update_teacher(teacher_id, request.get_json(silent=True) or {})
    return success_response("Docente actualizado correctamente", data)


@docentes_bp.delete("/docentes/<int:teacher_id>")
def delete_teacher(teacher_id: int):
    DocenteService.delete_teacher(teacher_id)
    return success_response("Docente eliminado correctamente", None)


@docentes_bp.get("/docentes/<int:teacher_id>/horas")
def get_teacher_hours(teacher_id: int):
    data = DocenteService.get_teacher_hours(teacher_id)
    return success_response("Horas acumuladas obtenidas correctamente", data)


@docentes_bp.put("/docentes/<int:teacher_id>/horario_juez")
def set_judge_schedule(teacher_id: int):
    payload = request.get_json(silent=True) or {}
    slots = payload.get("slots", [])
    if not isinstance(slots, list):
        slots = []
    data = DocenteService.set_judge_schedule(teacher_id, slots)
    return success_response("Horario de juez actualizado correctamente", data)


# ──── Historial ────────────────────────────────────────────────────────────

@docentes_bp.get("/docentes/historial")
def get_historial_all():
    data = HistorialService.get_historial_all()
    return success_response("Historial obtenido correctamente", data)


@docentes_bp.get("/docentes/<int:teacher_id>/historial")
def get_historial_by_teacher(teacher_id: int):
    data = HistorialService.get_historial_by_teacher(teacher_id)
    return success_response("Historial del docente obtenido correctamente", data)


# ──── Observaciones ────────────────────────────────────────────────────────

@docentes_bp.get("/docentes/observaciones")
def get_all_observaciones():
    data = HistorialService.get_all_observaciones()
    return success_response("Observaciones obtenidas correctamente", data)


@docentes_bp.get("/docentes/<int:teacher_id>/observaciones/<int:materia_id>")
def get_observacion(teacher_id: int, materia_id: int):
    data = HistorialService.get_observacion(teacher_id, materia_id)
    return success_response("Observación obtenida correctamente", data)


@docentes_bp.put("/docentes/<int:teacher_id>/observaciones/<int:materia_id>")
def upsert_observacion(teacher_id: int, materia_id: int):
    data = HistorialService.upsert_observacion(
        teacher_id, materia_id, request.get_json(silent=True) or {}
    )
    return success_response("Observación guardada correctamente", data)


@docentes_bp.delete("/docentes/<int:teacher_id>/observaciones/<int:materia_id>")
def delete_observacion(teacher_id: int, materia_id: int):
    HistorialService.delete_observacion(teacher_id, materia_id)
    return success_response("Observación eliminada correctamente", None)
