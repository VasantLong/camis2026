"""initial_baseline

Revision ID: cb5a4a01a7c5
Revises:
Create Date: 2026-06-01 22:36:13.887953

Baseline marker — all tables already exist in the database from init-scripts.
No DDL executed; this revision marks the starting point for future migrations.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'cb5a4a01a7c5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline — schema already exists, nothing to do."""
    pass


def downgrade() -> None:
    """Cannot downgrade from baseline."""
    pass
