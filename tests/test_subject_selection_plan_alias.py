from app.extensions import db
from app.models import Grupo, Materia, PlanEstudio
from app.services.subject_selection import build_valid_subjects_query_for_group


def test_subject_selection_falls_back_to_alias_plan_when_old_plan_has_no_subjects(db):
    old_plan = PlanEstudio(clave="2015-2", nombre="Plan Viejo")
    alias_plan = PlanEstudio(clave="2025-2", nombre="Plan Alias")
    db.session.add_all([old_plan, alias_plan])
    db.session.flush()

    group = Grupo(
        numero_grupo=551,
        semestre=5,
        plan_estudio_id=old_plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    db.session.add(group)
    db.session.flush()

    mandatory = Materia(
        clave="N25-501",
        nombre="Derecho Procesal del Trabajo",
        semestre=5,
        plan_estudio_id=alias_plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    wrong_semester = Materia(
        clave="N25-401",
        nombre="Derecho Colectivo del Trabajo",
        semestre=4,
        plan_estudio_id=alias_plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    db.session.add_all([mandatory, wrong_semester])
    db.session.commit()

    db.session.refresh(group)
    subjects = db.session.scalars(build_valid_subjects_query_for_group(group)).all()
    keys = {subject.clave for subject in subjects}

    assert "N25-501" in keys
    assert "N25-401" not in keys


def test_subject_selection_prefers_group_plan_when_it_has_subjects(db):
    old_plan = PlanEstudio(clave="2015-2", nombre="Plan Viejo")
    alias_plan = PlanEstudio(clave="2025-2", nombre="Plan Alias")
    db.session.add_all([old_plan, alias_plan])
    db.session.flush()

    group = Grupo(
        numero_grupo=551,
        semestre=5,
        plan_estudio_id=old_plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    db.session.add(group)
    db.session.flush()

    own_plan_subject = Materia(
        clave="OLD-501",
        nombre="Materia Plan Viejo",
        semestre=5,
        plan_estudio_id=old_plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    alias_subject = Materia(
        clave="N25-501",
        nombre="Materia Plan Alias",
        semestre=5,
        plan_estudio_id=alias_plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    db.session.add_all([own_plan_subject, alias_subject])
    db.session.commit()

    db.session.refresh(group)
    subjects = db.session.scalars(build_valid_subjects_query_for_group(group)).all()
    keys = {subject.clave for subject in subjects}

    assert "OLD-501" in keys
    assert "N25-501" not in keys


def test_subject_selection_includes_disciplinary_optativas_for_fourth_semester(db):
    plan = PlanEstudio(clave="2025-2", nombre="Plan Nuevo")
    db.session.add(plan)
    db.session.flush()

    group = Grupo(
        numero_grupo=541,
        semestre=4,
        plan_estudio_id=plan.id,
        capacidad_alumnos=40,
        tipo_grupo="normal",
    )
    db.session.add(group)
    db.session.flush()

    mandatory_sem4 = Materia(
        clave="N25-401",
        nombre="Materia Obligatoria 4to",
        semestre=4,
        plan_estudio_id=plan.id,
        tipo_materia="normal",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    disciplinary_optativa_other_sem = Materia(
        clave="N25OD02",
        nombre="Optativa Disciplinaria",
        semestre=3,
        plan_estudio_id=plan.id,
        tipo_materia="optativa",
        etapa="disciplinaria",
        modalidad="presencial",
        activa=True,
    )
    wrong_stage_optativa = Materia(
        clave="N25OT01",
        nombre="Optativa Terminal",
        semestre=7,
        plan_estudio_id=plan.id,
        tipo_materia="optativa",
        etapa="terminal",
        modalidad="presencial",
        activa=True,
    )

    db.session.add_all([mandatory_sem4, disciplinary_optativa_other_sem, wrong_stage_optativa])
    db.session.commit()

    db.session.refresh(group)
    subjects = db.session.scalars(build_valid_subjects_query_for_group(group)).all()
    keys = {subject.clave for subject in subjects}

    assert "N25-401" in keys
    assert "N25OD02" in keys
    assert "N25OT01" not in keys
