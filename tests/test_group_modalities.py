from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.group_service import GroupService
from app.services.subject_selection import build_valid_subjects_query_for_group


def test_create_intersemestral_group_without_manual_number(db):
    plan = PlanEstudio(clave="2025-1", nombre="Plan Test")
    db.session.add(plan)
    db.session.commit()

    result = GroupService.create_group(
        {
            "tipo_grupo": "intersemestral",
            "semestre": 2,
            "plan_estudio_clave": "2025-1",
            "capacidad_alumnos": 30,
        }
    )

    assert result["modalidad_grupo"] == "intersemestral"
    assert result["numero_grupo"] >= 910000
    assert result["numero_grupo_visible"].startswith("Grupo ")
    assert result["semestre"] == 2


def test_create_maestria_group_without_manual_number(db):
    plan = PlanEstudio(clave="2015-2", nombre="Plan Viejo")
    db.session.add(plan)
    db.session.commit()

    result = GroupService.create_group(
        {
            "tipo_grupo": "maestria",
            "capacidad_alumnos": 25,
        }
    )

    assert result["modalidad_grupo"] == "maestria"
    assert result["numero_grupo"] >= 920000
    assert result["numero_grupo_visible"].startswith("Grupo ")
    assert result["semestre"] == 1


def test_create_maestria_group_with_manual_visible_number(db):
    plan = PlanEstudio(clave="2025-1", nombre="Plan Test")
    db.session.add(plan)
    db.session.commit()

    result = GroupService.create_group(
        {
            "tipo_grupo": "maestria",
            "numero_grupo": 7,
            "capacidad_alumnos": 25,
        }
    )

    assert result["modalidad_grupo"] == "maestria"
    assert result["numero_grupo"] == 920006
    assert result["numero_grupo_visible"] == "Grupo 7"


def test_update_maestria_group_manual_visible_number(db):
    plan = PlanEstudio(clave="2025-1", nombre="Plan Test")
    db.session.add(plan)
    db.session.commit()

    created = GroupService.create_group(
        {
            "tipo_grupo": "maestria",
            "capacidad_alumnos": 20,
        }
    )

    updated = GroupService.update_group(
        created["id"],
        {
            "tipo_grupo": "maestria",
            "numero_grupo": 3,
        },
    )

    assert updated["modalidad_grupo"] == "maestria"
    assert updated["numero_grupo"] == 920002
    assert updated["numero_grupo_visible"] == "Grupo 3"


def test_maestria_group_can_pick_subjects_without_plan_or_semester_filter(db):
    plan_a = PlanEstudio(clave="2025-1", nombre="Plan A")
    plan_b = PlanEstudio(clave="2015-2", nombre="Plan B")
    db.session.add_all([plan_a, plan_b])
    db.session.flush()

    db.session.add_all(
        [
            Materia(
                clave="A101",
                nombre="Materia A",
                semestre=1,
                plan_estudio_id=plan_a.id,
                tipo_materia="normal",
                modalidad="presencial",
                activa=True,
            ),
            Materia(
                clave="B701",
                nombre="Materia B",
                semestre=7,
                plan_estudio_id=plan_b.id,
                tipo_materia="normal",
                modalidad="presencial",
                activa=True,
            ),
        ]
    )
    db.session.commit()

    created = GroupService.create_group(
        {
            "tipo_grupo": "maestria",
            "capacidad_alumnos": 20,
        }
    )

    group = db.session.get(Grupo, created["id"])
    subjects = db.session.scalars(build_valid_subjects_query_for_group(group)).all()
    keys = {subject.clave for subject in subjects}

    assert "A101" in keys
    assert "B701" in keys
