"""repair missing tenant tables in the isolated gadgets schema

Revision ID: d8a4c7e91b20
Revises: 4b72c9a81d30
Create Date: 2026-11-26
"""

from alembic import op
from flask import current_app

revision = "d8a4c7e91b20"
down_revision = "4b72c9a81d30"
branch_labels = None
depends_on = None


def upgrade():
    # Earlier revisions were recorded as applied, but their unqualified DDL
    # did not leave the application's tables in the gadgets schema. Rebuild
    # any missing tables from the current ORM metadata, without touching
    # tables in public or altering any existing table.
    op.execute("SET LOCAL search_path TO gadgets")
    db = current_app.extensions["sqlalchemy"]
    db.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    # Intentionally non-destructive: this repair migration must never drop
    # tenant data or shared-schema objects.
    pass
