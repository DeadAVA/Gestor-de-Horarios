from datetime import time

from app.extensions import db
from app.models import BloqueHorario, Docente, Grupo, Materia, PlanEstudio
from app.services.summary_service import SummaryService


def test_group_summary_hides_remaining_optativas_once_one_is_assigned(db):
    plan = PlanEstudio(clave="2025-2", nombre="Plan 2025-2")
    db.session.add(plan)
    db.session.flush()

    group = Grupo(
        numero_grupo=551,
        semestre=5,
        plan_estudio_id=plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    teacher = Docente(clave_docente="DOC-001", nombre="Docente Test", activo=True)

    mandatory_subject = Materia(
        clave="N25-501",
        nombre="Materia Obligatoria",
        semestre=5,
        plan_estudio_id=plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    assigned_optativa = Materia(
        clave="N25OD01",
        nombre="Optativa Asignada",
        semestre=4,
        plan_estudio_id=plan.id,
        tipo_materia="optativa",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    unassigned_optativa = Materia(
        clave="N25OD02",
        nombre="Optativa Pendiente",
        semestre=4,
        plan_estudio_id=plan.id,
        tipo_materia="optativa",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )

    db.session.add_all([group, teacher, mandatory_subject, assigned_optativa, unassigned_optativa])
    db.session.flush()

    block = BloqueHorario(
        grupo_id=group.id,
        materia_id=assigned_optativa.id,
        docente_id=teacher.id,
        dia="lunes",
        hora_inicio=time(8, 0),
        hora_fin=time(9, 0),
        modalidad="presencial",
    )
    db.session.add(block)
    db.session.commit()

    summary = SummaryService.get_group_summary(group.id)
    missing_keys = {subject["clave"] for subject in summary["materias_sin_docente"]}

    assert "N25-501" in missing_keys
    assert "N25OD02" not in missing_keys


def test_group_summary_hides_optativas_when_assigned_in_another_group(db):
    plan = PlanEstudio(clave="2025-2", nombre="Plan 2025-2")
    db.session.add(plan)
    db.session.flush()

    group_a = Grupo(
        numero_grupo=551,
        semestre=5,
        plan_estudio_id=plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    group_b = Grupo(
        numero_grupo=552,
        semestre=5,
        plan_estudio_id=plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    teacher = Docente(clave_docente="DOC-002", nombre="Docente Test 2", activo=True)

    mandatory_subject = Materia(
        clave="N25-502",
        nombre="Materia Obligatoria 2",
        semestre=5,
        plan_estudio_id=plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    assigned_optativa = Materia(
        clave="N25OD11",
        nombre="Optativa Global Asignada",
        semestre=4,
        plan_estudio_id=plan.id,
        tipo_materia="optativa",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    unassigned_optativa = Materia(
        clave="N25OD12",
        nombre="Optativa Global Pendiente",
        semestre=4,
        plan_estudio_id=plan.id,
        tipo_materia="optativa",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )

    db.session.add_all([
        group_a,
        group_b,
        teacher,
        mandatory_subject,
        assigned_optativa,
        unassigned_optativa,
    ])
    db.session.flush()

    block = BloqueHorario(
        grupo_id=group_a.id,
        materia_id=assigned_optativa.id,
        docente_id=teacher.id,
        dia="martes",
        hora_inicio=time(8, 0),
        hora_fin=time(9, 0),
        modalidad="presencial",
    )
    db.session.add(block)
    db.session.commit()

    summary_group_b = SummaryService.get_group_summary(group_b.id)
    missing_keys = {subject["clave"] for subject in summary_group_b["materias_sin_docente"]}

    assert "N25-502" in missing_keys
    assert "N25OD12" not in missing_keys
