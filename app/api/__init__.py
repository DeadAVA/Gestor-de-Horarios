from flask import Flask, Blueprint

from app.api.routes import register_route_modules
from app.services.response_service import success_response


def register_blueprints(app: Flask) -> None:
    api_bp = Blueprint("api", __name__, url_prefix="/api")

    @api_bp.get("/health")
    def healthcheck():
        return success_response("API operativa", {"status": "ok"})

    register_route_modules(api_bp)
    app.register_blueprint(api_bp)