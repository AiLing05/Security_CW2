
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from Filedigital.models import File
from firebase_app.models import NotificationToken, FCMTokens
from firebase_app.firebase import (
    generate_firebase_auth_key,
    send_push_notification,
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=File)
def notify_user_on_file_upload(sender, instance, created, **kwargs):
    if not created:
        return

    owner = instance.uploaded_by

    def send_notification():
        try:
            auth_token = generate_firebase_auth_key()

            token_entry, token_created = (
                NotificationToken.objects.get_or_create(
                    owner=owner,
                    token=auth_token,
                )
            )

            fcm_entry = FCMTokens.objects.first()

            if fcm_entry is None or not fcm_entry.fcm_token:
                logger.warning(
                    "Firebase notification skipped: no FCM token configured."
                )
                return

            if token_created:
                send_push_notification(
                    token_entry.token,
                    fcm_entry.fcm_token,
                )

            logger.info(
                "Firebase notification processing completed for %s",
                owner.pk,
            )

        except Exception:
            logger.exception(
                "Firebase notification failed for user %s",
                owner.pk,
            )

    # Notifications run only after a successful database commit.
    transaction.on_commit(send_notification)
