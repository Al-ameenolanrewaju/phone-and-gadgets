"""add editable storefront brand content and SEO fields

Revision ID: c9a7e21f4d60
Revises: b61c8d5a92ef
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa

revision = "c9a7e21f4d60"
down_revision = "b61c8d5a92ef"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("store_settings") as batch_op:
        batch_op.add_column(sa.Column("tagline", sa.String(length=160), nullable=True))
        batch_op.add_column(sa.Column("hero_cta", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("hero_whatsapp_cta", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("proof1_title", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("proof1_text", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("proof2_title", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("proof2_text", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("proof3_title", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("proof3_text", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("catalogue_eyebrow", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("catalogue_title", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("empty_title", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("empty_text", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("order_eyebrow", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("order_title", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("order_text", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("order_button", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("nav_home", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("nav_contact", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("footer_text", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("copyright_text", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("seo_title", sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column("seo_description", sa.String(length=320), nullable=True))

def downgrade():
    with op.batch_alter_table("store_settings") as batch_op:
        batch_op.drop_column("seo_description")
        batch_op.drop_column("seo_title")
        batch_op.drop_column("copyright_text")
        batch_op.drop_column("footer_text")
        batch_op.drop_column("nav_contact")
        batch_op.drop_column("nav_home")
        batch_op.drop_column("order_button")
        batch_op.drop_column("order_text")
        batch_op.drop_column("order_title")
        batch_op.drop_column("order_eyebrow")
        batch_op.drop_column("empty_text")
        batch_op.drop_column("empty_title")
        batch_op.drop_column("catalogue_title")
        batch_op.drop_column("catalogue_eyebrow")
        batch_op.drop_column("proof3_text")
        batch_op.drop_column("proof3_title")
        batch_op.drop_column("proof2_text")
        batch_op.drop_column("proof2_title")
        batch_op.drop_column("proof1_text")
        batch_op.drop_column("proof1_title")
        batch_op.drop_column("hero_whatsapp_cta")
        batch_op.drop_column("hero_cta")
        batch_op.drop_column("tagline")
