# # from celery import shared_task
# # from django.core.mail import send_mail
# # from django.conf import settings

# # @shared_task
# # def escalate_pending_approval(approval_id):
# #     from .models import FileApproval
# #     try:
# #         approval = FileApproval.objects.get(id=approval_id)
# #         if approval.status == 'pending':
# #             # Perform escalation actions
# #             print(f"Approval {approval_id} is still pending. Escalating...")

# #             # Send escalation email
# #             send_mail(
# #                 subject='Approval Escalation Alert',
# #                 message=f'The file "{approval.file.name}" is still pending approval after 24 hours.',
# #                 from_email=settings.DEFAULT_FROM_EMAIL,
# #                 recipient_list=[settings.ADMIN_EMAIL],  # Replace with actual recipient
# #                 fail_silently=True,
# #             )
# #     except FileApproval.DoesNotExist:
# #         print(f"Approval with ID {approval_id} not found.")
# #         return "Approval not found."

# #     return "Escalation checked."

# # celery -A fileproject worker --loglevel=info --pool=solo


# import logging
# from celery import shared_task
# from django.core.mail import send_mail
# from django.conf import settings

# # Set up a logger
# logger = logging.getLogger(__name__)

# @shared_task
# def escalate_pending_approval(approval_id):
#     from .models import FileApproval
#     try:
#         approval = FileApproval.objects.get(id=approval_id)
#         if approval.status == 'pending':
#             # Perform escalation actions
#             logger.info(f"Approval {approval_id} is still pending. Escalating...")

#             # Send escalation email
#             send_mail(
#                 subject='Approval Escalation Alert',
#                 message=f'The file "{approval.file.name}" is still pending approval after 24 hours.',
#                 from_email=settings.DEFAULT_FROM_EMAIL,
#                 recipient_list=[settings.ADMIN_EMAIL],  
#                 fail_silently=True,
#             )
#             logger.info(f"Escalation email sent for approval {approval_id}.")
#         else:
#             logger.info(f"Approval {approval_id} status is not pending.")
#     except FileApproval.DoesNotExist:
#         logger.error(f"Approval with ID {approval_id} not found.")
#         return "Approval not found."
#     except Exception as e:
#         logger.error(f"Error while escalating approval {approval_id}: {e}")
#         return f"Error: {str(e)}"

#     return "Escalation checked."
