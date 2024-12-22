from django.conf import settings

import copy, time
import json

import requests

from dateutil.parser import parse

from powersong.models import *

from celery import group

import os.path

import spotipy

import logging

logger = logging.getLogger(__name__)

TEMPLATE = {
        "album": {
          "#text": "",
          "mbid": "",
          "name": ""
        },
        "artist": {
          "image": [
            {
              "#text": "",
              "size": "extralarge"
            }
          ],
          "mbid": "",
          "spotify_id": "",
          "name": "",
          "url": ""
        },
        "date": {
          "#text": "",
          "uts": ""
        },
        "image": [
          {
            "#text": "",
            "size": "extralarge"
          }
        ],
        "mbid": "",
        "name": "",
        "url": ""
      }

def spotify_get_user_info(code,token,refresh,athlete_id):
    listeners = ListenerSpotify.objects.filter(spotify_code=code)
    #logger.debug("Getting ListenerSpotify with code {}".format(code))

    if listeners:
        listener = listeners[0]
        listener.spotify_code = code
        listener.spotify_token = token
        listener.spotify_refresh_token = refresh
        listener.save()
        #logger.debug("ListenerSpotify {} found in DB".format(code))
        return listener

    #logger.debug("ListenerSpotify {} not in DB, creating new for athlete_id {}.".format(code,athlete_id))
    
    r = requests.get("https://api.spotify.com/v1/me", headers={'Authorization': 'Bearer  ' + token})
        
    out = r.json()

    listeners = ListenerSpotify.objects.filter(nickname=out['id'])
    
    if listeners:
        listener = listeners[0]
    else:
        listener = ListenerSpotify()

        listener.nickname = out['id']
        listener.real_name = out['display_name']

        if 'images' in out and out['images'] and 'url' in out['images'][0]:
            listener.profile_image_url = out['images'][0]['url']
        
        if 'external_urls' in out and out['external_urls'] and 'spotify' in out['external_urls']:
            listener.url = out['external_urls']['spotify']
        listener.product = out['product']

    listener.spotify_code = code
    listener.spotify_token = token
    listener.spotify_refresh_token = refresh

    listener.save()

    athletes = PowerUser.objects.filter(athlete__athlete_id=athlete_id)
    if athletes:
         athlete = athletes[0]
         athlete.listener_spotify = listener
         athlete.save()

    return listener

def spotify_get_auth_url():
    return settings.SPOTIFY_BASE.format(settings.SPOTIPY_CLIENT_ID, settings.SPOTIFY_CALLBACK_URL)

def spotify_get_auth_url_edit():
    return settings.SPOTIFY_BASE_EDIT.format(settings.SPOTIPY_CLIENT_ID, settings.SPOTIFY_CALLBACK_URL)


def spotify_to_lastfm(results,start,end):
    track_list = []
    last_timestamp = None
    for track in results['items']:
        res = copy.deepcopy(TEMPLATE)
        res['spotify_id'] = track['track']['id']
        res['name'] = track['track']['name']
        res['url'] = track['track']['external_urls']['spotify']
        res['image'][0]['extralarge'] = track['track']['album']['images'][0]['url']
        res['artist']['name'] = track['track']['artists'][0]['name']
        res['artist']['spotify_id'] = track['track']['artists'][0]['id']
        res['artist']['url'] = track['track']['artists'][0]['external_urls']['spotify']
        #res['artist']['image'][0]['extralarge'] = track['track']['artists'][0]['images'][0]['url']

        current_timestamp = parse(track['played_at']).timestamp()
        duration = (track['track']['duration_ms']/1000)
        res['duration'] = duration
        #res['date']['uts'] = str(current_timestamp).split('.')[0]
        res['album']['#text'] = track['track']['album']['name']
        if last_timestamp == None:
            res['date']['uts'] = str(current_timestamp).split('.')[0]
        else:
        #  if (current_timestamp-last_timestamp)>duration*1.5:
        #    res['date']['uts'] = str(last_timestamp).split('.')[0]
        #    last_timestamp = current_timestamp
        #  else:
           res['date']['uts'] = str(current_timestamp).split('.')[0]
           last_timestamp = current_timestamp
        ts = int(res['date']['uts'])
        #logger.debug(ts)
        #logger.debug(start)
        #logger.debug(end)
        if ts >= start and ts <= end:
            track_list.append(res)
    return track_list


def spotify_get_recent_tracks_before(token,athlete_id,start,end,force=False):
    ending = (end + (10*60)) * 1000
    path = "data/data_{}_{}.json".format(athlete_id,str(ending).split('.')[0])

    if os.path.isfile(path) and not force:
        with open(path) as f:
            results = json.load(f)
    else:
        r = requests.get("https://api.spotify.com/v1/me/player/recently-played", params={'before': ending, 'limit':50}, headers={'Authorization': 'Bearer  ' + token})
        results = r.json()
        if 'error' in results:
            raise Exception('')
        with open(path,'w') as outfile:
            json.dump(results, outfile)

    final_res = {}
    final_res['recenttracks'] = {}
    final_res['recenttracks']['track'] = spotify_to_lastfm(results,start,end)

    return final_res

def spotify_get_recent_tracks(token,athlete_id,start,end):
    sp = spotipy.Spotify(auth=token)
    results = sp.current_user_recently_played()    
    track_list = []

    if 'items' in results and results['items']:
        with open("data/data_{}_{}.json".format(athlete_id,str(time.time()).split('.')[0]), 'w') as outfile:
            json.dump(results, outfile)

    final_res = {}
    final_res['recenttracks'] = {}
    final_res['recenttracks']['track'] = spotify_to_lastfm(results,start,end)

    return final_res


def spotify_sync_tracks():
    from powersong.tasks import spotify_task
    songs = Song.objects.all()
    songs_to_sync = []
    for song in songs:
        if song.spotify_id:
            songs_to_sync.append(spotify_task.s('spotify_update_track',(song.id,)))
    if len(songs_to_sync) > 1:
        promise = group(*songs_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = songs_to_sync[0]
        job_result = promise.delay()
    
    return job_result.id, len(songs_to_sync)

def spotify_sync_artists():
    from powersong.tasks import spotify_task
    artists = Artist.objects.all()
    artists_to_sync = []
    for artist in artists:
        if artist.spotify_id:
            artists_to_sync.append(spotify_task.s('spotify_update_artist',(artist.id,)))
    if len(artists_to_sync) > 1:
        promise = group(*artists_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = artists_to_sync[0]
        job_result = promise.delay()
    
    return job_result.id, len(artists_to_sync)


def spotify_sync_ids():
    from powersong.tasks import spotify_task
    songs = Song.objects.all()

    poweruser = PowerUser.objects.all()[0]

    code = poweruser.listener_spotify.spotify_code
    token = poweruser.listener_spotify.spotify_token
    reftoken = poweruser.listener_spotify.spotify_refresh_token


    songs_to_sync = []
    for song in songs:
        if not song.spotify_id:
            songs_to_sync.append(spotify_task.s('spotify_get_spotify_ids',(code,token,reftoken,song.id)))

    if len(songs_to_sync) > 1:
        promise = group(*songs_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = songs_to_sync[0]
        job_result = promise.delay()
    
    return job_result.id, len(songs_to_sync)


def spotify_get_track_features():
    from powersong.tasks import spotify_task
    songs = Song.objects.exclude(spotify_id=None)

    songs_to_sync = []
    track_ids = []
    for song in songs:
        if song.bpm == -1:
            track_ids.append(song.spotify_id)
            if len(track_ids) == 50:
                songs_to_sync.append(spotify_task.s('spotify_multi_track_get_stats', (track_ids,)))
                track_ids = []

    if track_ids:
        songs_to_sync.append(spotify_task.s('spotify_multi_track_get_stats', (track_ids,)))

    if len(songs_to_sync) > 1:
        promise = group(*songs_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = songs_to_sync[0]
        job_result = promise.delay()

    return job_result.id, len(songs_to_sync)




def spotify_refresh_token(code,token,reftoken,athlete_id):
    logger.debug("Refreshing spotify token")
    r = requests.post("https://accounts.spotify.com/api/token", data={'grant_type': 'refresh_token', 'refresh_token': reftoken, 'redirect_uri': settings.SPOTIFY_CALLBACK_URL, 'client_id':settings.SPOTIPY_CLIENT_ID, 'client_secret':settings.SPOTIPY_CLIENT_SECRET})
    out = r.json()
    spotify_get_user_info(code,out['access_token'],reftoken,athlete_id)
    return out['access_token']
