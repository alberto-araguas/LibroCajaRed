"""Initial cashbook schema.

Revision ID: 20260510_0001
Revises:
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260510_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_accounts_code"),
    )

    op.create_table(
        "counterparties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("normalized_name", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", name="uq_counterparties_normalized_name"),
    )

    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("normalized_name", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name", name="uq_concepts_normalized_name"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("counterparty_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            server_onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint("type in ('income', 'expense')", name="ck_transactions_type"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], name="fk_transactions_account_id"),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], name="fk_transactions_concept_id"),
        sa.ForeignKeyConstraint(
            ["counterparty_id"],
            ["counterparties.id"],
            name="fk_transactions_counterparty_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_concept_id", "transactions", ["concept_id"])
    op.create_index("ix_transactions_counterparty_id", "transactions", ["counterparty_id"])
    op.create_index("ix_transactions_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_type", "transactions", ["type"])

    accounts_table = sa.table(
        "accounts",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
    )
    op.bulk_insert(
        accounts_table,
        [
            {"code": "cash", "name": "Efectivo"},
            {"code": "card", "name": "Tarjeta"},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_type", table_name="transactions")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_index("ix_transactions_counterparty_id", table_name="transactions")
    op.drop_index("ix_transactions_concept_id", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("concepts")
    op.drop_table("counterparties")
    op.drop_table("accounts")
