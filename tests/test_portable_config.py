from pathlib import Path

from app import create_app
from app.config import INSTANCE_DIR


def test_create_app_usa_instance_path_configurado():
    app = create_app("testing")

    assert Path(app.instance_path) == INSTANCE_DIR
    assert Path(app.config["INSTANCE_PATH"]) == INSTANCE_DIR
