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

app.control.rate_limit('powersong.tasks.strava_download_activity', '20/m')
app.control.rate_limit('powersong.tasks.lastfm_download_activity_tracks', '250/m')
app.control.rate_limit('powersong.tasks.lastfm_download_track_info', '250/m')
app.control.rate_limit('powersong.tasks.lastfm_download_artist_info', '250/m')
app.control.rate_limit('powersong.tasks.spotify_get_spotify_ids', '250/m')

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))