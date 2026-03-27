from app.extensions import db


class HorarioJuez(db.Model):
    """Franjas de tiempo predefinidas para docentes que fungen como jueces."""

    __tablename__ = "horarios_juez"

    id = db.Column(db.Integer, primary_key=True)
    docente_id = db.Column(
        db.Integer,
        db.ForeignKey("docentes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dia = db.Column(db.String(12), nullable=False)
    hora_inicio = db.Column(db.Integer, nullable=False)
    hora_fin = db.Column(db.Integer, nullable=False)

    docente = db.relationship("Docente", back_populates="horario_juez")

    def __repr__(self) -> str:
        return f"<HorarioJuez docente={self.docente_id} {self.dia} {self.hora_inicio}-{self.hora_fin}>"
