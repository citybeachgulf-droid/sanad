"""add user permissions

Revision ID: 7f3a1b2c9d0a
Revises: e6ded8b7f19d
Create Date: 2025-09-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f3a1b2c9d0a'
down_revision = 'e6ded8b7f19d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('permissions', sa.Text(), nullable=False, server_default='{}'))

    # Drop server_default after setting existing rows
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column('permissions', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('permissions')

