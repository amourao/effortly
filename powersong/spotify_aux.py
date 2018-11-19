from django.conf import settings

import copy, time
import json
import spotipy

import requests

from dateutil.parser import parse

from powersong.models import *
from powersong.tasks import *

from celery import chain, group
from celery.result import AsyncResult,GroupResult
from celery import current_app


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
    logger.debug("Getting ListenerSpotify with code {}".format(code))

    if listeners:
        listener = listeners[0]
        listener.spotify_code = code
        listener.spotify_token = token
        listener.spotify_refresh_token = refresh
        listener.save()
        logger.debug("ListenerSpotify {} found in DB".format(code))
        return listener

    logger.debug("ListenerSpotify {} not in DB, creating new for athlete_id {}.".format(code,athlete_id))
    
    listener = ListenerSpotify()
    listener.spotify_code = code
    listener.spotify_token = token
    listener.spotify_refresh_token = refresh

    listener.save()

    athletes = PowerUser.objects.filter(athlete_id=athlete_id)
    if athletes:
         athlete = athletes[0]
         athlete.listener_spotify = listener
         athlete.save()

    return listener

def spotify_get_auth_url():
    return settings.SPOTIFY_BASE.format(settings.SPOTIPY_CLIENT_ID, settings.SPOTIFY_CALLBACK_URL)

def spotify_to_lastfm(results):
    track_list = []
    for track in results['items']:
        res = copy.deepcopy(TEMPLATE)
        res['spotify_id'] = track['track']['id']
        res['name'] = track['track']['name']
        res['url'] = track['track']['external_urls']['spotify']
        res['image'][0]['extralarge'] = track['track']['album']['images'][0]['url']
        res['artist']['name'] = track['track']['artists'][0]['name']
        res['artist']['url'] = track['track']['artists'][0]['external_urls']['spotify']
        
        current_timestamp = parse(track['played_at']).timestamp()
        duration = (track['track']['duration_ms']/1000)
        res['date']['uts'] = str(current_timestamp).split('.')[0]
        res['album']['#text'] = track['track']['album']['name']
        #if last_timestamp == None:
        #    res['date']['uts'] = str(current_timestamp-duration).split('.')[0]
        #else:
        #  if (current_timestamp-last_timestamp)>duration*1.5:
        #    res['date']['uts'] = str(last_timestamp).split('.')[0]
        #    last_timestamp = current_timestamp
        #  else:
        #    res['date']['uts'] = str(current_timestamp-duration*1.5).split('.')[0]
        #    last_timestamp = current_timestamp-duration*1.5
        
        track_list.append(res)
    return track_list


def spotify_get_recent_tracks(token,athlete_id):
    sp = spotipy.Spotify(auth=token)
    results = sp.current_user_recently_played()    
    track_list = []
    last_timestamp = None

    with open("data/data_{}_{}.json".format(athlete_id,str(time.time())).split('.')[0], 'w') as outfile:
        json.dump(results, outfile)

    final_res = {}
    final_res['recenttracks'] = {}
    final_res['recenttracks']['track'] = spotify_to_lastfm(results)

    return final_res


def spotify_sync_ids():
    songs = Song.objects.all()

    poweruser = PowerUser.objects.all()[0]

    code = poweruser.listener_spotify.spotify_code
    token = poweruser.listener_spotify.spotify_token
    reftoken = poweruser.listener_spotify.spotify_refresh_token


    songs_to_sync = []
    for song in songs:
        #if song.last_sync_date == None or song.last_sync_date == "":
        songs_to_sync.append(spotify_get_spotify_ids.s(code,token,reftoken,song.id))

    if len(songs_to_sync) > 1:
        promise = group(*songs_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = songs_to_sync[0]
        job_result = promise.delay()
    
    return job_result.id, len(songs_to_sync)

def spotify_refresh_token_endpoint(request):
    poweruser = PowerUser.objects.all()[0]
    

def spotify_refresh_token(code,token,reftoken,athlete_id):
    logger.debug("Refreshing spotify token")
    r = requests.post("https://accounts.spotify.com/api/token", data={'grant_type': 'refresh_token', 'refresh_token': reftoken, 'redirect_uri': settings.SPOTIFY_CALLBACK_URL, 'client_id':settings.SPOTIPY_CLIENT_ID, 'client_secret':settings.SPOTIPY_CLIENT_SECRET})
    out = r.json()
    spotify_get_user_info(code,out['access_token'],reftoken,athlete_id)
    return out['access_token']