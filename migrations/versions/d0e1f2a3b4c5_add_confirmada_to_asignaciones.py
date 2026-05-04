"""add_confirmada_to_asignaciones

Revision ID: d0e1f2a3b4c5
Revises: c9d8e7f6a5b4
Create Date: 2026-05-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0e1f2a3b4c5'
down_revision = 'c9d8e7f6a5b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asignaciones_materia_grupo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('confirmada', sa.Boolean(), server_default='0', nullable=False))


def downgrade():
    with op.batch_alter_table('asignaciones_materia_grupo', schema=None) as batch_op:
        batch_op.drop_column('confirmada')
