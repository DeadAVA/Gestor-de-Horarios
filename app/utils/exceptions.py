from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.services.response_service import error_response


class ApiError(Exception):
    status_code = 400

    def __init__(self, message: str, errors=None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []
        if status_code is not None:
            self.status_code = status_code


class ValidationApiError(ApiError):
    status_code = 400


class NotFoundApiError(ApiError):
    status_code = 404


class ConflictApiError(ApiError):
    status_code = 409


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        db.session.rollback()
        return error_response(error.message, error.errors, error.status_code)

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error: IntegrityError):
        db.session.rollback()
        return error_response(
            "No fue posible completar la operacion por una restriccion de integridad",
            [str(error.orig)],
            409,
        )

    @app.errorhandler(404)
    def handle_not_found(error):
        return error_response("Recurso no encontrado", ["La ruta solicitada no existe"], 404)

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return error_response(
            "Metodo no permitido",
            ["El metodo HTTP no esta permitido para este recurso"],
            405,
        )

    @app.errorhandler(500)
    def handle_server_error(error):
        db.session.rollback()
        return error_response(
            "Error interno del servidor",
            ["Ocurrio un error inesperado al procesar la solicitud"],
            500,
        )