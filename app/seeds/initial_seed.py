import click
import re
import unicodedata
from flask.cli import with_appcontext
from sqlalchemy import select

from app.extensions import db
from app.models import Docente, Materia, PlanEstudio


INITIAL_PLANS = [
    {"clave": "2025-1", "nombre": "Plan de Estudios 2025-1", "activo": True},
    {"clave": "2015-2", "nombre": "Plan de Estudios 2015-2", "activo": True},
    {"clave": "maestria", "nombre": "Plan de Maestría", "activo": True},
]

INITIAL_TEACHERS = [
    {"clave_docente": "DOC-001", "nombre": "Juan Perez", "activo": True},
    {"clave_docente": "DOC-002", "nombre": "Maria Gonzalez", "activo": True},
    {"clave_docente": "DOC-003", "nombre": "Rosa Martinez", "activo": True},
    {"clave_docente": "DOC-004", "nombre": "Carlos Ramirez", "activo": True},
    {"clave_docente": "DOC-005", "nombre": "Lucia Hernandez", "activo": True},
]


# Carga academica para materias del plan 2025-1 (plan viejo).
# Cuando no se cuenta con el desglose completo desde documento fuente,
# se mantiene en cero para permitir ajustes posteriores sin romper integridad.
OLD_PLAN_LOADS = {
    "DER101": {"hc": 3, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 8},
    "DER102": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "DER201": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "DER202": {"hc": 3, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 8},
    "DER301": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "DER302": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "DER401": {"hc": 3, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 8},
    "DER402": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP301": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP302": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP303": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP304": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP305": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP306": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP307": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP308": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP309": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "ODP310": {"hc": 2, "ht": 2, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 6},
    "OPT701": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT702": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT703": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT704": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT705": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT706": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT707": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT708": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
    "OPT709": {"hc": 0, "ht": 4, "hl": 0, "hpc": 0, "hcl": 0, "he": 0, "cr": 5},
}

INITIAL_SUBJECTS = [
    # Etapa basica (I-II)
    {
        "clave": "DER101",
        "nombre": "Introduccion al Derecho",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER102",
        "nombre": "Cultura de Paz",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER103",
        "nombre": "Instituciones Civiles del Derecho Romano",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER104",
        "nombre": "Logica y Ciencia",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER105",
        "nombre": "Herramientas Digitales para el Derecho",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER106",
        "nombre": "Comprension Lectora y Expresion Oral y Escrita",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER107",
        "nombre": "Sociologia Juridica",
        "semestre": 1,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER201",
        "nombre": "Filosofia Juridica",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER202",
        "nombre": "Metodologia de la Investigacion Juridica",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER203",
        "nombre": "Personas e Instituciones Familiares",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER204",
        "nombre": "Responsabilidad Social y Desarrollo Sustentable",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER205",
        "nombre": "Fundamentos del Derecho Penal",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER206",
        "nombre": "Teoria del Proceso",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER207",
        "nombre": "Justicia Digital",
        "semestre": 2,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "basica",
        "modalidad": "presencial",
        "activa": True,
    },

    # Etapa disciplinaria (III-VI)
    {
        "clave": "DER301",
        "nombre": "Teoria del Estado",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER302",
        "nombre": "Interpretacion y Argumentacion Juridica",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER303",
        "nombre": "Bienes y Derechos Reales",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER304",
        "nombre": "Derecho Individual del Trabajo",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER305",
        "nombre": "Delitos del Orden Comun",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER306",
        "nombre": "Medios Alternativos de Solucion de Conflictos",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER401",
        "nombre": "Derecho Constitucional",
        "semestre": 4,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER402",
        "nombre": "Sucesiones",
        "semestre": 4,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER403",
        "nombre": "Teoria de las Obligaciones",
        "semestre": 4,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER404",
        "nombre": "Derecho Colectivo del Trabajo",
        "semestre": 4,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER405",
        "nombre": "Delitos Especiales",
        "semestre": 4,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER501",
        "nombre": "Derechos Humanos",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER502",
        "nombre": "Derecho Procesal Civil y Familiar",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER503",
        "nombre": "Contratos Civiles",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER504",
        "nombre": "Derecho Procesal del Trabajo",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER505",
        "nombre": "Derecho Procesal Penal",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER506",
        "nombre": "Derecho Administrativo",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER507",
        "nombre": "Derecho Mercantil",
        "semestre": 5,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER601",
        "nombre": "Derecho Procesal Constitucional",
        "semestre": 6,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER602",
        "nombre": "Practica Forense de Derecho Civil y Familiar",
        "semestre": 6,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER603",
        "nombre": "Derecho Internacional Publico",
        "semestre": 6,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER604",
        "nombre": "Practica Forense de Derecho Penal",
        "semestre": 6,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER605",
        "nombre": "Derecho Fiscal",
        "semestre": 6,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER606",
        "nombre": "Derecho Societario",
        "semestre": 6,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },

    # Etapa terminal (VII-VIII)
    {
        "clave": "DER701",
        "nombre": "Instituciones del Derecho Procesal Constitucional",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER702",
        "nombre": "Derecho Electoral",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER703",
        "nombre": "Derecho Internacional de los Derechos Humanos",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER704",
        "nombre": "Derecho Procesal Administrativo",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER705",
        "nombre": "Derecho Procesal Mercantil",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER801",
        "nombre": "Practica Forense de Derecho Constitucional",
        "semestre": 8,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER802",
        "nombre": "Derecho Notarial y Registral",
        "semestre": 8,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER803",
        "nombre": "Derecho Internacional Privado",
        "semestre": 8,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "DER804",
        "nombre": "Derecho Agrario",
        "semestre": 8,
        "plan_clave": "2025-1",
        "tipo_materia": "normal",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },

    # Optativas etapa disciplinaria
    {
        "clave": "ODP301",
        "nombre": "Etica Profesional",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP302",
        "nombre": "Genero y Derecho",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP303",
        "nombre": "Paradigmas del Derecho Mexicano",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP304",
        "nombre": "Bioetica y Bioderecho",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP305",
        "nombre": "Derechos Humanos de las Ninas, Ninos y Adolescentes",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP306",
        "nombre": "Criminologia",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP307",
        "nombre": "Derecho Constitucional Local",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP308",
        "nombre": "Estadistica Juridica",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP309",
        "nombre": "Practica del Derecho del Trabajo",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "ODP310",
        "nombre": "Propiedad Intelectual",
        "semestre": 3,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "disciplinaria",
        "modalidad": "presencial",
        "activa": True,
    },

    # Optativas etapa terminal
    {
        "clave": "OPT701",
        "nombre": "Derecho Urbanistico",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT702",
        "nombre": "Practica de Derechos Emergentes y Tecnologias",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT703",
        "nombre": "Criminalistica",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT704",
        "nombre": "Derecho y Crisis Climatica",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT705",
        "nombre": "Derecho de las Empresas",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT706",
        "nombre": "Aspectos Juridicos de la Movilidad Humana",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT707",
        "nombre": "Emprendimiento y Liderazgo",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT708",
        "nombre": "Approach to Legal Justice",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
    {
        "clave": "OPT709",
        "nombre": "Derecho de Acceso a la Informacion y Proteccion de Datos Personales",
        "semestre": 7,
        "plan_clave": "2025-1",
        "tipo_materia": "optativa",
        "etapa": "terminal",
        "modalidad": "presencial",
        "activa": True,
    },
]


NEW_PLAN_2025_2_REQUIRED_SUBJECTS = [
    # Etapa basica (I-III)
    {"clave": "N25-101", "nombre": "Introduccion al Derecho", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-102", "nombre": "Derecho Romano", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-103", "nombre": "Logica", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-104", "nombre": "Evolucion de los Sistemas Juridicos Contemporaneos", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-105", "nombre": "Sociologia Juridica", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-106", "nombre": "Comunicacion Oral y Escrita", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},

    {"clave": "N25-201", "nombre": "Axiologia Juridica", "semestre": 2, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-202", "nombre": "Teoria del Estado", "semestre": 2, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-203", "nombre": "Derecho de las Personas y Familia", "semestre": 2, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-204", "nombre": "Fundamentos del Derecho Penal", "semestre": 2, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},

    {"clave": "N25-301", "nombre": "Derecho Individual del Trabajo", "semestre": 3, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-302", "nombre": "Derecho Constitucional", "semestre": 3, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-303", "nombre": "Bienes, Derechos Reales y Sucesiones", "semestre": 3, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-304", "nombre": "Delitos de Orden Comun", "semestre": 3, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25-305", "nombre": "Teoria del Proceso", "semestre": 3, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "basica", "modalidad": "presencial", "activa": True},

    # Etapa disciplinaria (IV-VI)
    {"clave": "N25-401", "nombre": "Derecho Colectivo del Trabajo", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-402", "nombre": "Derechos Humanos", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-403", "nombre": "Teoria General de las Obligaciones", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-404", "nombre": "Derecho Procesal Penal", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-405", "nombre": "Medios Alternos de Solucion de Conflictos", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},

    {"clave": "N25-501", "nombre": "Derecho Procesal del Trabajo", "semestre": 5, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-502", "nombre": "Derecho Procesal Constitucional", "semestre": 5, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-503", "nombre": "Contratos Civiles", "semestre": 5, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-504", "nombre": "Derecho Administrativo", "semestre": 5, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-505", "nombre": "Derecho Internacional Publico", "semestre": 5, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},

    {"clave": "N25-601", "nombre": "Derecho Mercantil", "semestre": 6, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-602", "nombre": "Instituciones del Derecho Procesal Constitucional", "semestre": 6, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-603", "nombre": "Derecho Procesal Civil", "semestre": 6, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-604", "nombre": "Derecho Fiscal", "semestre": 6, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-605", "nombre": "Metodologia de la Investigacion Juridica", "semestre": 6, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25-606", "nombre": "Derecho Internacional de los Derechos Humanos", "semestre": 6, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},

    # Etapa terminal (VII-VIII)
    {"clave": "N25-701", "nombre": "Derecho Procesal Mercantil", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25-702", "nombre": "Derecho Societario", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25-703", "nombre": "Interpretacion y Argumentacion Juridica", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25-704", "nombre": "Procesal Administrativo", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25-705", "nombre": "Derecho Internacional Privado", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},

    {"clave": "N25-801", "nombre": "Filosofia del Derecho", "semestre": 8, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25-802", "nombre": "Derecho Agrario", "semestre": 8, "plan_clave": "2025-2", "tipo_materia": "normal", "etapa": "terminal", "modalidad": "presencial", "activa": True},
]


NEW_PLAN_2025_2_OPTATIVA_SUBJECTS = [
    # Optativas etapa basica
    {"clave": "N25OB01", "nombre": "Etica Profesional", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB02", "nombre": "Historia del Derecho Mexicano", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB03", "nombre": "Ingles Tecnico Juridico", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB04", "nombre": "Introduccion a la Administracion de Recursos Humanos", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB05", "nombre": "Ortografia y Redaccion", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB06", "nombre": "Tecnicas de Investigacion", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB07", "nombre": "Tecnologias de la Investigacion Juridica", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB08", "nombre": "Aleman Tecnico Juridico", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB09", "nombre": "Contexto Socio Juridico en la Literatura", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB10", "nombre": "Derechos Humanos de Ninos, Ninas y Adolescentes", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB11", "nombre": "Emprendedores", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB12", "nombre": "Emprendimiento Ambiental", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},
    {"clave": "N25OB13", "nombre": "Oralidad y Lenguaje Corporal", "semestre": 1, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "basica", "modalidad": "presencial", "activa": True},

    # Optativas etapa disciplinaria
    {"clave": "N25OD01", "nombre": "Administracion Publica", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD02", "nombre": "Bioetica y Derecho", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD03", "nombre": "Criminalistica", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD04", "nombre": "Criminologia", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD05", "nombre": "Delitos Especiales", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD06", "nombre": "Derecho Aduanero", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD07", "nombre": "Derecho Ambiental", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD08", "nombre": "Derecho Burocratico", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD09", "nombre": "Derecho Constitucional Local", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD10", "nombre": "Derecho Economico", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD11", "nombre": "Derecho Electoral", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD12", "nombre": "Derecho Informatico", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD13", "nombre": "Derecho Militar", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD14", "nombre": "Derecho Parlamentario", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD15", "nombre": "Derecho Penitenciario", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD16", "nombre": "Derechos Humanos de la Ninez", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD17", "nombre": "Introduccion al Sistema Legal Estadounidense", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD18", "nombre": "Juicios Orales", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD19", "nombre": "Justicia para Adolescentes", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD20", "nombre": "Medicina Legal", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD21", "nombre": "Procedimientos Civiles Especiales", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD22", "nombre": "Propiedad Intelectual", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD23", "nombre": "Derecho del Agua", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD24", "nombre": "Derecho a la Seguridad Social", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD25", "nombre": "Italiano Tecnico Juridico", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD26", "nombre": "Principios Procesales Civiles Vinculados con el Amparo", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD27", "nombre": "Transparencia y Derecho de Acceso a la Informacion Publica", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD28", "nombre": "Derechos de los Adultos Mayores", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},
    {"clave": "N25OD29", "nombre": "Derecho Corporativo y la Empresa", "semestre": 4, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "disciplinaria", "modalidad": "presencial", "activa": True},

    # Optativas etapa terminal
    {"clave": "N25OT01", "nombre": "Seminario de Actualizacion Juridica", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT02", "nombre": "Seminario de Derecho Administrativo y Fiscal", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT03", "nombre": "Seminario de Derecho Civil", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT04", "nombre": "Seminario de Derecho Constitucional", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT05", "nombre": "Seminario de Derecho Internacional", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT06", "nombre": "Seminario de Derecho Mercantil", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT07", "nombre": "Seminario de Derecho Penal", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT08", "nombre": "Seminario de Derecho Procesal Familiar", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT09", "nombre": "Seminario de Derecho Social", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT10", "nombre": "Seminario de Estrategias de Litigacion Oral", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT11", "nombre": "Seminario de Mediacion", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT12", "nombre": "Derecho Notarial y Registral", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT13", "nombre": "Seminario de Practica Juridica I", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT14", "nombre": "Seminario de Practica Juridica II", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
    {"clave": "N25OT15", "nombre": "Derecho Migratorio Mexicano", "semestre": 7, "plan_clave": "2025-2", "tipo_materia": "optativa", "etapa": "terminal", "modalidad": "presencial", "activa": True},
]


INITIAL_SUBJECTS.extend(NEW_PLAN_2025_2_REQUIRED_SUBJECTS)
INITIAL_SUBJECTS.extend(NEW_PLAN_2025_2_OPTATIVA_SUBJECTS)

NEW_PLAN_2025_2_ALLOWED_OPTATIVA_KEYS = {
    subject["clave"] for subject in NEW_PLAN_2025_2_OPTATIVA_SUBJECTS
}

# Claves oficiales detectadas en carpetas "etapa 1" y "etapa 2" del plan 2025-1.
PLAN_2025_1_KEYS_BY_NAME = {
    # Etapa basica
    "introduccion al derecho": "48833",
    "cultura de paz": "48834",
    "instituciones civiles del derecho romano": "48835",
    "logica y ciencia": "48836",
    "herramientas digitales para el derecho": "48837",
    "comprension lectora y expresion oral y escrita": "48838",
    "filosofia juridica": "48840",
    "metodologia de la investigacion juridica": "48841",
    "personas e instituciones familiares": "48842",
    "responsabilidad social y desarrollo sustentable": "48843",
    "fundamentos del derecho penal": "48844",
    "teoria del proceso": "48845",
    "justicia digital": "48846",

    # Etapa disciplinaria
    "teoria del estado": "48847",
    "interpretacion y argumentacion juridica": "48848",
    "bienes y derechos reales": "48849",
    "derecho individual del trabajo": "48850",
    "delitos de orden comun": "48851",
    "delitos del orden comun": "48851",
    "medios alternativos de solucion de conflictos": "48852",
    "derecho constitucional": "48853",
    "sucesiones": "48854",
    "teoria de las obligaciones": "48855",
    "derecho colectivo del trabajo": "48856",
    "delitos especiales": "48857",
    "derechos humanos": "48858",
    "derecho procesal civil y familiar": "48859",
    "contratos civiles": "48860",
    "derecho procesal penal": "48862",
    "derecho administrativo": "48863",
    "derecho mercantil": "48864",
    "derecho procesal constitucional": "48865",
    "practica forense de derecho civil y familiar": "48866",
    "derecho internacional publico": "48867",
    "practica forense de derecho penal": "48868",
    "derecho fiscal": "48869",
    "derecho societario": "48870",

    # Etapa terminal
    "instituciones del derecho procesal constitucional": "48871",
    "derecho electoral": "48872",
    "derecho internacional de los derechos humanos": "48873",
    "derecho procesal administrativo": "48874",
    "derecho procesal mercantil": "48875",
    "practica forense de derecho constitucional": "48876",
    "derecho notarial y registral": "48877",
    "derecho internacional privado": "48878",
    "derecho agrario": "48879",

    # Optativas disciplinarias
    "etica profesional": "48880",
    "genero y derecho": "48881",
    "paradigmas del derecho mexicano": "48882",
    "bioetica y bioderecho": "48883",
    "derechos humanos de las ninas ninos y adolescentes": "48884",
    "criminologia": "48885",
    "derecho constitucional local": "48886",
    "estadistica juridica": "48887",
    "practica del derecho del trabajo": "48888",
    "propiedad intelectual": "48889",

    # Optativas terminales
    "derecho urbanistico": "48890",
    "practica de derechos emergentes y tecnologias": "48891",
    "criminalistica": "48892",
    "derecho y crisis climatica": "48893",
    "derecho de las empresas": "48894",
    "aspectos juridicos de la movilidad humana": "48895",
    "emprendimiento y liderazgo": "48896",
    "approach to legal justice": "48897",
    "derecho de acceso a la informacion y proteccion de datos personales": "48898",
}


def _normalize_subject_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower().replace("_", " ").replace("-", " ")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _resolve_2025_1_basic_official_key(subject_payload: dict) -> str | None:
    if subject_payload.get("tipo_materia") not in {"normal", "optativa"}:
        return None

    normalized_name = _normalize_subject_name(subject_payload.get("nombre"))
    return PLAN_2025_1_KEYS_BY_NAME.get(normalized_name)


def _find_subject_by_plan_and_normalized_name(plan_id: int, name: str):
    normalized_target = _normalize_subject_name(name)
    candidates = db.session.scalars(
        select(Materia).where(Materia.plan_estudio_id == plan_id)
    ).all()
    for subject in candidates:
        if _normalize_subject_name(subject.nombre) == normalized_target:
            return subject
    return None


def _assign_2025_2_optativa_semester(subject_payload: dict) -> None:
    """Distribuye optativas 2025-2 en los semestres donde existen espacios de optativa."""
    clave = subject_payload.get("clave", "")

    if clave.startswith("N25OB"):
        index = int(clave.replace("N25OB", ""))
        subject_payload["semestre"] = 2 if index <= 7 else 3
        return

    if clave.startswith("N25OD"):
        index = int(clave.replace("N25OD", ""))
        if index <= 10:
            subject_payload["semestre"] = 4
        elif index <= 20:
            subject_payload["semestre"] = 5
        else:
            subject_payload["semestre"] = 6
        return

    if clave.startswith("N25OT"):
        index = int(clave.replace("N25OT", ""))
        subject_payload["semestre"] = 7 if index <= 8 else 8


def seed_initial_data() -> dict:
    plan_map = _seed_plans()
    subject_count = _seed_subjects(plan_map)
    teacher_count = _seed_teachers()
    db.session.commit()

    return {
        "planes": len(plan_map),
        "materias": subject_count,
        "docentes": teacher_count,
    }


def register_seed_commands(app) -> None:
    @app.cli.command("seed-initial-data")
    @with_appcontext
    def seed_initial_data_command():
        summary = seed_initial_data()
        click.echo(
            "Seed inicial completado: "
            f"{summary['planes']} planes, {summary['materias']} materias, {summary['docentes']} docentes"
        )


def _seed_plans() -> dict[str, PlanEstudio]:
    plan_map = {}
    for plan_data in INITIAL_PLANS:
        plan = db.session.scalar(
            select(PlanEstudio).where(PlanEstudio.clave == plan_data["clave"])
        )
        if plan is None:
            plan = PlanEstudio(**plan_data)
            db.session.add(plan)
            db.session.flush()
        plan_map[plan.clave] = plan
    if "2015-2" in plan_map:
        plan_map["2025-2"] = plan_map["2015-2"]
    return plan_map


def _seed_subjects(plan_map: dict[str, PlanEstudio]) -> int:
    inserted = 0
    load_fields = ["hc", "ht", "hl", "hpc", "hcl", "he", "cr"]
    for subject_data in INITIAL_SUBJECTS:
        subject_payload = subject_data.copy()
        original_key = subject_payload["clave"]
        plan_clave = subject_payload.pop("plan_clave")
        plan = plan_map[plan_clave]

        normalized_plan_key = "2015-2" if plan_clave == "2025-2" else plan_clave

        if normalized_plan_key == "2025-1":
            official_key = _resolve_2025_1_basic_official_key(subject_payload)
            if official_key:
                subject_payload["clave"] = official_key

        for field in load_fields:
            subject_payload.setdefault(field, 0)

        if normalized_plan_key == "2025-1":
            load_data = OLD_PLAN_LOADS.get(subject_payload["clave"], {})
            if not load_data:
                load_data = OLD_PLAN_LOADS.get(original_key, {})
            subject_payload.update(load_data)

        if (
            normalized_plan_key == "2015-2"
            and subject_payload.get("tipo_materia") == "optativa"
        ):
            _assign_2025_2_optativa_semester(subject_payload)

        existing_subject = db.session.scalar(
            select(Materia).where(Materia.clave == subject_payload["clave"])
        )
        if existing_subject is None:
            existing_subject = _find_subject_by_plan_and_normalized_name(
                plan.id,
                subject_payload["nombre"],
            )

        if existing_subject is not None:
            existing_subject.clave = subject_payload["clave"]
            existing_subject.nombre = subject_payload["nombre"]
            existing_subject.semestre = subject_payload["semestre"]
            existing_subject.plan_estudio_id = plan.id
            existing_subject.tipo_materia = subject_payload["tipo_materia"]
            existing_subject.etapa = subject_payload["etapa"]
            existing_subject.modalidad = subject_payload["modalidad"]
            existing_subject.activa = subject_payload["activa"]
            existing_subject.hc = subject_payload["hc"]
            existing_subject.ht = subject_payload["ht"]
            existing_subject.hl = subject_payload["hl"]
            existing_subject.hpc = subject_payload["hpc"]
            existing_subject.hcl = subject_payload["hcl"]
            existing_subject.he = subject_payload["he"]
            existing_subject.cr = subject_payload["cr"]
            continue

        subject_payload["plan_estudio_id"] = plan.id
        db.session.add(Materia(**subject_payload))
        inserted += 1

    # Mantener consistente el plan viejo: solo optativas del listado oficial activo.
    old_plan = plan_map.get("2015-2") or plan_map.get("2025-2")
    if old_plan is not None:
        legacy_optativas = db.session.scalars(
            select(Materia)
            .where(Materia.plan_estudio_id == old_plan.id)
            .where(Materia.tipo_materia == "optativa")
            .where(Materia.clave.not_in(NEW_PLAN_2025_2_ALLOWED_OPTATIVA_KEYS))
        ).all()
        for subject in legacy_optativas:
            subject.activa = False

    return inserted


def _seed_teachers() -> int:
    inserted = 0
    for teacher_data in INITIAL_TEACHERS:
        existing_teacher = db.session.scalar(
            select(Docente).where(Docente.clave_docente == teacher_data["clave_docente"])
        )
        if existing_teacher is not None:
            continue

        db.session.add(Docente(**teacher_data))
        inserted += 1
    return inserted