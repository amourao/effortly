from django.shortcuts import render_to_response
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

import stravalib.client

from django.conf import settings

from lastfm_aux import lastfm_get_session_id, lastfm_get_user_info
from strava_aux import strava_get_user_info, strava_get_activities

def index(request):
    result = {}
    if not 'lastfm_token' in request.session or not 'strava_token' in request.session:
        return render_to_response('home.html', result)
    if not 'lastfm_key' in request.session:
        username, key = lastfm_get_session_id(request.session['lastfm_token'])
        request.session['lastfm_key'] = key
        request.session['lastfm_username'] = username
    
    result['athlete'] = strava_get_user_info(request.session['strava_token'])
    result['listener'] = lastfm_get_user_info(request.session['lastfm_username'])
    result['session'] = request.session

    a,b,c = strava_get_activities(request.session['lastfm_username'],request.session['strava_token'])

    result['a'] = a
    result['b'] = b
    result['c'] = c

    return render_to_response('top.html', result)

