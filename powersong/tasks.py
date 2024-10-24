import stravalib.client

from celery import shared_task, chain, group
from celery.result import AsyncResult, GroupResult
from celery import current_app
from datetime import datetime, timedelta, timezone

import time, json
import math
from bisect import bisect_left

import numpy as np
import base64

from django.conf import settings
import requests

import spotipy

from powersong.models import *
from powersong.spotify_aux import spotify_get_recent_tracks, spotify_refresh_token, spotify_get_recent_tracks_before
from urllib.error import HTTPError

from urllib.parse import quote_plus

import logging, time

logger = logging.getLogger(__name__)


def strava_refresh_oauth(athlete_id):
    athletes = Athlete.objects.filter(athlete_id=athlete_id)

    if not athletes:
        return None

    athlete = athletes[0]

    refresh_token = athlete.strava_refresh_token

    strava_client = stravalib.client.Client()

    refresh_response = strava_client.refresh_access_token(client_id=settings.STRAVA_CLIENT_ID,
                                                          client_secret=settings.STRAVA_CLIENT_SECRET,
                                                          refresh_token=refresh_token)
    access_token = refresh_response['access_token']
    refresh_token = refresh_response['refresh_token']
    expires_at = refresh_response['expires_at']

    athlete.strava_token = access_token
    athlete.strava_refresh_token = refresh_token
    athlete.strava_token_expires_at = expires_at
    athlete.save()

    return athlete


def unpack_chain(nodes):
    while nodes.children:
        yield nodes.children[0]
        nodes = nodes.children[0]
    yield nodes


def count_finished(job_result):
    pending = 0
    failure = 0
    success = 0
    i = 0
    for t in unpack_chain(job_result):
        if t.status == 'SUCCESS':
            success += 1
        elif t.status == 'FAILURE':
            failure += 1
        elif t.status == 'PENDING':
            pending += 1
        i += 1
    return int(pending / 4), int(success / 4), int(failure / 4), int(i / 4)


@shared_task
def clear_sync_id(athlete_id):
    athlete = Athlete.objects.filter(id=athlete_id)[0]
    athlete.last_celery_task_id = "00000000-0000-0000-0000-000000000000"
    athlete.save()


########################## Strava API tasks ##########################

def strava_nop():
    return None


def strava_op(access_token):
    # client = stravalib.client.Client()
    # client.access_token = access_token
    # athlete_api = client.get_athlete()
    return None


def strava_generate_nops(count):
    new_activities = [strava_task.s('strava_nop', ()) for i in range(count)]
    promise = group(*new_activities)
    job_result = promise.delay()


def strava_send_song_activities(act_id_s):
    if len(act_id_s) != 1 or act_id_s[0] == None:
        return (None,)

    act_id = act_id_s[0]
    act = Activity.objects.filter(activity_id=act_id)

    if not act:
        return (None,)

    act = act[0]

    if not act.athlete.share_activity_songs:
        return (None,)

    # act.athlete.save()
    ath = strava_get_user_info(id=act.athlete.athlete_id)

    client = stravalib.client.Client()
    client.access_token = ath.strava_token
    client.refresh_token = ath.strava_refresh_token
    client.token_expires_at = ath.strava_token_expires_at

    activity = client.get_activity(act_id)
    description = activity.description

    if description:
        start = description.find("Songs listened during activity:")
        end = description.rfind("effortly(dot)run/activity/" + str(act_id))
        if start != -1 and end != -1:
            end += len("effortly(dot)run/activity/" + str(act_id))
            description = description[:start] + description[end:]
        else:
            start = description.find("Songs listened during activity:")
            end = description.rfind("- by effortly(dot)run")
            if start != -1 and end != -1:
                end += len("- by effortly(dot)run")
                description = description[:start] + description[end:]
            else:
                start = description.find("Songs listened during activity:")
                end = description.rfind("- by")
                if start != -1 and end != -1:
                    end += len("- by")
                    description = description[:start] + description[end:]
                else:
                    start = description.find("No songs found")
                    end = description.rfind("- by effortly(dot)run")
                    if start != -1 and end != -1:
                        end += len("- by effortly(dot)run")
                        description = description[:start] + description[end:]
                    else:
                        start = description.find("No songs found")
                        end = description.rfind("- by")
                        if start != -1 and end != -1:
                            end += len("- by")
                            description = description[:start] + description[end:]
            description = act.activity_share_message + '\n' + description
    else:
        description = act.activity_share_message

    client.update_activity(act_id, description=description.strip())
    return (None,)


def strava_download_activity(act):
    ath = strava_get_user_info(id=act['athlete_id'])

    if ath == None:
        return (None,)

    client = stravalib.client.Client()
    client.access_token = ath.strava_token
    client.refresh_token = ath.strava_refresh_token
    client.token_expires_at = ath.strava_token_expires_at

    stored_act = create_activity_from_dict(act)

    if stored_act == None:
        act_ign = ActivitiesToIgnore()
        act_ign.activity_id = act['id']
        act_ign.save()
        return (None,)
    try:
        stream_keys = ['time', 'distance', 'heartrate', 'watts', 'altitude', 'cadence', 'velocity_smooth',
                       'grade_smooth', 'moving']

        # actStream = client.get_activity_streams(act['id'],types=['time','latlng','distance','altitude','velocity_smooth','heartrate','watts','moving','grade_smooth'])
        act_stream_api = client.get_activity_streams(act['id'], types=stream_keys, resolution="high")
        act_stream = {}
        for k in stream_keys:
            if k in act_stream_api:
                act_stream[k] = act_stream_api[k].data
        # stored_act.detailed_vectors = act_stream
        stored_act.save()
    except Exception as e:
        logger.error("Exception on activity {}".format(act['id']))
        logger.error(e)

        act_ign = ActivitiesToIgnore()
        act_ign.activity_id = act['id']
        act_ign.save()
        return (None,)
    return (act_stream, stored_act.activity_id)


@shared_task
def strava_task(*args, **kwargs):
    prev_args = []
    new_args = []
    if len(args) == 3:
        prev_args, function, new_args = args
    elif len(args) == 2:
        function, new_args = args

    if prev_args != []:
        nargs = [tuple(prev_args)] + new_args
    else:
        nargs = new_args

    if function == 'strava_download_activity':
        return strava_download_activity(*nargs, **kwargs)
    elif function == 'strava_send_song_activities':
        return strava_send_song_activities(*nargs, **kwargs)
    elif function == 'strava_nop':
        return strava_nop()
    elif function == 'strava_op':
        return strava_op(*nargs, **kwargs)
    return None


########################## END Strava API tasks ##########################

########################## Last.fm API tasks ##########################

def lastfm_download_activity_tracks(act_stream_stored_act):
    if act_stream_stored_act == None or act_stream_stored_act == (None,):
        return None

    (act_stream, stored_act_id) = act_stream_stored_act

    stored_act = strava_get_activity_by_id(stored_act_id)

    athelte = strava_get_user_info(id=stored_act.athlete.athlete_id)

    poweruser = Athlete.objects.filter(id=stored_act.athlete.id)[0].poweruser_set.all()[0]

    start = strava_get_start_timestamp(stored_act.start_date - timedelta(seconds=600))
    end = strava_get_start_timestamp(stored_act.start_date + timedelta(seconds=int(stored_act.elapsed_time)))

    method = 'user.getrecenttracks'
    url = settings.LASTFM_API_RECENT.format(method, settings.LASTFM_API_KEY, poweruser.listener.nickname, start, end)
    response = requests.get(url).json()

    # with open('data_in_{}.json'.format(stored_act_id), 'w') as outfile:
    #    json.dump(response, outfile)

    lastfm_tracks = response
    return act_stream, stored_act_id, lastfm_tracks


def lastfm_download_track_info(artist_name, track_name):
    method = 'track.getInfo'

    url = settings.LASTFM_API_TRACK.format(method, settings.LASTFM_API_KEY, quote_plus(artist_name),
                                           quote_plus(track_name))

    response = requests.get(url).json()

    if 'lfm' in response:
        response = response['lfm']
    track_json = response['track']
    logger.debug(url)
    logger.debug(response)
    track = lastfm_get_track(artist_name, track_name)

    if track == None:
        track = Song()

    if 'mbid' in track_json and track_json['mbid'].strip() != "":
        track.mbid = track_json['mbid']

    track.duration = int(track_json['duration'])
    track.listeners_count = int(track_json['listeners'])
    track.plays_count = int(track_json['playcount'])
    track.url = track_json['url']
    track.last_sync_date = datetime.now(timezone.utc)

    track.save()


def lastfm_download_artist_info(artist_name, mb_id=None):
    method = 'artist.getInfo'
    if mb_id:
        url = settings.LASTFM_API_ARTIST_MB.format(method, settings.LASTFM_API_KEY, mb_id)
    else:
        url = settings.LASTFM_API_ARTIST.format(method, settings.LASTFM_API_KEY, quote_plus(artist_name))

    response = requests.get(url).json()

    if 'lfm' in response:
        response = response['lfm']
    artist_json = response['artist']

    artist = lastfm_get_artist(artist_name, mb_id)

    if artist == None:
        artist = Artist()

    if 'mbid' in artist_json and artist_json['mbid'].strip() != "":
        artist.mbid = artist_json['mbid']

    artist.listeners_count = int(artist_json['stats']['listeners'])
    artist.plays_count = int(artist_json['stats']['playcount'])
    artist.url = artist_json['url']
    artist.last_sync_date = datetime.now(timezone.utc)

    artist.save()


@shared_task
def lastfm_task(*args, **kwargs):
    prev_args = []
    new_args = []
    if len(args) == 3:
        prev_args, function, new_args = args
    elif len(args) == 2:
        function, new_args = args

    if prev_args != []:
        nargs = [tuple(prev_args)] + new_args
    else:
        nargs = new_args

    if function == 'lastfm_download_activity_tracks':
        return lastfm_download_activity_tracks(*nargs, **kwargs)
    elif function == 'lastfm_download_track_info':
        return lastfm_download_track_info(*nargs, **kwargs)
    elif function == 'lastfm_download_artist_info':
        return lastfm_download_artist_info(*nargs, **kwargs)
    return None


########################## END Last.fm API tasks ##########################

########################## Spotify API tasks ##########################

def spotify_get_spotify_ids(code, token, reftoken, song_id):
    try:
        song = Song.objects.filter(original_song_id=song_id)[0]

        athlete_id = 1

        sp = spotipy.Spotify(auth=token)
        query = "track:\"{}\" artist:\"{}\"".format(song.title, song.artist_name)
        # out_file = "{}-{}.json".format(song.title.replace(' ','_'),song.artist_name.replace(' ','_'))

        try:
            results = sp.search(q=query, type="track", limit=20)
        except:
            token = spotify_refresh_token(code, token, reftoken, athlete_id)
            sp = spotipy.Spotify(auth=token)
            results = sp.search(q=query, type="track", limit=20)

        if not song.spotify_id and results['tracks'] and results['tracks']['items']:
            song.spotify_id = results['tracks']['items'][0]['id']
            song.duration = results['tracks']['items'][0]['duration_ms']
            song.save()

        artist = song.artist
        if not artist.spotify_id:
            artist.spotify_id = results['artists'][0]['id']
            artist.save()
    except:
        return


def spotify_update_track(song_id):
    song = Song.objects.filter(original_song_id=song_id)[0]
    track_id = song.spotify_id

    poweruser = PowerUser.objects.all()[0]
    athlete_id = poweruser.athlete_id

    code = poweruser.listener_spotify.spotify_code
    token = poweruser.listener_spotify.spotify_token
    reftoken = poweruser.listener_spotify.spotify_refresh_token

    sp = spotipy.Spotify(auth=token)
    # out_file = "{}-{}.json".format(song.title.replace(' ','_'),song.artist_name.replace(' ','_'))

    try:
        results = sp.track(track_id)
    except:
        token = spotify_refresh_token(code, token, reftoken, athlete_id)
        sp = spotipy.Spotify(auth=token)
        results = sp.track(track_id)

    image_url = None
    if results['album']['images']:
        image_url = results['album']['images'][0]['url']

    if image_url != None:
        song.image_url = image_url
    elif song.image_url:
        r = requests.get(song.image_url)
        if song.image_url == None or r.status_code != 200:
            song.image_url = ''
    else:
        song.image_url = ''

    if song.duration == 0:
        song.duration = results['duration_ms']

    artist = song.artist
    if not artist.spotify_id:
        artist.spotify_id = results['artists'][0]['id']
        artist.save()

    song.save()


def spotify_update_artist(artist_id):
    artist = Artist.objects.filter(id=artist_id)[0]
    artist_spotify_id = artist.spotify_id

    poweruser = PowerUser.objects.all()[0]
    athlete_id = poweruser.athlete_id

    code = poweruser.listener_spotify.spotify_code
    token = poweruser.listener_spotify.spotify_token
    reftoken = poweruser.listener_spotify.spotify_refresh_token

    sp = spotipy.Spotify(auth=token)

    try:
        results = sp.artist(artist_spotify_id)
    except:
        token = spotify_refresh_token(code, token, reftoken, athlete_id)
        sp = spotipy.Spotify(auth=token)
        results = sp.artist(artist_spotify_id)

    image_url = None
    if results['images']:
        image_url = results['images'][0]['url']

    logger.error(image_url)

    if image_url != None:
        artist.image_url = image_url
    elif artist.image_url:
        r = requests.get(artist.image_url)
        if artist.image_url == None or r.status_code != 200:
            artist.image_url = ''
    else:
        artist.image_url = ''

    artist.save()


def spotify_download_activity_tracks(act_stream_stored_act, force):
    if act_stream_stored_act == None or act_stream_stored_act == (None,):
        return None

    (act_stream, stored_act_id) = act_stream_stored_act
    stored_act = strava_get_activity_by_id(stored_act_id)

    athelte = strava_get_user_info(id=stored_act.athlete.athlete_id)
    athlete_id = athelte.athlete_id

    poweruser = Athlete.objects.filter(athlete_id=athlete_id)[0].poweruser_set.all()[0]
    code = poweruser.listener_spotify.spotify_code
    token = poweruser.listener_spotify.spotify_token
    reftoken = poweruser.listener_spotify.spotify_refresh_token

    start = strava_get_start_timestamp(stored_act.start_date - timedelta(seconds=600))
    end = strava_get_start_timestamp(stored_act.start_date + timedelta(seconds=int(stored_act.elapsed_time)))

    try:
        spotify_tracks = spotify_get_recent_tracks_before(token, athlete_id, start, end, force)
    except:
        token = spotify_refresh_token(code, token, reftoken, athlete_id)
        spotify_tracks = spotify_get_recent_tracks_before(token, athlete_id, start, end, force)

    if not spotify_tracks['recenttracks']['track']:
        resync_activity(stored_act_id, athlete_id, True)

    return act_stream, stored_act_id, spotify_tracks


def spotify_multi_track_get_stats(song_ids):
    track_ids = ["spotify:track:{}".format(spotify_id) for spotify_id in song_ids]

    poweruser = PowerUser.objects.all()[0]
    athlete_id = poweruser.athlete_id

    sp = spotipy.Spotify(auth=poweruser.listener_spotify.spotify_token)
    # out_file = "{}-{}.json".format(song.title.replace(' ','_'),song.artist_name.replace(' ','_'))

    try:
        results = sp.audio_features(track_ids)
    except:
        token = spotify_refresh_token(poweruser.listener_spotify.spotify_code, poweruser.listener_spotify.spotify_token, poweruser.listener_spotify.spotify_refresh_token, athlete_id)
        sp = spotipy.Spotify(auth=token)
        results = sp.audio_features(track_ids)

    for song in results:
        if song:
            for track in Song.objects.filter(spotify_id=song["id"]):
                track.danceability = song["danceability"]
                track.energy = song["energy"]
                track.key = song["key"]
                track.loudness = song["loudness"]
                track.mode = song["mode"]
                track.speechiness = song["speechiness"]
                track.acousticness = song["acousticness"]
                track.instrumentalness = song["instrumentalness"]
                track.liveness = song["liveness"]
                track.valence = song["valence"]
                track.bpm = song["tempo"]
                track.time_signature = song["time_signature"]
                track.duration = song["duration_ms"]
                track.save()


@shared_task
def spotify_task(*args, **kwargs):
    prev_args = []
    new_args = []
    if len(args) == 3:
        prev_args, function, new_args = args
    elif len(args) == 2:
        function, new_args = args

    if prev_args != []:
        nargs = [tuple(prev_args)] + new_args
    else:
        nargs = new_args

    if function == 'spotify_download_activity_tracks':
        return spotify_download_activity_tracks(*nargs, **kwargs)
    elif function == 'spotify_get_spotify_ids':
        return spotify_get_spotify_ids(*nargs, **kwargs)
    elif function == 'spotify_update_track':
        return spotify_update_track(*nargs, **kwargs)
    elif function == 'spotify_update_artist':
        return spotify_update_artist(*nargs, **kwargs)
    elif function == 'spotify_multi_track_get_stats':
        return spotify_multi_track_get_stats(*nargs, **kwargs)
    return None


########################## END Spotify API tasks ##########################

########################## Internal tasks ##########################

@shared_task
def activity_to_efforts(act_stream_stored_act_id_lastfm_tracks):
    try:
        if act_stream_stored_act_id_lastfm_tracks == None or act_stream_stored_act_id_lastfm_tracks == (None,):
            return (None,)
        act_stream, stored_act_id, lastfm_tracks = act_stream_stored_act_id_lastfm_tracks
        stored_act = strava_get_activity_by_id(stored_act_id)

        if lastfm_tracks:
            if not 'recenttracks' in lastfm_tracks:
                logger.error("Bad response in activity {}".format(stored_act_id))
                logger.error(lastfm_tracks)
                return (None,)
            else:
                songs = lastfm_tracks['recenttracks']['track'][::-1]
        else:
            logger.debug("No songs in activity {}".format(stored_act_id))
            return (stored_act_id,)

        act_avg_speed = stored_act.avg_speed
        act_avg_hr = stored_act.avg_hr

        start_time = stored_act.start_date
        elapsed_time = timedelta(seconds=int(stored_act.elapsed_time))

        (total_ascent, total_descent, _, _) = get_ascent_in_interval(act_stream, 0, elapsed_time.seconds, 'altitude')

        stored_act.total_ascent = total_ascent
        stored_act.total_descent = -total_descent

        stored_act.save()

        stored_act.effort_set.all().delete()

        act_start_timestamp = strava_get_start_timestamp(start_time)

        last_speed = 0
        last_hr = 0
        last_watts = 0
        last_cadence = 0

        effort_idx_in_act = 0
        idx = 0
        while idx < len(songs):
            song_api = songs[idx]
            if not 'date' in song_api:
                break
            start = int(song_api['date']['uts']) - act_start_timestamp

            # multiple similar scrobbles protection
            while (idx + 1) < len(songs) and ((song_api['url'] == songs[idx + 1]['url']) or (
                    'date' in songs[idx + 1] and int(song_api['date']['uts']) == int(
                    songs[idx + 1]['date']['uts']))):  # if the next song is the same, do not create new song
                song_api = songs[idx + 1]
                idx += 1

            if (idx + 1) < len(songs) and 'date' in songs[idx + 1]:
                end = int(songs[idx + 1]['date']['uts']) - act_start_timestamp
                if end > elapsed_time.seconds:
                    end = elapsed_time.seconds
            else:
                end = elapsed_time.seconds

            idx += 1

            if start <= 0:
                start = 0
            if start < 0 or end <= 0:
                continue
            if start > elapsed_time.seconds:
                continue
            if (end - start) <= 0:
                continue

            song = create_song_from_dict(song_api)

            # stream_keys = ['time','distance','heartrate','watts','altitude']
            # time:     integer seconds
            # latlng:     floats [latitude, longitude]
            # distance:   float meters
            # altitude:   float meters
            # velocity_smooth:    float meters per second
            # heartrate:  integer BPM
            # cadence:    integer RPM
            # watts:  integer watts
            # temp:   integer degrees Celsius
            # moving:     boolean
            # grade_smooth:   float percent

            # (effort_avg_speed, effort_start_dist, effort_end_dist) = get_avg_speed_in_interval(act_stream,start,end)
            (effort_avg_speed, effort_start_dist, effort_end_dist) = get_avg_moving_speed_in_interval(act_stream, start,
                                                                                                      end)
            (effort_avg_hr, effort_start_dist_t, effort_end_dist_t) = get_avg_in_interval(act_stream, start, end,
                                                                                          'heartrate')
            (effort_avg_watts, effort_start_dist_t, effort_end_dist_t) = get_avg_in_interval(act_stream, start, end,
                                                                                             'watts')
            (effort_avg_cadence, effort_start_cadence, effort_end_cadence) = get_avg_in_interval(act_stream, start, end,
                                                                                                 'cadence')
            (
            effort_total_ascent, effort_total_descent, effort_start_dist_t, effort_end_dist_t) = get_ascent_in_interval(
                act_stream, start, end, 'altitude')

            (data_vel, time_vel) = get_diff_set(act_stream, start, end, 'velocity_smooth')

            effort_diff_hr = None
            effort_diff_speed = None
            effort_diff_watts = None
            effort_diff_cadence = None

            if effort_idx_in_act > 0:  # ignore diff to last in the first activity of the session
                effort_diff_hr = effort_avg_hr - last_hr
                effort_diff_speed = effort_avg_speed - last_speed
                effort_diff_watts = effort_avg_watts - last_watts
                effort_diff_cadence = effort_avg_cadence - last_cadence

            effort = Effort()

            effort.act_type = stored_act.act_type

            effort.start_time = start
            effort.duration = end - start

            effort.start_distance = effort_start_dist
            effort.distance = effort_end_dist - effort_start_dist

            effort.avg_speed = effort_avg_speed

            effort.diff_avg_speed = effort_avg_speed - act_avg_speed

            if effort_idx_in_act > 0:
                effort.diff_last_speed = effort_avg_speed - last_speed
            else:
                effort.diff_last_speed = None

            effort_avg_speed_s = 0
            if effort_avg_speed != 0:
                effort_avg_speed_s = 1.0 / effort_avg_speed

            act_avg_speed_s = 0
            if act_avg_speed != 0:
                act_avg_speed_s = 1.0 / act_avg_speed

            last_speed_s = 0
            if last_speed != 0:
                last_speed_s = 1.0 / last_speed

            effort.diff_avg_speed_s = act_avg_speed_s - effort_avg_speed_s

            if effort_idx_in_act > 0:
                effort.diff_last_speed_s = last_speed_s - effort_avg_speed_s
            else:
                effort.diff_last_speed_s = None

            if (stored_act.avg_hr):
                effort.avg_hr = effort_avg_hr
                effort.diff_avg_hr = (effort_avg_hr - stored_act.avg_hr)
                effort.diff_last_hr = effort_diff_hr

            if (stored_act.avg_cadence):
                effort.avg_cadence = effort_avg_cadence
                effort.diff_avg_cadence = (effort_avg_cadence - stored_act.avg_cadence)
                effort.diff_last_cadence = effort_diff_cadence

            effort.idx_in_activity = effort_idx_in_act

            effort.total_ascent = effort_total_ascent
            effort.total_descent = -effort_total_descent

            effort.song = song
            effort.activity = stored_act

            effort.data = data_vel.tobytes()
            effort.time = time_vel.tobytes()

            if stored_act.act_type == 1:
                if (stored_act.avg_watts) != None:
                    effort.avg_watts = effort_avg_watts
                    effort.diff_avg_watts = (effort_avg_watts - stored_act.avg_watts)
                    effort.diff_last_watts = effort_diff_watts

            if effort_avg_speed != 0.0:
                effort.save()
                last_hr = effort_avg_hr
                last_speed = effort_avg_speed
                last_watts = effort_avg_watts
                last_cadence = effort_avg_cadence

            effort_idx_in_act += 1

        return (stored_act.activity_id,)
    except Exception as e:
        logger.error("Exception on parsing activity {}".format(stored_act['id']))
        logger.error(e)
        return (stored_act.activity_id,)


def resync_activity(activity_id, athlete_id, resend=False):
    ath = strava_get_user_info(id=athlete_id)

    client = stravalib.client.Client()
    client.access_token = ath.strava_token
    client.refresh_token = ath.strava_refresh_token
    client.token_expires_at = ath.strava_token_expires_at

    if not ath.strava_token_expires_at:
        return "00000000-0000-0000-0000-000000000000", 0

    activity = strava_get_activity_by_id(activity_id)
    if athlete_id != activity.athlete.athlete_id:
        return None, None

    efforts_to_delete = Effort.objects.filter(activity__activity_id=activity_id)
    efforts_to_delete.delete()
    act_p = {}
    act_p['id'] = activity_id
    act_p['athlete_id'] = athlete_id
    if resend:
        download_chain = chain(strava_task.si('strava_download_activity', (act_p,)),
                               lastfm_task.s('lastfm_download_activity_tracks', ()),
                               activity_to_efforts.s(),
                               strava_task.s('strava_send_song_activities', ())
                               )
    else:
        download_chain = chain(strava_task.si('strava_download_activity', (act_p,)),
                               lastfm_task.s('lastfm_download_activity_tracks', ()),
                               activity_to_efforts.s()
                               )
    job_result = download_chain.delay()

    return job_result.id, 1

########################## END Internal tasks ##########################

########################## Aux code ##########################

def strava_get_start_timestamp(st):
    return int(time.mktime(st.timetuple()))


def take_closest_point(myList, myNumber):
    pos = bisect_left(myList, myNumber)
    if pos == 0:
        return 0
    if pos == len(myList):
        return len(myList) - 1
    before = myList[pos - 1]
    after = myList[pos]
    if after - myNumber < myNumber - before:
        return pos
    else:
        return pos - 1


def get_avg_speed_in_interval(stream, start, end):
    start_pos = take_closest_point(stream['time'], start)
    end_pos = take_closest_point(stream['time'], end)

    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]

    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]

    if (end_time - begin_time) == 0:
        return (0, 0, 0)
    return (float(end_dist - begin_dist) / float(end_time - begin_time)), begin_dist, end_dist


def get_avg_moving_speed_in_interval(stream, start, end):
    start_pos = take_closest_point(stream['time'], start)
    end_pos = take_closest_point(stream['time'], end)

    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]

    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]

    if (end_time - begin_time) == 0:
        return 0, 0, 0

    last_time = 0
    last_dist = 0

    if start_pos > 0:
        last_time = stream['time'][start_pos - 1]
        last_dist = stream['distance'][start_pos - 1]

    sum_key_value = 0.0
    sum_time = 0.0

    for idx, key_value in enumerate(stream['distance'][start_pos:end_pos]):
        time_diff = stream['time'][start_pos + idx] - last_time
        dist_diff = stream['distance'][start_pos + idx] - last_dist
        last_time = stream['time'][start_pos + idx]
        last_dist = stream['distance'][start_pos + idx]
        if stream['moving'][start_pos + idx]:
            sum_key_value += dist_diff
            sum_time += time_diff

    if sum_time == 0:
        return 0, 0, 0

    return sum_key_value / (sum_time), begin_dist, end_dist


def get_avg_in_interval(stream, start, end, key, ignore_moving=False):
    if not key in stream:
        return 0, 0, 0

    start_pos = take_closest_point(stream['time'], start)
    end_pos = take_closest_point(stream['time'], end)

    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]

    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]

    if (end_time - begin_time) == 0:
        return 0, 0, 0

    last_time = 0

    if start_pos > 0:
        last_time = stream['time'][start_pos - 1]

    sum_key_value = 0
    sum_time = 0

    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos + idx] - last_time
        last_time = stream['time'][start_pos + idx]
        if stream['moving'][start_pos + idx] or ignore_moving:
            sum_time += time_diff
            sum_key_value += key_value * time_diff

    if sum_time == 0:
        return 0, 0, 0

    return sum_key_value / (sum_time), begin_dist, end_dist


def get_sum_in_interval(stream, start, end, key, ignore_moving=False):
    if not key in stream:
        return 0, 0, 0

    start_pos = take_closest_point(stream['time'], start)
    end_pos = take_closest_point(stream['time'], end)

    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]

    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]

    if (end_time - begin_time) == 0:
        return 0, 0, 0

    last_time = 0

    if start_pos > 0:
        last_time = stream['time'][start_pos - 1]

    sum_key_value = 0
    sum_time = 0

    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos + idx] - last_time
        last_time = stream['time'][start_pos + idx]
        if stream['moving'][start_pos + idx] or ignore_moving:
            sum_time += time_diff
            sum_key_value += key_value * time_diff

    return sum_key_value, begin_dist, end_dist


def get_ascent_in_interval(stream, start, end, key):
    if not key in stream:
        return 0, 0, 0, 0

    start_pos = take_closest_point(stream['time'], start)
    end_pos = take_closest_point(stream['time'], end)

    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]

    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]

    if (end_time - begin_time) == 0:
        return 0, 0, 0, 0

    last_key_val = 0
    last_time = 0

    if start_pos > 0:
        last_time = stream['time'][start_pos - 1]

    sum_pos_key_value = 0
    sum_neg_key_value = 0
    sum_time = 0

    last_key_val = stream[key][start_pos]
    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos + idx] - last_time
        sum_time += time_diff
        last_time = stream['time'][start_pos + idx]
        key_val_diff = key_value - last_key_val
        if key_val_diff > 0:
            sum_pos_key_value += key_val_diff
        else:
            sum_neg_key_value += key_val_diff
        last_key_val = key_value

    return sum_pos_key_value, sum_neg_key_value, begin_dist, end_dist


def get_diff_set(stream, start, end, key, ignore_moving=False):
    start_pos = take_closest_point(stream['time'], start)
    end_pos = take_closest_point(stream['time'], end)

    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]

    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]

    data = []
    time = []

    if (end_time - begin_time) == 0:
        return np.array(data, np.float16), np.array(time, np.uint16)

    last_key_val = None

    if start_pos > 0:
        last_time = stream['time'][start_pos - 1]
    else:
        last_time = 0

    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos + idx] - last_time
        last_time = stream['time'][start_pos + idx]
        if stream['moving'][start_pos + idx] or ignore_moving:
            key_val_diff = key_value
            stream_time = last_time - begin_time
            data.append(key_val_diff)
            time.append(stream_time)
        last_key_val = key_value

    return np.array(data, np.float16), np.array(time, np.uint16)


def strava_get_user_info(id):
    athletes = Athlete.objects.filter(athlete_id=id)
    # logger.debug("Getting athlete with token {}".format(access_token))

    if athletes:
        athlete = athletes[0]

        if athlete.strava_token_expires_at and time.time() > float(athlete.strava_token_expires_at):
            athlete = strava_refresh_oauth(athlete.athlete_id)
        # logger.debug("Athlete {} found with current token".format(athlete.athlete_id))
        return athlete
    return None


def strava_parse_base_activity(act):
    actFinal = {}

    actFinal['achievement_count'] = act.achievement_count
    actFinal['athlete_id'] = act.athlete.id
    actFinal['average_cadence'] = act.average_cadence
    actFinal['average_heartrate'] = act.average_heartrate
    actFinal['average_speed'] = float(act.average_speed)
    actFinal['average_temp'] = act.average_temp
    actFinal['average_watts'] = act.average_watts

    actFinal['calories'] = act.calories
    actFinal['description'] = act.description
    actFinal['total_distance'] = float(act.distance)
    actFinal['elapsed_time'] = float(act.elapsed_time.total_seconds())
    actFinal['moving_time'] = float(act.moving_time.total_seconds())
    actFinal['elev_high'] = act.elev_high
    actFinal['elev_low'] = act.elev_low
    actFinal['embed_token'] = act.embed_token
    # actFinal['end_latlng'] = act.end_latlng

    actFinal['flagged'] = act.flagged
    # actFinal['gear'] = act.gear
    actFinal['gear_id'] = act.gear_id

    actFinal['has_heartrate'] = act.has_heartrate
    actFinal['has_kudoed'] = act.has_kudoed

    actFinal['id'] = act.id
    # actFinal['kudos'] = [k for k in a.kudos]
    actFinal['kudos_count'] = act.kudos_count

    # actFinal['laps'] = [k for k in a.laps]

    actFinal['location_city'] = act.location_city
    actFinal['location_country'] = act.location_country
    actFinal['location_state'] = act.location_state

    actFinal['manual'] = act.manual
    actFinal['max_heartrate'] = act.max_heartrate
    actFinal['max_speed'] = float(act.max_speed)
    actFinal['max_watts'] = act.max_watts

    actFinal['name'] = act.name
    actFinal['photo_count'] = act.photo_count
    # actFinal['segment_efforts'] = act.segment_efforts
    actFinal['start_date'] = act.start_date
    actFinal['start_date_local'] = act.start_date_local

    actFinal['start_latitude'] = act.start_latitude
    actFinal['start_longitude'] = act.start_longitude

    # actFinal['start_latlng'] = act.start_latlng

    actFinal['suffer_score'] = act.suffer_score
    # actFinal['timezone'] = act.timezone
    actFinal['total_elevation_gain'] = float(act.total_elevation_gain)
    actFinal['trainer'] = act.trainer
    actFinal['type'] = act.type

    actFinal['upload_id'] = act.upload_id

    actFinal['weighted_average_watts'] = act.weighted_average_watts
    actFinal['workout_type'] = act.workout_type

    return actFinal


########################## END Aux code ##########################

@shared_task
def sync_efforts_spotify(athlete_id, limit=None, after=None, force=False):
    athlete = strava_get_user_info(id=athlete_id)

    client = stravalib.client.Client()
    client.access_token = athlete.strava_token
    client.refresh_token = athlete.strava_refresh_token
    client.token_expires_at = athlete.strava_token_expires_at

    if not athlete.strava_token_expires_at:
        return "00000000-0000-0000-0000-000000000000", 0

    last_sync_date = athlete.last_sync_date

    athlete.last_celery_task_count = -1
    athlete.save()

    if not force and not after:
        after = last_sync_date

    athlete_api = client.get_athlete()
    stats = athlete_api.stats

    all_activities = client.get_activities(limit=limit, after=after)
    new_activities = []
    activity_count = 0
    for act in all_activities:
        try:
            activity_count += 1
            if not strava_is_activity_to_ignore(act.id) and not strava_get_activity_by_id(act.id):
                act_p = strava_parse_base_activity(act)
                download_chain = chain(strava_task.si('strava_download_activity', (act_p,)),
                                       spotify_task.s('spotify_download_activity_tracks', (False,)),
                                       activity_to_efforts.s(),
                                       strava_task.s('strava_send_song_activities', ())
                                       )
                new_activities.append(download_chain)
        except Exception as e:
            logger.error("Error parsing activity")        

    strava_generate_nops(4 + math.ceil(activity_count / 200))

    act_count = len(new_activities)
    if len(new_activities) == 0:
        job_result_id = "00000000-0000-0000-0000-000000000000"
    else:
        new_activities.append(clear_sync_id.si(athlete.id))
        promise = chain(new_activities)
        job_result = promise.delay()
        while True:
            if job_result.parent:
                job_result = job_result.parent
            else:
                break
        job_result_id = job_result.id

    athlete = strava_get_user_info(id=athlete_id)
    athlete.activity_count = stats.all_ride_totals.count
    athlete.runs_count = stats.all_run_totals.count
    athlete.rides_count = stats.all_ride_totals.count
    athlete.activity_count = stats.all_ride_totals.count + stats.all_run_totals.count
    athlete.updated_strava_at = athlete_api.updated_at
    athlete.last_celery_task_id = str(job_result_id)
    athlete.last_celery_task_count = act_count

    if athlete.activity_set.all():
        athlete.last_sync_date = athlete.activity_set.all().order_by('-start_date')[0].start_date
    else:
        athlete.last_sync_date = datetime.now(timezone.utc)

    athlete.save()

    # logger.debug(athlete.last_celery_task_id)
    # logger.debug(athlete.last_celery_task_count)

    return job_result_id, len(new_activities)


@shared_task
def sync_efforts_lastfm(athlete_id, limit=None, after=None, force=False):
    athlete = strava_get_user_info(id=athlete_id)

    client = stravalib.client.Client()
    client.access_token = athlete.strava_token
    client.refresh_token = athlete.strava_refresh_token
    client.token_expires_at = athlete.strava_token_expires_at

    if not athlete.strava_token_expires_at:
        return "00000000-0000-0000-0000-000000000000", 0

    last_sync_date = athlete.last_sync_date
    athlete.last_celery_task_count = -1
    athlete.save()

    if not force and not after:
        after = last_sync_date

    athlete_api = client.get_athlete()
    stats = athlete_api.stats

    all_activities = client.get_activities(limit=limit, after=after)
    new_activities = []
    activity_count = 0
    for act in all_activities:
        try:
            activity_count += 1
            if not strava_is_activity_to_ignore(act.id) and not strava_get_activity_by_id(act.id):
                act_p = strava_parse_base_activity(act)
                download_chain = chain(strava_task.si('strava_download_activity', (act_p,)),
                                       lastfm_task.s('lastfm_download_activity_tracks', ()),
                                       activity_to_efforts.s(),
                                       strava_task.s('strava_send_song_activities', ())
                                       )
                new_activities.append(download_chain)
        except Exception as e:
            logger.error("Error parsing activity")

    strava_generate_nops(4 + math.ceil(activity_count / 200))

    act_count = len(new_activities)
    if len(new_activities) == 0:
        job_result_id = "00000000-0000-0000-0000-000000000000"
    else:
        new_activities.append(clear_sync_id.si(athlete.id))
        promise = chain(new_activities)
        job_result = promise.delay()
        while True:
            if job_result.parent:
                job_result = job_result.parent
            else:
                break
        job_result_id = job_result.id

    athlete = strava_get_user_info(id=athlete_id)
    athlete.activity_count = stats.all_ride_totals.count
    athlete.runs_count = stats.all_run_totals.count
    athlete.rides_count = stats.all_ride_totals.count
    athlete.swims_count = stats.all_swim_totals.count
    athlete.activity_count = stats.all_ride_totals.count + stats.all_run_totals.count + stats.all_swim_totals.count
    athlete.updated_strava_at = athlete_api.updated_at
    athlete.last_celery_task_id = str(job_result_id)
    athlete.last_celery_task_count = act_count

    if athlete.activity_set.all():
        athlete.last_sync_date = athlete.activity_set.all().order_by('-start_date')[0].start_date
    else:
        athlete.last_sync_date = datetime.now(timezone.utc)

    athlete.save()

    # logger.debug(athlete.last_celery_task_id)
    # logger.debug(athlete.last_celery_task_count)

    return job_result_id, len(new_activities)


########################## Strava API tasks ##########################

@shared_task
def refresh_all(force=False):
    for poweruser in PowerUser.objects.all():
        if poweruser.athlete and poweruser.listener:
            sync_efforts_lastfm.delay(poweruser.athlete.athlete_id, force=force)
        elif poweruser.athlete and poweruser.listener_spotify:
            sync_efforts_spotify.delay(poweruser.athlete.athlete_id, force=force)
