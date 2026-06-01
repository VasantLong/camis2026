"""add_key_material_fk_and_indexes

Revision ID: 9f971c2c2961
Revises: cb5a4a01a7c5
Create Date: 2026-06-01 22:39:10.460482
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '9f971c2c2961'
down_revision: Union[str, Sequence[str], None] = 'cb5a4a01a7c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. KeyMaterial + activity_id FK + index
    op.add_column('key_materials',
                  sa.Column('activity_id', sa.UUID(), nullable=True))
    op.create_index('ix_key_materials_activity_id', 'key_materials',
                    ['activity_id'], unique=False)
    op.create_foreign_key(None, 'key_materials', 'activities',
                          ['activity_id'], ['id'])

    # 2. ActivityStatusLog composite index (operator_id, created_at)
    op.create_index('idx_status_log_operator_time', 'activity_status_log',
                    ['operator_id', 'created_at'], unique=False)

    # 3. FilingDocs UNIQUE(activity_id) — prevent duplicate packs
    op.create_unique_constraint(None, 'filing_docs', ['activity_id'])

    # 4. Notifications FK: CASCADE → RESTRICT (audit trail independence)
    op.drop_constraint('notifications_user_id_fkey', 'notifications',
                       type_='foreignkey')
    op.create_foreign_key(None, 'notifications', 'users',
                          ['user_id'], ['id'], ondelete='RESTRICT')

    # 5. Documents FK: add SET NULL (files survive activity deletion)
    op.drop_constraint('documents_activity_id_fkey', 'documents',
                       type_='foreignkey')
    op.create_foreign_key(None, 'documents', 'activities',
                          ['activity_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # Reverse documents FK
    op.drop_constraint(None, 'documents', type_='foreignkey')
    op.create_foreign_key('documents_activity_id_fkey', 'documents',
                          'activities', ['activity_id'], ['id'])

    # Reverse notifications FK
    op.drop_constraint(None, 'notifications', type_='foreignkey')
    op.create_foreign_key('notifications_user_id_fkey', 'notifications',
                          'users', ['user_id'], ['id'], ondelete='CASCADE')

    # Reverse filing_docs UNIQUE
    op.drop_constraint(None, 'filing_docs', type_='unique')

    # Reverse status_log index
    op.drop_index('idx_status_log_operator_time', table_name='activity_status_log')

    # Reverse key_materials changes
    op.drop_constraint(None, 'key_materials', type_='foreignkey')
    op.drop_index('ix_key_materials_activity_id', table_name='key_materials')
    op.drop_column('key_materials', 'activity_id')
