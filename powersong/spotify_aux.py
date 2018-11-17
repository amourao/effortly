from django.conf import settings

import copy, time
import json
import spotipy
from dateutil.parser import parse

from powersong.models import *

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

def spotify_get_recent_tracks(token,athlete_id):
    sp = spotipy.Spotify(auth=token)
    results = sp.current_user_recently_played()    
    track_list = []
    last_timestamp = None

    with open('data_{}_{}.json'.format(athlete_id,str(time.time())).split('.')[0], 'w') as outfile:
        json.dump(results, outfile)

    for track in results['items']:
        res = d2 = copy.deepcopy(TEMPLATE)
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
    final_res = {}
    final_res['recenttracks'] = {}
    final_res['recenttracks']['track'] = track_list

    return final_res

