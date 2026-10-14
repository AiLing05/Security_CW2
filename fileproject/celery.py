# # fileproject/celery.py

# import os
# from celery import Celery


# import os
# from celery import Celery

# # Set default Django settings module for Celery
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fileproject.settings")  

# app = Celery("fileproject") 

# # Load task modules from all registered Django app configs.
# app.config_from_object("django.conf:settings", namespace="CELERY")
# from django.conf import settings
# app.conf.update(
#     broker_url=settings.CELERY_BROKER_URL,
#     result_backend=settings.CELERY_RESULT_BACKEND,
# )

# # Autodiscover tasks in all installed apps
# app.autodiscover_tasks()




