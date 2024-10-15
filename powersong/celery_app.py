import os
from celery import Celery
import django
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'powersong.settings')

django.setup()

app = Celery('powersong')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.add_defaults({
    'CELERYD_HIJACK_ROOT_LOGGER': False,
})

app.autodiscover_tasks()

app.control.rate_limit('powersong.tasks.strava_task', '40/m')
app.control.rate_limit('powersong.tasks.lastfm_task', '250/m')
app.control.rate_limit('powersong.tasks.spotify_task', '250/m')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
