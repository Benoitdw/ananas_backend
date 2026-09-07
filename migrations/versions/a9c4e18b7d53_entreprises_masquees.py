"""entreprises masquees

Revision ID: a9c4e18b7d53
Revises: f8b6d3e05c42
Create Date: 2026-09-07 12:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'a9c4e18b7d53'
down_revision = 'f8b6d3e05c42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hidden_companies',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('hidden_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'company_id'),
    )


def downgrade() -> None:
    op.drop_table('hidden_companies')
