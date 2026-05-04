"""add group subject assignments

Revision ID: c9d8e7f6a5b4
Revises: b3c4d5e6f7a8
Create Date: 2026-04-14 15:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9d8e7f6a5b4'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asignaciones_materia_grupo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grupo_id', sa.Integer(), nullable=False),
        sa.Column('materia_id', sa.Integer(), nullable=False),
        sa.Column('docente_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['docente_id'], ['docentes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['grupo_id'], ['grupos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['materia_id'], ['materias.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grupo_id', 'materia_id', name='uq_asignacion_grupo_materia'),
    )
    op.create_index(op.f('ix_asignaciones_materia_grupo_docente_id'), 'asignaciones_materia_grupo', ['docente_id'], unique=False)
    op.create_index(op.f('ix_asignaciones_materia_grupo_grupo_id'), 'asignaciones_materia_grupo', ['grupo_id'], unique=False)
    op.create_index(op.f('ix_asignaciones_materia_grupo_materia_id'), 'asignaciones_materia_grupo', ['materia_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_asignaciones_materia_grupo_materia_id'), table_name='asignaciones_materia_grupo')
    op.drop_index(op.f('ix_asignaciones_materia_grupo_grupo_id'), table_name='asignaciones_materia_grupo')
    op.drop_index(op.f('ix_asignaciones_materia_grupo_docente_id'), table_name='asignaciones_materia_grupo')
    op.drop_table('asignaciones_materia_grupo')
