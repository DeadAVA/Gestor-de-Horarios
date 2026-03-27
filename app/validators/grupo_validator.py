from app.utils.exceptions import ValidationApiError


ALLOWED_GROUP_TYPES = {"normal", "semi", "intersemestral", "maestria"}
ALLOWED_PLAN_KEYS = {"2025-1", "2015-2", "2025-2", "maestria"}


def validate_group_payload(payload: dict, partial: bool = False) -> dict:
    errors = []
    cleaned = {}

    group_type_for_number_validation = payload.get("tipo_grupo")

    if not partial or "numero_grupo" in payload:
        numero_grupo = payload.get("numero_grupo")
        if group_type_for_number_validation in {"intersemestral", "maestria"} and numero_grupo in (None, ""):
            pass
        elif numero_grupo in (None, ""):
            errors.append("El numero_grupo es obligatorio")
        else:
            try:
                cleaned["numero_grupo"] = int(numero_grupo)
            except (TypeError, ValueError):
                errors.append("El numero_grupo debe ser numerico")

    if not partial or "semestre" in payload:
        semestre = payload.get("semestre")
        if semestre not in (None, ""):
            try:
                cleaned["semestre"] = int(semestre)
                if cleaned["semestre"] < 1 or cleaned["semestre"] > 8:
                    errors.append("El semestre debe estar entre 1 y 8")
            except (TypeError, ValueError):
                errors.append("El semestre debe ser numerico")

    if not partial or "capacidad_alumnos" in payload:
        capacidad = payload.get("capacidad_alumnos")
        if capacidad in (None, ""):
            errors.append("La capacidad_alumnos es obligatoria")
        else:
            try:
                cleaned["capacidad_alumnos"] = int(capacidad)
                if cleaned["capacidad_alumnos"] <= 0:
                    errors.append("La capacidad_alumnos debe ser mayor a cero")
            except (TypeError, ValueError):
                errors.append("La capacidad_alumnos debe ser numerica")

    if not partial or "tipo_grupo" in payload:
        tipo_grupo = payload.get("tipo_grupo")
        if not tipo_grupo:
            errors.append("El tipo_grupo es obligatorio")
        elif tipo_grupo not in ALLOWED_GROUP_TYPES:
            errors.append("El tipo_grupo debe ser normal, semi, intersemestral o maestria")
        else:
            cleaned["tipo_grupo"] = tipo_grupo

    selected_group_type = cleaned.get("tipo_grupo") or group_type_for_number_validation
    if selected_group_type == "intersemestral" and "semestre" not in cleaned:
        errors.append("El semestre es obligatorio para grupos intersemestrales")

    if not partial or "plan_estudio_clave" in payload:
        plan_estudio_clave = payload.get("plan_estudio_clave")
        if selected_group_type == "maestria" and not plan_estudio_clave:
            pass
        elif not plan_estudio_clave:
            errors.append("El plan_estudio_clave es obligatorio")
        else:
            plan_estudio_clave = str(plan_estudio_clave).strip()
            if plan_estudio_clave not in ALLOWED_PLAN_KEYS:
                errors.append("El plan_estudio_clave debe ser 2025-1, 2015-2 o maestria")
            else:
                cleaned["plan_estudio_clave"] = plan_estudio_clave

    if errors:
        raise ValidationApiError("Error de validacion al procesar el grupo", errors)

    return cleaned