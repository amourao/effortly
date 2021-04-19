from django.conf.urls import url
from django.contrib import admin

from powersong.view_playlists import *
from django.conf import settings
from django.conf.urls import include

urlpatterns = [
    url(r'^$', get_playlists),
    url(r'^get/(?P<playlist_code>.*)/', get_playlist),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
