from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, request
from werkzeug.utils import secure_filename

from app.services.ia_service import IAService
from app.services.response_service import success_response
from app.utils.exceptions import ValidationApiError


ia_bp = Blueprint("ia", __name__)


@ia_bp.get("/ia/health")
def ia_health():
    data = IAService.get_status()
    return success_response("IA local disponible", data)


@ia_bp.get("/ia/status")
def ia_status():
    data = IAService.get_status()
    return success_response("Estado de IA obtenido correctamente", data)


@ia_bp.get("/ia/modelos")
def ia_models_status():
    data = IAService.get_model_inventory()
    return success_response("Estado de modelos obtenido correctamente", data)


@ia_bp.post("/ia/modelo")
def ia_set_model():
    payload = request.get_json(silent=True) or {}
    model_name = (payload.get("modelo") or "").strip()
    if not model_name:
        raise ValidationApiError("Modelo requerido", ["Debes indicar el campo 'modelo'"])
    data = IAService.set_chat_model(model_name)
    return success_response(f"Modelo cambiado a {model_name}", data)


@ia_bp.post("/ia/modelos/instalar")
def ia_models_install():
    payload = request.get_json(silent=True) or {}
    force = bool(payload.get("force", False))

    data = IAService.start_portable_model_install(force=force)
    return success_response("Instalacion de modelos iniciada", data, status_code=202)


@ia_bp.post("/ia/ingestar-pdf")
def ia_ingest_pdf():
    incoming = request.files.get("archivo")
    if incoming is None:
        raise ValidationApiError("Archivo requerido", ["Debes adjuntar un archivo PDF en el campo archivo"])

    filename = secure_filename(incoming.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise ValidationApiError("Archivo invalido", ["Solo se permite formato PDF"])

    max_mb = int(current_app.config.get("AI_MAX_FILE_MB", 20))
    incoming.stream.seek(0, 2)
    size_bytes = incoming.stream.tell()
    incoming.stream.seek(0)
    if size_bytes > max_mb * 1024 * 1024:
        raise ValidationApiError(
            "Archivo demasiado grande",
            [f"El archivo supera el limite de {max_mb} MB"],
        )

    upload_dir = Path(current_app.config["AI_UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    local_name = f"{uuid4()}_{filename}"
    local_path = upload_dir / local_name
    incoming.save(local_path)

    data = IAService.ingest_pdf(str(local_path), source_name=filename)
    return success_response("PDF indexado correctamente", data, status_code=201)


@ia_bp.post("/ia/chat")
def ia_chat():
    payload = request.get_json(silent=True) or {}
    question = payload.get("pregunta", "")
    top_k = payload.get("top_k")
    history = payload.get("historial") or []

    data = IAService.ask_with_context(question=question, top_k=top_k, history=history)
    return success_response("Respuesta generada correctamente", data)


@ia_bp.post("/ia/aprender")
def ia_learn():
    payload = request.get_json(silent=True) or {}
    note = payload.get("texto", "")
    metadata = payload.get("metadata") or {}

    data = IAService.learn_from_user(note=note, metadata=metadata)
    return success_response("Conocimiento guardado localmente", data, status_code=201)


@ia_bp.post("/ia/aprender-interaccion")
def ia_learn_interaction():
    payload = request.get_json(silent=True) or {}
    question = payload.get("pregunta", "")
    answer = payload.get("respuesta", "")
    metadata = payload.get("metadata") or {}

    data = IAService.learn_from_interaction(question=question, answer=answer, metadata=metadata)
    return success_response("Interaccion validada guardada localmente", data, status_code=201)


@ia_bp.post("/ia/importar-docentes-texto")
def ia_import_teachers_text():
    payload = request.get_json(silent=True) or {}
    text = payload.get("texto", "")
    dry_run = bool(payload.get("dry_run", True))

    data = IAService.import_teachers_from_text(text=text, dry_run=dry_run)
    message = "Analisis generado (dry run)" if dry_run else "Importacion de docentes completada"
    return success_response(message, data)
