from app.extensions import db


class Materia(db.Model):
    __tablename__ = "materias"
    __table_args__ = (
        db.CheckConstraint("semestre >= 1 AND semestre <= 8", name="semestre_rango"),
        db.CheckConstraint(
            "tipo_materia IN ('normal', 'optativa')",
            name="tipo_materia_valido",
        ),
        db.CheckConstraint(
            "modalidad IN ('presencial', 'virtual')",
            name="modalidad_valida",
        ),
        db.CheckConstraint("hc >= 0", name="hc_no_negativo"),
        db.CheckConstraint("ht >= 0", name="ht_no_negativo"),
        db.CheckConstraint("hl >= 0", name="hl_no_negativo"),
        db.CheckConstraint("hpc >= 0", name="hpc_no_negativo"),
        db.CheckConstraint("hcl >= 0", name="hcl_no_negativo"),
        db.CheckConstraint("he >= 0", name="he_no_negativo"),
        db.CheckConstraint("cr >= 0", name="cr_no_negativo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    semestre = db.Column(db.Integer, nullable=False, index=True)
    plan_estudio_id = db.Column(
        db.Integer,
        db.ForeignKey("planes_estudio.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo_materia = db.Column(db.String(20), nullable=False)
    etapa = db.Column(db.String(50), nullable=True)
    modalidad = db.Column(db.String(20), nullable=False)
    hc = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    ht = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    hl = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    hpc = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    hcl = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    he = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    cr = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    activa = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())

    plan_estudio = db.relationship("PlanEstudio", back_populates="materias", lazy="joined")
    bloques_horario = db.relationship(
        "BloqueHorario",
        back_populates="materia",
        cascade="save-update, merge",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Materia {self.clave}>"