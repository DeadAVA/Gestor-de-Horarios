import sqlite3

from sqlalchemy import MetaData
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")   # mejor concurrencia multi-hilo
        cursor.execute("PRAGMA synchronous=NORMAL")  # más rápido, seguro con WAL
        cursor.execute("PRAGMA busy_timeout=5000")   # espera 5s antes de 'database locked'
        cursor.close()


def init_extensions(app) -> None:
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from app import models  # noqa: F401