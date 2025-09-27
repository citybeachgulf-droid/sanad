"""add fee to managed_transactions

Revision ID: a1b2c3e4f5g6
Revises: 0a1b2c3d4e5f
Create Date: 2025-09-27 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3e4f5g6'
down_revision = '0a1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('managed_transactions') as batch_op:
        batch_op.add_column(sa.Column('fee', sa.Numeric(12, 2), nullable=False, server_default='0'))
        batch_op.alter_column('fee', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('managed_transactions') as batch_op:
        batch_op.drop_column('fee')

