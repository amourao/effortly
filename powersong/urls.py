from django.conf.urls import url
from django.contrib import admin

from powersong.view_oauth import strava_oauth, lastfm_oauth
from powersong.view_home import index, about, home, logout
from powersong.view_tops import top

from django.conf import settings
from django.conf.urls import include

urlpatterns = [
	url(r'^$', index, name='index'),
    
    url(r'^home/', home),
    url(r'^about/', about),
    url(r'^logout/', logout),
    url(r'^top/', top),

    url(r'^strava_oauth_callback/', strava_oauth),
    url(r'^lastfm_oauth_callback/', lastfm_oauth),
    
    url(r'^admin/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns