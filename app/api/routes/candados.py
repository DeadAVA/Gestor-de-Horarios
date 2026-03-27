from flask import Blueprint, request

from app.services.candado_service import CandadoService
from app.services.response_service import success_response


candados_bp = Blueprint("candados", __name__)


@candados_bp.get("/candados")
def list_candados():
    data = CandadoService.list_locks()
    return success_response("Candados obtenidos correctamente", data)


@candados_bp.post("/candados")
def create_candado():
    data = CandadoService.create_lock(request.get_json(silent=True) or {})
    return success_response("Candado creado correctamente", data, status_code=201)


@candados_bp.patch("/candados/<int:lock_id>")
def update_candado(lock_id: int):
    data = CandadoService.update_lock(lock_id, request.get_json(silent=True) or {})
    return success_response("Candado actualizado correctamente", data)


@candados_bp.delete("/candados/<int:lock_id>")
def delete_candado(lock_id: int):
    CandadoService.delete_lock(lock_id)
    return success_response("Candado eliminado correctamente", None)
