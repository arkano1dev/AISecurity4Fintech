"""Create audit record table and append-only trigger.

Revision ID: 20261103_create_audit_record_table
Revises: None
Create Date: 2026-11-03
"""

from __future__ import annotations

from alembic import op

revision = "20261103_create_audit_record_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_record (
            id UUID PRIMARY KEY,
            seq BIGINT UNIQUE NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            actor_sub TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            action TEXT NOT NULL,
            payload JSONB NOT NULL,
            payload_hash TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL,
            retention_until TIMESTAMPTZ
        );
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_record_immutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'append-only audit log: UPDATE and DELETE are forbidden';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_record_no_update
        BEFORE UPDATE ON audit_record
        FOR EACH ROW
        EXECUTE FUNCTION audit_record_immutable();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_record_no_delete
        BEFORE DELETE ON audit_record
        FOR EACH ROW
        EXECUTE FUNCTION audit_record_immutable();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_record_no_delete ON audit_record;")
    op.execute("DROP TRIGGER IF EXISTS audit_record_no_update ON audit_record;")
    op.execute("DROP FUNCTION IF EXISTS audit_record_immutable();")
    op.execute("DROP TABLE IF EXISTS audit_record;")
