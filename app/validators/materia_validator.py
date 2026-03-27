from app.utils.exceptions import ValidationApiError
from app.utils.parsing import coerce_bool


ALLOWED_SUBJECT_TYPES = {"normal", "optativa"}
ALLOWED_MODALITIES = {"presencial", "virtual"}


def validate_subject_payload(payload: dict, partial: bool = False) -> dict:
    errors = []
    cleaned = {}

    string_fields = [
        ("clave", "La clave es obligatoria"),
        ("nombre", "El nombre es obligatorio"),
        ("tipo_materia", "El tipo_materia es obligatorio"),
        ("modalidad", "La modalidad es obligatoria"),
    ]

    for field_name, required_message in string_fields:
        if not partial or field_name in payload:
            value = payload.get(field_name)
            if value in (None, ""):
                errors.append(required_message)
            else:
                cleaned[field_name] = str(value).strip()

    if not partial or "semestre" in payload:
        semestre = payload.get("semestre")
        if semestre in (None, ""):
            errors.append("El semestre es obligatorio")
        else:
            try:
                cleaned["semestre"] = int(semestre)
                if not 1 <= cleaned["semestre"] <= 8:
                    errors.append("El semestre debe estar entre 1 y 8")
            except (TypeError, ValueError):
                errors.append("El semestre debe ser numerico")

    if not partial or "plan_estudio_id" in payload:
        plan_estudio_id = payload.get("plan_estudio_id")
        if plan_estudio_id in (None, ""):
            errors.append("El plan_estudio_id es obligatorio")
        else:
            try:
                cleaned["plan_estudio_id"] = int(plan_estudio_id)
            except (TypeError, ValueError):
                errors.append("El plan_estudio_id debe ser numerico")

    if "tipo_materia" in cleaned and cleaned["tipo_materia"] not in ALLOWED_SUBJECT_TYPES:
        errors.append("El tipo_materia debe ser normal u optativa")

    if "modalidad" in cleaned and cleaned["modalidad"] not in ALLOWED_MODALITIES:
        errors.append("La modalidad debe ser presencial o virtual")

    if "etapa" in payload:
        cleaned["etapa"] = str(payload["etapa"]).strip() or None
    elif not partial:
        cleaned["etapa"] = None

    if "activa" in payload:
        try:
            cleaned["activa"] = coerce_bool(payload["activa"])
        except ValueError:
            errors.append("El campo activa debe ser booleano")
    elif not partial:
        cleaned["activa"] = True

    numeric_load_fields = ["hc", "ht", "hl", "hpc", "hcl", "he", "cr"]
    for field_name in numeric_load_fields:
        if field_name in payload:
            value = payload.get(field_name)
            if value in (None, ""):
                cleaned[field_name] = 0
                continue
            try:
                cleaned[field_name] = int(value)
                if cleaned[field_name] < 0:
                    errors.append(f"El campo {field_name} debe ser mayor o igual a cero")
            except (TypeError, ValueError):
                errors.append(f"El campo {field_name} debe ser numerico")
        elif not partial:
            cleaned[field_name] = 0

    if errors:
        raise ValidationApiError("Error de validacion al procesar la materia", errors)

    return cleaned