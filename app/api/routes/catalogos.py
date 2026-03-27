from flask import Blueprint
from sqlalchemy import select

from app.extensions import db
from app.models import PlanEstudio
from app.services.response_service import success_response

catalogos_bp = Blueprint("catalogos", __name__)


@catalogos_bp.get("/catalogos/modalidades")
def get_modalidades():
    return success_response(
        "Catalogo de modalidades obtenido correctamente",
        ["presencial", "virtual"],
    )


@catalogos_bp.get("/catalogos/planes-estudio")
def get_planes_estudio():
    planes = db.session.scalars(
        select(PlanEstudio)
        .where(PlanEstudio.activo.is_(True))
        .order_by(PlanEstudio.clave.asc())
    ).all()
    return success_response(
        "Catalogo de planes de estudio obtenido correctamente",
        [
            {
                "id": plan.id,
                "clave": plan.clave,
                "nombre": plan.nombre,
            }
            for plan in planes
        ],
    )