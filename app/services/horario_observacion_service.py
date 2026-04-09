from sqlalchemy import inspect, select, text

from app.extensions import db
from app.models import Grupo, HorarioObservacion
from app.utils.exceptions import NotFoundApiError, ValidationApiError
from app.utils.serializers import serialize_schedule_observation


class HorarioObservacionService:
    @staticmethod
    def list_group_observations(group_id: int) -> list[dict]:
        HorarioObservacionService._ensure_storage_ready()
        HorarioObservacionService._get_group_or_404(group_id)
        observations = db.session.scalars(
            select(HorarioObservacion)
            .where(HorarioObservacion.grupo_id == group_id)
            .order_by(HorarioObservacion.updated_at.desc(), HorarioObservacion.id.desc())
        ).all()
        return [serialize_schedule_observation(item) for item in observations]

    @staticmethod
    def create_observation(group_id: int, payload: dict) -> dict:
        HorarioObservacionService._ensure_storage_ready()
        group = HorarioObservacionService._get_group_or_404(group_id)
        comentario = HorarioObservacionService._validate_comment(payload.get("comentario"))

        observation = HorarioObservacion(
            grupo_id=group.id,
            materia_id=None,
            comentario=comentario,
            atendido=HorarioObservacionService._parse_bool(payload.get("atendido"), default=False),
        )
        db.session.add(observation)
        db.session.commit()
        db.session.refresh(observation)
        return serialize_schedule_observation(observation)

    @staticmethod
    def update_observation(observation_id: int, payload: dict) -> dict:
        HorarioObservacionService._ensure_storage_ready()
        observation = HorarioObservacionService._get_observation_or_404(observation_id)
        HorarioObservacionService._get_group_or_404(observation.grupo_id)

        if "comentario" in payload:
            observation.comentario = HorarioObservacionService._validate_comment(payload.get("comentario"))

        if "atendido" in payload:
            observation.atendido = HorarioObservacionService._parse_bool(payload.get("atendido"), default=bool(observation.atendido))

        # Observaciones de horario son generales del grupo.
        observation.materia_id = None

        db.session.commit()
        db.session.refresh(observation)
        return serialize_schedule_observation(observation)

    @staticmethod
    def delete_observation(observation_id: int) -> dict:
        HorarioObservacionService._ensure_storage_ready()
        observation = HorarioObservacionService._get_observation_or_404(observation_id)
        serialized = serialize_schedule_observation(observation)
        db.session.delete(observation)
        db.session.commit()
        return serialized

    @staticmethod
    def _ensure_storage_ready() -> None:
        # Compatibilidad para SQLite local: si el usuario no ha corrido migraciones,
        # crear solo la tabla de observaciones de horario al vuelo.
        if db.engine.dialect.name != "sqlite":
            return

        inspector = inspect(db.engine)
        if "horario_observaciones" not in inspector.get_table_names():
            HorarioObservacion.__table__.create(bind=db.engine, checkfirst=True)
            return

        columns = {column["name"] for column in inspector.get_columns("horario_observaciones")}
        if "atendido" not in columns:
            db.session.execute(text("ALTER TABLE horario_observaciones ADD COLUMN atendido BOOLEAN NOT NULL DEFAULT 0"))
            db.session.commit()

    @staticmethod
    def _get_group_or_404(group_id: int) -> Grupo:
        group = db.session.get(Grupo, group_id)
        if group is None:
            raise NotFoundApiError("Grupo no encontrado", [f"No existe un grupo con id {group_id}"])
        return group

    @staticmethod
    def _get_observation_or_404(observation_id: int) -> HorarioObservacion:
        observation = db.session.get(HorarioObservacion, observation_id)
        if observation is None:
            raise NotFoundApiError(
                "Observacion no encontrada",
                [f"No existe una observacion de horario con id {observation_id}"],
            )
        return observation

    @staticmethod
    def _validate_comment(raw_comment) -> str:
        comentario = str(raw_comment or "").strip()
        errors = []
        if not comentario:
            errors.append("El comentario es obligatorio")
        if len(comentario) > 1000:
            errors.append("El comentario no puede exceder 1000 caracteres")
        if errors:
            raise ValidationApiError("Error de validacion al procesar observacion", errors)
        return comentario

    @staticmethod
    def _parse_bool(value, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)

        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "t", "si", "sí", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off"}:
            return False
        raise ValidationApiError("Error de validacion al procesar observacion", ["atendido invalido"])
