"""add docente materia observaciones

Revision ID: a1b2c3d4e5f6
Revises: 7247a338a726
Create Date: 2026-03-23 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '7247a338a726'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'docente_materia_observaciones',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('docente_id', sa.Integer(), nullable=False),
        sa.Column('materia_id', sa.Integer(), nullable=False),
        sa.Column('observacion', sa.Text(), nullable=False),
        sa.Column('nivel', sa.String(length=20), server_default='malo', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("nivel IN ('malo', 'regular', 'bueno')", name='nivel_valido'),
        sa.ForeignKeyConstraint(
            ['docente_id'], ['docentes.id'],
            name=op.f('fk_docente_materia_observaciones_docente_id_docentes'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['materia_id'], ['materias.id'],
            name=op.f('fk_docente_materia_observaciones_materia_id_materias'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_docente_materia_observaciones')),
        sa.UniqueConstraint('docente_id', 'materia_id', name='uq_obs_docente_materia'),
    )
    with op.batch_alter_table('docente_materia_observaciones', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_docente_materia_observaciones_docente_id'),
            ['docente_id'],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f('ix_docente_materia_observaciones_materia_id'),
            ['materia_id'],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table('docente_materia_observaciones', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_docente_materia_observaciones_materia_id'))
        batch_op.drop_index(batch_op.f('ix_docente_materia_observaciones_docente_id'))

    op.drop_table('docente_materia_observaciones')
