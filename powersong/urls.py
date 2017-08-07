from django.conf.urls import url
from django.contrib import admin

from powersong.view_oauth import strava_oauth, lastfm_oauth
from powersong.view_home import index, about

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', index, name='home'),
    url(r'^strava_oauth_callback/', strava_oauth),
    url(r'^lastfm_oauth_callback/', lastfm_oauth),
    url(r'^about/', about),
]
