"""create managed_transactions

Revision ID: 0a1b2c3d4e5f
Revises: 7f3a1b2c9d0a
Create Date: 2025-09-27 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a1b2c3d4e5f'
down_revision = '7f3a1b2c9d0a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'managed_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('authority', sa.String(length=200), nullable=False),
        sa.Column('service', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='نشطة'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    # Drop server_default after creation
    with op.batch_alter_table('managed_transactions') as batch_op:
        batch_op.alter_column('status', server_default=None)


def downgrade() -> None:
    op.drop_table('managed_transactions')

