from pathlib import Path

from app.config import BASE_DIR


INSTITUTIONAL_GREEN = "006B3F"
INSTITUTIONAL_GREEN_LIGHT = "D9EEE3"
INSTITUTIONAL_GRAY = "666666"
TABLE_GRID = "B7B7B7"
WHITE = "FFFFFF"
BLACK = "000000"

UNIT_CODE = "414"
UNIT_NAME = "FACULTAD DE DERECHO"
CAREER_CODE = "8"
CAREER_NAME = "LICENCIADO EN DERECHO"
COORDINATION_NAME = "COORDINACIÓN GENERAL DE RECURSOS HUMANOS"
INSTITUTION_NAME = "UNIVERSIDAD AUTÓNOMA DE BAJA CALIFORNIA"
REPORT_TITLE = "CUADRÍCULA DE HORARIOS"
DEFAULT_PERIOD = "2025-2"
REPORT_CODE = "RPLAN005"

TABLE_HEADERS = [
    "CVE. ASIGNAT.\nNO. CONTROL",
    "DESCRIPCIÓN\nMAESTRO",
    "EDIFICIO",
    "SALÓN",
    "CAP\nASG",
    "TPO\nSGP",
    "LUNES",
    "MARTES",
    "MIÉRCOLES",
    "JUEVES",
    "VIERNES",
    "SÁBADO",
    "DOMINGO",
    "E/S",
]

DAY_KEYS = [
    ("lunes", "LUNES"),
    ("martes", "MARTES"),
    ("miercoles", "MIÉRCOLES"),
    ("jueves", "JUEVES"),
    ("viernes", "VIERNES"),
    ("sabado", "SÁBADO"),
    ("domingo", "DOMINGO"),
]

EXCEL_COLUMN_WIDTHS = {
    "A": 14,
    "B": 30,
    "C": 8,
    "D": 8,
    "E": 6,
    "F": 7,
    "G": 10,
    "H": 10,
    "I": 11,
    "J": 10,
    "K": 10,
    "L": 10,
    "M": 10,
    "N": 6,
}

LOGO_CANDIDATES = [
    BASE_DIR / "app" / "assets" / "institution_logo.png",
    BASE_DIR / "app" / "assets" / "institution_logo.jpg",
    BASE_DIR / "app" / "assets" / "institution_logo.jpeg",
]


def get_logo_path() -> Path | None:
    for candidate in LOGO_CANDIDATES:
        if candidate.exists():
            return candidate
    return None
