"""create incomes table

Revision ID: e7f8g9h0i1j2
Revises: b9c8d7e6f5a4
Create Date: 2025-09-28 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f8g9h0i1j2'
down_revision = 'b9c8d7e6f5a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'incomes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('method', sa.String(length=50), nullable=True),
        sa.Column('reference', sa.String(length=120), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_incomes_source_source_id', 'incomes', ['source', 'source_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_incomes_source_source_id', table_name='incomes')
    op.drop_table('incomes')

