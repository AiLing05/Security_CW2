from django.core.management.base import BaseCommand, CommandError

from audit.services import verify_chain


class Command(BaseCommand):
    help = "Recompute the audit hash chain and report the first tampered record, if any."

    def handle(self, *args, **options):
        ok, checked, bad_id = verify_chain()
        if not ok:
            raise CommandError(f"Audit chain BROKEN at record id={bad_id} (after {checked} valid records).")
        self.stdout.write(self.style.SUCCESS(f"Audit chain intact: {checked} record(s) verified."))
