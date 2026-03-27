# Fase 1 - Analisis y arquitectura propuesta

## 1. Estado actual del workspace

El workspace contiene un unico archivo: Horarios.html.

Hallazgos principales:

- El archivo actual es un prototipo visual de una sola pagina.
- No existe backend real, ni estructura de aplicacion, ni persistencia en SQLite.
- No existen modelos, migraciones, servicios, validadores, pruebas ni exportadores.
- La supuesta API esta simulada dentro del mismo HTML con Promise.resolve.
- Las validaciones actuales son de interfaz y no garantizan integridad de datos.
- El selector de grupo, los catalogos y los horarios estan hardcodeados.
- Se usa el termino HorariosPro y datos de ejemplo que no corresponden al dominio real de Facultad de Derecho.

## 2. Que sirve y que debe reemplazarse

### Se puede reutilizar

- La distribucion visual general de modulos: dashboard, grupos, materias, docentes, horarios y exportacion.
- La tabla semanal de horarios como referencia de presentacion para la integracion futura.
- La presencia del indicador VIR en la vista de horario como requerimiento funcional visible.
- La idea de modales y formularios como guia de UX, no como base tecnica.

### Debe reemplazarse

- Toda la logica embebida en Horarios.html.
- Toda la simulacion de API definida en el bloque script.
- Toda la persistencia simulada en memoria.
- El modelo de datos actual implicito, porque no existe de manera formal ni consistente.
- Las validaciones actuales, porque no cubren reglas criticas de negocio.
- Los datos de ejemplo de materias y docentes, porque no representan la Facultad de Derecho.

### Por que debe reemplazarse

- El HTML mezcla presentacion, datos, validaciones y transporte en un solo archivo.
- No hay trazabilidad ni consistencia para evitar duplicados, traslapes o perdida de datos.
- No hay restricciones de base de datos ni reglas centralizadas de dominio.
- No existe una API integrable de forma segura con el frontend.
- El prototipo permite estados invalidos que el sistema final debe bloquear.

## 3. Inconsistencias detectadas en el prototipo

- El formulario de grupo permite capturar semestre y plan manualmente, pero el nuevo sistema debe calcular ambos automaticamente.
- El prototipo muestra grupos como 1A, 3A, 5A, mientras que la regla real se basa en numeros como 501, 521 y 741.
- El prototipo usa materias de otras areas como Calculo y Fisica, no de Derecho.
- El prototipo muestra docentes con horas saturadas, pero no hay logica real para calcularlas.
- El prototipo ofrece exportacion PDF, pero el alcance obligatorio pide Excel y Word.
- La validacion de conflictos del docente esta simulada con una condicion fija y no con datos reales.

## 4. Objetivo arquitectonico

Construir un backend Flask modular, con persistencia real en SQLite, reglas de negocio centralizadas y API REST estable, listo para integrarse despues con el frontend existente o con uno nuevo.

Principios:

- Separacion estricta de responsabilidades.
- Reglas criticas en servicios de dominio, no en rutas.
- Validacion de entrada en capa dedicada.
- Restricciones de integridad en base de datos y en servicios.
- Respuestas JSON uniformes.
- Exportaciones desacopladas de la logica HTTP.
- Preparacion para crecimiento sin rehacer la base.

## 5. Arquitectura propuesta

Se propone una arquitectura por capas dentro de Flask.

### Capas

- app: fabrica de aplicacion, configuracion, extensiones y registro de blueprints.
- models: entidades SQLAlchemy, relaciones y restricciones.
- routes: endpoints REST por agregado funcional.
- services: reglas de negocio, calculos, validaciones de dominio y orquestacion.
- validators: validacion de payloads y normalizacion de entrada.
- exports: generadores de archivos Excel y Word.
- seeds: datos iniciales de catalogo.
- tests: pruebas unitarias y funcionales minimas.
- migrations: historial real de migraciones.

### Estructura de carpetas propuesta

```text
SistemaDeHorariosUABC/
  app/
    __init__.py
    config.py
    extensions.py
    api/
      __init__.py
      routes/
        grupos.py
        materias.py
        docentes.py
        horarios.py
        exportaciones.py
        catalogos.py
    models/
      __init__.py
      plan_estudio.py
      grupo.py
      materia.py
      docente.py
      bloque_horario.py
    services/
      response_service.py
      group_rules.py
      group_service.py
      materia_service.py
      docente_service.py
      horario_service.py
      resumen_service.py
    validators/
      grupo_validator.py
      materia_validator.py
      docente_validator.py
      horario_validator.py
    exports/
      excel_exporter.py
      word_exporter.py
    seeds/
      initial_seed.py
    utils/
      enums.py
      datetime_utils.py
      exceptions.py
  migrations/
  tests/
    conftest.py
    test_group_rules.py
    test_horario_conflicts.py
    test_docente_hours.py
  instance/
  run.py
  requirements.txt
  README.md
```

## 6. Modelo de datos

Se mantendran las entidades minimas pedidas y se agregaran restricciones explicitas.

### PlanEstudio

Campos:

- id
- clave
- nombre
- activo

Restricciones:

- clave unica
- activo con valor booleano

Relacion:

- un plan tiene muchos grupos
- un plan tiene muchas materias

### Grupo

Campos:

- id
- numero_grupo
- semestre
- plan_estudio_id
- capacidad_alumnos
- tipo_grupo
- created_at
- updated_at

Restricciones:

- numero_grupo unico
- semestre no editable manualmente desde negocio; se deriva del numero_grupo
- tipo_grupo limitado a normal o semi
- capacidad_alumnos mayor a cero

Relacion:

- un grupo pertenece a un plan
- un grupo tiene muchos bloques_horario

### Materia

Campos:

- id
- clave
- nombre
- semestre
- plan_estudio_id
- tipo_materia
- etapa
- modalidad
- activa

Restricciones:

- clave unica
- tipo_materia limitado a normal u optativa
- modalidad limitada a presencial o virtual
- semestre entre 1 y 8
- etapa nullable para materias no optativas o donde no aplique

Relacion:

- una materia pertenece a un plan
- una materia puede aparecer en muchos bloques_horario

### Docente

Campos:

- id
- clave_docente
- nombre
- activo

Restricciones:

- clave_docente unica
- activo booleano

Relacion:

- un docente puede tener muchos bloques_horario

### BloqueHorario

Campos:

- id
- grupo_id
- materia_id
- docente_id
- dia
- hora_inicio
- hora_fin
- modalidad
- created_at
- updated_at

Restricciones:

- dia limitado a lunes, martes, miercoles, jueves, viernes y sabado
- modalidad limitada a presencial o virtual
- hora_inicio menor que hora_fin
- no se resuelven todos los conflictos con una constraint SQL simple; se validan en servicio antes de persistir

Relacion:

- un bloque pertenece a un grupo
- un bloque pertenece a una materia
- un bloque pertenece a un docente

## 7. Reglas de negocio criticas

### Grupos

- El grupo se crea con numero_grupo, capacidad_alumnos y tipo_grupo.
- El semestre se calcula automaticamente.
- El plan de estudio se calcula automaticamente a partir del semestre.
- No se permiten duplicados por numero_grupo.

### Calculo de semestre

Se implementara en una funcion pura y testeable.

Primera decision tecnica:

- No codificar la regla con una cadena larga de if repetitivos.
- Usar una funcion basada en rangos configurables y excepciones para grupos especiales.

Regla base propuesta:

- 500 a 519 -> semestre 1
- 520 a 529 -> semestre 2
- 530 a 539 -> semestre 3
- 540 a 549 -> semestre 4
- 550 a 559 -> semestre 5
- 560 a 569 -> semestre 6
- 570 a 579 -> semestre 7
- 580 a 589 -> semestre 8

Grupos especiales:

- 741 -> semestre 1
- 742 -> semestre 2
- 743 -> semestre 3
- 744 -> semestre 4
- 745 -> semestre 5
- 746 -> semestre 6
- 747 -> semestre 7
- 748 -> semestre 8

Supuesto explicito:

- Se asume esa progresion para especiales porque el requerimiento dice continuar logica equivalente. Si despues hay una tabla institucional distinta, se sustituye sin tocar el resto del dominio.

### Calculo de plan

- semestres 1 a 4 -> plan 2025-1
- semestres 5 a 8 -> plan 2015-2

Esta regla se centralizara en el mismo modulo de reglas de grupo para evitar divergencias.

### Materias

- Solo se listan por grupo las materias del mismo plan y semestre.
- Si la materia es optativa y tiene etapa, el filtro considerara la etapa cuando el grupo la requiera.
- La modalidad virtual se conserva en la materia y tambien puede reflejarse en el bloque mediante el indicador VIR.

Decision:

- Mantener modalidad en Materia y en BloqueHorario.
- En Materia representa capacidad academica por catalogo.
- En BloqueHorario representa como quedo programada la imparticion.

### Docentes

- Las horas acumuladas se calcularan sumando la duracion de sus bloques.
- El maximo permitido sera 25 horas.
- Cualquier alta o actualizacion de bloque debe recalcular y bloquear si excede el limite.

### Horarios

Validaciones en servicio:

- conflicto por traslape dentro del mismo grupo
- conflicto por traslape del mismo docente en otro grupo
- limite maximo de 25 horas del docente
- un solo docente por materia dentro del mismo grupo
- misma materia con multiples bloques si mantiene el mismo docente y no hay traslape
- hora_inicio < hora_fin

Mensajes de error:

- Se construiran con contexto real de materia y docente recuperados de la base.
- Ejemplo: Conflicto con Introduccion al Derecho - Prof. Juan Perez

## 8. Contrato base de API

Formato uniforme de respuesta:

```json
{
  "success": true,
  "message": "Texto descriptivo",
  "data": {},
  "errors": []
}
```

Convencion:

- success: boolean
- message: resumen legible
- data: objeto o arreglo
- errors: lista de errores de validacion o negocio

### Grupos

- GET /api/grupos
- POST /api/grupos
- GET /api/grupos/<id>
- PATCH /api/grupos/<id>
- DELETE /api/grupos/<id>
- GET /api/grupos/<id>/resumen

Payload POST / PATCH:

```json
{
  "numero_grupo": 501,
  "capacidad_alumnos": 40,
  "tipo_grupo": "normal"
}
```

Respuesta detalle esperada:

```json
{
  "success": true,
  "message": "Grupo obtenido correctamente",
  "data": {
    "id": 1,
    "numero_grupo": 501,
    "semestre": 1,
    "plan_estudio": {
      "id": 1,
      "clave": "2025-1",
      "nombre": "Plan 2025-1"
    },
    "capacidad_alumnos": 40,
    "tipo_grupo": "normal",
    "materias_disponibles": [],
    "bloques": []
  },
  "errors": []
}
```

### Materias

- GET /api/materias
- POST /api/materias
- GET /api/materias/<id>
- PATCH /api/materias/<id>
- DELETE /api/materias/<id>
- GET /api/grupos/<id>/materias

Payload POST / PATCH:

```json
{
  "clave": "DER101",
  "nombre": "Introduccion al Derecho",
  "semestre": 1,
  "plan_estudio_id": 1,
  "tipo_materia": "normal",
  "etapa": null,
  "modalidad": "presencial",
  "activa": true
}
```

### Docentes

- GET /api/docentes
- POST /api/docentes
- GET /api/docentes/<id>
- PATCH /api/docentes/<id>
- DELETE /api/docentes/<id>
- GET /api/docentes/<id>/horas

Payload POST / PATCH:

```json
{
  "clave_docente": "DOC-001",
  "nombre": "Juan Perez",
  "activo": true
}
```

### Horarios

- GET /api/grupos/<id>/horarios
- POST /api/horarios/bloques
- DELETE /api/horarios/bloques/<id>
- POST /api/horarios/validar
- GET /api/grupos/<id>/resumen
- GET /api/planes/<id>/resumen
- GET /api/materias/sin-docente

Payload POST /api/horarios/bloques:

```json
{
  "grupo_id": 1,
  "materia_id": 10,
  "docente_id": 7,
  "dia": "lunes",
  "hora_inicio": "07:00",
  "hora_fin": "09:00",
  "modalidad": "virtual"
}
```

Respuesta esperada de bloque:

```json
{
  "success": true,
  "message": "Bloque creado correctamente",
  "data": {
    "id": 12,
    "grupo": {
      "id": 1,
      "numero_grupo": 501,
      "semestre": 1
    },
    "materia": {
      "id": 10,
      "clave": "DER101",
      "nombre": "Introduccion al Derecho"
    },
    "docente": {
      "id": 7,
      "clave_docente": "DOC-001",
      "nombre": "Juan Perez"
    },
    "dia": "lunes",
    "hora_inicio": "07:00",
    "hora_fin": "09:00",
    "modalidad": "virtual",
    "indicador": "VIR"
  },
  "errors": []
}
```

### Exportaciones

- GET /api/exportaciones/grupos/<id>/excel
- GET /api/exportaciones/grupos/<id>/word

Contenido obligatorio:

- plan de estudios
- grupo
- capacidad
- clave y nombre de materia
- clave y nombre del docente
- indicador VIR si aplica
- tabla completa del horario

## 9. Decisiones tecnicas clave

### Flask con application factory

Motivo:

- Facilita pruebas, configuraciones por entorno y registro limpio de blueprints.

### SQLAlchemy ORM

Motivo:

- Permite expresar relaciones y restricciones con claridad.
- Facilita migraciones y consultas compuestas para resumentes y filtros.

### Flask-Migrate sobre Alembic

Decision:

- Usar Flask-Migrate como capa de integracion con Alembic para simplificar el flujo en Flask.

### Validadores separados de servicios

Decision:

- validators revisan formato, campos requeridos y enums.
- services aplican reglas de negocio y consistencia transversal.

### No almacenar horas como enteros de bloque fijo

Decision:

- Guardar hora_inicio y hora_fin como tipo Time en SQLite via SQLAlchemy.
- Esto evita acoplarse a una grilla fija de una hora y permite crecer si luego aparecen bloques de 90 minutos.

### Restricciones mixtas

Decision:

- Lo que puede vivir en base de datos ira a constraints unicas o checks.
- Lo que depende de comparacion entre registros ira a servicios.

## 10. Riesgos y supuestos

### Supuestos

- Los grupos especiales 741 a 748 siguen la equivalencia 1 a 8.
- La etapa de optativas sera un valor libre corto o enumerado simple hasta recibir catalogo oficial.
- La duracion de horas docente se medira como diferencia entre hora_inicio y hora_fin.
- El frontend actual solo se tomara como referencia visual, no como base de integracion inmediata.

### Riesgos

- Si existe una normatividad institucional adicional para grupos especiales, habra que ajustar solo la tabla de reglas.
- Si hay materias que cambian de modalidad segun periodo, convendra revisar si modalidad en Materia debe ser preferencia y no restriccion.
- SQLite es correcta para esta etapa, pero tiene limites si luego aparecen concurrencia alta o multiples usuarios escribiendo al mismo tiempo.
- El filtrado de optativas por etapa depende de que el seed inicial tenga datos consistentes.

## 11. Plan de ejecucion para la Fase 2

Al recibir confirmacion, la Fase 2 ejecutara lo siguiente:

- crear estructura Flask real
- configurar SQLite, SQLAlchemy y Flask-Migrate
- implementar modelos y relaciones
- generar migracion inicial real
- dejar el proyecto arrancable desde run.py

## 12. Conclusion de Fase 1

Conclusion tecnica:

- Horarios.html se conserva unicamente como referencia visual y funcional de interfaz.
- La base tecnica actual no es reutilizable para backend ni para persistencia.
- La reconstruccion correcta debe iniciar con una nueva base Flask modular y una base SQLite normalizada.
- La propuesta anterior minimiza deuda tecnica y deja listo el camino para integracion futura con el frontend.