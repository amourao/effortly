from django.conf import settings
from hashlib import md5

from powersong.models import *
from powersong.tasks import lastfm_download_artist_info,lastfm_download_track_info

from celery import chain, group
from celery.result import AsyncResult,GroupResult
from celery import current_app

import requests

import logging

logger = logging.getLogger(__name__)

def lastfm_get_auth_url():
    return settings.LASTFM_BASE + settings.LASTFM_API_KEY

def lastfm_get_session_id(token):
    method = 'auth.getSession'
    api_sig = lastfm_get_sig(settings.LASTFM_API_KEY,method,token,settings.LASTFM_API_SECRET)
    
    url = settings.LASTFM_API_AUTHBASE.format(method,settings.LASTFM_API_KEY,token,api_sig)
    response = requests.get(url).json()
    if not 'session' in response:
        return None,None
    return (response['session']['name'], response['session']['key'])

def lastfm_get_user_info(username,key,poweruser_id):

    listeners = Listener.objects.filter(nickname=username)
    logger.debug("Getting listener with username {}".format(username))

    if listeners:
        listener = listeners[0]
        listener.lastfm_token = key
        listener.save()
        logger.debug("Listener {} found in DB".format(username))
    else:
        logger.debug("Listener {} not in DB, creating new.".format(username))
        
        method = 'user.getinfo'
        url = settings.LASTFM_API_BASE.format(method,settings.LASTFM_API_KEY,username)
        response = requests.get(url).json()

        if not 'user' in response:
            #invalid key, must get new
            return None

        response = response['user']
        listener = create_listener_from_dict(response,key)
        listener.save()

        powerusers = PowerUser.objects.filter(athlete_id=poweruser_id)
        if powerusers:
            poweruser = powerusers[0]
            poweruser.listener = listener
            poweruser.save()

    return listener

def lastfm_get_sig(api_key,method,token,secret):
    return md5('api_key{}method{}token{}{}'.format(api_key,method,token,secret).encode()).hexdigest()


def lastfm_sync_artists():

    artists = Artist.objects.all()

    artists_to_sync = []
    for artist in artists:
        artists_to_sync.append(lastfm_download_artist_info.s(artist.name,artist.mb_id))

    if len(artists_to_sync) > 1:
        promise = group(*artists_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = artists_to_sync[0]
        job_result = promise.delay()
    
    return job_result.id, len(artists_to_sync)

def lastfm_sync_tracks():

    songs = Song.objects.all()

    songs_to_sync = []
    for song in songs:
        #if song.last_sync_date == None or song.last_sync_date == "":
        songs_to_sync.append(lastfm_download_track_info.s(song.artist_name,song.title))

    if len(songs_to_sync) > 1:
        promise = group(*songs_to_sync)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = songs_to_sync[0]
        job_result = promise.delay()
    
    return job_result.id, len(songs_to_sync)
