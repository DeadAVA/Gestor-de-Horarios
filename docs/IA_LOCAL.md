# IA local para Sistema de Horarios UABC

## Objetivo

Agregar asistencia local con LLM para:

- Consultar informacion cargada desde PDFs
- Aprender notas y decisiones validadas por el usuario
- Extraer docentes desde texto libre
- Mantener todo el procesamiento dentro del equipo local

## Stack implementado

- Ollama como runtime local de modelos
- LangChain para orquestacion
- qwen2.5:3b como modelo de chat por defecto
- qwen2.5:7b como opcion de mayor calidad para equipos mas potentes
- nomic-embed-text como modelo de embeddings
- Almacen local de vectores en instance/ai_vector_store.json
- Historial local de chat en instance/ai_uploads/ai_chat_history.jsonl
- Aprendizaje local en instance/ai_uploads/ai_learning_log.jsonl

## Endpoints

- GET /api/ia/health
- POST /api/ia/ingestar-pdf
- POST /api/ia/chat
- POST /api/ia/aprender
- POST /api/ia/aprender-interaccion
- POST /api/ia/importar-docentes-texto

## Flujo recomendado

1. Cargar uno o mas PDFs con POST /api/ia/ingestar-pdf
2. Hacer preguntas con POST /api/ia/chat
3. Si una respuesta o criterio ya fue validado por el usuario, consolidarlo con POST /api/ia/aprender-interaccion
4. Para listas copiadas desde oficios, reportes o texto OCR, usar POST /api/ia/importar-docentes-texto con dry_run=true antes de persistir

## Ejemplos

### Salud del servicio

```http
GET /api/ia/health
```

### Ingestar PDF

Campo multipart:

- archivo: PDF

### Preguntar con contexto

```json
{
  "pregunta": "Que docentes aparecen en el archivo cargado para el grupo 251?",
  "top_k": 4
}
```

### Aprender nota del usuario

```json
{
  "texto": "El docente ABC123 solo puede impartir clases despues de las 17:00",
  "metadata": {
    "tipo": "restriccion_docente"
  }
}
```

### Aprender interaccion validada

```json
{
  "pregunta": "Cual es la regla para el docente ABC123?",
  "respuesta": "Solo puede impartir clases despues de las 17:00",
  "metadata": {
    "confirmado_por": "usuario"
  }
}
```

### Importar docentes desde texto

```json
{
  "texto": "1234 Juan Perez\n5678 Maria Lopez",
  "dry_run": true
}
```

## Instalacion local requerida

Si Ollama no esta disponible en PATH, usar su ruta instalada en Windows:

C:/Users/alanv/AppData/Local/Programs/Ollama/ollama.exe

Modelos recomendados:

```powershell
& "C:\Users\alanv\AppData\Local\Programs\Ollama\ollama.exe" pull qwen2.5:3b
& "C:\Users\alanv\AppData\Local\Programs\Ollama\ollama.exe" pull qwen2.5:7b
& "C:\Users\alanv\AppData\Local\Programs\Ollama\ollama.exe" pull nomic-embed-text
```

## Modo portable (carpeta movible)

Para que todo funcione desde una sola carpeta (sin depender de perfiles de usuario):

1. Genera el build portable con build_portable.ps1.
2. Verifica que exista ollama/ollama.exe dentro de dist/HorariosUABCPortable.
3. Ejecuta dist/HorariosUABCPortable/portable_ai_setup.ps1.
4. Esto descarga modelos en dist/HorariosUABCPortable/instance/ollama_models.

Al ejecutar HorariosUABCPortable.exe:

- El launcher configura OLLAMA_MODELS apuntando a instance/ollama_models.
- Intenta iniciar ollama serve automaticamente desde la carpeta portable en 127.0.0.1:11435.
- Si mueves la carpeta completa a otra PC, se conserva base, conocimiento y modelos.

## Limitaciones actuales

- El aprendizaje es local y controlado: registra notas, interacciones validadas e historial. No reentrena el modelo base.
- Para PDFs escaneados sin texto embebido, primero conviene OCR.
- La importacion de docentes desde IA debe ejecutarse en dry_run antes de persistir.

## Siguiente evolucion recomendada

- Integrar OCR previo para PDFs escaneados
- Agregar importacion IA de materias y grupos
- Conectar respuestas validadas con reglas de negocio y confirmacion UI
