def coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "si", "sí", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False

    raise ValueError("Valor booleano invalido")


def coerce_int(value, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"El parametro {field_name} debe ser numerico")