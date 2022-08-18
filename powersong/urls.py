from django.urls import include, re_path

from django.contrib import admin

from powersong.view_oauth import strava_oauth, lastfm_oauth, spotify_oauth, spotify_refresh_token_endpoint
from powersong.view_home import index, home, logout, demo
from powersong.view_tops import top, top_song_artist, top_activities, top_global_song_artist
from powersong.view_detail import activity, song, artist, artists, songs
from powersong.view_main import about, stats, get_sync_progress, sync, sync_spotify, resync_last_fm, resync_spotify, \
    detailed, global_top, send_song_info_to_strava
from powersong.view_settings import setting, flag_activity, flag_artist, flag_song, flag_effort, remove_spotify, \
    remove_lastfm, delete_account
from powersong.view_webhooks import strava_webhooks_callback
from django.conf import settings
from django.conf.urls import include
import powersong.urls_playlists

urlpatterns = [
    re_path(r'^$', index, name='index'),

    re_path(r'^demo/', demo),

    re_path(r'^home/', home),
    re_path(r'^sync/', sync),
    re_path(r'^sync_spotify/', sync_spotify),
    re_path(r'^about/', about),
    re_path(r'^stats/', stats),
    re_path(r'^settings/', setting),
    re_path(r'^logout/', logout),
    re_path(r'^top/', top),
    re_path(r'^top_song_artist/', top_song_artist),
    re_path(r'^top_global/', top_global_song_artist),
    re_path(r'^top_activities/', top_activities),

    re_path(r'^detailed/', detailed),
    re_path(r'^global/', global_top),
    re_path(r'^artists/', artists),
    re_path(r'^songs/', songs),

    re_path(r'^activity/(?P<activity_id>.*)/', activity),
    re_path(r'^flag_activity/(?P<activity_id>.*)/', flag_activity),
    re_path(r'^flag_effort/(?P<effort_id>.*)/', flag_effort),

    re_path(r'^song/(?P<song_id>.*)/', song),
    re_path(r'^flag_song/(?P<song_id>.*)/', flag_song),

    re_path(r'^artist/(?P<artist_id>.*)/', artist),
    re_path(r'^flag_artist/(?P<artist_id>.*)/', flag_artist),

    re_path(r'^get_sync_progress/', get_sync_progress),

    re_path(r'^resync_last_fm/(?P<activity_id>.*)/', resync_last_fm),
    re_path(r'^resync_spotify/(?P<activity_id>.*)/', resync_spotify),
    re_path(r'^send_song_info_to_strava/(?P<activity_id>.*)/', send_song_info_to_strava),

    re_path(r'^strava_webhooks/', strava_webhooks_callback),

    re_path(r'^strava_oauth_callback/', strava_oauth),
    re_path(r'^strava_oauth_refresh/', spotify_refresh_token_endpoint),

    re_path(r'^lastfm_oauth_callback/', lastfm_oauth),
    re_path(r'^spotify_oauth_callback/', spotify_oauth),

    re_path(r'^remove_lastfm/', remove_lastfm),
    re_path(r'^remove_spotify/', remove_spotify),
    re_path(r'^delete_account/', delete_account),

    re_path(r'^admin/', admin.site.urls),

    re_path(r'^playlists/', include(powersong.urls_playlists)),

    re_path(r'^async_include/', include('async_include.urls', namespace="async_include")),
]

# urlpatterns += [re_path(r'^silk/', include('silk.urls', namespace='silk'))]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      re_path(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns
