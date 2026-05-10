"""Add contact fields to counterparties.

Revision ID: 20260510_0002
Revises: 20260510_0001
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260510_0002"
down_revision: Union[str, None] = "20260510_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("counterparties", sa.Column("dni_cif", sa.String(length=32), nullable=True))
    op.add_column("counterparties", sa.Column("address", sa.String(length=255), nullable=True))
    op.add_column("counterparties", sa.Column("phone", sa.String(length=40), nullable=True))
    op.add_column("counterparties", sa.Column("email", sa.String(length=180), nullable=True))


def downgrade() -> None:
    op.drop_column("counterparties", "email")
    op.drop_column("counterparties", "phone")
    op.drop_column("counterparties", "address")
    op.drop_column("counterparties", "dni_cif")
