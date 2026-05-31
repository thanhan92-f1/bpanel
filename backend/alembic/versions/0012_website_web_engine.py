"""add per-website web_engine field

Revision ID: 0012_website_web_engine
Revises: 0011_website_waf_enabled
Create Date: 2026-05-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_website_web_engine"
down_revision: Union[str, None] = "0011_website_waf_enabled"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "websites",
        sa.Column("web_engine", sa.String(50), nullable=False, server_default="nginx"),
    )


def downgrade() -> None:
    op.drop_column("websites", "web_engine")
