import json
from pathlib import Path

from flask import current_app

from app.utils.exceptions import NotFoundApiError, ValidationApiError


ALLOWED_DAYS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado"}
ALLOWED_SCOPES = {"ambos", "presencial", "virtual"}

DEFAULT_LOCKS = [
    {
        "id": 1,
        "etiqueta": "Hora universitaria",
        "dia": "jueves",
        "hora_inicio": 10,
        "hora_fin": 11,
        "alcance": "presencial",
    },
    {
        "id": 2,
        "etiqueta": "Hora universitaria",
        "dia": "jueves",
        "hora_inicio": 17,
        "hora_fin": 18,
        "alcance": "presencial",
    },
]


class CandadoService:
    @staticmethod
    def list_locks() -> list[dict]:
        data = CandadoService._read_data()
        if not data:
            return []
        return sorted(data, key=lambda item: (item["dia"], item["hora_inicio"], item["hora_fin"], item["id"]))

    @staticmethod
    def create_lock(payload: dict) -> dict:
        validated = CandadoService._validate_payload(payload)
        data = CandadoService._read_data()
        next_id = max((item["id"] for item in data), default=0) + 1
        new_lock = {"id": next_id, **validated}
        data.append(new_lock)
        CandadoService._write_data(data)
        return new_lock

    @staticmethod
    def update_lock(lock_id: int, payload: dict) -> dict:
        data = CandadoService._read_data()
        target = next((item for item in data if item["id"] == lock_id), None)
        if target is None:
            raise NotFoundApiError("Candado no encontrado", [f"No existe un candado con id {lock_id}"])

        validated = CandadoService._validate_payload(payload)
        target.update(validated)
        CandadoService._write_data(data)
        return target

    @staticmethod
    def delete_lock(lock_id: int) -> None:
        data = CandadoService._read_data()
        next_data = [item for item in data if item["id"] != lock_id]
        if len(next_data) == len(data):
            raise NotFoundApiError("Candado no encontrado", [f"No existe un candado con id {lock_id}"])
        CandadoService._write_data(next_data)

    @staticmethod
    def find_conflicting_lock(dia: str, hora_inicio: int, hora_fin: int, modalidad: str):
        for lock in CandadoService.list_locks():
            if lock["dia"] != dia:
                continue
            if lock["alcance"] != "ambos" and lock["alcance"] != modalidad:
                continue
            overlaps = hora_inicio < lock["hora_fin"] and hora_fin > lock["hora_inicio"]
            if overlaps:
                return lock
        return None

    @staticmethod
    def _validate_payload(payload: dict) -> dict:
        errors = []

        etiqueta = str(payload.get("etiqueta", "")).strip()
        if len(etiqueta) > 80:
            errors.append("La etiqueta no puede exceder 80 caracteres")

        dia = str(payload.get("dia", "")).strip().lower()
        if dia not in ALLOWED_DAYS:
            errors.append("El dia debe ser lunes, martes, miercoles, jueves, viernes o sabado")

        alcance = str(payload.get("alcance", "")).strip().lower()
        if alcance not in ALLOWED_SCOPES:
            errors.append("El alcance debe ser ambos, presencial o virtual")

        hora_inicio = payload.get("hora_inicio")
        hora_fin = payload.get("hora_fin")

        try:
            hora_inicio = int(hora_inicio)
        except (TypeError, ValueError):
            errors.append("La hora_inicio debe ser numerica")

        try:
            hora_fin = int(hora_fin)
        except (TypeError, ValueError):
            errors.append("La hora_fin debe ser numerica")

        if isinstance(hora_inicio, int) and (hora_inicio < 7 or hora_inicio > 23):
            errors.append("La hora_inicio debe estar entre 7 y 23")

        if isinstance(hora_fin, int) and (hora_fin < 8 or hora_fin > 24):
            errors.append("La hora_fin debe estar entre 8 y 24")

        if isinstance(hora_inicio, int) and isinstance(hora_fin, int) and hora_inicio >= hora_fin:
            errors.append("La hora_inicio debe ser menor que la hora_fin")

        if errors:
            raise ValidationApiError("Error de validacion al procesar candado", errors)

        return {
            "etiqueta": etiqueta,
            "dia": dia,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin,
            "alcance": alcance,
        }

    @staticmethod
    def _get_file_path() -> Path:
        instance_path = Path(current_app.config.get("INSTANCE_PATH", "."))
        instance_path.mkdir(parents=True, exist_ok=True)
        return instance_path / "candados.json"

    @staticmethod
    def _read_data() -> list[dict]:
        file_path = CandadoService._get_file_path()
        if not file_path.exists():
            CandadoService._write_data(DEFAULT_LOCKS)
            return [dict(item) for item in DEFAULT_LOCKS]

        try:
            content = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValidationApiError("Archivo de candados invalido", [str(error)])

        if not isinstance(content, list):
            raise ValidationApiError("Archivo de candados invalido", ["El archivo debe contener una lista"])

        normalized = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if not {"id", "dia", "hora_inicio", "hora_fin", "alcance"}.issubset(item.keys()):
                continue
            normalized.append(
                {
                    "id": int(item["id"]),
                    "etiqueta": str(item.get("etiqueta", "")).strip(),
                    "dia": str(item["dia"]).strip().lower(),
                    "hora_inicio": int(item["hora_inicio"]),
                    "hora_fin": int(item["hora_fin"]),
                    "alcance": str(item["alcance"]).strip().lower(),
                }
            )
        return normalized

    @staticmethod
    def _write_data(data: list[dict]) -> None:
        file_path = CandadoService._get_file_path()
        file_path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
