"""add organizations and org_services tables

Revision ID: c1d2e3f4g5h6
Revises: e7f8g9h0i1j2
Create Date: 2025-09-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4g5h6'
down_revision = 'e7f8g9h0i1j2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('name', name='uq_organizations_name')
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'], unique=False)
    op.create_index('ix_organizations_kind', 'organizations', ['kind'], unique=False)

    op.create_table(
        'org_services',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_org_services_org'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_service_name_per_org')
    )
    op.create_index('ix_org_services_name', 'org_services', ['name'], unique=False)
    op.create_index('ix_org_services_organization_id', 'org_services', ['organization_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_org_services_organization_id', table_name='org_services')
    op.drop_index('ix_org_services_name', table_name='org_services')
    op.drop_table('org_services')
    op.drop_index('ix_organizations_kind', table_name='organizations')
    op.drop_index('ix_organizations_name', table_name='organizations')
    op.drop_table('organizations')

