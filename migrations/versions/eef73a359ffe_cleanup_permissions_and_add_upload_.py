"""cleanup_permissions_and_add_upload_document

Revision ID: eef73a359ffe
Revises: 9f971c2c2961
Create Date: 2026-06-01 22:59:26.738948

Delete 4 unused permissions, add upload_document, update role_permissions.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'eef73a359ffe'
down_revision: Union[str, Sequence[str], None] = '9f971c2c2961'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE name IN (
                'upload_plan', 'upload_security_material',
                'upload_approval', 'update_approval_status'
            )
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE name IN (
            'upload_plan', 'upload_security_material',
            'upload_approval', 'update_approval_status'
        )
    """)
    op.execute("""
        INSERT INTO permissions (name, resource, action)
        VALUES ('upload_document', 'documents', 'upload')
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name IN ('Promoter', 'SecurityOfficer', 'SecurityManager', 'GovLiaison')
          AND p.name = 'upload_document'
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE name = 'upload_document'
        )
    """)
    op.execute("DELETE FROM permissions WHERE name = 'upload_document'")
    op.execute("""
        INSERT INTO permissions (name, resource, action) VALUES
            ('upload_plan', 'activities', 'upload_plan'),
            ('upload_security_material', 'documents', 'upload'),
            ('upload_approval', 'documents', 'upload_approval'),
            ('update_approval_status', 'activities', 'update_approval_status')
        ON CONFLICT (name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'Promoter' AND p.name = 'upload_plan'
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'SecurityOfficer' AND p.name = 'upload_security_material'
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'GovLiaison'
          AND p.name IN ('upload_approval', 'update_approval_status')
        ON CONFLICT DO NOTHING
    """)
