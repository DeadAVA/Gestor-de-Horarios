"""add horario observaciones

Revision ID: f2a9c1d3e4b7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a9c1d3e4b7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'horario_observaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grupo_id', sa.Integer(), nullable=False),
        sa.Column('materia_id', sa.Integer(), nullable=True),
        sa.Column('comentario', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['grupo_id'], ['grupos.id'],
            name='fk_horario_observaciones_grupo_id_grupos',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['materia_id'], ['materias.id'],
            name='fk_horario_observaciones_materia_id_materias',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id', name='pk_horario_observaciones'),
    )

    with op.batch_alter_table('horario_observaciones', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_horario_observaciones_grupo_id'),
            ['grupo_id'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_horario_observaciones_materia_id'),
            ['materia_id'],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('horario_observaciones', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_horario_observaciones_materia_id'))
        batch_op.drop_index(batch_op.f('ix_horario_observaciones_grupo_id'))

    op.drop_table('horario_observaciones')
