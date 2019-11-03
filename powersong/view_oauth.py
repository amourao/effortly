from django.shortcuts import redirect
from django.template import RequestContext
from django.http import JsonResponse

from django.conf import settings

import stravalib.client

import sys, json

import spotipy

import requests

from powersong.view_main import get_all_data, NonAuthenticatedException
from powersong.view_home import index
from powersong.view_settings import setting
from powersong.models import *
from powersong.spotify_aux import spotify_refresh_token
from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info

import logging

logger = logging.getLogger(__name__)

def strava_oauth(request):
    if not 'code' in request.GET:
        return redirect(index)
        
    code = request.GET['code']

    strava_client = stravalib.client.Client()
    token_response = strava_client.exchange_code_for_token(client_id=settings.STRAVA_CLIENT_ID, client_secret=settings.STRAVA_CLIENT_SECRET, code=code)

    access_token = token_response['access_token']
    refresh_token = token_response['refresh_token']
    expires_at = token_response['expires_at']

    athlete_api = strava_client.get_athlete()
    athlete_id = athlete_api.id

    athletes = Athlete.objects.filter(athlete_id=athlete_id)
    if athletes:
        #logger.debug("Athlete {} found with invalid token. Updating token.".format(athlete.athlete_id))
        athlete = athletes[0]
    else:
        athlete = create_athlete_from_dict(athlete_api)

    athlete.strava_token = access_token
    athlete.strava_refresh_token = refresh_token
    athlete.strava_token_expires_at = expires_at
    athlete.save()

    request.session['athlete_id'] = athlete_id

    return redirect(index)
  
def lastfm_oauth(request):

    if not 'token' in request.GET:
        return redirect(index)

    token = request.GET['token']

    request.session['lastfm_token'] = token

    username, key = lastfm_get_session_id(token)

    request.session['lastfm_key'] = key
    request.session['lastfm_username'] = username

    return redirect(index)

def spotify_oauth(request):  
    if not 'code' in request.GET:
        return redirect(index)

    code = request.GET['code']

    r = requests.post("https://accounts.spotify.com/api/token", data={'grant_type': 'authorization_code', 'code': code, 'redirect_uri': settings.SPOTIFY_CALLBACK_URL, 'client_id':settings.SPOTIPY_CLIENT_ID, 'client_secret':settings.SPOTIPY_CLIENT_SECRET})
    out = r.json()

    request.session['spotify_code'] = code
    request.session['spotify_token'] = out['access_token']
    request.session['spotify_refresh_token'] = out['refresh_token']

    return redirect(index)


def spotify_refresh_token_endpoint(request):  
    if not 'athlete_id' in request.session:
        return JsonResponse({})

    poweruser = get_poweruser(request.session['athlete_id'])

    token = spotify_refresh_token(poweruser.listener_spotify.spotify_code,poweruser.listener_spotify.spotify_token,poweruser.listener_spotify.spotify_refresh_token, poweruser.athlete.athlete_id)

    request.session['spotify_token'] = token

    return JsonResponse({'token': token})

