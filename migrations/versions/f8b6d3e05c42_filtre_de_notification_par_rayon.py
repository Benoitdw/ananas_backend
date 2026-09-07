"""filtre de notification par rayon

Revision ID: f8b6d3e05c42
Revises: e7a5c2d94b31
Create Date: 2026-09-07 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'f8b6d3e05c42'
down_revision = 'e7a5c2d94b31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # false par defaut: personne ne doit se mettre a rater des offres parce
    # qu'un rayon saisi pour la carte s'est mis a filtrer ses notifications.
    op.add_column(
        'user_homes',
        sa.Column('notify_within_radius', sa.Boolean(), server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('user_homes', 'notify_within_radius')
