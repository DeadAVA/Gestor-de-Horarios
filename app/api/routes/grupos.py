from flask import Blueprint, request

from app.services.group_service import GroupService
from app.services.response_service import success_response


grupos_bp = Blueprint("grupos", __name__)


@grupos_bp.get("/grupos")
def list_groups():
    data = GroupService.list_groups(request.args)
    return success_response("Grupos obtenidos correctamente", data)


@grupos_bp.post("/grupos")
def create_group():
    data = GroupService.create_group(request.get_json(silent=True) or {})
    return success_response("Grupo creado correctamente", data, status_code=201)


@grupos_bp.get("/grupos/<int:group_id>")
def get_group(group_id: int):
    data = GroupService.get_group_detail(group_id)
    return success_response("Grupo obtenido correctamente", data)


@grupos_bp.patch("/grupos/<int:group_id>")
def update_group(group_id: int):
    data = GroupService.update_group(group_id, request.get_json(silent=True) or {})
    return success_response("Grupo actualizado correctamente", data)


@grupos_bp.delete("/grupos/<int:group_id>")
def delete_group(group_id: int):
    GroupService.delete_group(group_id)
    return success_response("Grupo eliminado correctamente", None)