"""compte d'administration

Revision ID: b3c1a7f40d92
Revises: 797dabc9a31a
Create Date: 2026-09-02 15:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b3c1a7f40d92'
down_revision = '797dabc9a31a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('users', 'is_admin')
