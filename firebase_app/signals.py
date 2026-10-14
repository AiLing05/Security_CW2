from django.db.models.signals import post_save
from django.dispatch import receiver
from firebase_app.models import *
from firebase_app.firebase import generate_firebase_auth_key, send_push_notification
from django.db.models.signals import post_save
from django.dispatch import receiver
from Filedigital.models import *
@receiver(post_save, sender=File)
def notify_user_on_file_upload(sender, instance, created, **kwargs):
    if created:
        print("Signal triggered.")
        owner = instance.uploaded_by
        auth_token= generate_firebase_auth_key()

        try:
            # Get the user's FCM token
            token_entry,created = NotificationToken.objects.get_or_create(owner=owner,token=auth_token)
            fcm_token = FCMTokens.objects.first().fcm_token
            print(token_entry.token)
            if created:
                token_entry.save()
                send_push_notification(
                token_entry.token,
                fcm_token)

            # Firebase auth key (JWT or API key)
            # auth_token = generate_firebase_auth_key()
            print("FCM ",fcm_token)

            # Send notification
            

            print(f"Notification sent to {owner.email}")

        except Exception as e:
            print(f"Error sending notification: {e}")




