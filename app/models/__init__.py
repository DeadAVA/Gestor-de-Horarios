from app.models.asignacion_materia import AsignacionMateriaGrupo
from app.models.bloque_horario import BloqueHorario
from app.models.docente import Docente
from app.models.grupo import Grupo
from app.models.horario_observacion import HorarioObservacion
from app.models.horario_juez import HorarioJuez
from app.models.materia import Materia
from app.models.observacion_docente import DocenteMateriaObservacion
from app.models.plan_estudio import PlanEstudio


__all__ = [
    "PlanEstudio",
    "Grupo",
    "Materia",
    "Docente",
    "AsignacionMateriaGrupo",
    "BloqueHorario",
    "DocenteMateriaObservacion",
    "HorarioJuez",
    "HorarioObservacion",
]