import os
import sys
from pathlib import Path
from sqlalchemy.pool import StaticPool


def _detect_resource_base_dir() -> Path:
    # PyInstaller onefile exposes bundled files under _MEIPASS.
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def _detect_data_base_dir() -> Path:
    # In portable mode store mutable data next to the executable.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


RESOURCE_BASE_DIR = _detect_resource_base_dir()
DATA_BASE_DIR = _detect_data_base_dir()
INSTANCE_DIR = DATA_BASE_DIR / "instance"
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = INSTANCE_DIR / "horarios.db"

# Backward-compatible name used in other modules for resource lookup.
BASE_DIR = RESOURCE_BASE_DIR


class Config:
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,   # verifica la conexión antes de usarla
        "pool_recycle": 1800,    # recicla conexiones cada 30 min
    }
    JSON_SORT_KEYS = False
    SECRET_KEY = "dev-secret-key-change-in-production"
    INSTANCE_PATH = INSTANCE_DIR.as_posix()

    # Useful for diagnostics in packaged mode.
    PORTABLE_MODE = bool(getattr(sys, "frozen", False))
    RESOURCE_BASE_DIR = RESOURCE_BASE_DIR.as_posix()
    DATA_BASE_DIR = DATA_BASE_DIR.as_posix()

    # IA local con Ollama y almacenamiento local de embeddings.
    AI_ENABLED = True
    AI_STRICT_LOCAL_ONLY = True
    AI_OLLAMA_BASE_URL = os.getenv("AI_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    AI_CHAT_MODEL = os.getenv("AI_CHAT_MODEL", "qwen2.5:3b")
    AI_EMBED_MODEL = os.getenv("AI_EMBED_MODEL", "nomic-embed-text")
    AI_OLLAMA_MODELS_DIR = os.getenv("OLLAMA_MODELS", (INSTANCE_DIR / "ollama_models").as_posix())
    AI_PORTABLE_SETUP_SCRIPT = os.getenv(
        "AI_PORTABLE_SETUP_SCRIPT",
        (INSTANCE_DIR.parent / "portable_ai_setup.ps1").as_posix(),
    )
    AI_VECTOR_STORE_PATH = (INSTANCE_DIR / "ai_vector_store.json").as_posix()
    AI_UPLOAD_DIR = (INSTANCE_DIR / "ai_uploads").as_posix()
    AI_MAX_FILE_MB = int(os.getenv("AI_MAX_FILE_MB", "20"))
    AI_TOP_K = int(os.getenv("AI_TOP_K", "4"))
    AI_RAG_MIN_SCORE = float(os.getenv("AI_RAG_MIN_SCORE", "0.62"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }


config_by_name = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}