import json
import os
import threading
import time
from datetime import datetime
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from app.services.backup_service import BackupService

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")


@backup_bp.post("/shutdown")
def shutdown():
    """Cierra el servidor guardando correctamente la base de datos."""
    def _stop():
        time.sleep(0.6)
        try:
            from app.extensions import db
            db.session.remove()  # cierra sesiones abiertas
            with db.engine.connect() as conn:
                conn.execute(db.text("PRAGMA wal_checkpoint(FULL)"))  # vuelca WAL al archivo principal
            db.engine.dispose()  # cierra pool de conexiones
        except Exception:
            pass
        os._exit(0)
    threading.Thread(target=_stop, daemon=True).start()
    return jsonify({"ok": True, "message": "Guardando y cerrando sistema..."}), 200


@backup_bp.get("/export")
def export_backup():
    """Descarga un JSON con toda la base de datos."""
    data = BackupService.export_data()
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    buf = BytesIO(json_bytes)
    filename = f"horarios_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=filename,
    )


@backup_bp.post("/import")
def import_backup():
    """Recibe un JSON de backup y reemplaza toda la base de datos."""
    if "file" not in request.files:
        return jsonify({"error": "No se proporcionó ningún archivo."}), 400

    f = request.files["file"]
    if not f.filename or not f.filename.lower().endswith(".json"):
        return jsonify({"error": "El archivo debe ser un .json generado por este sistema."}), 400

    raw = f.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return jsonify({"error": f"El archivo no es un JSON válido: {exc}"}), 400

    try:
        summary = BackupService.import_data(payload)
        return jsonify({"ok": True, "summary": summary}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Error al importar los datos: {exc}"}), 500
