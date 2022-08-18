from django.urls import include, re_path
from django.contrib import admin

from powersong.view_playlists import *
from django.conf import settings
from django.conf.urls import include

urlpatterns = [
    re_path(r'^$', get_playlists),
    re_path(r'^get/(?P<playlist_code>.*)/', get_playlist),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
