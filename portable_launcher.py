import os
import atexit
import signal
import socket
import threading
import sys
import webbrowser
from pathlib import Path


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
