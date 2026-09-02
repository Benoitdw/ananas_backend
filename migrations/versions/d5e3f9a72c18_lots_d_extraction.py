"""lots d'extraction

Revision ID: d5e3f9a72c18
Revises: c4d2b8e51a06
Create Date: 2026-09-02 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'd5e3f9a72c18'
down_revision = 'c4d2b8e51a06'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'extraction_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('provider_batch_id', sa.String(length=255), nullable=False),
        sa.Column('job_ids', sa.JSON(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=16), server_default='pending', nullable=False),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_extraction_batches_status', 'extraction_batches', ['status'])


def downgrade() -> None:
    op.drop_index('ix_extraction_batches_status', table_name='extraction_batches')
    op.drop_table('extraction_batches')
