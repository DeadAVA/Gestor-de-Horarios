from datetime import datetime

from sqlalchemy import select

from app.extensions import db
from app.models import BloqueHorario, Docente, Materia
from app.models.observacion_docente import DocenteMateriaObservacion
from app.utils.exceptions import NotFoundApiError, ValidationApiError
from app.utils.serializers import serialize_teacher, serialize_subject
from app.utils.time_utils import calculate_hours_from_blocks


NIVEL_LABELS = {
    "malo": "Da mal la materia",
    "regular": "Regular",
    "bueno": "La da bien",
}


class HistorialService:
    # ------------------------------------------------------------------ #
    #  Historial aggregation                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_historial_all() -> list[dict]:
        """Return all teacher × subject combinations from assigned blocks, plus observations."""
        blocks = db.session.scalars(select(BloqueHorario)).all()
        observations = {
            (obs.docente_id, obs.materia_id): obs
            for obs in db.session.scalars(select(DocenteMateriaObservacion)).all()
        }
        return HistorialService._aggregate_blocks(blocks, observations)

    @staticmethod
    def get_historial_by_teacher(teacher_id: int) -> list[dict]:
        teacher = db.session.get(Docente, teacher_id)
        if not teacher:
            raise NotFoundApiError(f"Docente {teacher_id} no encontrado")
        blocks = [b for b in teacher.bloques_horario]
        observations = {
            (obs.docente_id, obs.materia_id): obs
            for obs in db.session.scalars(
                select(DocenteMateriaObservacion).where(
                    DocenteMateriaObservacion.docente_id == teacher_id
                )
            ).all()
        }
        return HistorialService._aggregate_blocks(blocks, observations)

    @staticmethod
    def _aggregate_blocks(blocks, observations: dict) -> list[dict]:
        # Group by (docente_id, materia_id)
        grouped: dict[tuple, dict] = {}
        for block in blocks:
            key = (block.docente_id, block.materia_id)
            if key not in grouped:
                grupo_label = f"G{block.grupo.numero_grupo}" if block.grupo else "?"
                grouped[key] = {
                    "docente": serialize_teacher(block.docente, include_hours=False),
                    "materia": serialize_subject(block.materia),
                    "grupos": set(),
                    "bloques": [],
                }
            grouped[key]["grupos"].add(
                f"G{block.grupo.numero_grupo}" if block.grupo else "?"
            )
            grouped[key]["bloques"].append(block)

        result = []
        for (docente_id, materia_id), entry in grouped.items():
            obs = observations.get((docente_id, materia_id))
            horas = calculate_hours_from_blocks(entry["bloques"])
            result.append({
                "docente": entry["docente"],
                "materia": entry["materia"],
                "grupos": sorted(entry["grupos"]),
                "horas_asignadas": horas,
                "observacion": _serialize_obs(obs),
            })

        result.sort(key=lambda r: (r["docente"]["nombre"], r["materia"]["nombre"]))
        return result

    # ------------------------------------------------------------------ #
    #  Observations CRUD                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def upsert_observacion(docente_id: int, materia_id: int, payload: dict) -> dict:
        """Create or update an observation for a teacher × subject pair."""
        _ensure_teacher_exists(docente_id)
        _ensure_subject_exists(materia_id)

        observacion_text = (payload.get("observacion") or "").strip()
        if not observacion_text:
            raise ValidationApiError("La observación no puede estar vacía", [])

        nivel = payload.get("nivel", "malo")
        if nivel not in ("malo", "regular", "bueno"):
            raise ValidationApiError("Nivel inválido", ["Debe ser malo, regular o bueno"])

        obs = db.session.scalars(
            select(DocenteMateriaObservacion).where(
                DocenteMateriaObservacion.docente_id == docente_id,
                DocenteMateriaObservacion.materia_id == materia_id,
            )
        ).first()

        if obs:
            obs.observacion = observacion_text
            obs.nivel = nivel
            obs.updated_at = datetime.utcnow()
        else:
            obs = DocenteMateriaObservacion(
                docente_id=docente_id,
                materia_id=materia_id,
                observacion=observacion_text,
                nivel=nivel,
            )
            db.session.add(obs)

        db.session.commit()
        db.session.refresh(obs)
        return _serialize_obs(obs)

    @staticmethod
    def delete_observacion(docente_id: int, materia_id: int) -> None:
        obs = db.session.scalars(
            select(DocenteMateriaObservacion).where(
                DocenteMateriaObservacion.docente_id == docente_id,
                DocenteMateriaObservacion.materia_id == materia_id,
            )
        ).first()
        if not obs:
            raise NotFoundApiError("Observación no encontrada")
        db.session.delete(obs)
        db.session.commit()

    @staticmethod
    def get_observacion(docente_id: int, materia_id: int) -> dict | None:
        obs = db.session.scalars(
            select(DocenteMateriaObservacion).where(
                DocenteMateriaObservacion.docente_id == docente_id,
                DocenteMateriaObservacion.materia_id == materia_id,
            )
        ).first()
        return _serialize_obs(obs)

    @staticmethod
    def get_all_observaciones() -> list[dict]:
        rows = db.session.scalars(select(DocenteMateriaObservacion)).all()
        return [_serialize_obs(r) for r in rows]


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _serialize_obs(obs: DocenteMateriaObservacion | None) -> dict | None:
    if obs is None:
        return None
    return {
        "id": obs.id,
        "docente_id": obs.docente_id,
        "materia_id": obs.materia_id,
        "observacion": obs.observacion,
        "nivel": obs.nivel,
        "nivel_label": NIVEL_LABELS.get(obs.nivel, obs.nivel),
        "docente": serialize_teacher(obs.docente, include_hours=False) if obs.docente else None,
        "materia": serialize_subject(obs.materia) if obs.materia else None,
        "created_at": obs.created_at.isoformat(),
        "updated_at": obs.updated_at.isoformat(),
    }


def _ensure_teacher_exists(teacher_id: int) -> None:
    if not db.session.get(Docente, teacher_id):
        raise NotFoundApiError(f"Docente {teacher_id} no encontrado")


def _ensure_subject_exists(materia_id: int) -> None:
    if not db.session.get(Materia, materia_id):
        raise NotFoundApiError(f"Materia {materia_id} no encontrada")
