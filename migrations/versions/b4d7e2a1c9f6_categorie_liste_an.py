"""categorie liste an, tags videes

La Liste An n'est plus portee par le tag « Liste An » mais par sa propre
colonne, qui donne aussi la categorie de l'employeur. Les tags disparaissent du
site: on les vide (la colonne reste, rien ne la lit plus).

Apres cette migration, relancer ``python -m ananas.seed`` pour remplir la
categorie depuis data/liste-an.csv.

Revision ID: b4d7e2a1c9f6
Revises: a9c4e18b7d53
Create Date: 2026-11-20 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = 'b4d7e2a1c9f6'
down_revision = 'a9c4e18b7d53'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('liste_an_category', sa.String(length=80), nullable=True))
    op.create_index('ix_companies_liste_an_category', 'companies', ['liste_an_category'])
    op.execute("UPDATE companies SET tags = ''")


def downgrade() -> None:
    # Les tags videes ne reviennent pas.
    op.drop_index('ix_companies_liste_an_category', table_name='companies')
    op.drop_column('companies', 'liste_an_category')
