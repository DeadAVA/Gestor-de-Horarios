"""
Fixtures globales para la suite de pruebas del Sistema de Horarios UABC.

Utiliza SQLite en memoria (TestingConfig con StaticPool) para que todas
las sesiones compartan la misma conexión física.
"""
import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Docente, Grupo, Materia, PlanEstudio


# ---------------------------------------------------------------------------
# Fixtures de infraestructura
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """
    Crea la app Flask una sola vez por sesión. Usa 'testing' que configura
    SQLite en memoria + StaticPool antes de que cualquier engine se inicialice.
    """
    return create_app("testing")


@pytest.fixture()
def db(app):
    """
    Crea todas las tablas antes de cada prueba y las elimina al terminar.
    Activa un app context durante toda la prueba.
    """
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app, db):
    """Test client de Flask con tablas frescas."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Fixture de datos semilla
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed(db):
    """
    Inserta datos mínimos para pruebas de conflictos de horario:
      - Dos planes de estudio (2025-1 y 2015-2)
      - Dos grupos (501 y 502, ambos semestre 1)
      - Dos materias (semestre 1, plan 2025-1)
      - Dos docentes activos

    Devuelve un dict con los IDs para usar en los tests.
    """
    plan1 = PlanEstudio(clave="2025-1", nombre="Plan 2025-1 Test")
    plan2 = PlanEstudio(clave="2015-2", nombre="Plan 2015-2 Test")
    db.session.add_all([plan1, plan2])
    db.session.flush()

    grupo1 = Grupo(
        numero_grupo=501,
        semestre=1,
        plan_estudio_id=plan1.id,
        capacidad_alumnos=30,
        tipo_grupo="normal",
    )
    grupo2 = Grupo(
        numero_grupo=502,
        semestre=1,
        plan_estudio_id=plan1.id,
        capacidad_alumnos=30,
        tipo_grupo="normal",
    )
    materia1 = Materia(
        clave="T1001",
        nombre="Materia Test 1",
        semestre=1,
        plan_estudio_id=plan1.id,
        tipo_materia="normal",
        modalidad="presencial",
    )
    materia2 = Materia(
        clave="T1002",
        nombre="Materia Test 2",
        semestre=1,
        plan_estudio_id=plan1.id,
        tipo_materia="normal",
        modalidad="presencial",
    )
    docente1 = Docente(clave_docente="FDOC01", nombre="Docente Test Uno", activo=True)
    docente2 = Docente(clave_docente="FDOC02", nombre="Docente Test Dos", activo=True)

    db.session.add_all([grupo1, grupo2, materia1, materia2, docente1, docente2])
    db.session.commit()

    return {
        "plan1_id": plan1.id,
        "plan2_id": plan2.id,
        "grupo1_id": grupo1.id,
        "grupo2_id": grupo2.id,
        "materia1_id": materia1.id,
        "materia2_id": materia2.id,
        "docente1_id": docente1.id,
        "docente2_id": docente2.id,
    }
