"""
Database-level protection for the audit trail (PostgreSQL only).

Even code that bypasses the Django ORM (raw SQL, a psql session using the app
account) cannot UPDATE, DELETE or TRUNCATE audit rows. The retention command
is the single exception: it sets `audit.allow_purge` for its own transaction.
"""
from django.db import migrations

CREATE_SQL = """
CREATE OR REPLACE FUNCTION audit_securityevent_protect() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('audit.allow_purge', true) = 'on' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'audit_securityevent is append-only: %% is not allowed', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_securityevent_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_securityevent
    FOR EACH ROW EXECUTE FUNCTION audit_securityevent_protect();

CREATE TRIGGER audit_securityevent_no_truncate
    BEFORE TRUNCATE ON audit_securityevent
    FOR EACH STATEMENT EXECUTE FUNCTION audit_securityevent_protect();
"""

DROP_SQL = """
DROP TRIGGER IF EXISTS audit_securityevent_no_truncate ON audit_securityevent;
DROP TRIGGER IF EXISTS audit_securityevent_no_update_delete ON audit_securityevent;
DROP FUNCTION IF EXISTS audit_securityevent_protect();
"""


def create_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(CREATE_SQL)


def drop_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunPython(create_trigger, drop_trigger)]
