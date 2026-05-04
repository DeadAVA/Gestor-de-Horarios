from app.models import AsignacionMateriaGrupo, BloqueHorario, Docente, Grupo, Materia, PlanEstudio
from app.services.backup_service import BackupService
from app.services.vacancy_teacher import VACANCY_TEACHER_KEY


def test_import_backup_maps_invalid_teacher_to_vacante(db):
    payload = {
        "version": "1.0",
        "data": {
            "planes_estudio": [
                {"id": 1, "clave": "2025-1", "nombre": "Plan Test", "activo": True},
            ],
            "docentes": [
                {"id": 10, "clave_docente": "DOC-10", "nombre": "Docente Real", "activo": True},
            ],
            "materias": [
                {
                    "id": 20,
                    "clave": "MAT-20",
                    "nombre": "Materia Test",
                    "semestre": 1,
                    "plan_estudio_id": 1,
                    "tipo_materia": "normal",
                    "etapa": "basica",
                    "modalidad": "presencial",
                    "activa": True,
                },
            ],
            "grupos": [
                {
                    "id": 30,
                    "numero_grupo": 501,
                    "semestre": 1,
                    "plan_estudio_id": 1,
                    "capacidad_alumnos": 30,
                    "tipo_grupo": "normal",
                },
            ],
            "bloques_horario": [
                {
                    "id": 40,
                    "grupo_id": 30,
                    "materia_id": 20,
                    "docente_id": 0,
                    "dia": "lunes",
                    "hora_inicio": "08:00:00",
                    "hora_fin": "09:00:00",
                    "modalidad": "presencial",
                },
            ],
        },
    }

    summary = BackupService.import_data(payload)

    block = db.session.get(BloqueHorario, 40)
    assert block is not None
    assert block.docente is not None
    assert block.docente.clave_docente == VACANCY_TEACHER_KEY
    assert summary["bloques_horario"] == 1


def test_export_import_persists_subject_assignment_without_blocks(db):
    plan = PlanEstudio(clave="2025-1", nombre="Plan 2025")
    subject = Materia(
        clave="OPT-01",
        nombre="Optativa Persistida",
        semestre=1,
        plan_estudio=plan,
        tipo_materia="optativa",
        etapa="disciplinaria",
        modalidad="presencial",
    )
    group = Grupo(
        numero_grupo=501,
        semestre=1,
        plan_estudio=plan,
        capacidad_alumnos=30,
        tipo_grupo="normal",
    )
    teacher = Docente(clave_docente="DOC-OPT", nombre="Docente Optativa", activo=True)

    db.session.add_all([plan, subject, group, teacher])
    db.session.flush()

    assignment = AsignacionMateriaGrupo(
        grupo_id=group.id,
        materia_id=subject.id,
        docente_id=teacher.id,
    )
    db.session.add(assignment)
    db.session.commit()

    exported = BackupService.export_data()
    exported_assignments = exported["data"].get("asignaciones_materia", [])
    assert len(exported_assignments) == 1
    assert exported_assignments[0]["grupo_id"] == group.id
    assert exported_assignments[0]["materia_id"] == subject.id
    assert exported_assignments[0]["docente_id"] == teacher.id

    summary = BackupService.import_data(exported)

    restored = db.session.query(AsignacionMateriaGrupo).all()
    assert len(restored) == 1
    assert restored[0].grupo_id == group.id
    assert restored[0].materia_id == subject.id
    assert restored[0].docente_id == teacher.id
    assert summary["asignaciones_materia"] == 1
