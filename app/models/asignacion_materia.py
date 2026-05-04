from datetime import datetime

from app.extensions import db


class AsignacionMateriaGrupo(db.Model):
    __tablename__ = "asignaciones_materia_grupo"
    __table_args__ = (
        db.UniqueConstraint("grupo_id", "materia_id", name="uq_asignacion_grupo_materia"),
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
        db.ForeignKey("materias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    docente_id = db.Column(
        db.Integer,
        db.ForeignKey("docentes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    grupo = db.relationship("Grupo", lazy="joined")
    materia = db.relationship("Materia", lazy="joined")
    docente = db.relationship("Docente", lazy="joined")

    def __repr__(self) -> str:
        return f"<AsignacionMateriaGrupo grupo={self.grupo_id} materia={self.materia_id} docente={self.docente_id}>"
