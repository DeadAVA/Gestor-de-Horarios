from datetime import datetime

from app.extensions import db
from sqlalchemy import text


class HorarioObservacion(db.Model):
    __tablename__ = "horario_observaciones"

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(
        db.Integer,
        db.ForeignKey("grupos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    materia_id = db.Column(
        db.Integer,
        db.ForeignKey("materias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    comentario = db.Column(db.Text, nullable=False)
    atendido = db.Column(db.Boolean, nullable=False, default=False, server_default=text("0"))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    grupo = db.relationship("Grupo", lazy="joined")
    materia = db.relationship("Materia", lazy="joined")

    def __repr__(self) -> str:
        return f"<HorarioObservacion grupo={self.grupo_id} materia={self.materia_id}>"
