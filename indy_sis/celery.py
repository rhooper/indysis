import os

from django.conf import settings
import raven
from raven.contrib.celery import register_signal, register_logger_signal
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'indy_sis.settings')

if settings.RAVEN_DSN:
    class Celery(Celery):
        def on_configure(self):
            client = raven.Client(settings.RAVEN_DSN)
            register_logger_signal(client)
            register_signal(client)

app = Celery('indy_sis')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
