import stravalib

from powersong.sink_or_swim import lastfm_submit, playlist_tools
from powersong.tasks import strava_get_user_info


def submit(activity_id, athlete_id):
    athlete = strava_get_user_info(id=athlete_id)
    client = stravalib.client.Client()
    client.access_token = athlete.strava_token
    client.refresh_token = athlete.strava_refresh_token
    client.token_expires_at = athlete.strava_token_expires_at
    act = client.get_activity(activity_id)
    if act.type == 'Swim':
        total_duration = float(act.elapsed_time)
        start_date = act.start_date
        submit_internal(start_date, total_duration)


def submit_internal(start_date, total_duration):
    tracks = playlist_tools.load_pickled_tracks()
    index = playlist_tools.load_lastest_start()
    index = lastfm_submit.submit_tracks(tracks, start_date, total_duration, index, 0)
    playlist_tools.save_lastest_start(index)
