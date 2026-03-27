"""
Pruebas unitarias para las reglas de cálculo de semestre y plan de estudios.
No se requiere base de datos, son funciones puras.
"""
import pytest

from app.services.group_rules import calculate_plan_key, calculate_semester, validate_group_number_for_type


# ---------------------------------------------------------------------------
# calculate_semester
# ---------------------------------------------------------------------------

def test_semestre_rango_500s_escolarizado():
    """Primer semestre escolarizado: 501 a 504."""
    for n in [501, 502, 503, 504]:
        assert calculate_semester(n) == 1, f"Fallo para numero_grupo={n}"


def test_semestre_rango_520s():
    """Segundo semestre escolarizado: 521 a 524."""
    for n in [521, 522, 523, 524]:
        assert calculate_semester(n) == 2


def test_semestre_rango_530s():
    for n in [531, 532, 533, 534]:
        assert calculate_semester(n) == 3


def test_semestre_rango_540s():
    for n in [541, 542, 543, 544]:
        assert calculate_semester(n) == 4


def test_semestre_rango_550s():
    for n in [551, 552, 553, 554]:
        assert calculate_semester(n) == 5


def test_semestre_rango_560s():
    for n in [561, 562, 563, 564]:
        assert calculate_semester(n) == 6


def test_semestre_rango_570s():
    for n in [571, 572, 573, 574]:
        assert calculate_semester(n) == 7


def test_semestre_rango_580s():
    for n in [581, 582, 583, 584]:
        assert calculate_semester(n) == 8


def test_semestre_especiales():
    """Grupos especiales 741–748 tienen sus semestres definidos explícitamente."""
    mapping = {741: 1, 742: 2, 743: 3, 744: 4, 745: 5, 746: 6, 747: 7, 748: 8}
    for numero, semestre_esperado in mapping.items():
        assert calculate_semester(numero) == semestre_esperado


def test_semestre_numero_invalido_alto():
    with pytest.raises(ValueError):
        calculate_semester(999)


def test_semestre_numero_invalido_bajo():
    with pytest.raises(ValueError):
        calculate_semester(100)


def test_semestre_numero_sin_decena_valida():
    with pytest.raises(ValueError):
        calculate_semester(600)


def test_semestre_escolarizado_sufijo_valido_completo():
    """Escolarizados permiten sufijos del 1 al 9 (grupos hasta 9 por semestre)."""
    # 525 = prefijo 52 (semestre 2), sufijo 5 → válido
    assert calculate_semester(525) == 2
    assert calculate_semester(529) == 2


def test_validacion_tipo_normal_valida():
    assert validate_group_number_for_type(503, "normal") == 1


def test_validacion_tipo_normal_rechaza_numero_semi():
    with pytest.raises(ValueError):
        validate_group_number_for_type(741, "normal")


def test_validacion_tipo_semi_valida():
    assert validate_group_number_for_type(748, "semi") == 8


def test_validacion_tipo_semi_rechaza_numero_escolarizado():
    with pytest.raises(ValueError):
        validate_group_number_for_type(501, "semi")


# ---------------------------------------------------------------------------
# calculate_plan_key
# ---------------------------------------------------------------------------

def test_plan_semestres_1_a_4():
    """Semestres 1–4 pertenecen al plan 2025-1."""
    for semestre in range(1, 5):
        assert calculate_plan_key(semestre) == "2025-1"


def test_plan_semestres_5_a_8():
    """Semestres 5–8 pertenecen al plan 2015-2 (plan histórico de la institución)."""
    for semestre in range(5, 9):
        assert calculate_plan_key(semestre) == "2015-2"


def test_plan_semestre_cero_invalido():
    with pytest.raises(ValueError):
        calculate_plan_key(0)


def test_plan_semestre_nueve_invalido():
    with pytest.raises(ValueError):
        calculate_plan_key(9)


def test_plan_semestre_negativo():
    with pytest.raises(ValueError):
        calculate_plan_key(-1)
