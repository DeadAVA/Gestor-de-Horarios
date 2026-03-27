from datetime import datetime

from app.extensions import db


class DocenteMateriaObservacion(db.Model):
    __tablename__ = "docente_materia_observaciones"
    __table_args__ = (
        db.UniqueConstraint("docente_id", "materia_id", name="uq_obs_docente_materia"),
        db.CheckConstraint(
            "nivel IN ('malo', 'regular', 'bueno')",
            name="nivel_valido",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    docente_id = db.Column(
        db.Integer,
        db.ForeignKey("docentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    materia_id = db.Column(
        db.Integer,
        db.ForeignKey("materias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observacion = db.Column(db.Text, nullable=False)
    nivel = db.Column(db.String(20), nullable=False, default="malo", server_default="malo")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    docente = db.relationship("Docente", lazy="joined")
    materia = db.relationship("Materia", lazy="joined")

    def __repr__(self) -> str:
        return f"<DocenteMateriaObservacion docente={self.docente_id} materia={self.materia_id}>"
