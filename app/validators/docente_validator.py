from app.utils.exceptions import ValidationApiError
from app.utils.parsing import coerce_bool


def validate_teacher_payload(payload: dict, partial: bool = False) -> dict:
    errors = []
    cleaned = {}

    for field_name, message in [
        ("clave_docente", "La clave_docente es obligatoria"),
        ("nombre", "El nombre es obligatorio"),
    ]:
        if not partial or field_name in payload:
            value = payload.get(field_name)
            if value in (None, ""):
                errors.append(message)
            else:
                cleaned[field_name] = str(value).strip()

    if "activo" in payload:
        try:
            cleaned["activo"] = coerce_bool(payload["activo"])
        except ValueError:
            errors.append("El campo activo debe ser booleano")
    elif not partial:
        cleaned["activo"] = True

    if "foraneo" in payload:
        try:
            cleaned["foraneo"] = coerce_bool(payload["foraneo"])
        except ValueError:
            errors.append("El campo foraneo debe ser booleano")
    elif not partial:
        cleaned["foraneo"] = False

    if "es_juez" in payload:
        try:
            cleaned["es_juez"] = coerce_bool(payload["es_juez"])
        except ValueError:
            errors.append("El campo es_juez debe ser booleano")
    elif not partial:
        cleaned["es_juez"] = False

    if errors:
        raise ValidationApiError("Error de validacion al procesar el docente", errors)

    return cleaned