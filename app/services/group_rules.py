SPECIAL_GROUP_MAPPING = {
    741: 1,
    742: 2,
    743: 3,
    744: 4,
    745: 5,
    746: 6,
    747: 7,
    748: 8,
}

INTERSEMESTRAL_GROUP_START = 910000
MAESTRIA_GROUP_START = 920000

ESCOLARIZED_PREFIX_TO_SEMESTER = {
    50: 1,
    52: 2,
    53: 3,
    54: 4,
    55: 5,
    56: 6,
    57: 7,
    58: 8,
}


def _calculate_escolarized_semester(numero_grupo: int) -> int:
    prefix = numero_grupo // 10
    suffix = numero_grupo % 10

    semester = ESCOLARIZED_PREFIX_TO_SEMESTER.get(prefix)
    if semester is None:
        raise ValueError("El numero de grupo no corresponde a una regla de semestre valida")

    if suffix not in {1, 2, 3, 4, 5, 6, 7, 8, 9}:
        raise ValueError("Los grupos escolarizados deben terminar en un digito del 1 al 9")

    return semester


def calculate_semester(numero_grupo: int) -> int:
    if numero_grupo in SPECIAL_GROUP_MAPPING:
        return SPECIAL_GROUP_MAPPING[numero_grupo]

    return _calculate_escolarized_semester(numero_grupo)


def validate_group_number_for_type(numero_grupo: int, tipo_grupo: str) -> int:
    if tipo_grupo == "semi":
        semester = SPECIAL_GROUP_MAPPING.get(numero_grupo)
        if semester is None:
            raise ValueError("Los grupos semi deben estar en el rango 741 a 748")
        return semester

    if tipo_grupo == "normal":
        return _calculate_escolarized_semester(numero_grupo)

    raise ValueError("El tipo_grupo debe ser normal o semi")


def calculate_plan_key(semestre: int) -> str:
    if 1 <= semestre <= 4:
        return "2025-1"
    if 5 <= semestre <= 8:
        return "2015-2"
    raise ValueError("El semestre debe estar entre 1 y 8")


def resolve_group_modality(numero_grupo: int, tipo_grupo: str) -> str:
    if numero_grupo >= MAESTRIA_GROUP_START:
        return "maestria"
    if numero_grupo >= INTERSEMESTRAL_GROUP_START:
        return "intersemestral"
    if tipo_grupo == "semi":
        return "semi"
    return "normal"


def is_manual_selection_group(numero_grupo: int, tipo_grupo: str) -> bool:
    if resolve_group_modality(numero_grupo, tipo_grupo) != "normal":
        return False

    try:
        _calculate_escolarized_semester(numero_grupo)
    except ValueError:
        return False

    return numero_grupo % 10 in {5, 6, 7, 8, 9}


def get_virtual_group_index(numero_grupo: int, modalidad_grupo: str) -> int | None:
    if modalidad_grupo == "intersemestral" and numero_grupo >= INTERSEMESTRAL_GROUP_START:
        return numero_grupo - INTERSEMESTRAL_GROUP_START + 1
    if modalidad_grupo == "maestria" and numero_grupo >= MAESTRIA_GROUP_START:
        return numero_grupo - MAESTRIA_GROUP_START + 1
    return None