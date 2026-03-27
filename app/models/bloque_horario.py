from datetime import datetime

from app.extensions import db


class BloqueHorario(db.Model):
    __tablename__ = "bloques_horario"
    __table_args__ = (
        db.CheckConstraint(
            "dia IN ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado')",
            name="dia_valido",
        ),
        db.CheckConstraint(
            "modalidad IN ('presencial', 'virtual')",
            name="modalidad_valida",
        ),
        db.CheckConstraint("hora_inicio < hora_fin", name="rango_horas_valido"),
    )

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(
        db.Integer,
        db.ForeignKey("grupos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    materia_id = db.Column(
        db.Integer,
        db.ForeignKey("materias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    docente_id = db.Column(
        db.Integer,
        db.ForeignKey("docentes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dia = db.Column(db.String(20), nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    modalidad = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    grupo = db.relationship("Grupo", back_populates="bloques_horario", lazy="joined")
    materia = db.relationship("Materia", back_populates="bloques_horario", lazy="joined")
    docente = db.relationship("Docente", back_populates="bloques_horario", lazy="joined")

    def __repr__(self) -> str:
        return f"<BloqueHorario grupo={self.grupo_id} materia={self.materia_id}>"