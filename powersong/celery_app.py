import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'powersong.settings')

app = Celery('powersong')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.control.rate_limit('powersong.tasks.strava_get_activity', '40/m')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))