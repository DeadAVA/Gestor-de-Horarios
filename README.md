# Sistema de Horarios UABC

Sistema web para la gestion academica de horarios, grupos, materias y docentes, con reglas de negocio centralizadas, persistencia local en SQLite y exportaciones institucionales.

Este proyecto esta orientado a escenarios academicos donde se requiere construir, validar y exportar horarios sin depender de servicios en la nube. La aplicacion puede ejecutarse en entorno de desarrollo o distribuirse como version portable para Windows.

## Resumen

- Backend modular con Flask y SQLAlchemy.
- Base de datos SQLite local para operacion sencilla y despliegue ligero.
- API REST para grupos, materias, docentes, horarios, catalogos, respaldos y candados.
- Exportacion a Excel, Word y PDF.
- Empaquetado portable para Windows con almacenamiento local de datos.

## Objetivo del sistema

Centralizar la operacion de un gestor de horarios academicos en una base mantenible y extensible, evitando la fragilidad de prototipos monoliticos o archivos manuales dispersos. El sistema busca:

- Registrar grupos, materias y docentes con integridad de datos.
- Aplicar reglas de negocio sobre asignacion y conflictos de horario.
- Mantener trazabilidad mediante servicios, validadores y migraciones.
- Generar exportables listos para uso administrativo.
- Permitir trabajo completamente local.

## Alcance funcional

### Modulos principales

- Catalogos base y datos semilla.
- Gestion de grupos y resolucion de plan/semestre.
- Gestion de materias y modalidades.
- Gestion de docentes.
- Captura y validacion de bloques de horario.
- Exportaciones institucionales.
- Respaldos y restauracion.
- Candados operativos.

### Endpoints base

- GET /api/health
- /api/catalogos
- /api/candados
- /api/grupos
- /api/materias
- /api/docentes
- /api/horarios
- /api/exportaciones
- /api/backup

## Arquitectura

El proyecto sigue una estructura modular por capas para separar rutas HTTP, logica de dominio, persistencia, validaciones y exportaciones.

```text
SistemaDeHorariosUABC/
	app/
		api/            # Blueprints y rutas REST
		exports/        # Generadores Excel, Word, PDF e historial
		models/         # Modelos SQLAlchemy
		seeds/          # Datos iniciales
		services/       # Reglas de negocio y orquestacion
		templates/      # Interfaz HTML principal
		utils/          # Utilidades compartidas
		validators/     # Validacion de payloads
	docs/             # Documentacion tecnica y funcional
	migrations/       # Historial Alembic
	tests/            # Pruebas automatizadas
	instance/         # Datos locales en ejecucion
```

Documentacion adicional disponible en:

- docs/FASE1_ARQUITECTURA.md
- docs/exports/LOGO_INSTITUCIONAL.md

## Stack tecnico

- Python 3.13+
- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- SQLite
- openpyxl
- python-docx
- reportlab
- pytest

## Instalacion

### 1. Clonar el repositorio

```bash
git clone https://github.com/DeadAVA/Gestor-de-Horarios.git
cd Gestor-de-Horarios
```

### 2. Crear entorno virtual

En Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## Ejecucion local

```bash
python run.py
```

La aplicacion expone la interfaz principal en la raiz y la API bajo /api.

## Base de datos y migraciones

La base local se guarda en instance/horarios.db.

Aplicar migraciones:

```bash
flask --app run.py db upgrade
```

Cargar datos iniciales:

```bash
flask --app run.py seed-initial-data
```

## Pruebas

Ejecutar la suite automatizada:

```bash
pytest
```

## Exportaciones

El sistema incluye exportacion institucional para grupos:

- Excel
- Word
- PDF

Si se requiere logo institucional, puede colocarse un archivo en app/assets/institution_logo.png.

## Version portable para Windows

El proyecto puede empaquetarse como aplicacion portable que ejecuta el sistema sin instalar Python en el equipo destino.

Generar version portable:

```powershell
.\build_portable.ps1
```

Aspectos relevantes:

- La base de datos se conserva junto al ejecutable.
- El launcher puede abrir automaticamente el navegador.
- Si el puerto 5000 esta ocupado, selecciona otro puerto libre.
- El seed inicial solo corre sobre base vacia.

## Estado del proyecto

Estado actual:

- Arquitectura base definida.
- Backend modular operativo.
- Persistencia local y migraciones habilitadas.
- Exportaciones institucionales implementadas.
- Suite de pruebas presente.

## Contribucion

Las contribuciones son bienvenidas siempre que respeten la estructura del proyecto y mantengan el enfoque en reglas de negocio claras, pruebas y cambios acotados.

Consulta la guia en CONTRIBUTING.md.

## Licencia

Este repositorio se distribuye bajo la licencia MIT. Consulta el archivo LICENSE.

## Aviso

Este proyecto describe y automatiza procesos academicos; su uso institucional, nombres, logotipos o despliegue formal deben ajustarse a las politicas y autorizaciones que correspondan.