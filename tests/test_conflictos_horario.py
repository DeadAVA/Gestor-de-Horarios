"""
Pruebas de integración para las cinco reglas de conflicto del HorarioService.

Usa la BD en memoria configurada en conftest.py.
Las llamadas van directamente al servicio (sin HTTP) para mayor simplicidad.
"""
import pytest

from app.models import Docente, Materia
from app.services.candado_service import CandadoService
from app.services.horario_service import HorarioService
from app.services.summary_service import SummaryService
from app.utils.exceptions import ConflictApiError, ValidationApiError
from app.utils.time_utils import calculate_hours_from_blocks


# Bloque base reutilizable (lunes 07:00-08:00)
BASE = {
    "dia": "lunes",
    "hora_inicio": "07:00",
    "hora_fin": "08:00",
    "modalidad": "presencial",
}


def bloque(seed, grupo="grupo1", materia="materia1", docente="docente1", **kwargs):
    """Helper para construir un payload de bloque."""
    return {
        "group_id": seed[f"{grupo}_id"],
        "materia_id": seed[f"{materia}_id"],
        "docente_id": seed[f"{docente}_id"],
        **BASE,
        **kwargs,
    }


@pytest.fixture(autouse=True)
def candados_en_instancia_temporal(app, tmp_path):
    """Aísla el archivo de candados para evitar contaminación entre pruebas."""
    with app.app_context():
        app.config["INSTANCE_PATH"] = str(tmp_path)
        yield


# ---------------------------------------------------------------------------
# Creación exitosa
# ---------------------------------------------------------------------------

def test_bloque_valido_se_persiste(seed):
    result = HorarioService.create_block(bloque(seed))
    assert result["id"] is not None
    assert result["dia"] == "lunes"
    assert result["materia"]["clave"] == "T1001"


def test_eliminar_bloque(seed):
    created = HorarioService.create_block(bloque(seed))
    deleted = HorarioService.delete_block(created["id"])
    assert deleted["id"] == created["id"]


# ---------------------------------------------------------------------------
# Regla 1: solapamiento dentro del mismo grupo
# ---------------------------------------------------------------------------

def test_solapamiento_mismo_grupo(seed):
    """Dos bloques con horario traslapado en el mismo grupo deben producir conflicto."""
    HorarioService.create_block(bloque(seed))

    # Mismo grupo, diferente materia+docente, horario traslapado (07:30-08:30)
    with pytest.raises(ConflictApiError):
        HorarioService.create_block(
            bloque(seed, materia="materia2", docente="docente2",
                   hora_inicio="07:30", hora_fin="08:30")
        )


def test_no_solapamiento_mismo_grupo_dias_distintos(seed):
    """Mismo horario en días diferentes no debe generar conflicto."""
    HorarioService.create_block(bloque(seed, dia="lunes"))
    HorarioService.create_block(
        bloque(seed, materia="materia2", docente="docente2", dia="martes")
    )


def test_no_solapamiento_mismo_grupo_horas_adyacentes(seed):
    """Bloques contiguos (08:00-09:00 y 09:00-10:00) no se solapan."""
    HorarioService.create_block(bloque(seed, hora_inicio="08:00", hora_fin="09:00"))
    HorarioService.create_block(
        bloque(seed, materia="materia2", docente="docente2",
               hora_inicio="09:00", hora_fin="10:00")
    )


def test_bloque_vacante_se_permite(seed):
    result = HorarioService.create_block({
        **bloque(seed),
        "docente_id": 0,
    })

    assert result["id"] is not None
    assert result["docente"]["clave_docente"] == "VACANTE-SISTEMA"


def test_bloque_vacante_no_cuenta_como_materia_con_docente(seed):
    HorarioService.create_block({
        **bloque(seed),
        "docente_id": 0,
    })

    summary = SummaryService.get_group_summary(seed["grupo1_id"])
    missing_keys = {subject["clave"] for subject in summary["materias_sin_docente"]}

    assert "T1001" in missing_keys


def test_bloques_vacantes_permiten_choque_en_mismo_grupo(seed):
    HorarioService.create_block({
        **bloque(seed),
        "docente_id": 0,
        "hora_inicio": "09:00",
        "hora_fin": "10:00",
    })

    result = HorarioService.create_block({
        **bloque(seed, materia="materia2"),
        "docente_id": 0,
        "hora_inicio": "09:00",
        "hora_fin": "10:00",
    })

    assert result["id"] is not None


def test_reassign_subject_teacher_moves_blocks_and_load(seed, db):
    HorarioService.create_block(
        bloque(seed, docente="docente1", dia="lunes", hora_inicio="07:00", hora_fin="08:00")
    )
    HorarioService.create_block(
        bloque(seed, docente="docente1", dia="martes", hora_inicio="07:00", hora_fin="08:00")
    )

    result = HorarioService.reassign_subject_teacher(
        seed["grupo1_id"],
        seed["materia1_id"],
        seed["docente2_id"],
    )

    assert result["updated_blocks"] == 2
    assert all(block["docente"]["id"] == seed["docente2_id"] for block in result["bloques"])

    teacher1 = db.session.get(Docente, seed["docente1_id"])
    teacher2 = db.session.get(Docente, seed["docente2_id"])
    assert calculate_hours_from_blocks(teacher1.bloques_horario) == 0
    assert calculate_hours_from_blocks(teacher2.bloques_horario) == 2


def test_reassign_subject_teacher_to_vacante_clears_teacher_load(seed, db):
    HorarioService.create_block(
        bloque(seed, docente="docente1", dia="lunes", hora_inicio="07:00", hora_fin="08:00")
    )

    result = HorarioService.reassign_subject_teacher(
        seed["grupo1_id"],
        seed["materia1_id"],
        0,
    )

    assert result["updated_blocks"] == 1
    assert result["bloques"][0]["docente"]["clave_docente"] == "VACANTE-SISTEMA"

    teacher1 = db.session.get(Docente, seed["docente1_id"])
    assert calculate_hours_from_blocks(teacher1.bloques_horario) == 0


# ---------------------------------------------------------------------------
# Regla 2: solapamiento del docente en otro grupo
# ---------------------------------------------------------------------------

def test_solapamiento_docente_diferente_grupo(seed):
    """Un docente no puede estar en dos grupos al mismo tiempo."""
    HorarioService.create_block(bloque(seed, grupo="grupo1"))

    # Mismo docente, otro grupo, mismo día y hora
    with pytest.raises(ConflictApiError):
        HorarioService.create_block(bloque(seed, grupo="grupo2"))


def test_docente_puede_dar_clase_en_otro_grupo_diferente_hora(seed):
    """El mismo docente puede estar en otro grupo en horario distinto."""
    HorarioService.create_block(bloque(seed, grupo="grupo1", hora_inicio="07:00", hora_fin="08:00"))
    HorarioService.create_block(
        bloque(seed, grupo="grupo2", hora_inicio="09:00", hora_fin="10:00")
    )


# ---------------------------------------------------------------------------
# Regla 3: un solo docente por materia por grupo
# ---------------------------------------------------------------------------

def test_un_docente_por_materia_por_grupo(seed):
    """Una materia en un grupo solo puede tener un docente asignado."""
    # docente1 asignado a materia1 en grupo1 el lunes
    HorarioService.create_block(bloque(seed))

    # Intentar asignar docente2 a la misma materia en el mismo grupo (martes)
    with pytest.raises(ConflictApiError):
        HorarioService.create_block(
            bloque(seed, docente="docente2", dia="martes")
        )


def test_mismo_docente_misma_materia_otro_dia(seed):
    """El mismo docente puede tener varios bloques de la misma materia en días distintos."""
    HorarioService.create_block(bloque(seed, dia="lunes"))
    HorarioService.create_block(bloque(seed, dia="miercoles"))


# ---------------------------------------------------------------------------
# Regla 4: docente inactivo
# ---------------------------------------------------------------------------

def test_docente_inactivo_rechazado(seed, db):
    """Un docente marcado como inactivo no puede recibir nuevos bloques."""
    teacher = db.session.get(Docente, seed["docente1_id"])
    teacher.activo = False
    db.session.commit()

    with pytest.raises(ValidationApiError, match="activo"):
        HorarioService.create_block(bloque(seed))


# ---------------------------------------------------------------------------
# Regla 5: materia de otro semestre / plan
# ---------------------------------------------------------------------------

def test_materia_de_otro_semestre_rechazada(seed, db):
    """Una materia de semestre distinto al del grupo debe ser rechazada."""
    materia_sem2 = Materia(
        clave="TOTHER",
        nombre="Materia Semestre 2",
        semestre=2,  # grupo1 es semestre 1
        plan_estudio_id=seed["plan1_id"],
        tipo_materia="normal",
        modalidad="presencial",
    )
    db.session.add(materia_sem2)
    db.session.commit()

    with pytest.raises(ValidationApiError, match="no es valida"):
        HorarioService.create_block({
            **BASE,
            "group_id": seed["grupo1_id"],
            "materia_id": materia_sem2.id,
            "docente_id": seed["docente1_id"],
        })


# ---------------------------------------------------------------------------
# Regla 6: límite de 25 horas del docente
# ---------------------------------------------------------------------------

def test_excede_limite_25_horas(seed):
    """Un bloque que llevaría al docente sobre 25 h acumuladas debe ser rechazado."""
    # 4 bloques de 6 h cada uno = 24 h en días distintos
    for dia in ["lunes", "martes", "miercoles", "viernes"]:
        HorarioService.create_block(
            bloque(seed, dia=dia, hora_inicio="07:00", hora_fin="13:00")
        )
    # Intentar agregar 2 h más (24 + 2 = 26 > 25)
    with pytest.raises(ConflictApiError, match="excede el máximo"):
        HorarioService.create_block(
            bloque(seed, dia="sabado", hora_inicio="07:00", hora_fin="09:00")
        )


def test_ya_en_25_horas_rechaza_cualquier_bloque(seed):
    """Cuando el docente acumula exactamente 25 h, cualquier bloque adicional se rechaza."""
    # 4 x 6 h = 24 h
    for dia in ["lunes", "martes", "miercoles", "viernes"]:
        HorarioService.create_block(
            bloque(seed, dia=dia, hora_inicio="07:00", hora_fin="13:00")
        )
    # + 1 h = 25 h exactas (debe aceptarse)
    HorarioService.create_block(
        bloque(seed, dia="sabado", hora_inicio="07:00", hora_fin="08:00")
    )
    # Ya en 25 h: cualquier bloque adicional se rechaza (usar horario diferente al sabado 07-08 ya ocupado)
    with pytest.raises(ConflictApiError, match="ya alcanzó"):
        HorarioService.create_block(
            bloque(seed, dia="sabado", hora_inicio="09:00", hora_fin="10:00")
        )


def test_bloque_exactamente_25_horas_permitido(seed):
    """Un docente en 24 h puede agregar 1 h para llegar exactamente a 25 h."""
    for dia in ["lunes", "martes", "miercoles", "viernes"]:
        HorarioService.create_block(
            bloque(seed, dia=dia, hora_inicio="07:00", hora_fin="13:00")
        )
    # llegar a exactamente 25 h debe ser permitido
    result = HorarioService.create_block(
        bloque(seed, dia="sabado", hora_inicio="07:00", hora_fin="08:00")
    )
    assert result["id"] is not None


# ---------------------------------------------------------------------------
# Regla 7: candados por modalidad
# ---------------------------------------------------------------------------

def test_candado_presencial_bloquea_modalidad_presencial(seed):
    CandadoService.create_lock({
        "dia": "jueves",
        "hora_inicio": 10,
        "hora_fin": 11,
        "alcance": "presencial",
    })

    with pytest.raises(ConflictApiError, match="candado"):
        HorarioService.create_block(
            bloque(seed, dia="jueves", hora_inicio="10:00", hora_fin="11:00", modalidad="presencial")
        )


def test_candado_presencial_no_bloquea_modalidad_virtual(seed):
    CandadoService.create_lock({
        "dia": "jueves",
        "hora_inicio": 10,
        "hora_fin": 11,
        "alcance": "presencial",
    })

    result = HorarioService.create_block(
        bloque(seed, dia="jueves", hora_inicio="10:00", hora_fin="11:00", modalidad="virtual")
    )
    assert result["id"] is not None
    assert result["modalidad"] == "virtual"


def test_candado_no_bloquea_docente_juez(seed, db):
    teacher = db.session.get(Docente, seed["docente1_id"])
    teacher.es_juez = True
    db.session.commit()

    CandadoService.create_lock({
        "dia": "jueves",
        "hora_inicio": 18,
        "hora_fin": 19,
        "alcance": "presencial",
    })

    result = HorarioService.create_block(
        bloque(seed, dia="jueves", hora_inicio="18:00", hora_fin="19:00", modalidad="presencial")
    )

    assert result["id"] is not None
    assert result["docente"]["id"] == seed["docente1_id"]


def test_candado_ambos_bloquea_virtual_y_presencial(seed):
    CandadoService.create_lock({
        "dia": "martes",
        "hora_inicio": 9,
        "hora_fin": 10,
        "alcance": "ambos",
    })

    with pytest.raises(ConflictApiError, match="candado"):
        HorarioService.create_block(
            bloque(seed, dia="martes", hora_inicio="09:00", hora_fin="10:00", modalidad="presencial")
        )

    with pytest.raises(ConflictApiError, match="candado"):
        HorarioService.create_block(
            bloque(seed, dia="martes", hora_inicio="09:00", hora_fin="10:00", modalidad="virtual")
        )
