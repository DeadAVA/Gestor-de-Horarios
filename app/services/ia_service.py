import json
import math
import os
import re
import subprocess
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from app.extensions import db
from app.models import BloqueHorario, Docente, Grupo, Materia, PlanEstudio
from app.services.docente_service import DocenteService
from app.services.group_service import GroupService
from app.services.horario_service import HorarioService
from app.services.materia_service import MateriaService
from app.utils.exceptions import ConflictApiError, NotFoundApiError, ValidationApiError

_SYSTEM_PROMPT = """\
Eres el Asistente IA del Sistema de Gestión de Horarios Académicos de la UABC (Facultad de Ciencias Administrativas y Sociales).

## Sobre el sistema
El sistema permite a los coordinadores académicos gestionar:
- **Grupos**: Número de grupo, semestre (1°–8°), capacidad, tipo (`normal` = Escolarizado, `semi` = SemiEscolarizado) y plan de estudios.
- **Materias**: Clave, nombre, semestre, tipo, modalidad (presencial/virtual), plan de estudios y carga (HC, HT, HL, HPC, HCL, HE, CR).
- **Docentes**: Clave docente, nombre, estado activo/inactivo y carga acumulada.
- **Horarios**: Bloques horarios que asignan una materia y un docente a un grupo en un día y franja horaria específicos. El sistema valida que no haya conflictos (mismo docente o grupo en el mismo horario).
- **Exportaciones**: Los horarios se pueden exportar a PDF, Excel (.xlsx) y Word (.docx), así como imprimir directamente.
- **IA Local**: Servicio local con Ollama que funciona sin conexión a internet. Permite cargar PDFs para indexarlos (RAG), guardar reglas personalizadas y consultar con contexto. Los modelos usados son qwen2.5:3b (chat) y nomic-embed-text (embeddings).

## Reglas de negocio clave
- Un docente no puede tener dos bloques el mismo día y en la misma franja horaria.
- Un grupo no puede tener dos bloques el mismo día y en la misma franja horaria.
- El horario se maneja en formato de 24 horas de 07:00 a 24:00.
- Un docente se considera saturado a partir de 25 horas acumuladas.
- Las materias optativas pueden no asignarse a todos los grupos.

## Dashboard actual
El dashboard muestra, entre otros, estos componentes:
- Total de grupos
- Docentes saturados
- Materias sin asignar
- Tabla de grupos con más materias pendientes
- Tabla de docentes con mayor carga

## Tu rol
Responde SIEMPRE en español. Sé conciso, directo y útil. Cuando el usuario te haga una pregunta sobre cómo usar el sistema, explícale los pasos concretos. No inventes comportamientos ni campos que no existan en la app. Si algo no lo sabes, dilo claramente.

## Instrucciones sobre contexto RAG
Si se incluye un bloque [Contexto de documentos cargados], úsalo SOLO cuando sea directamente relevante a la pregunta del usuario. Si el contexto RAG no tiene relación con lo que el usuario pregunta, IGNÓRALO por completo y responde basándote únicamente en tu conocimiento del sistema. NUNCA respondas únicamente sobre el contenido RAG si el usuario preguntó algo diferente.

## Acciones directas
Este sistema puede ejecutar acciones directas como crear, actualizar y eliminar docentes, grupos, materias y horarios. Si el usuario pide una acción, intenta ejecutarla con los datos proporcionados. NO digas que no puedes hacerlo; el sistema SÍ puede ejecutar estas acciones.
"""

_APP_KNOWLEDGE_CONTEXT = """\
## Conocimiento operativo de la app (fuente interna)
- El dashboard usa datos reales de grupos, docentes, materias y resúmenes por grupo.
- "Total de Grupos" muestra la cantidad de grupos registrados.
- "Docentes Saturados" cuenta docentes con 25 horas o más.
- "Materias sin asignar" suma las materias sin docente en todos los grupos.
- También se muestran tablas de grupos con más pendientes y docentes con mayor carga.
- Si te piden acciones, orienta a estas secciones: Grupos, Materias, Docentes, Horarios y Exportar.
- No afirmar reglas que no estén en este contexto ni en documentos RAG.
"""

_GREETING_HINT = {
    "hola",
    "holi",
    "buenos dias",
    "buen dia",
    "buenas tardes",
    "buenas noches",
    "que onda",
    "saludos",
}

_HELP_KEYWORDS = {
    "que puedes hacer", "que sabes hacer", "en que me ayudas",
    "como me ayudas", "que haces", "como funciona",
    "que puedes hacer?", "que puedes hacer ia", "ayuda", "help",
}

# ── Verb groups for action‑intent regex (normalized / accent‑free) ──────────
_CREATE_VERBS = (
    r"agrega|agregar|anade|anadir|crea|crear|registra|registrar|"
    r"alta|dar de alta|da de alta|ingresa|ingresar|"
    r"genera|generar|haz|hazme|dame|mete|meter|pon|poner"
)
_UPDATE_VERBS = (
    r"actualiza|actualizar|edita|editar|modifica|modificar|"
    r"cambia|cambiar|corrige|corregir|ajusta|ajustar|renueva|renovar"
)
_DELETE_VERBS = (
    r"elimina|eliminar|borra|borrar|quita|quitar|"
    r"remueve|remover|saca|sacar|da de baja|dar de baja"
)
_TEACHER_NOUNS = r"docente|docento|profesor|profesora|maestro|maestra|profe"
_GROUP_NOUNS = r"grupo"
_SUBJECT_NOUNS = r"materia|asignatura"
_SCHEDULE_NOUNS = r"horario|bloque|clase"


class IAService:
    _install_process: subprocess.Popen | None = None
    _install_log_handle = None
    _install_log_path: Path | None = None

    # Modelos de chat disponibles para elegir, con descripcion comparativa.
    _CHAT_MODEL_CATALOG: list[dict] = [
        {
            "name": "qwen2.5:3b",
            "label": "Qwen 2.5 — 3B (Rápido)",
            "description": "Modelo ligero (~2 GB). Responde al instante, ideal para el día a día. Menos preciso en razonamientos complejos.",
            "pro": False,
        },
        {
            "name": "qwen2.5:7b",
            "label": "Qwen 2.5 — 7B ★ Más potente",
            "description": "Modelo avanzado (~4.7 GB). Razona mejor, entiende peticiones complejas y da respuestas más completas. Algo más lento.",
            "pro": True,
        },
    ]

    @staticmethod
    def get_status() -> dict:
        config = current_app.config
        # Cargar configuracion persistida (modelo elegido por el usuario)
        IAService._apply_persisted_settings(config)
        chat_model = config.get("AI_CHAT_MODEL")
        catalog = IAService._CHAT_MODEL_CATALOG
        active_entry = next((m for m in catalog if m["name"] == chat_model), None)
        return {
            "enabled": bool(config.get("AI_ENABLED", False)),
            "strict_local_only": bool(config.get("AI_STRICT_LOCAL_ONLY", True)),
            "ollama_base_url": config.get("AI_OLLAMA_BASE_URL"),
            "chat_model": chat_model,
            "chat_model_label": active_entry["label"] if active_entry else chat_model,
            "chat_model_pro": active_entry["pro"] if active_entry else False,
            "embed_model": config.get("AI_EMBED_MODEL"),
            "ollama_models_dir": config.get("AI_OLLAMA_MODELS_DIR"),
            "portable_setup_script": config.get("AI_PORTABLE_SETUP_SCRIPT"),
            "vector_store_path": config.get("AI_VECTOR_STORE_PATH"),
            "available_chat_models": catalog,
        }

    @staticmethod
    def set_chat_model(model_name: str) -> dict:
        """Cambia el modelo de chat activo en tiempo real y persiste la eleccion."""
        allowed = {m["name"] for m in IAService._CHAT_MODEL_CATALOG}
        if model_name not in allowed:
            raise ValidationApiError(
                "Modelo no permitido",
                [f"Opciones validas: {', '.join(sorted(allowed))}"],
            )
        config = current_app.config
        config["AI_CHAT_MODEL"] = model_name
        # Persistir en instance/ai_settings.json
        settings_path = Path(config.get("INSTANCE_PATH", "instance")) / "ai_settings.json"
        try:
            existing: dict = {}
            if settings_path.exists():
                existing = json.loads(settings_path.read_text(encoding="utf-8"))
            existing["chat_model"] = model_name
            settings_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass  # No falla si no puede escribir; la sesion igual usa el modelo correcto
        return IAService.get_status()

    @staticmethod
    def _apply_persisted_settings(config: dict) -> None:
        """Lee instance/ai_settings.json y aplica configuracion guardada si existe."""
        settings_path = Path(config.get("INSTANCE_PATH", "instance")) / "ai_settings.json"
        if not settings_path.exists():
            return
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if "chat_model" in settings and settings["chat_model"]:
                config["AI_CHAT_MODEL"] = settings["chat_model"]
        except (OSError, json.JSONDecodeError):
            pass

    @staticmethod
    def get_model_inventory() -> dict:
        config = current_app.config
        IAService._apply_persisted_settings(config)
        required_models = [config["AI_CHAT_MODEL"], config["AI_EMBED_MODEL"]]
        optional_models = ["qwen2.5:7b"]
        models_dir = Path(config["AI_OLLAMA_MODELS_DIR"])
        server_models = IAService._list_models_from_ollama_api(config.get("AI_OLLAMA_BASE_URL", ""))

        installed = []
        for model_name in [*required_models, *optional_models]:
            local_present = IAService._model_manifest_exists(models_dir, model_name)
            server_present = model_name in server_models
            installed.append(
                {
                    "name": model_name,
                    "required": model_name in required_models,
                    "present": local_present or server_present,
                    "present_local": local_present,
                    "present_server": server_present,
                }
            )

        installation = IAService._get_installation_status()
        return {
            "models_dir": models_dir.as_posix(),
            "portable_setup_script": config["AI_PORTABLE_SETUP_SCRIPT"],
            "available": Path(config["AI_PORTABLE_SETUP_SCRIPT"]).exists(),
            "installed_models": installed,
            "missing_required_models": [item["name"] for item in installed if item["required"] and not item["present"]],
            "installation": installation,
        }

    @staticmethod
    def start_portable_model_install(force: bool = False) -> dict:
        status = IAService._get_installation_status()
        if status["running"]:
            return status

        inventory = IAService.get_model_inventory()
        if inventory["missing_required_models"] == [] and not force:
            return inventory["installation"]

        script_path = Path(current_app.config["AI_PORTABLE_SETUP_SCRIPT"])
        if not script_path.exists():
            raise ValidationApiError(
                "Setup portable no disponible",
                [f"No se encontro el script {script_path.name} en la carpeta de la app"],
            )

        log_path = Path(current_app.config["AI_UPLOAD_DIR"]) / "ai_model_install.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")
        log_handle = log_path.open("a", encoding="utf-8")

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            cwd=str(script_path.parent),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
            env=os.environ.copy(),
        )

        IAService._install_process = process
        IAService._install_log_handle = log_handle
        IAService._install_log_path = log_path
        return IAService._get_installation_status()

    @staticmethod
    def ingest_pdf(file_path: str, source_name: str | None = None) -> dict:
        if not file_path.lower().endswith(".pdf"):
            raise ValidationApiError("Archivo invalido", ["Solo se permiten archivos PDF"])

        loader = PyPDFLoader(file_path)
        documents = loader.load()
        if not documents:
            raise ValidationApiError("No se detecto contenido", ["El PDF no contiene texto utilizable"])

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=900,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(documents)

        texts = [chunk.page_content.strip() for chunk in chunks if chunk.page_content and chunk.page_content.strip()]
        if not texts:
            raise ValidationApiError("No se detecto contenido", ["No fue posible extraer texto del PDF"])

        try:
            embeddings = IAService._get_embeddings_client().embed_documents(texts)
        except Exception as error:  # noqa: BLE001
            raise ValidationApiError(
                "No fue posible indexar el PDF",
                [IAService._format_runtime_error(error)],
            )
        store = IAService._load_vector_store()

        for idx, text in enumerate(texts):
            metadata = dict(chunks[idx].metadata or {})
            metadata["source"] = source_name or Path(file_path).name
            metadata["doc_type"] = "pdf"
            store["documents"].append(
                {
                    "id": str(uuid4()),
                    "text": text,
                    "metadata": metadata,
                    "embedding": embeddings[idx],
                }
            )

        IAService._save_vector_store(store)
        return {
            "documentos_previos": store.get("count_before", 0),
            "documentos_agregados": len(texts),
            "documentos_totales": len(store["documents"]),
            "origen": source_name or Path(file_path).name,
        }

    @staticmethod
    def ask_with_context(
        question: str,
        top_k: int | None = None,
        history: list[dict] | None = None,
    ) -> dict:
        question = (question or "").strip()
        if not question:
            raise ValidationApiError("Pregunta invalida", ["El campo pregunta es obligatorio"])

        quick_result = IAService._handle_quick_request(question)
        if quick_result is not None:
            IAService._append_chat_log({"question": question, "answer": quick_result["respuesta"], "sources": []})
            return quick_result

        # --- RAG: buscar documentos relevantes (si los hay) ---
        effective_top_k = top_k if top_k is not None else int(current_app.config.get("AI_TOP_K", 4))
        store = IAService._load_vector_store()
        docs = store["documents"]
        ranked_docs = []
        sources = []

        if docs and effective_top_k > 0:
            try:
                query_embedding = IAService._get_embeddings_client().embed_query(question)
                ranked_docs = IAService._rank_documents(query_embedding, docs, effective_top_k)
                ranked_docs = IAService._filter_ranked_docs_for_question(question, ranked_docs)
                for entry in ranked_docs:
                    metadata = entry.get("metadata", {})
                    sources.append({
                        "source": metadata.get("source", "desconocido"),
                        "page": metadata.get("page", "?"),
                        "score": round(entry["score"], 4),
                    })
            except Exception:  # noqa: BLE001
                # Si falla embeddings, continúa sin RAG
                ranked_docs = []

        # --- Construir prompt con mensajes ---
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        messages = [SystemMessage(content=_SYSTEM_PROMPT)]
        messages.append(SystemMessage(content=_APP_KNOWLEDGE_CONTEXT))

        # Contexto vivo de la BD (grupos, docentes activos) para que el modelo pueda razonar
        db_ctx = IAService._build_db_context()
        if db_ctx:
            messages.append(SystemMessage(content=db_ctx))

        # Historial de conversación previo (limitar a últimos 6 turnos para evitar contaminación)
        recent_history = (history or [])[-6:]
        for turn in recent_history:
            role = turn.get("role", "")
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        # Contexto RAG opcional — inyectar como SystemMessage separado (no dentro del mensaje del usuario)
        if ranked_docs:
            context_blocks = [
                f"Fuente: {entry.get('metadata', {}).get('source', '?')} (pag. {entry.get('metadata', {}).get('page', '?')})\n{entry.get('text', '')}"
                for entry in ranked_docs
            ]
            context_text = "\n\n".join(context_blocks)
            rag_note = (
                "[Contexto de documentos cargados — usa SOLO si es relevante a la pregunta del usuario]\n"
                + context_text
            )
            messages.append(SystemMessage(content=rag_note))

        messages.append(HumanMessage(content=question))

        llm = IAService._get_chat_client()
        try:
            response = llm.invoke(messages)
        except Exception as error:  # noqa: BLE001
            raise ValidationApiError(
                "No fue posible generar respuesta con IA",
                [IAService._format_runtime_error(error)],
            )

        answer = response.content if hasattr(response, "content") else str(response)
        IAService._append_chat_log({"question": question, "answer": answer, "sources": sources})
        return {
            "respuesta": answer,
            "fuentes": sources,
            "contexto_usado": len(ranked_docs),
        }

    @staticmethod
    def _handle_quick_request(question: str) -> dict | None:
        normalized = IAService._normalize_text(question)

        # ── Greeting detection (flexible) ──────────────────────────
        is_greeting = normalized in _GREETING_HINT or any(
            normalized.startswith(g + " ") or normalized.startswith(g + ",")
            for g in _GREETING_HINT if len(g) > 3
        )
        # Check if also asking for help in the same message
        is_help = normalized in _HELP_KEYWORDS or any(kw in normalized for kw in _HELP_KEYWORDS)

        if is_help:
            return IAService._help_response()

        if is_greeting:
            return {
                "respuesta": (
                    "Hola, estoy listo para ayudarte.\n"
                    "Puedes pedirme consultas o acciones directas como crear/actualizar/eliminar docentes, grupos, materias y horarios.\n"
                    "Si quieres ver ejemplos, escribe: que puedes hacer"
                ),
                "fuentes": [],
                "contexto_usado": 0,
            }

        # ── Regex‑based action detection ───────────────────────────
        action_result = IAService._try_execute_platform_action(question)
        if action_result is not None:
            return action_result

        # ── LLM fallback: re‑phrase as standard command ────────────
        action_result = IAService._try_llm_action_detection(question)
        return action_result

    @staticmethod
    def _help_response() -> dict:
        return {
            "respuesta": (
                "Puedo ayudarte de dos formas: consultar y ejecutar acciones claras dentro de la plataforma.\n\n"
                "Consultas:\n"
                "- Explicar cómo usar grupos, materias, docentes, horarios y exportaciones\n"
                "- Responder con contexto de documentos PDF cargados\n"
                "- Revisar reglas como conflictos, carga docente y disponibilidad\n\n"
                "Acciones directas soportadas:\n"
                "- Agregar docente: 'agrega docente nombre Juan Perez clave JP001'\n"
                "- Actualizar docente: 'actualiza docente clave JP001 nombre Juan P. activo si'\n"
                "- Eliminar docente: 'elimina docente clave JP001'\n"
                "- Agregar grupo: 'crea grupo 501 plan 2025-1 capacidad 40 tipo normal'\n"
                "- Actualizar grupo: 'actualiza grupo 501 capacidad 45 tipo semi plan 2015-2'\n"
                "- Eliminar grupo: 'elimina grupo 501'\n"
                "- Agregar materia: 'crea materia clave ADM101 nombre Administracion semestre 3 tipo normal modalidad presencial plan 2025-1 hc 2 ht 2 cr 6'\n"
                "- Actualizar materia: 'actualiza materia clave ADM101 nombre Admin I modalidad virtual'\n"
                "- Eliminar materia: 'elimina materia clave ADM101'\n"
                "- Agregar horario: 'agrega horario grupo 501 materia ADM101 docente JP001 dia lunes 7 a 9 modalidad presencial'\n\n"
                "- Actualizar horario: 'actualiza horario bloque 12 dia martes 8 a 10 modalidad virtual'\n"
                "- Eliminar horario: 'elimina horario bloque 12'\n\n"
                "Si una instrucción no trae los datos mínimos, te diré exactamente qué falta."
            ),
            "fuentes": [],
            "contexto_usado": 0,
        }

    @staticmethod
    def _try_execute_platform_action(question: str) -> dict | None:
        normalized = IAService._normalize_text(question)

        try:
            # Creates — schedule PRIMERO: contiene grupo+materia+docente, confunde con teacher si va al final
            if IAService._looks_like_create_schedule(normalized):
                return IAService._execute_create_schedule(question)

            if IAService._looks_like_create_teacher(normalized):
                return IAService._execute_create_teacher(question)

            if IAService._looks_like_create_group(normalized):
                return IAService._execute_create_group(question)

            if IAService._looks_like_create_subject(normalized):
                return IAService._execute_create_subject(question)
            if IAService._looks_like_update_teacher(normalized):
                return IAService._execute_update_teacher(question)

            if IAService._looks_like_update_group(normalized):
                return IAService._execute_update_group(question)

            if IAService._looks_like_update_subject(normalized):
                return IAService._execute_update_subject(question)

            if IAService._looks_like_update_schedule(normalized):
                return IAService._execute_update_schedule(question)

            if IAService._looks_like_create_teacher(normalized):
                return IAService._execute_create_teacher(question)

            if IAService._looks_like_create_group(normalized):
                return IAService._execute_create_group(question)

            if IAService._looks_like_create_subject(normalized):
                return IAService._execute_create_subject(question)

            if IAService._looks_like_create_schedule(normalized):
                return IAService._execute_create_schedule(question)

            # Fallback conversacional cuando no mencionan explícitamente "grupo"
            # pero usan pronombre sobre la última entidad en contexto.
            if re.search(r"\b(modificalo|cambialo|editalo|ajustalo|actualizalo)\b", normalized) and re.search(
                r"\b(capacidad|tipo|plan|numero)\b",
                normalized,
            ):
                return IAService._execute_update_group(question)
        except SQLAlchemyError as error:
            raise ValidationApiError(
                "No fue posible ejecutar la accion solicitada",
                [f"Error de base de datos: {error.__class__.__name__}"],
            ) from error

        return None

    @staticmethod
    def _try_llm_action_detection(question: str) -> dict | None:
        """Fallback: ask the LLM to re-phrase as a standard command when regex didn't match."""
        normalized = IAService._normalize_text(question)

        # Only try if the question mentions an entity AND has action/data hints
        has_entity = bool(re.search(
            rf"\b({_TEACHER_NOUNS}|{_GROUP_NOUNS}|{_SUBJECT_NOUNS}|{_SCHEDULE_NOUNS})\b",
            normalized,
        ))
        has_action_data = bool(re.search(
            r"\b(clave|nombre|capacidad|semestre|plan|dia|hora|nuev[oa]|alta|"
            r"activo|numero|puedes|podrias|necesito|quiero|ocupo|hazme|dame|"
            r"meteme|llamad[oa]|con\s+clave)\b",
            normalized,
        ))
        if not has_entity or not has_action_data:
            return None

        llm = IAService._get_chat_client()
        classification_prompt = (
            "Eres un clasificador de intenciones. Tu UNICA funcion es reescribir "
            "la solicitud del usuario en formato estandar.\n\n"
            f"Solicitud del usuario: \"{question}\"\n\n"
            "Si el usuario quiere CREAR un docente, responde UNICAMENTE:\n"
            "agrega docente nombre [NOMBRE] clave [CLAVE]\n\n"
            "Si quiere CREAR un grupo:\n"
            "crea grupo [NUMERO] plan [PLAN] capacidad [CAP] tipo [TIPO]\n\n"
            "Si quiere ACTUALIZAR un docente:\n"
            "actualiza docente clave [CLAVE] nombre [NOMBRE] activo [si/no]\n\n"
            "Si quiere ELIMINAR un docente:\n"
            "elimina docente clave [CLAVE]\n\n"
            "Si quiere CREAR una materia:\n"
            "crea materia clave [CLAVE] nombre [NOMBRE] semestre [N] tipo [TIPO] modalidad [MOD] plan [PLAN]\n\n"
            "Si quiere CREAR un horario:\n"
            "agrega horario grupo [NUM] materia [CLAVE] docente [CLAVE] dia [DIA] [INICIO] a [FIN] modalidad [MOD]\n\n"
            "Si NO es una accion sobre docente/grupo/materia/horario, responde UNICAMENTE: NO_ACTION\n\n"
            "IMPORTANTE: Responde SOLO con el formato indicado. Sin explicaciones."
        )

        try:
            response = llm.invoke(classification_prompt)
            content = response.content if hasattr(response, "content") else str(response)
            content = content.strip()

            # Clean markdown fences if present
            if content.startswith("```"):
                content = content.strip("`").strip()

            if "NO_ACTION" in content.upper():
                return None

            # Try to execute the reformulated request through existing regex+extraction
            result = IAService._try_execute_platform_action(content)
            return result
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _looks_like_create_teacher(normalized: str) -> bool:
        if re.search(
            rf"\b({_CREATE_VERBS})\b.*\b({_TEACHER_NOUNS})\b",
            normalized,
        ):
            return True
        # "quiero/necesito un docente nuevo", "nuevo docente con clave ..."
        if re.search(
            rf"\b(quiero|necesito|ocupo)\b.*\b({_TEACHER_NOUNS})\b.*\b(nuev[oa]|con clave|nombre)\b",
            normalized,
        ):
            return True
        if re.search(
            rf"\bnuev[oa]\s+({_TEACHER_NOUNS})\b",
            normalized,
        ):
            return True
        return False

    @staticmethod
    def _looks_like_create_group(normalized: str) -> bool:
        if re.search(rf"\b({_CREATE_VERBS})\b.*\b({_GROUP_NOUNS})\b", normalized):
            return True
        if re.search(rf"\b(quiero|necesito|ocupo)\b.*\b({_GROUP_NOUNS})\b.*\b(nuev[oa]|capacidad|plan|semestre)\b", normalized):
            return True
        return False

    @staticmethod
    def _looks_like_create_subject(normalized: str) -> bool:
        if re.search(rf"\b({_CREATE_VERBS})\b.*\b({_SUBJECT_NOUNS})\b", normalized):
            return True
        if re.search(rf"\b(quiero|necesito|ocupo)\b.*\b({_SUBJECT_NOUNS})\b.*\b(nuev[oa]|clave|nombre)\b", normalized):
            return True
        return False

    @staticmethod
    def _looks_like_create_schedule(normalized: str) -> bool:
        # Patrón 1: verbo + "horario/bloque/clase" explícito
        if re.search(rf"\b({_CREATE_VERBS}|asigna|asignar|programa|programar)\b.*\b({_SCHEDULE_NOUNS})\b", normalized):
            return True
        # Patrón 2: "asignar" + materia + docente (sin necesitar la palabra "horario")
        if re.search(r"\b(asigna|asignar|pon|poner|agrega|agregar|programa|programar)\b", normalized) and re.search(
            r"\b(materia|asignatura)\b", normalized
        ) and re.search(r"\b(docente|profesor|profesora|maestro|maestra|profe)\b", normalized):
            return True
        return False

    @staticmethod
    def _looks_like_update_teacher(normalized: str) -> bool:
        return bool(re.search(rf"\b({_UPDATE_VERBS})\b.*\b({_TEACHER_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_update_group(normalized: str) -> bool:
        return bool(re.search(rf"\b({_UPDATE_VERBS})\b.*\b({_GROUP_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_update_subject(normalized: str) -> bool:
        return bool(re.search(rf"\b({_UPDATE_VERBS})\b.*\b({_SUBJECT_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_update_schedule(normalized: str) -> bool:
        return bool(re.search(rf"\b({_UPDATE_VERBS})\b.*\b({_SCHEDULE_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_delete_teacher(normalized: str) -> bool:
        return bool(re.search(rf"\b({_DELETE_VERBS})\b.*\b({_TEACHER_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_delete_group(normalized: str) -> bool:
        return bool(re.search(rf"\b({_DELETE_VERBS})\b.*\b({_GROUP_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_delete_subject(normalized: str) -> bool:
        return bool(re.search(rf"\b({_DELETE_VERBS})\b.*\b({_SUBJECT_NOUNS})\b", normalized))

    @staticmethod
    def _looks_like_delete_schedule(normalized: str) -> bool:
        return bool(re.search(rf"\b({_DELETE_VERBS})\b.*\b({_SCHEDULE_NOUNS})\b", normalized))

    @staticmethod
    def _execute_create_teacher(question: str) -> dict:
        key_match = re.search(r"clave(?: docente)?\s*[:=]?\s*([A-Za-z0-9_-]+)", question, re.IGNORECASE)
        # Try multiple name-extraction patterns in order of specificity
        name_match = re.search(
            r"nombre\s*[:=]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .'-]+?)(?=\s+clave\b|\s+activo\b|$)",
            question,
            re.IGNORECASE,
        )
        if name_match is None:
            name_match = re.search(
                r"(?:llamad[oa]|de nombre)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]+?)(?=\s+(?:con\s+)?clave\b|\s+activo\b|$)",
                question,
                re.IGNORECASE,
            )
        if name_match is None:
            name_match = re.search(
                r"(?:docente|docento|profesor|profesora|maestro|maestra|profe)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ .'-]+?)(?=\s+(?:con\s+)?clave\b|$)",
                question,
                re.IGNORECASE,
            )
        # "clave X nombre Y" — nombre at tail
        if name_match is None:
            name_match = re.search(
                r"nombre\s*[:=]?\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .'-]+?)\s*$",
                question,
                re.IGNORECASE,
            )

        missing = []
        if key_match is None:
            missing.append("clave_docente")
        if name_match is None:
            missing.append("nombre")
        if missing:
            return IAService._missing_fields_response(
                "crear docente",
                missing,
                "Ejemplo: agrega docente nombre Juan Perez clave JP001",
            )

        payload = {
            "clave_docente": key_match.group(1).strip(),
            "nombre": name_match.group(1).strip(),
            "activo": True,
        }
        created = DocenteService.create_teacher(payload)
        return {
            "respuesta": f"Docente creado correctamente: {created['nombre']} ({created['clave_docente']}).",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "crear_docente", "resultado": created},
        }

    @staticmethod
    def _execute_create_group(question: str) -> dict:
        normalized = IAService._normalize_text(question)
        group_match = re.search(r"\bgrupo\s+(\d{3,})\b", question, re.IGNORECASE)
        # Soporta frases como: "que sea 509", "numero 509", "#509"
        if group_match is None:
            group_match = re.search(r"\b(?:sea|numero|num|no\.?|#)\s*(\d{3,})\b", normalized)

        capacity_match = re.search(r"\bcapacidad\s*[:=]?\s*(\d+)\b", question, re.IGNORECASE)
        plan_match = re.search(r"\bplan\s*[:=]?\s*(2025-1|2015-2|2025-2)\b", question, re.IGNORECASE)
        type_match = re.search(r"\btipo\s*[:=]?\s*(normal|semi|escolarizado|semiescolarizado)\b", question, re.IGNORECASE)

        # Si no viene 'tipo ...', detectar por palabra suelta en la frase.
        inferred_type = None
        if type_match is None:
            if re.search(r"\b(semiescolarizado|semi)\b", normalized):
                inferred_type = "semi"
            elif re.search(r"\b(escolarizado|normal)\b", normalized):
                inferred_type = "normal"

        # Modo defaults si el usuario lo pide explícitamente.
        wants_defaults = any(token in normalized for token in ["default", "por defecto", "predeterminado"])

        if capacity_match is None and wants_defaults:
            capacity_value = 40
        else:
            capacity_value = int(capacity_match.group(1)) if capacity_match else None

        if plan_match is None and wants_defaults:
            plan_value = "2025-1"
        else:
            plan_value = plan_match.group(1) if plan_match else None

        if type_match is not None:
            type_value = type_match.group(1)
        elif inferred_type is not None:
            type_value = inferred_type
        elif wants_defaults:
            type_value = "normal"
        else:
            type_value = None

        missing = []
        if group_match is None:
            missing.append("numero_grupo")
        if capacity_value is None:
            missing.append("capacidad_alumnos")
        if plan_value is None:
            missing.append("plan_estudio_clave")
        if type_value is None:
            missing.append("tipo_grupo")
        if missing:
            return IAService._missing_fields_response(
                "crear grupo",
                missing,
                "Ejemplo: crea grupo 501 plan 2025-1 capacidad 40 tipo normal",
            )

        raw_type = IAService._normalize_text(type_value)
        group_type = "semi" if raw_type.startswith("semi") else "normal"
        group_number = int(group_match.group(1))

        # Respuesta idempotente: si ya existe, no falla, informa el estado actual.
        existing_group = db.session.scalar(select(Grupo).where(Grupo.numero_grupo == group_number))
        if existing_group is not None:
            return {
                "respuesta": (
                    f"El grupo {existing_group.numero_grupo} ya existe. "
                    f"Configuracion actual: capacidad {existing_group.capacidad_alumnos}, "
                    f"tipo {existing_group.tipo_grupo}, semestre {existing_group.semestre}."
                ),
                "fuentes": [],
                "contexto_usado": 0,
                "accion_ejecutada": {
                    "tipo": "grupo_existente",
                    "resultado": {"id": existing_group.id, "numero_grupo": existing_group.numero_grupo},
                },
            }

        payload = {
            "numero_grupo": group_number,
            "capacidad_alumnos": capacity_value,
            "plan_estudio_clave": plan_value,
            "tipo_grupo": group_type,
        }
        created = GroupService.create_group(payload)
        return {
            "respuesta": (
                f"Grupo creado correctamente: {created['numero_grupo']} · "
                f"{created['semestre']}° semestre · {created['plan_estudio']['clave']}"
            ),
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "crear_grupo", "resultado": created},
        }

    @staticmethod
    def _execute_create_subject(question: str) -> dict:
        data = IAService._extract_keyword_values(question)
        plan_key = data.get("plan") or data.get("plan_estudio") or data.get("plan_estudio_clave")
        plan = IAService._find_plan_by_key(plan_key) if plan_key else None

        payload = {
            "clave": data.get("clave"),
            "nombre": data.get("nombre"),
            "semestre": data.get("semestre"),
            "tipo_materia": IAService._normalize_subject_type(data.get("tipo") or data.get("tipo_materia")),
            "modalidad": IAService._normalize_modality(data.get("modalidad")),
            "plan_estudio_id": plan.id if plan else None,
            "hc": data.get("hc", 0),
            "ht": data.get("ht", 0),
            "hl": data.get("hl", 0),
            "hpc": data.get("hpc", 0),
            "hcl": data.get("hcl", 0),
            "he": data.get("he", 0),
            "cr": data.get("cr", 0),
        }

        missing = [
            name for name, value in payload.items()
            if name in {"clave", "nombre", "semestre", "tipo_materia", "modalidad", "plan_estudio_id"} and value in (None, "")
        ]
        if missing:
            return IAService._missing_fields_response(
                "crear materia",
                missing,
                "Ejemplo: crea materia clave ADM101 nombre Administracion semestre 3 tipo normal modalidad presencial plan 2025-1 hc 2 ht 2 cr 6",
            )

        created = MateriaService.create_subject(payload)
        return {
            "respuesta": f"Materia creada correctamente: {created['clave']} - {created['nombre']}.",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "crear_materia", "resultado": created},
        }

    @staticmethod
    def _execute_create_schedule(question: str) -> dict:
        normalized = IAService._normalize_text(question)

        # Grupo
        group_match = re.search(r"\bgrupo\s+(\d{3,})\b", question, re.IGNORECASE)

        # Días — captura todos (lunes y jueves → ["lunes", "jueves"])
        day_list = re.findall(r"\b(lunes|martes|miercoles|jueves|viernes|sabado)\b", normalized)

        # Hora de inicio y fin
        time_match = re.search(r"\b(\d{1,2})(?::00)?\s*(?:a|-|hasta)\s*(\d{1,2})(?::00)?\b", normalized)

        # Modalidad — default presencial si no se especifica
        modality_match = re.search(r"\b(presencial|virtual)\b", normalized)
        modality = modality_match.group(1) if modality_match else "presencial"

        # Materia — soporta "en la materia X" y termina antes de "al docente", "docente", "en los dias", etc.
        subject_match = re.search(
            r"\b(?:en\s+(?:la|el)\s+)?materia\s+([A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ ._-]+?)"
            r"(?=\s+(?:al\s+)?(?:docente|profesor|profesora|maestro|maestra|profe)\b"
            r"|\s+(?:en\s+(?:los?\s+)?)?d[ií]as?\b"
            r"|\s+(?:en\s+el\s+)?grupo\b|\s+modalidad\b"
            r"|\s+\d{1,2}(?::00)?\s*(?:a|-|hasta)|$)",
            question,
            re.IGNORECASE,
        )

        # Docente — prioridad: buscar por clave primero, luego por nombre
        teacher: Docente | None = None
        teacher_error: str | None = None

        clave_match = re.search(r"\bcon\s+clave\s+([A-Za-z0-9_-]+)\b", question, re.IGNORECASE)
        if clave_match is None:
            clave_match = re.search(r"\bclave\s+([A-Za-z0-9_-]+)\b", question, re.IGNORECASE)
        if clave_match:
            try:
                teacher = IAService._find_teacher(clave_match.group(1).strip())
            except ValidationApiError as exc:
                teacher_error = exc.message

        if teacher is None:
            teacher_name_match = re.search(
                r"\b(?:al\s+)?(?:docente|profesor|profesora|maestro|maestra|profe)\s+"
                r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ ._'-]+?)"
                r"(?=\s+con\s+clave\b|\s+clave\b"
                r"|\s+(?:en\s+(?:los?\s+)?)?d[ií]as?\b"
                r"|\s+(?:en\s+el\s+)?grupo\b|\s+modalidad\b"
                r"|\s+\d{1,2}(?::00)?\s*(?:a|-|hasta)|$)",
                question,
                re.IGNORECASE,
            )
            if teacher_name_match:
                try:
                    teacher = IAService._find_teacher(teacher_name_match.group(1).strip())
                except ValidationApiError as exc:
                    teacher_error = exc.message

        # Validar campos obligatorios
        missing = []
        if group_match is None:
            missing.append("grupo")
        if subject_match is None:
            missing.append("materia")
        if teacher is None and teacher_error is None:
            missing.append("docente")
        if not day_list:
            missing.append("dia")
        if time_match is None:
            missing.append("hora_inicio y hora_fin")
        if missing:
            return IAService._missing_fields_response(
                "crear horario",
                missing,
                "Ejemplo: agrega horario grupo 501 materia ADM101 docente JP001 dia lunes 7 a 9 modalidad presencial",
            )

        if teacher is None:
            raise ValidationApiError("Docente no encontrado", [teacher_error or "Verifica la clave o nombre del docente"])

        group = db.session.scalar(select(Grupo).where(Grupo.numero_grupo == int(group_match.group(1))))
        if group is None:
            raise ValidationApiError("Grupo no encontrado", [f"No existe el grupo {group_match.group(1)}"])

        subject_token = subject_match.group(1).strip()
        subject = IAService._find_subject_for_group(group.id, subject_token)
        start_hour = int(time_match.group(1))
        end_hour = int(time_match.group(2))

        # Crear un bloque por cada día indicado
        created_blocks: list[dict] = []
        day_errors: list[str] = []
        for day in day_list:
            payload = {
                "group_id": group.id,
                "materia_id": subject.id,
                "docente_id": teacher.id,
                "dia": IAService._normalize_day(day),
                "hora_inicio": f"{start_hour:02d}:00",
                "hora_fin": f"{end_hour:02d}:00",
                "modalidad": IAService._normalize_modality(modality),
            }
            try:
                created_blocks.append(HorarioService.create_block(payload))
            except (ConflictApiError, ValidationApiError) as exc:
                day_errors.append(f"{day}: {exc.message}")

        if not created_blocks:
            raise ValidationApiError("No se pudo crear ningún bloque", day_errors)

        days_str = ", ".join(b["dia"] for b in created_blocks)
        s = "s" if len(created_blocks) > 1 else ""
        respuesta = (
            f"Bloque{s} creado{s} correctamente: grupo {group.numero_grupo}, "
            f"{subject.nombre}, docente {teacher.nombre}, "
            f"dia{s}: {days_str} {created_blocks[0]['hora_inicio']}-{created_blocks[0]['hora_fin']}."
        )
        if day_errors:
            respuesta += f" Advertencia — no se pudo crear: {'; '.join(day_errors)}"

        return {
            "respuesta": respuesta,
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "crear_horario", "resultado": created_blocks},
        }

    @staticmethod
    def _execute_update_teacher(question: str) -> dict:
        teacher = IAService._find_teacher_by_ref(question)
        data = IAService._extract_keyword_values(question)
        payload: dict[str, Any] = {}
        if data.get("nombre"):
            payload["nombre"] = data["nombre"]

        key_match = re.search(r"(?:nueva\s+)?clave(?: docente)?\s*[:=]?\s*([A-Za-z0-9_-]+)", question, re.IGNORECASE)
        if key_match:
            payload["clave_docente"] = key_match.group(1).strip()

        active_match = re.search(r"\bactivo\s*[:=]?\s*(si|sí|no|true|false|1|0)\b", IAService._normalize_text(question))
        if active_match:
            payload["activo"] = active_match.group(1) in {"si", "sí", "true", "1"}

        if not payload:
            return IAService._missing_fields_response(
                "actualizar docente",
                ["al menos un campo a actualizar (nombre, clave_docente o activo)"],
                "Ejemplo: actualiza docente clave JP001 nombre Juan Perez activo si",
            )

        updated = DocenteService.update_teacher(teacher.id, payload)
        return {
            "respuesta": f"Docente actualizado correctamente: {updated['nombre']} ({updated['clave_docente']}).",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "actualizar_docente", "resultado": updated},
        }

    @staticmethod
    def _execute_delete_teacher(question: str) -> dict:
        confirmation = IAService._require_delete_confirmation(question, "docente")
        if confirmation is not None:
            return confirmation

        teacher = IAService._find_teacher_by_ref(question)
        teacher_name = teacher.nombre
        teacher_key = teacher.clave_docente
        DocenteService.delete_teacher(teacher.id)
        return {
            "respuesta": f"Docente eliminado correctamente: {teacher_name} ({teacher_key}).",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "eliminar_docente", "resultado": {"id": teacher.id}},
        }

    @staticmethod
    def _execute_update_group(question: str) -> dict:
        try:
            group = IAService._find_group_by_ref(question)
        except ValidationApiError:
            normalized = IAService._normalize_text(question)
            # Fallback conversacional: "modificalo", "cambialo" sobre el ultimo grupo creado.
            if re.search(r"\b(modificalo|cambialo|editalo|ajustalo|actualizalo)\b", normalized):
                group = db.session.scalar(select(Grupo).order_by(Grupo.created_at.desc()))
                if group is None:
                    raise ValidationApiError(
                        "No hay grupos para actualizar",
                        ["Primero crea un grupo o indica 'grupo <numero>'"],
                    )
            else:
                raise

        payload: dict[str, Any] = {}

        number_match = re.search(r"(?:nuevo\s+)?numero(?:_grupo)?\s*[:=]?\s*(\d{3,})\b", question, re.IGNORECASE)
        if number_match:
            payload["numero_grupo"] = int(number_match.group(1))

        capacity_match = re.search(r"\bcapacidad\s*[:=]?\s*(\d+)\b", question, re.IGNORECASE)
        if capacity_match:
            payload["capacidad_alumnos"] = int(capacity_match.group(1))
        else:
            # Soporta frases como "que solo tenga capacidad de 10"
            capacity_fallback = re.search(r"\bcapacidad\s+(?:de\s+)?(\d+)\b", IAService._normalize_text(question))
            if capacity_fallback:
                payload["capacidad_alumnos"] = int(capacity_fallback.group(1))

        type_match = re.search(r"\btipo\s*[:=]?\s*(normal|semi|escolarizado|semiescolarizado)\b", question, re.IGNORECASE)
        if type_match:
            payload["tipo_grupo"] = "semi" if IAService._normalize_text(type_match.group(1)).startswith("semi") else "normal"

        plan_match = re.search(r"\bplan\s*[:=]?\s*(2025-1|2015-2|2025-2)\b", question, re.IGNORECASE)
        if plan_match:
            payload["plan_estudio_clave"] = plan_match.group(1)

        if not payload:
            return IAService._missing_fields_response(
                "actualizar grupo",
                ["al menos un campo a actualizar (numero_grupo, capacidad, tipo o plan)"],
                "Ejemplo: actualiza grupo 501 capacidad 45 tipo semi plan 2015-2",
            )

        updated = GroupService.update_group(group.id, payload)
        return {
            "respuesta": f"Grupo actualizado correctamente: {updated['numero_grupo']} ({updated['plan_estudio']['clave']}).",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "actualizar_grupo", "resultado": updated},
        }

    @staticmethod
    def _execute_delete_group(question: str) -> dict:
        confirmation = IAService._require_delete_confirmation(question, "grupo")
        if confirmation is not None:
            return confirmation

        group = IAService._find_group_by_ref(question)
        group_num = group.numero_grupo
        GroupService.delete_group(group.id)
        return {
            "respuesta": f"Grupo eliminado correctamente: {group_num}.",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "eliminar_grupo", "resultado": {"id": group.id}},
        }

    @staticmethod
    def _execute_update_subject(question: str) -> dict:
        subject = IAService._find_subject_by_ref(question)
        data = IAService._extract_keyword_values(question)
        payload: dict[str, Any] = {}

        for field in ["clave", "nombre", "semestre", "hc", "ht", "hl", "hpc", "hcl", "he", "cr"]:
            if field in data:
                payload[field] = data[field]

        if data.get("tipo") or data.get("tipo_materia"):
            payload["tipo_materia"] = IAService._normalize_subject_type(data.get("tipo") or data.get("tipo_materia"))

        if data.get("modalidad"):
            payload["modalidad"] = IAService._normalize_modality(data.get("modalidad"))

        plan_key = data.get("plan") or data.get("plan_estudio") or data.get("plan_estudio_clave")
        if plan_key:
            plan = IAService._find_plan_by_key(str(plan_key))
            if plan is None:
                raise ValidationApiError("Plan no encontrado", [f"No se encontro el plan {plan_key}"])
            payload["plan_estudio_id"] = plan.id

        if not payload:
            return IAService._missing_fields_response(
                "actualizar materia",
                ["al menos un campo a actualizar (nombre, semestre, modalidad, tipo, hc/ht/...)"] ,
                "Ejemplo: actualiza materia clave ADM101 nombre Administracion I modalidad virtual",
            )

        updated = MateriaService.update_subject(subject.id, payload)
        return {
            "respuesta": f"Materia actualizada correctamente: {updated['clave']} - {updated['nombre']}.",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "actualizar_materia", "resultado": updated},
        }

    @staticmethod
    def _execute_delete_subject(question: str) -> dict:
        confirmation = IAService._require_delete_confirmation(question, "materia")
        if confirmation is not None:
            return confirmation

        subject = IAService._find_subject_by_ref(question)
        subject_key = subject.clave
        subject_name = subject.nombre
        MateriaService.delete_subject(subject.id)
        return {
            "respuesta": f"Materia eliminada correctamente: {subject_key} - {subject_name}.",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "eliminar_materia", "resultado": {"id": subject.id}},
        }

    @staticmethod
    def _execute_update_schedule(question: str) -> dict:
        block = IAService._find_block_by_ref(question)
        payload: dict[str, Any] = {
            "group_id": block.grupo_id,
            "materia_id": block.materia_id,
            "docente_id": block.docente_id,
            "dia": block.dia,
            "hora_inicio": f"{block.hora_inicio.hour:02d}:00",
            "hora_fin": f"{block.hora_fin.hour:02d}:00",
            "modalidad": block.modalidad,
        }

        normalized = IAService._normalize_text(question)
        day_match = re.search(r"\b(lunes|martes|miercoles|jueves|viernes|sabado)\b", normalized)
        if day_match:
            payload["dia"] = IAService._normalize_day(day_match.group(1))

        time_match = re.search(r"\b(\d{1,2})(?::00)?\s*(?:a|-|hasta)\s*(\d{1,2})(?::00)?\b", normalized)
        if time_match:
            payload["hora_inicio"] = f"{int(time_match.group(1)):02d}:00"
            payload["hora_fin"] = f"{int(time_match.group(2)):02d}:00"

        modality_match = re.search(r"\b(presencial|virtual)\b", normalized)
        if modality_match:
            payload["modalidad"] = IAService._normalize_modality(modality_match.group(1))

        group_match = re.search(r"\bgrupo\s+(\d{3,})\b", question, re.IGNORECASE)
        if group_match:
            group = db.session.scalar(select(Grupo).where(Grupo.numero_grupo == int(group_match.group(1))))
            if group is None:
                raise ValidationApiError("Grupo no encontrado", [f"No existe el grupo {group_match.group(1)}"])
            payload["group_id"] = group.id

        teacher_match = re.search(r"\bdocente\s+([A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ ._-]+?)(?=\s+dia\b|\s+d[ií]a\b|\s+modalidad\b|\s+grupo\b|\s+materia\b|\s+\d{1,2}(?::00)?\s*(?:a|-|hasta)|$)", question, re.IGNORECASE)
        if teacher_match:
            teacher = IAService._find_teacher(teacher_match.group(1).strip())
            payload["docente_id"] = teacher.id

        subject_match = re.search(r"\bmateria\s+([A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ ._-]+?)(?=\s+docente\b|\s+dia\b|\s+d[ií]a\b|\s+modalidad\b|\s+grupo\b|\s+\d{1,2}(?::00)?\s*(?:a|-|hasta)|$)", question, re.IGNORECASE)
        if subject_match:
            subject = IAService._find_subject_for_group(payload["group_id"], subject_match.group(1).strip())
            payload["materia_id"] = subject.id

        updated = HorarioService.update_block(block.id, payload)
        return {
            "respuesta": (
                f"Bloque actualizado correctamente: {updated['id']} · {updated['dia']} "
                f"{updated['hora_inicio']}-{updated['hora_fin']}."
            ),
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "actualizar_horario", "resultado": updated},
        }

    @staticmethod
    def _execute_delete_schedule(question: str) -> dict:
        confirmation = IAService._require_delete_confirmation(question, "bloque de horario")
        if confirmation is not None:
            return confirmation

        block = IAService._find_block_by_ref(question)
        deleted = HorarioService.delete_block(block.id)
        return {
            "respuesta": f"Bloque eliminado correctamente: {deleted['id']}.",
            "fuentes": [],
            "contexto_usado": 0,
            "accion_ejecutada": {"tipo": "eliminar_horario", "resultado": deleted},
        }

    @staticmethod
    def _require_delete_confirmation(question: str, target_name: str) -> dict | None:
        normalized = IAService._normalize_text(question)
        confirmation_tokens = [
            "confirmo",
            "confirmar",
            "confirmado",
            "si elimina",
            "si eliminar",
            "si borra",
            "si borrar",
        ]
        if any(token in normalized for token in confirmation_tokens):
            return None

        return {
            "respuesta": (
                f"Para seguridad, confirma la eliminación del {target_name}. "
                f"Vuelve a enviar la instrucción incluyendo 'confirmo'."
            ),
            "fuentes": [],
            "contexto_usado": 0,
        }

    @staticmethod
    def _extract_keyword_values(question: str) -> dict:
        fields = [
            "clave",
            "nombre",
            "activo",
            "capacidad",
            "semestre",
            "tipo",
            "tipo_materia",
            "modalidad",
            "plan",
            "plan_estudio",
            "plan_estudio_clave",
            "hc",
            "ht",
            "hl",
            "hpc",
            "hcl",
            "he",
            "cr",
        ]
        result: dict[str, Any] = {}
        for index, field in enumerate(fields):
            next_fields = "|".join(re.escape(item) for item in fields if item != field)
            pattern = rf"\b{re.escape(field)}\b\s*[:=]?\s*(.+?)(?=\s+(?:{next_fields})\b|$)"
            match = re.search(pattern, question, re.IGNORECASE)
            if not match:
                continue
            value = match.group(1).strip().strip(",")
            if field in {"semestre", "hc", "ht", "hl", "hpc", "hcl", "he", "cr"}:
                try:
                    result[field] = int(value)
                except ValueError:
                    result[field] = value
            else:
                result[field] = value
        return result

    @staticmethod
    def _find_plan_by_key(plan_key: str | None) -> PlanEstudio | None:
        if not plan_key:
            return None
        normalized = plan_key.strip()
        plan = db.session.scalar(select(PlanEstudio).where(PlanEstudio.clave == normalized))
        if plan is not None:
            return plan

        alias = None
        if normalized == "2015-2":
            alias = "2025-2"
        elif normalized == "2025-2":
            alias = "2015-2"

        if alias is None:
            return None

        return db.session.scalar(select(PlanEstudio).where(PlanEstudio.clave == alias))

    @staticmethod
    def _find_teacher(token: str) -> Docente:
        token = token.strip()
        # 1. Clave exacta
        teacher = db.session.scalar(select(Docente).where(Docente.clave_docente == token))
        if teacher:
            return teacher
        # 2. Nombre exacto case-insensitive
        teacher = db.session.scalar(select(Docente).where(Docente.nombre.ilike(token)))
        if teacher:
            return teacher
        # 3. Formato "NUMERO NOMBRE" — el numero es la clave del empleado
        parts = token.split(maxsplit=1)
        if parts and re.match(r"^\d+$", parts[0]):
            teacher = db.session.scalar(select(Docente).where(Docente.clave_docente == parts[0]))
            if teacher:
                return teacher
            if len(parts) == 2:
                name_part = parts[1].strip()
                teacher = db.session.scalar(select(Docente).where(Docente.nombre.ilike(name_part)))
                if teacher:
                    return teacher
                teacher = db.session.scalar(select(Docente).where(Docente.nombre.ilike(f"%{name_part}%")))
                if teacher:
                    return teacher
        # 4. Coincidencia parcial de nombre
        teacher = db.session.scalar(select(Docente).where(Docente.nombre.ilike(f"%{token}%")))
        if teacher:
            return teacher
        raise ValidationApiError("Docente no encontrado", [f"No se encontro el docente '{token}'"])

    @staticmethod
    def _find_teacher_by_ref(question: str) -> Docente:
        id_match = re.search(r"\bdocente\s+id\s*(\d+)\b", question, re.IGNORECASE)
        if id_match:
            teacher = db.session.get(Docente, int(id_match.group(1)))
            if teacher is None:
                raise ValidationApiError("Docente no encontrado", [f"No existe docente con id {id_match.group(1)}"])
            return teacher

        key_match = re.search(r"\bclave(?: docente)?\s*[:=]?\s*([A-Za-z0-9_-]+)\b", question, re.IGNORECASE)
        if key_match:
            return IAService._find_teacher(key_match.group(1))

        raise ValidationApiError(
            "Referencia de docente incompleta",
            ["Para actualizar/eliminar docente indica 'docente id <id>' o 'clave <CLAVE>'"],
        )

    @staticmethod
    def _find_group_by_ref(question: str) -> Grupo:
        id_match = re.search(r"\bgrupo\s+id\s*(\d+)\b", question, re.IGNORECASE)
        if id_match:
            group = db.session.get(Grupo, int(id_match.group(1)))
            if group is None:
                raise ValidationApiError("Grupo no encontrado", [f"No existe grupo con id {id_match.group(1)}"])
            return group

        num_match = re.search(r"\bgrupo\s+(\d{3,})\b", question, re.IGNORECASE)
        if num_match:
            group = db.session.scalar(select(Grupo).where(Grupo.numero_grupo == int(num_match.group(1))))
            if group is None:
                raise ValidationApiError("Grupo no encontrado", [f"No existe el grupo {num_match.group(1)}"])
            return group

        raise ValidationApiError(
            "Referencia de grupo incompleta",
            ["Para actualizar/eliminar grupo indica 'grupo <numero>' o 'grupo id <id>'"],
        )

    @staticmethod
    def _find_subject_by_ref(question: str) -> Materia:
        id_match = re.search(r"\bmateria\s+id\s*(\d+)\b", question, re.IGNORECASE)
        if id_match:
            subject = db.session.get(Materia, int(id_match.group(1)))
            if subject is None:
                raise ValidationApiError("Materia no encontrada", [f"No existe materia con id {id_match.group(1)}"])
            return subject

        key_match = re.search(r"\bclave\s*[:=]?\s*([A-Za-z0-9_-]+)\b", question, re.IGNORECASE)
        if key_match:
            subject = db.session.scalar(select(Materia).where(Materia.clave == key_match.group(1).strip()))
            if subject is None:
                raise ValidationApiError("Materia no encontrada", [f"No existe la materia {key_match.group(1)}"])
            return subject

        raise ValidationApiError(
            "Referencia de materia incompleta",
            ["Para actualizar/eliminar materia indica 'materia id <id>' o 'clave <CLAVE>'"],
        )

    @staticmethod
    def _find_block_by_ref(question: str) -> BloqueHorario:
        match = re.search(r"\bbloque\s+(\d+)\b", question, re.IGNORECASE)
        if not match:
            match = re.search(r"\bhorario\s+id\s*(\d+)\b", question, re.IGNORECASE)
        if not match:
            raise ValidationApiError(
                "Referencia de bloque incompleta",
                ["Para actualizar/eliminar horario indica 'bloque <id>'"],
            )

        block = db.session.get(BloqueHorario, int(match.group(1)))
        if block is None:
            raise ValidationApiError("Bloque no encontrado", [f"No existe bloque con id {match.group(1)}"])
        return block

    @staticmethod
    def _find_subject_for_group(group_id: int, token: str) -> Materia:
        token = token.strip()
        token_norm = IAService._normalize_text(token)
        schedule = HorarioService.get_group_schedule(group_id)
        available = schedule.get("materias_disponibles", [])

        def _n(s: str) -> str:
            return IAService._normalize_text(s)

        # Si el token tiene formato "ID - Nombre" (ej: "48833 - Introduccion al Derecho"), extraer partes
        id_prefix_match = re.match(r"^(\d+)\s*[-\u2013]\s*(.+)$", token_norm)
        stripped_token_norm = id_prefix_match.group(2).strip() if id_prefix_match else token_norm

        # Buscar por clave exacta o nombre exacto (normalizados)
        match = next((item for item in available if _n(item["clave"]) == token_norm), None)
        if match is None:
            match = next((item for item in available if _n(item["nombre"]) == token_norm), None)
        # Buscar con token sin prefijo numérico
        if match is None and stripped_token_norm != token_norm:
            match = next((item for item in available if _n(item["nombre"]) == stripped_token_norm), None)
            if match is None:
                match = next((item for item in available if _n(item["clave"]) == stripped_token_norm), None)
        # Coincidencia parcial de nombre
        if match is None:
            match = next(
                (item for item in available if token_norm in _n(item["nombre"]) or _n(item["nombre"]) in token_norm),
                None,
            )
        if match is None and stripped_token_norm != token_norm:
            match = next(
                (item for item in available if stripped_token_norm in _n(item["nombre"]) or _n(item["nombre"]) in stripped_token_norm),
                None,
            )
        if match is not None:
            subject = db.session.get(Materia, match["id"])
            if subject is not None:
                return subject

        # Buscar por ID numérico si el token tenía prefijo "ID - Nombre"
        if id_prefix_match:
            try:
                subject_by_id = db.session.get(Materia, int(id_prefix_match.group(1)))
                if subject_by_id is not None:
                    return subject_by_id
            except (ValueError, TypeError):
                pass

        # Fallback global: busca en todas las materias
        subject = db.session.scalar(select(Materia).where(Materia.clave.ilike(token)))
        if subject is None:
            subject = db.session.scalar(select(Materia).where(Materia.nombre.ilike(f"%{stripped_token_norm}%")))
        if subject is None and stripped_token_norm != token_norm:
            subject = db.session.scalar(select(Materia).where(Materia.nombre.ilike(f"%{token}%")))
        if subject is not None:
            return subject

        raise ValidationApiError(
            "Materia no encontrada",
            [f"No se encontro la materia '{token}' en el grupo indicado ni en el catalogo"],
        )

    @staticmethod
    def _normalize_subject_type(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = IAService._normalize_text(value)
        return "optativa" if "optativa" in normalized else "normal"

    @staticmethod
    def _normalize_modality(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = IAService._normalize_text(value)
        return "virtual" if "virtual" in normalized else "presencial"

    @staticmethod
    def _normalize_day(value: str) -> str:
        normalized = IAService._normalize_text(value)
        return normalized.replace("miércoles", "miercoles").replace("sabado", "sabado")

    @staticmethod
    def _normalize_text(value: str) -> str:
        normalized = (value or "").strip().lower()
        replacements = str.maketrans("áéíóúüñ", "aeiouun")
        return normalized.translate(replacements)

    @staticmethod
    def _build_db_context() -> str:
        """Resumen compacto del estado actual de la BD para inyectar al LLM como contexto."""
        try:
            groups = db.session.scalars(select(Grupo)).all()
            teachers = db.session.scalars(select(Docente).where(Docente.activo == True).limit(40)).all()  # noqa: E712
            total_teachers = db.session.query(Docente).filter(Docente.activo == True).count()  # noqa: E712

            groups_text = ", ".join(
                f"Grupo {g.numero_grupo} (plan {g.plan_estudio.clave if g.plan_estudio else '?'}, cap.{g.capacidad_alumnos})"
                for g in groups
            ) or "ninguno"

            teachers_text = " | ".join(f"{t.clave_docente}={t.nombre}" for t in teachers)
            suffix = f" (+{total_teachers - len(teachers)} más)" if total_teachers > len(teachers) else ""

            return (
                "[Datos actuales del sistema — usa esto para responder preguntas sobre el contenido de la BD]\n"
                f"Grupos activos: {groups_text}\n"
                f"Docentes activos ({total_teachers}): {teachers_text}{suffix}\n"
            )
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _missing_fields_response(action_name: str, missing_fields: list[str], example: str) -> dict:
        fields = ", ".join(missing_fields)
        return {
            "respuesta": f"Puedo {action_name}, pero faltan estos datos: {fields}. {example}",
            "fuentes": [],
            "contexto_usado": 0,
        }

    @staticmethod
    def learn_from_interaction(question: str, answer: str, metadata: dict[str, Any] | None = None) -> dict:
        question = (question or "").strip()
        answer = (answer or "").strip()
        if not question or not answer:
            raise ValidationApiError(
                "Interaccion invalida",
                ["Los campos pregunta y respuesta son obligatorios"],
            )

        consolidated = f"Pregunta del usuario: {question}\nRespuesta validada: {answer}"
        merged_metadata = {"source": "interaccion_validada", **(metadata or {})}
        return IAService.learn_from_user(consolidated, metadata=merged_metadata)

    @staticmethod
    def learn_from_user(note: str, metadata: dict[str, Any] | None = None) -> dict:
        note = (note or "").strip()
        if not note:
            raise ValidationApiError("Contenido invalido", ["El texto a aprender no puede estar vacio"])

        try:
            vector = IAService._get_embeddings_client().embed_query(note)
        except Exception as error:  # noqa: BLE001
            raise ValidationApiError(
                "No fue posible guardar conocimiento",
                [IAService._format_runtime_error(error)],
            )
        store = IAService._load_vector_store()
        store["documents"].append(
            {
                "id": str(uuid4()),
                "text": note,
                "metadata": {
                    "source": "aprendizaje_usuario",
                    "doc_type": "user_memory",
                    **(metadata or {}),
                },
                "embedding": vector,
            }
        )
        IAService._save_vector_store(store)

        IAService._append_learning_log({"text": note, "metadata": metadata or {}})
        return {
            "guardado": True,
            "documentos_totales": len(store["documents"]),
        }

    @staticmethod
    def import_teachers_from_text(text: str, dry_run: bool = True) -> dict:
        text = (text or "").strip()
        if not text:
            raise ValidationApiError("Entrada invalida", ["El campo texto es obligatorio"])

        llm = IAService._get_chat_client()
        prompt = (
            "Extrae docentes desde el texto y responde SOLO JSON valido con este formato:\n"
            "{\"docentes\": [{\"clave_docente\": \"string\", \"nombre\": \"string\", \"activo\": true}]}\n"
            "No agregues explicaciones. No inventes claves si no existen: usa null en clave_docente cuando falte.\n\n"
            f"Texto de entrada:\n{text}"
        )
        try:
            raw = llm.invoke(prompt)
        except Exception as error:  # noqa: BLE001
            raise ValidationApiError(
                "No fue posible procesar el texto con IA",
                [IAService._format_runtime_error(error)],
            )
        content = raw.content if hasattr(raw, "content") else str(raw)
        parsed = IAService._parse_json_response(content)

        teachers = parsed.get("docentes")
        if not isinstance(teachers, list):
            raise ValidationApiError("Respuesta IA invalida", ["No se encontro una lista de docentes"])

        accepted = []
        rejected = []
        created = []

        for idx, teacher_payload in enumerate(teachers, start=1):
            if not isinstance(teacher_payload, dict):
                rejected.append({"index": idx, "error": "Formato invalido"})
                continue

            normalized = {
                "clave_docente": (teacher_payload.get("clave_docente") or "").strip(),
                "nombre": (teacher_payload.get("nombre") or "").strip(),
                "activo": bool(teacher_payload.get("activo", True)),
            }

            errors = []
            if not normalized["clave_docente"]:
                errors.append("Falta clave_docente")
            if not normalized["nombre"]:
                errors.append("Falta nombre")

            if errors:
                rejected.append({"index": idx, "payload": teacher_payload, "errores": errors})
                continue

            accepted.append(normalized)

            if not dry_run:
                try:
                    created.append(DocenteService.create_teacher(normalized))
                except Exception as error:  # noqa: BLE001
                    rejected.append(
                        {
                            "index": idx,
                            "payload": normalized,
                            "errores": [str(error)],
                        }
                    )

        return {
            "dry_run": dry_run,
            "docentes_detectados": len(teachers),
            "docentes_validos": len(accepted),
            "docentes_creados": len(created),
            "creados": created,
            "rechazados": rejected,
            "candidatos": accepted if dry_run else None,
        }

    @staticmethod
    def _rank_documents(query_embedding: list[float], docs: list[dict], top_k: int) -> list[dict]:
        scored = []
        for entry in docs:
            embedding = entry.get("embedding")
            if not embedding:
                continue
            score = IAService._cosine_similarity(query_embedding, embedding)
            scored.append({**entry, "score": score})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[: max(1, top_k)]

    @staticmethod
    def _filter_ranked_docs_for_question(question: str, ranked_docs: list[dict]) -> list[dict]:
        if not ranked_docs:
            return ranked_docs

        normalized_q = IAService._normalize_text(question)
        min_score = float(current_app.config.get("AI_RAG_MIN_SCORE", 0.65))
        min_score_user_memory = float(current_app.config.get("AI_RAG_MIN_SCORE_USER_MEMORY", 0.80))
        use_user_memory = IAService._should_use_user_memory(normalized_q)

        filtered = []
        for entry in ranked_docs:
            metadata = entry.get("metadata") or {}
            source = str(metadata.get("source", "")).lower()
            doc_type = str(metadata.get("doc_type", "")).lower()
            score = float(entry.get("score", -1.0))
            is_user_memory = doc_type == "user_memory" or source == "aprendizaje_usuario"

            # Filtrar user_memory: requiere keywords explícitos Y score más alto
            if is_user_memory:
                if not use_user_memory or score < min_score_user_memory:
                    continue
            elif score < min_score:
                continue

            filtered.append(entry)

        return filtered

    @staticmethod
    def _should_use_user_memory(normalized_question: str) -> bool:
        keywords = [
            "restriccion",
            "restricciones",
            "regla",
            "reglas",
            "acuerdo",
            "preferencia",
            "recordatorio",
            "memoriza",
            "aprendizaje_usuario",
        ]
        return any(keyword in normalized_question for keyword in keywords)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return -1.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _get_chat_client() -> ChatOllama:
        return ChatOllama(
            model=current_app.config["AI_CHAT_MODEL"],
            base_url=current_app.config["AI_OLLAMA_BASE_URL"],
            temperature=0,
        )

    @staticmethod
    def _get_embeddings_client() -> OllamaEmbeddings:
        return OllamaEmbeddings(
            model=current_app.config["AI_EMBED_MODEL"],
            base_url=current_app.config["AI_OLLAMA_BASE_URL"],
        )

    @staticmethod
    def _load_vector_store() -> dict:
        file_path = Path(current_app.config["AI_VECTOR_STORE_PATH"])
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if not file_path.exists():
            return {"count_before": 0, "documents": []}

        raw_text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw_text:
            return {"count_before": 0, "documents": []}

        try:
            content = json.loads(raw_text)
            documents = content.get("documents", []) if isinstance(content, dict) else []
            if not isinstance(documents, list):
                documents = []
            return {"count_before": len(documents), "documents": documents}
        except json.JSONDecodeError:
            # Recuperacion defensiva: intentar extraer el primer objeto JSON valido.
            recovered = None
            match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
            if match:
                candidate = match.group(0)
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and isinstance(parsed.get("documents", []), list):
                        recovered = parsed
                except json.JSONDecodeError:
                    recovered = None

            if recovered is not None:
                # Sobrescribe con el JSON recuperado para evitar fallos futuros.
                file_path.write_text(json.dumps(recovered, ensure_ascii=True), encoding="utf-8")
                documents = recovered.get("documents", [])
                return {"count_before": len(documents), "documents": documents}

            # Si no se puede recuperar, respalda y reinicia en vacio.
            backup_path = file_path.with_suffix(file_path.suffix + ".corrupt")
            try:
                file_path.replace(backup_path)
            except OSError:
                pass
            file_path.write_text(json.dumps({"documents": []}, ensure_ascii=True), encoding="utf-8")
            return {"count_before": 0, "documents": []}

    @staticmethod
    def _save_vector_store(store: dict) -> None:
        payload = {"documents": store.get("documents", [])}
        file_path = Path(current_app.config["AI_VECTOR_STORE_PATH"])
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")

    @staticmethod
    def _append_learning_log(record: dict) -> None:
        logs_dir = Path(current_app.config["AI_UPLOAD_DIR"])
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "ai_learning_log.jsonl"
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")

    @staticmethod
    def _append_chat_log(record: dict) -> None:
        logs_dir = Path(current_app.config["AI_UPLOAD_DIR"])
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / "ai_chat_history.jsonl"
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")

    @staticmethod
    def _parse_json_response(raw_text: str) -> dict:
        raw_text = (raw_text or "").strip()
        if not raw_text:
            raise ValidationApiError("Respuesta vacia", ["El modelo no devolvio contenido"])

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            pass

        # Intento de recuperacion cuando el modelo envuelve JSON en markdown.
        if "```" in raw_text:
            blocks = raw_text.split("```")
            for block in blocks:
                candidate = block.strip()
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        continue

        raise ValidationApiError("Respuesta IA invalida", ["No fue posible parsear JSON del modelo"])

    @staticmethod
    def _format_runtime_error(error: Exception) -> str:
        details = str(error).strip()
        if details:
            return details
        base_url = current_app.config.get("AI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        return (
            f"Verifica que Ollama este ejecutandose en {base_url} y que los modelos "
            "configurados esten descargados localmente"
        )

    @staticmethod
    def _get_installation_status() -> dict:
        process = IAService._install_process
        running = False
        exit_code = None

        if process is not None:
            exit_code = process.poll()
            running = exit_code is None
            if not running and IAService._install_log_handle is not None:
                IAService._install_log_handle.close()
                IAService._install_log_handle = None

        log_tail = ""
        if IAService._install_log_path and IAService._install_log_path.exists():
            lines = IAService._install_log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            log_tail = "\n".join(lines[-12:])

        return {
            "running": running,
            "exit_code": exit_code,
            "log_tail": log_tail,
        }

    @staticmethod
    def _model_manifest_exists(models_dir: Path, model_name: str) -> bool:
        repo, _, tag = model_name.partition(":")
        manifest_tag = tag or "latest"
        manifest_path = models_dir / "manifests" / "registry.ollama.ai" / "library" / repo / manifest_tag
        return manifest_path.exists()

    @staticmethod
    def _list_models_from_ollama_api(base_url: str) -> set[str]:
        if not base_url:
            return set()

        url = base_url.rstrip("/") + "/api/tags"
        try:
            with urlopen(url, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, ValueError, OSError):
            return set()

        models = payload.get("models") or []
        names: set[str] = set()
        for model in models:
            if isinstance(model, dict):
                name = model.get("name")
                if isinstance(name, str) and name.strip():
                    full = name.strip()
                    names.add(full)
                    # Ollama devuelve "nomic-embed-text:latest" pero la config guarda
                    # "nomic-embed-text" (sin tag). Agregamos la version sin tag tambien.
                    if ":" in full:
                        names.add(full.split(":")[0])
        return names
