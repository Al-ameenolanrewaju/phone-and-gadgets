"""add editable social profile links to storefront settings

Revision ID: 4b72c9a81d30
Revises: c9a7e21f4d60
Create Date: 2026-11-21
"""
from alembic import op
import sqlalchemy as sa

revision = "4b72c9a81d30"
down_revision = "c9a7e21f4d60"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("store_settings") as batch_op:
        batch_op.add_column(sa.Column("instagram_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("facebook_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("tiktok_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("x_url", sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table("store_settings") as batch_op:
        batch_op.drop_column("x_url")
        batch_op.drop_column("tiktok_url")
        batch_op.drop_column("facebook_url")
        batch_op.drop_column("instagram_url")
