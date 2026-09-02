"""offres masquees

Revision ID: c4d2b8e51a06
Revises: b3c1a7f40d92
Create Date: 2026-09-02 16:10:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d2b8e51a06'
down_revision = 'b3c1a7f40d92'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hidden_jobs',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('hidden_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'job_id'),
    )


def downgrade() -> None:
    op.drop_table('hidden_jobs')
