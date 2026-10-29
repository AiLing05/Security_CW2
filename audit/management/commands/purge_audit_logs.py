from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from audit import conf
from audit.models import EventType, SecurityEvent
from audit.services import log_event


class Command(BaseCommand):
    help = "Delete audit records older than the retention period (AUDIT_LOG_RETENTION_DAYS)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, help="Override the retention period in days.")
        parser.add_argument("--dry-run", action="store_true", help="Only report how many records would be removed.")

    def handle(self, *args, **options):
        days = options["days"] or conf.retention_days()
        if days < 30:
            raise CommandError("Refusing to keep less than 30 days of audit history.")
        cutoff = timezone.now() - timedelta(days=days)
        expired = SecurityEvent.objects.filter(timestamp__lt=cutoff)
        count = expired.count()

        if options["dry_run"]:
            self.stdout.write(f"{count} audit record(s) older than {days} days would be purged.")
            return

        with transaction.atomic():
            if connection.vendor == "postgresql":
                # Allow deletes for this transaction only (see the DB trigger)
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL audit.allow_purge = 'on'")
            deleted, _ = expired._retention_purge()

        anchor = SecurityEvent.objects.order_by("id").values_list("prev_hash", flat=True).first()
        log_event(
            EventType.AUDIT_LOG_PURGED,
            details={"deleted": deleted, "retention_days": days, "cutoff": cutoff.isoformat(), "chain_anchor": anchor},
        )
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted} audit record(s) older than {days} days."))
