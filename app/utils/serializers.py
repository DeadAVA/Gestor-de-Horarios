from app.models import BloqueHorario, Docente, Grupo, Materia, PlanEstudio
from app.models.horario_juez import HorarioJuez
from app.services.group_rules import get_virtual_group_index, resolve_group_modality
from app.utils.time_utils import calculate_hours_from_blocks, format_time_value


def serialize_plan(plan: PlanEstudio) -> dict:
    return {
        "id": plan.id,
        "clave": plan.clave,
        "nombre": plan.nombre,
        "activo": plan.activo,
    }


def serialize_block(block: BloqueHorario) -> dict:
    return {
        "id": block.id,
        "dia": block.dia,
        "hora_inicio": format_time_value(block.hora_inicio),
        "hora_fin": format_time_value(block.hora_fin),
        "modalidad": block.modalidad,
        "indicador": "VIR" if block.modalidad == "virtual" else None,
        "materia": serialize_subject(block.materia, include_plan=False),
        "docente": serialize_teacher(block.docente, include_hours=False),
    }


def serialize_group(group: Grupo, include_related: bool = False) -> dict:
    modalidad_grupo = resolve_group_modality(group.numero_grupo, group.tipo_grupo)
    virtual_index = get_virtual_group_index(group.numero_grupo, modalidad_grupo)
    if modalidad_grupo == "intersemestral":
        etiqueta_grupo = f"Grupo {virtual_index}" if virtual_index is not None else "Grupo"
        numero_grupo_visible = etiqueta_grupo
    elif modalidad_grupo == "maestria":
        etiqueta_grupo = f"Grupo {virtual_index}" if virtual_index is not None else "Grupo"
        numero_grupo_visible = etiqueta_grupo
    else:
        etiqueta_grupo = f"Grupo {group.numero_grupo}"
        numero_grupo_visible = str(group.numero_grupo)

    payload = {
        "id": group.id,
        "numero_grupo": group.numero_grupo,
        "numero_grupo_visible": numero_grupo_visible,
        "etiqueta_grupo": etiqueta_grupo,
        "grupo_consecutivo": virtual_index,
        "semestre": group.semestre,
        "plan_estudio": serialize_plan(group.plan_estudio),
        "capacidad_alumnos": group.capacidad_alumnos,
        "tipo_grupo": group.tipo_grupo,
        "modalidad_grupo": modalidad_grupo,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
    }

    if include_related:
        payload["materias_disponibles"] = []
        payload["bloques"] = [serialize_block(block) for block in group.bloques_horario]

    return payload


def serialize_subject(materia: Materia, include_plan: bool = True) -> dict:
    payload = {
        "id": materia.id,
        "clave": materia.clave,
        "nombre": materia.nombre,
        "semestre": materia.semestre,
        "tipo_materia": materia.tipo_materia,
        "etapa": materia.etapa,
        "modalidad": materia.modalidad,
        "hc": materia.hc,
        "ht": materia.ht,
        "hl": materia.hl,
        "hpc": materia.hpc,
        "hcl": materia.hcl,
        "he": materia.he,
        "cr": materia.cr,
        "indicador": "VIR" if materia.modalidad == "virtual" else None,
        "activa": materia.activa,
    }

    if include_plan:
        payload["plan_estudio"] = serialize_plan(materia.plan_estudio)

    return payload


def serialize_horario_juez(slot: HorarioJuez) -> dict:
    return {
        "id": slot.id,
        "dia": slot.dia,
        "hora_inicio": slot.hora_inicio,
        "hora_fin": slot.hora_fin,
    }


def serialize_teacher(docente: Docente, include_hours: bool = True) -> dict:
    payload = {
        "id": docente.id,
        "clave_docente": docente.clave_docente,
        "nombre": docente.nombre,
        "foraneo": docente.foraneo,
        "activo": docente.activo,
        "es_juez": docente.es_juez,
        "horario_juez": [serialize_horario_juez(s) for s in (docente.horario_juez or [])],
    }

    if include_hours:
        payload["horas_acumuladas"] = calculate_hours_from_blocks(docente.bloques_horario)

    return payload


def serialize_schedule_observation(observation) -> dict:
    return {
        "id": observation.id,
        "grupo_id": observation.grupo_id,
        "materia_id": observation.materia_id,
        "comentario": observation.comentario,
        "atendido": bool(getattr(observation, "atendido", False)),
        "created_at": observation.created_at.isoformat() if observation.created_at else None,
        "updated_at": observation.updated_at.isoformat() if observation.updated_at else None,
        "materia": serialize_subject(observation.materia, include_plan=False) if observation.materia else None,
    }