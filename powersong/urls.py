from django.conf.urls import url
from django.contrib import admin

from powersong.view_oauth import strava_oauth, lastfm_oauth
from powersong.view_home import index, about, home, logout
from powersong.view_tops import top,latest
from powersong.view_detail import activity,song,artist,artists,songs
from powersong.view_main import get_sync_progress, sync, resync_last_fm

from django.conf import settings
from django.conf.urls import include

urlpatterns = [
	url(r'^$', index, name='index'),
    
    url(r'^home/', home),
    url(r'^sync/', sync),
    url(r'^about/', about),
    url(r'^logout/', logout),
    url(r'^top/', top),
    url(r'^activities/', latest),
    url(r'^artists/', artists),
    url(r'^songs/', songs),
    

    url(r'^activity/(?P<activity_id>.*)/', activity),
    url(r'^song/(?P<song_id>.*)/', song),
    url(r'^artist/(?P<artist_id>.*)/', artist),

    url(r'^get_sync_progress/', get_sync_progress),

    url(r'^resync_last_fm/(?P<activity_id>.*)/', resync_last_fm),


    url(r'^strava_oauth_callback/', strava_oauth),
    url(r'^lastfm_oauth_callback/', lastfm_oauth),
    
    url(r'^admin/', admin.site.urls),

    url(r'^async_include/', include('async_include.urls', namespace="async_include")),
]

#urlpatterns += [url(r'^silk/', include('silk.urls', namespace='silk'))]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
