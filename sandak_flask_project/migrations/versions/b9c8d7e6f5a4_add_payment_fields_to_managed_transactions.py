"""add payment fields to managed_transactions

Revision ID: b9c8d7e6f5a4
Revises: a1b2c3e4f5g6
Create Date: 2025-09-28 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9c8d7e6f5a4'
down_revision = 'a1b2c3e4f5g6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('managed_transactions') as batch_op:
        batch_op.add_column(sa.Column('is_paid', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('paid_amount', sa.Numeric(12, 2), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('paid_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('managed_transactions') as batch_op:
        batch_op.alter_column('is_paid', server_default=None)
        batch_op.alter_column('paid_amount', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('managed_transactions') as batch_op:
        batch_op.drop_column('paid_at')
        batch_op.drop_column('paid_amount')
        batch_op.drop_column('is_paid')

