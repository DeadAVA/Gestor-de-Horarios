from app.utils.exceptions import ValidationApiError
from app.utils.parsing import coerce_int
from app.utils.time_utils import parse_time_value


ALLOWED_DAYS = {"lunes", "martes", "miercoles", "jueves", "viernes", "sabado"}
ALLOWED_MODALITIES = {"presencial", "virtual"}


def validate_schedule_block_payload(payload: dict) -> dict:
    errors = []
    cleaned = {}

    for field_name in ["group_id", "materia_id", "docente_id"]:
        value = payload.get(field_name)
        if value in (None, ""):
            errors.append(f"El campo {field_name} es obligatorio")
            continue
        try:
            cleaned[field_name] = coerce_int(value, field_name)
        except ValueError as error:
            errors.append(str(error))

    dia = payload.get("dia")
    if not dia:
        errors.append("El campo dia es obligatorio")
    else:
        dia = str(dia).strip().lower()
        if dia not in ALLOWED_DAYS:
            errors.append("El dia debe ser uno de lunes, martes, miercoles, jueves, viernes o sabado")
        else:
            cleaned["dia"] = dia

    modalidad = payload.get("modalidad")
    if not modalidad:
        errors.append("El campo modalidad es obligatorio")
    else:
        modalidad = str(modalidad).strip().lower()
        if modalidad not in ALLOWED_MODALITIES:
            errors.append("La modalidad debe ser presencial o virtual")
        else:
            cleaned["modalidad"] = modalidad

    try:
        cleaned["hora_inicio"] = parse_time_value(payload.get("hora_inicio"), "hora_inicio")
    except ValueError as error:
        errors.append(str(error))

    try:
        cleaned["hora_fin"] = parse_time_value(payload.get("hora_fin"), "hora_fin")
    except ValueError as error:
        errors.append(str(error))

    if "hora_inicio" in cleaned and "hora_fin" in cleaned and cleaned["hora_inicio"] >= cleaned["hora_fin"]:
        errors.append("La hora_inicio debe ser menor que la hora_fin")

    if errors:
        raise ValidationApiError("Error de validacion al procesar el bloque de horario", errors)

    return cleaned