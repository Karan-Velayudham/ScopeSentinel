"""Add InstalledConnector table

Revision ID: 003
Revises: 002
Create Date: 2026-03-21 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'

def upgrade() -> None:
    op.create_table('installed_connectors',
    sa.Column('id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('org_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('connector_id', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    sa.Column('config_json', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_installed_connectors_connector_id'), 'installed_connectors', ['connector_id'], unique=False)
    op.create_index(op.f('ix_installed_connectors_org_id'), 'installed_connectors', ['org_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_installed_connectors_org_id'), table_name='installed_connectors')
    op.drop_index(op.f('ix_installed_connectors_connector_id'), table_name='installed_connectors')
    op.drop_table('installed_connectors')
