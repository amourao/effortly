from django.shortcuts import redirect
from django.template import RequestContext

from django.conf import settings

import stravalib.client

import sys, json

import spotipy

import requests

from powersong.view_home import index

import logging

logger = logging.getLogger(__name__)

def strava_oauth(request):
    if not 'code' in request.GET:
        return redirect(index)
        
    code = request.GET['code']

    strava_client = stravalib.client.Client()
    token = strava_client.exchange_code_for_token(client_id=settings.STRAVA_CLIENT_ID, client_secret=settings.STRAVA_CLIENT_SECRET, code=code)

    request.session['strava_token'] = token
    return redirect(index)

def lastfm_oauth(request):
    if not 'token' in request.GET:
        return redirect(index)

    token = request.GET['token']

    request.session['lastfm_token'] = token
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