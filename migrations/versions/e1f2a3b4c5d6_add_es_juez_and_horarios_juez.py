"""add es_juez flag and horarios_juez table

Revision ID: e1f2a3b4c5d6
Revises: d7e8f9a0b1c2
Create Date: 2026-03-24 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'docentes',
        sa.Column('es_juez', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )

    op.create_table(
        'horarios_juez',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('docente_id', sa.Integer(), nullable=False),
        sa.Column('dia', sa.String(length=12), nullable=False),
        sa.Column('hora_inicio', sa.Integer(), nullable=False),
        sa.Column('hora_fin', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['docente_id'], ['docentes.id'],
            name='fk_horarios_juez_docente_id',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_horarios_juez'),
    )
    op.create_index('ix_horarios_juez_docente_id', 'horarios_juez', ['docente_id'], unique=False)


def downgrade():
    op.drop_index('ix_horarios_juez_docente_id', table_name='horarios_juez')
    op.drop_table('horarios_juez')
    op.drop_column('docentes', 'es_juez')
