from datetime import datetime

from app.extensions import db


class Grupo(db.Model):
    __tablename__ = "grupos"
    __table_args__ = (
        db.CheckConstraint("semestre >= 1 AND semestre <= 8", name="semestre_rango"),
        db.CheckConstraint("capacidad_alumnos > 0", name="capacidad_positiva"),
        db.CheckConstraint(
            "tipo_grupo IN ('normal', 'semi')",
            name="tipo_grupo_valido",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    numero_grupo = db.Column(db.Integer, nullable=False, unique=True, index=True)
    semestre = db.Column(db.Integer, nullable=False)
    plan_estudio_id = db.Column(
        db.Integer,
        db.ForeignKey("planes_estudio.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    capacidad_alumnos = db.Column(db.Integer, nullable=False)
    tipo_grupo = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    plan_estudio = db.relationship("PlanEstudio", back_populates="grupos", lazy="joined")
    bloques_horario = db.relationship(
        "BloqueHorario",
        back_populates="grupo",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Grupo {self.numero_grupo}>"