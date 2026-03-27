from app.extensions import db


class PlanEstudio(db.Model):
    __tablename__ = "planes_estudio"

    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())

    grupos = db.relationship(
        "Grupo",
        back_populates="plan_estudio",
        cascade="save-update, merge",
        lazy="selectin",
    )
    materias = db.relationship(
        "Materia",
        back_populates="plan_estudio",
        cascade="save-update, merge",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PlanEstudio {self.clave}>"