"""store uploaded image bytes in the database

Revision ID: b61c8d5a92ef
Revises: 82860e178110
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa

revision = "b61c8d5a92ef"
down_revision = "82860e178110"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("business") as batch_op:
        batch_op.add_column(sa.Column("logo_data", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("logo_mime_type", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("banner_data", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("banner_mime_type", sa.String(length=50), nullable=True))
    with op.batch_alter_table("product_image") as batch_op:
        batch_op.add_column(sa.Column("image_data", sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column("mime_type", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("original_filename", sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table("product_image") as batch_op:
        batch_op.drop_column("original_filename")
        batch_op.drop_column("mime_type")
        batch_op.drop_column("image_data")
    with op.batch_alter_table("business") as batch_op:
        batch_op.drop_column("banner_mime_type")
        batch_op.drop_column("banner_data")
        batch_op.drop_column("logo_mime_type")
        batch_op.drop_column("logo_data")
