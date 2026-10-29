"""Audit trail cannot be changed, and tampering is detectable."""
from unittest import skipUnless

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.test import TestCase

from audit.models import AuditLogImmutableError, SecurityEvent
from audit.services import log_event, verify_chain


class AppendOnlyTests(TestCase):
    def setUp(self):
        self.event = log_event("LOGIN_FAILED", actor_username="mallory", run_detection=False)

    def test_existing_record_cannot_be_saved_again(self):
        self.event.actor_username = "someone-else"
        with self.assertRaises(AuditLogImmutableError):
            self.event.save()

    def test_record_cannot_be_deleted(self):
        with self.assertRaises(AuditLogImmutableError):
            self.event.delete()

    def test_queryset_update_and_delete_blocked(self):
        with self.assertRaises(AuditLogImmutableError):
            SecurityEvent.objects.filter(pk=self.event.pk).update(actor_username="x")
        with self.assertRaises(AuditLogImmutableError):
            SecurityEvent.objects.all().delete()


class HashChainTests(TestCase):
    def test_each_record_links_to_previous_hash(self):
        first = log_event("LOGIN_SUCCESS", actor_username="alice", run_detection=False)
        second = log_event("LOGOUT", actor_username="alice", run_detection=False)
        self.assertEqual(first.prev_hash, "")
        self.assertEqual(second.prev_hash, first.hash)
        self.assertEqual(verify_chain(), (True, 2, None))

    @skipUnless(connection.vendor == "sqlite", "PostgreSQL blocks the raw UPDATE itself (see trigger test)")
    def test_raw_sql_tampering_is_detected(self):
        log_event("LOGIN_SUCCESS", actor_username="alice", run_detection=False)
        target = log_event("ROLE_CHANGED", actor_username="admin1", details={"to": "admin"}, run_detection=False)
        log_event("LOGOUT", actor_username="alice", run_detection=False)

        # Simulate an attacker with direct database access hiding their action
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE audit_securityevent SET actor_username = 'nobody' WHERE id = %s", [target.pk]
            )

        ok, checked, bad_id = verify_chain()
        self.assertFalse(ok)
        self.assertEqual(bad_id, target.pk)
        with self.assertRaises(CommandError):
            call_command("verify_audit_chain")

    def test_verify_command_reports_intact_chain(self):
        log_event("LOGIN_SUCCESS", actor_username="alice", run_detection=False)
        call_command("verify_audit_chain")  # does not raise


@skipUnless(connection.vendor == "postgresql", "Database trigger exists only on PostgreSQL")
class PostgresTriggerTests(TestCase):
    def setUp(self):
        self.event = log_event("LOGIN_SUCCESS", actor_username="alice", run_detection=False)

    def _raw(self, sql):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(sql, [self.event.pk] if "%s" in sql else None)

    def test_raw_update_rejected_by_database(self):
        with self.assertRaises(DatabaseError):
            self._raw("UPDATE audit_securityevent SET actor_username = 'x' WHERE id = %s")

    def test_raw_delete_rejected_by_database(self):
        with self.assertRaises(DatabaseError):
            self._raw("DELETE FROM audit_securityevent WHERE id = %s")

    def test_truncate_rejected_by_database(self):
        with self.assertRaises(DatabaseError):
            self._raw("TRUNCATE audit_securityevent")
