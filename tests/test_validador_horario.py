"""
Pruebas unitarias para validate_schedule_block_payload.
No requieren base de datos.
"""
import pytest

from app.utils.exceptions import ValidationApiError
from app.validators.horario_validator import validate_schedule_block_payload


PAYLOAD_VALIDO = {
    "group_id": 1,
    "materia_id": 1,
    "docente_id": 1,
    "dia": "lunes",
    "hora_inicio": "07:00",
    "hora_fin": "08:00",
    "modalidad": "presencial",
}


# ---------------------------------------------------------------------------
# Casos válidos
# ---------------------------------------------------------------------------

def test_payload_completo_valido():
    result = validate_schedule_block_payload(PAYLOAD_VALIDO)
    assert result["group_id"] == 1
    assert result["materia_id"] == 1
    assert result["docente_id"] == 1
    assert result["dia"] == "lunes"
    assert result["modalidad"] == "presencial"


def test_dia_normalizado_a_minusculas():
    """El validador debe aceptar el día en mayúsculas y normalizarlo."""
    result = validate_schedule_block_payload({**PAYLOAD_VALIDO, "dia": "MARTES"})
    assert result["dia"] == "martes"


def test_modalidad_virtual():
    result = validate_schedule_block_payload({**PAYLOAD_VALIDO, "modalidad": "virtual"})
    assert result["modalidad"] == "virtual"


def test_hora_regresada_como_datetime_time():
    from datetime import time
    result = validate_schedule_block_payload(PAYLOAD_VALIDO)
    assert isinstance(result["hora_inicio"], time)
    assert isinstance(result["hora_fin"], time)


# ---------------------------------------------------------------------------
# Errores de campo dia
# ---------------------------------------------------------------------------

def test_dia_invalido_domingo():
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload({**PAYLOAD_VALIDO, "dia": "domingo"})
    assert any("dia" in e.lower() for e in exc_info.value.errors)


def test_dia_invalido_texto_libre():
    with pytest.raises(ValidationApiError):
        validate_schedule_block_payload({**PAYLOAD_VALIDO, "dia": "hoy"})


def test_dia_faltante():
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "dia"}
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(payload)
    assert any("dia" in e.lower() for e in exc_info.value.errors)


# ---------------------------------------------------------------------------
# Errores de campo modalidad
# ---------------------------------------------------------------------------

def test_modalidad_invalida_hibrida():
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload({**PAYLOAD_VALIDO, "modalidad": "hibrida"})
    assert any("modalidad" in e.lower() for e in exc_info.value.errors)


def test_modalidad_faltante():
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "modalidad"}
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(payload)
    assert any("modalidad" in e.lower() for e in exc_info.value.errors)


# ---------------------------------------------------------------------------
# Errores de hora
# ---------------------------------------------------------------------------

def test_hora_formato_invalido():
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload({**PAYLOAD_VALIDO, "hora_inicio": "7am"})
    assert any("hora_inicio" in e.lower() for e in exc_info.value.errors)


def test_hora_inicio_mayor_que_fin():
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(
            {**PAYLOAD_VALIDO, "hora_inicio": "10:00", "hora_fin": "08:00"}
        )
    assert any("hora_inicio" in e.lower() for e in exc_info.value.errors)


def test_hora_inicio_igual_a_fin():
    with pytest.raises(ValidationApiError):
        validate_schedule_block_payload(
            {**PAYLOAD_VALIDO, "hora_inicio": "08:00", "hora_fin": "08:00"}
        )


def test_hora_fin_faltante():
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "hora_fin"}
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(payload)
    assert any("hora_fin" in e.lower() for e in exc_info.value.errors)


# ---------------------------------------------------------------------------
# Errores de IDs
# ---------------------------------------------------------------------------

def test_group_id_faltante():
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "group_id"}
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(payload)
    assert any("group_id" in e.lower() for e in exc_info.value.errors)


def test_materia_id_faltante():
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k != "materia_id"}
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(payload)
    assert any("materia_id" in e.lower() for e in exc_info.value.errors)


def test_multiples_errores_coleccionados():
    """El validador debe reportar todos los errores, no solo el primero."""
    payload = {"group_id": "abc", "dia": "domingo", "hora_inicio": "not-a-time"}
    with pytest.raises(ValidationApiError) as exc_info:
        validate_schedule_block_payload(payload)
    assert len(exc_info.value.errors) >= 2
