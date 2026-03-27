"""add docente foraneo flag

Revision ID: d7e8f9a0b1c2
Revises: c4d5e6f7a8b9
Create Date: 2026-03-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7e8f9a0b1c2'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'docentes',
        sa.Column('foraneo', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )


def downgrade():
    op.drop_column('docentes', 'foraneo')
