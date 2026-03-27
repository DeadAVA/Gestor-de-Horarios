import os
import atexit
import signal
import socket
import subprocess
import threading
import sys
import time
import webbrowser
from pathlib import Path
from shutil import which


def _graceful_shutdown(signum=None, frame=None):
    """Guarda cambios pendientes en SQLite y termina el proceso limpiamente."""
    try:
        from app.extensions import db
        db.session.remove()
        with db.engine.connect() as conn:
            conn.execute(db.text("PRAGMA wal_checkpoint(FULL)"))
        db.engine.dispose()
    except Exception:
        pass
    os._exit(0)


def _portable_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _is_tcp_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _resolve_ollama_executable(root_dir: Path) -> str | None:
    candidates = [
        root_dir / "ollama" / "ollama.exe",
        root_dir / "ollama.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return which("ollama")


def _prepare_ollama_environment(root_dir: Path) -> dict:
    env = os.environ.copy()
    models_dir = root_dir / "instance" / "ollama_models"
    models_dir.mkdir(parents=True, exist_ok=True)

    env["OLLAMA_MODELS"] = str(models_dir)
    env.setdefault("OLLAMA_HOST", "127.0.0.1:11435")
    env["AI_OLLAMA_BASE_URL"] = f"http://{env['OLLAMA_HOST']}"
    return env


def _ensure_ollama_running(root_dir: Path) -> None:
    env = _prepare_ollama_environment(root_dir)
    host_port = env.get("OLLAMA_HOST", "127.0.0.1:11435")
    host, port_raw = host_port.split(":", 1)
    port = int(port_raw)
    if _is_tcp_open(host, port):
        return

    ollama_exe = _resolve_ollama_executable(root_dir)
    if not ollama_exe:
        print("[IA] Ollama no encontrado. La app funcionara sin IA hasta instalar/copiar Ollama.")
        return

    process = subprocess.Popen(
        [ollama_exe, "serve"],
        cwd=str(root_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    def _terminate_ollama() -> None:
        if process.poll() is None:
            process.terminate()

    atexit.register(_terminate_ollama)

    for _ in range(15):
        if _is_tcp_open(host, port):
            return
        if process.poll() is not None:
            break
        time.sleep(0.2)

    if not _is_tcp_open(host, port):
        print("[IA] No fue posible iniciar Ollama automaticamente.")


def _pick_free_port(default_port: int = 5000) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", default_port))
            return default_port
        except OSError:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])


def _bootstrap_data(app) -> None:
    from sqlalchemy import select

    from app.extensions import db
    from app.models import PlanEstudio
    from app.seeds.initial_seed import seed_initial_data

    with app.app_context():
        db.create_all()

        # Solo sembrar catalogos en primer arranque para no alterar datos de uso diario.
        existing_plan = db.session.scalar(select(PlanEstudio.id).limit(1))
        if existing_plan is None:
            seed_initial_data()


def main() -> None:
    # Capturar cierre por task manager, Ctrl+C o señal del SO → guardar DB antes de salir
    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)

    root_dir = _portable_root_dir()
    portable_env = _prepare_ollama_environment(root_dir)
    os.environ["OLLAMA_MODELS"] = portable_env["OLLAMA_MODELS"]
    os.environ["OLLAMA_HOST"] = portable_env["OLLAMA_HOST"]
    os.environ["AI_OLLAMA_BASE_URL"] = portable_env["AI_OLLAMA_BASE_URL"]
    _ensure_ollama_running(root_dir)

    from app import create_app

    app = create_app()
    _bootstrap_data(app)

    port = _pick_free_port(int(os.environ.get("PORTABLE_APP_PORT", "5000")))
    url = f"http://127.0.0.1:{port}"

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        from waitress import serve

        serve(app, host="127.0.0.1", port=port, threads=8)
    except Exception:
        # Fallback for environments where waitress is not bundled.
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
