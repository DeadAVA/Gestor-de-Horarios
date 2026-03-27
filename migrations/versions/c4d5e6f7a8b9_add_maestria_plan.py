"""add maestria plan

Revision ID: c4d5e6f7a8b9
Revises: a1b2c3d4e5f6
Create Date: 2026-03-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    existing = conn.execute(
        text("SELECT id FROM planes_estudio WHERE clave = 'maestria'")
    ).fetchone()
    if existing is None:
        conn.execute(
            text("INSERT INTO planes_estudio (clave, nombre, activo) VALUES ('maestria', 'Plan de Maestría', 1)")
        )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM planes_estudio WHERE clave = 'maestria'")
    )
