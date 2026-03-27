from flask import Blueprint, request

from app.services.materia_service import MateriaService
from app.services.response_service import success_response
from app.services.summary_service import SummaryService


materias_bp = Blueprint("materias", __name__)


@materias_bp.get("/materias")
def list_subjects():
    data = MateriaService.list_subjects(request.args)
    return success_response("Materias obtenidas correctamente", data)


@materias_bp.post("/materias")
def create_subject():
    data = MateriaService.create_subject(request.get_json(silent=True) or {})
    return success_response("Materia creada correctamente", data, status_code=201)


@materias_bp.get("/materias/<int:subject_id>")
def get_subject(subject_id: int):
    data = MateriaService.get_subject_detail(subject_id)
    return success_response("Materia obtenida correctamente", data)


@materias_bp.patch("/materias/<int:subject_id>")
def update_subject(subject_id: int):
    data = MateriaService.update_subject(subject_id, request.get_json(silent=True) or {})
    return success_response("Materia actualizada correctamente", data)


@materias_bp.delete("/materias/<int:subject_id>")
def delete_subject(subject_id: int):
    MateriaService.delete_subject(subject_id)
    return success_response("Materia eliminada correctamente", None)


@materias_bp.get("/grupos/<int:group_id>/materias")
def list_subjects_by_group(group_id: int):
    data = MateriaService.list_subjects_for_group(group_id, request.args)
    return success_response("Materias del grupo obtenidas correctamente", data)


@materias_bp.get("/materias/sin-docente")
def list_subjects_without_teacher():
    group_id = request.args.get("group_id")
    data = SummaryService.list_subjects_without_teacher(group_id)
    return success_response("Materias sin docente obtenidas correctamente", data)