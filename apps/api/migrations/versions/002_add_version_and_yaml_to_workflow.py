"""Add version and yaml_content to Workflow

Revision ID: 002
Revises: 001
Create Date: 2026-03-21 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'

def upgrade() -> None:
    # Add columns to workflows table
    op.add_column('workflows', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('workflows', sa.Column('yaml_content', sa.String(), nullable=False, server_default=''))

def downgrade() -> None:
    op.drop_column('workflows', 'yaml_content')
    op.drop_column('workflows', 'version')
