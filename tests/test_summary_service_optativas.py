import pytest
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


@pytest.mark.parametrize(
    "group_number, semester, plan_key",
    [
        (505, 1, "2025-1"),
        (506, 1, "2025-1"),
        (507, 1, "2025-1"),
        (508, 1, "2025-1"),
        (509, 1, "2025-1"),
        (525, 2, "2025-1"),
        (526, 2, "2025-1"),
        (527, 2, "2025-1"),
        (528, 2, "2025-1"),
        (529, 2, "2025-1"),
        (535, 3, "2025-1"),
        (536, 3, "2025-1"),
        (537, 3, "2025-1"),
        (538, 3, "2025-1"),
        (539, 3, "2025-1"),
        (545, 4, "2025-1"),
        (546, 4, "2025-1"),
        (547, 4, "2025-1"),
        (548, 4, "2025-1"),
        (549, 4, "2025-1"),
        (555, 5, "2015-2"),
        (556, 5, "2015-2"),
        (557, 5, "2015-2"),
        (558, 5, "2015-2"),
        (559, 5, "2015-2"),
        (565, 6, "2015-2"),
        (566, 6, "2015-2"),
        (567, 6, "2015-2"),
        (568, 6, "2015-2"),
        (569, 6, "2015-2"),
        (575, 7, "2015-2"),
        (576, 7, "2015-2"),
        (577, 7, "2015-2"),
        (578, 7, "2015-2"),
        (579, 7, "2015-2"),
        (585, 8, "2015-2"),
        (586, 8, "2015-2"),
        (587, 8, "2015-2"),
        (588, 8, "2015-2"),
        (589, 8, "2015-2"),
    ],
)
def test_manual_groups_x5_to_x9_do_not_report_all_plan_subjects_as_vacancies(db, group_number, semester, plan_key):
    plan = PlanEstudio(clave=plan_key, nombre=f"Plan {plan_key}")
    db.session.add(plan)
    db.session.flush()

    group = Grupo(
        numero_grupo=group_number,
        semestre=semester,
        plan_estudio_id=plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    teacher = Docente(
        clave_docente=f"DOC-{group_number}",
        nombre=f"Docente Test {group_number}",
        activo=True,
    )

    subject_a = Materia(
        clave="MAN-001",
        nombre="Materia Manual 1",
        semestre=semester,
        plan_estudio_id=plan.id,
        tipo_materia="normal",
        etapa="basica" if semester <= 4 else "disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    subject_b = Materia(
        clave="MAN-002",
        nombre="Materia Manual 2",
        semestre=1 if semester != 1 else 5,
        plan_estudio_id=plan.id,
        tipo_materia="normal",
        etapa="basica" if semester <= 4 else "disciplinaria",
        modalidad="presencial",
        activa=True,
    )

    db.session.add_all([group, teacher, subject_a, subject_b])
    db.session.flush()

    block = BloqueHorario(
        grupo_id=group.id,
        materia_id=subject_a.id,
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

    assert "MAN-001" not in missing_keys
    assert "MAN-002" not in missing_keys
