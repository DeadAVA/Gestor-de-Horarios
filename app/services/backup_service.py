from datetime import datetime, time

from app.extensions import db
from app.models import (
    BloqueHorario,
    Docente,
    DocenteMateriaObservacion,
    Grupo,
    Materia,
    PlanEstudio,
)

BACKUP_VERSION = "1.0"


class BackupService:
    @staticmethod
    def export_data() -> dict:
        """Serializa toda la base de datos a un dict JSON-serializable."""
        planes = PlanEstudio.query.all()
        docentes = Docente.query.all()
        materias = Materia.query.all()
        grupos = Grupo.query.all()
        bloques = BloqueHorario.query.all()
        observaciones = DocenteMateriaObservacion.query.all()

        return {
            "version": BACKUP_VERSION,
            "exported_at": datetime.utcnow().isoformat(),
            "data": {
                "planes_estudio": [
                    {"id": p.id, "clave": p.clave, "nombre": p.nombre, "activo": p.activo}
                    for p in planes
                ],
                "docentes": [
                    {"id": d.id, "clave_docente": d.clave_docente, "nombre": d.nombre, "activo": d.activo}
                    for d in docentes
                ],
                "materias": [
                    {
                        "id": m.id, "clave": m.clave, "nombre": m.nombre,
                        "semestre": m.semestre, "plan_estudio_id": m.plan_estudio_id,
                        "tipo_materia": m.tipo_materia, "etapa": m.etapa,
                        "modalidad": m.modalidad, "hc": m.hc, "ht": m.ht,
                        "hl": m.hl, "hpc": m.hpc, "hcl": m.hcl, "he": m.he,
                        "cr": m.cr, "activa": m.activa,
                    }
                    for m in materias
                ],
                "grupos": [
                    {
                        "id": g.id, "numero_grupo": g.numero_grupo, "semestre": g.semestre,
                        "plan_estudio_id": g.plan_estudio_id, "capacidad_alumnos": g.capacidad_alumnos,
                        "tipo_grupo": g.tipo_grupo,
                    }
                    for g in grupos
                ],
                "bloques_horario": [
                    {
                        "id": b.id, "grupo_id": b.grupo_id, "materia_id": b.materia_id,
                        "docente_id": b.docente_id, "dia": b.dia,
                        "hora_inicio": b.hora_inicio.strftime("%H:%M:%S"),
                        "hora_fin": b.hora_fin.strftime("%H:%M:%S"),
                        "modalidad": b.modalidad,
                    }
                    for b in bloques
                ],
                "observaciones": [
                    {
                        "id": o.id, "docente_id": o.docente_id, "materia_id": o.materia_id,
                        "observacion": o.observacion, "nivel": o.nivel,
                    }
                    for o in observaciones
                ],
            },
        }

    @staticmethod
    def import_data(payload: dict) -> dict:
        """
        Reemplaza toda la base de datos con los datos del backup.
        Retorna un resumen con la cantidad de registros importados.
        Lanza ValueError si el payload no es válido.
        """
        tables = payload.get("data", {})
        required = {"planes_estudio", "docentes", "materias", "grupos", "bloques_horario"}
        missing = required - tables.keys()
        if missing:
            raise ValueError(f"Backup incompleto. Faltan secciones: {', '.join(sorted(missing))}")

        # Borrar en orden inverso a las FK para evitar violaciones de integridad
        DocenteMateriaObservacion.query.delete()
        BloqueHorario.query.delete()
        Grupo.query.delete()
        Materia.query.delete()
        Docente.query.delete()
        PlanEstudio.query.delete()
        db.session.flush()

        # Planes de estudio
        for p in tables["planes_estudio"]:
            db.session.add(PlanEstudio(
                id=p["id"], clave=p["clave"], nombre=p["nombre"],
                activo=p.get("activo", True),
            ))
        db.session.flush()

        # Docentes
        for d in tables["docentes"]:
            db.session.add(Docente(
                id=d["id"], clave_docente=d["clave_docente"], nombre=d["nombre"],
                activo=d.get("activo", True),
            ))
        db.session.flush()

        # Materias
        for m in tables["materias"]:
            db.session.add(Materia(
                id=m["id"], clave=m["clave"], nombre=m["nombre"],
                semestre=m["semestre"], plan_estudio_id=m["plan_estudio_id"],
                tipo_materia=m["tipo_materia"], etapa=m.get("etapa"),
                modalidad=m["modalidad"], hc=m.get("hc", 0), ht=m.get("ht", 0),
                hl=m.get("hl", 0), hpc=m.get("hpc", 0), hcl=m.get("hcl", 0),
                he=m.get("he", 0), cr=m.get("cr", 0), activa=m.get("activa", True),
            ))
        db.session.flush()

        # Grupos
        for g in tables["grupos"]:
            db.session.add(Grupo(
                id=g["id"], numero_grupo=g["numero_grupo"], semestre=g["semestre"],
                plan_estudio_id=g["plan_estudio_id"], capacidad_alumnos=g["capacidad_alumnos"],
                tipo_grupo=g["tipo_grupo"],
            ))
        db.session.flush()

        # Bloques de horario
        for b in tables["bloques_horario"]:
            hi = _parse_time(b["hora_inicio"])
            hf = _parse_time(b["hora_fin"])
            db.session.add(BloqueHorario(
                id=b["id"], grupo_id=b["grupo_id"], materia_id=b["materia_id"],
                docente_id=b["docente_id"], dia=b["dia"],
                hora_inicio=hi, hora_fin=hf, modalidad=b["modalidad"],
            ))
        db.session.flush()

        # Observaciones (opcionales — campo nuevo en v1.0)
        for o in tables.get("observaciones", []):
            db.session.add(DocenteMateriaObservacion(
                id=o["id"], docente_id=o["docente_id"], materia_id=o["materia_id"],
                observacion=o["observacion"], nivel=o.get("nivel", "malo"),
            ))

        db.session.commit()

        return {
            "planes_estudio": len(tables["planes_estudio"]),
            "docentes": len(tables["docentes"]),
            "materias": len(tables["materias"]),
            "grupos": len(tables["grupos"]),
            "bloques_horario": len(tables["bloques_horario"]),
            "observaciones": len(tables.get("observaciones", [])),
        }


def _parse_time(t: str) -> time:
    parts = t.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    s = int(parts[2]) if len(parts) > 2 else 0
    return time(h, m, s)
