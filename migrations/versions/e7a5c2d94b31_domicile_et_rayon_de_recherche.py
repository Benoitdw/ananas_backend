"""domicile et rayon de recherche

Revision ID: e7a5c2d94b31
Revises: d5e3f9a72c18
Create Date: 2026-09-07 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7a5c2d94b31'
down_revision = 'd5e3f9a72c18'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_homes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('street', sa.String(length=255), server_default='', nullable=False),
        sa.Column('postal_code', sa.String(length=16), server_default='', nullable=False),
        sa.Column('city', sa.String(length=120), server_default='', nullable=False),
        sa.Column('country', sa.String(length=80), server_default='Belgium', nullable=False),
        sa.Column('address', sa.String(length=500), server_default='', nullable=False),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lon', sa.Float(), nullable=True),
        sa.Column('geo_precision', sa.String(length=32), server_default='', nullable=False),
        sa.Column('radius_km', sa.Integer(), server_default='25', nullable=False),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_homes')
