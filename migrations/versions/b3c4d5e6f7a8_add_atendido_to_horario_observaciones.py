"""add atendido to horario observaciones

Revision ID: b3c4d5e6f7a8
Revises: f2a9c1d3e4b7
Create Date: 2026-04-09 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'f2a9c1d3e4b7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('horario_observaciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('atendido', sa.Boolean(), server_default=sa.text('0'), nullable=False))


def downgrade():
    with op.batch_alter_table('horario_observaciones', schema=None) as batch_op:
        batch_op.drop_column('atendido')
