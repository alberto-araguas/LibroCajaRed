"""Track user that created each transaction.

Revision ID: 20260510_0004
Revises: 20260510_0003
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260510_0004"
down_revision: Union[str, None] = "20260510_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
    op.create_index("ix_transactions_created_by_user_id", "transactions", ["created_by_user_id"])
    op.create_foreign_key(
        "fk_transactions_created_by_user_id",
        "transactions",
        "users",
        ["created_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_transactions_created_by_user_id", "transactions", type_="foreignkey")
    op.drop_index("ix_transactions_created_by_user_id", table_name="transactions")
    op.drop_column("transactions", "created_by_user_id")
