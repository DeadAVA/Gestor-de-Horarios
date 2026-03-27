from app.extensions import db


class Docente(db.Model):
    __tablename__ = "docentes"

    id = db.Column(db.Integer, primary_key=True)
    clave_docente = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    foraneo = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    es_juez = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    bloques_horario = db.relationship(
        "BloqueHorario",
        back_populates="docente",
        cascade="save-update, merge",
        lazy="selectin",
    )

    horario_juez = db.relationship(
        "HorarioJuez",
        back_populates="docente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Docente {self.clave_docente}>"