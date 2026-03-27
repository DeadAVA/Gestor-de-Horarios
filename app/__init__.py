from flask import Flask, render_template
from flask_cors import CORS
from pathlib import Path

from app.api import register_blueprints
from app.config import config_by_name
from app.config import RESOURCE_BASE_DIR
from app.extensions import init_extensions
from app.seeds.initial_seed import register_seed_commands
from app.utils.exceptions import register_error_handlers


def create_app(config_name: str = "default") -> Flask:
    templates_dir = Path(RESOURCE_BASE_DIR) / "app" / "templates"
    static_dir = Path(RESOURCE_BASE_DIR) / "app" / "static"

    flask_kwargs = {
        "instance_relative_config": True,
        "template_folder": str(templates_dir),
    }
    if static_dir.exists():
        flask_kwargs["static_folder"] = str(static_dir)

    app = Flask(__name__, **flask_kwargs)
    app.config.from_object(config_by_name[config_name])

    @app.get("/")
    def index():
        return render_template("Horarios.html")

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    init_extensions(app)
    register_error_handlers(app)
    register_seed_commands(app)
    register_blueprints(app)

    return app