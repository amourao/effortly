from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info, lastfm_get_auth_url
from powersong.strava_aux import strava_get_auth_url,strava_get_user_info, strava_get_user_info_by_id, sync_efforts, strava_get_sync_progress

import logging


logger = logging.getLogger(__name__)

def index(request):

    result = {}
    #if no authorization, get back to home page
    if (not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) and not 'strava_token' in request.session:
        return render_to_response('home.html', result)

    if not 'strava_token' in request.session:
        return redirect(strava_get_auth_url())

    # exchange lastfm_key per token on first run
    # if invalid, go back to home for reauthorization
    if not 'lastfm_key' in request.session:
        username, key = lastfm_get_session_id(request.session['lastfm_token'])
        if username == None or key == None:
            request.session['lastfm_token'] = None
            del request.session['lastfm_token']
            return redirect(lastfm_get_auth_url())
        request.session['lastfm_key'] = key
        request.session['lastfm_username'] = username
    # check if stored lastfm session is valid
    if 'lastfm_key' in request.session and 'lastfm_username' in request.session:
        listener_model = lastfm_get_user_info(request.session['lastfm_username'],request.session['lastfm_key'])
        if listener_model == None:
            del request.session['lastfm_token']
            del request.session['lastfm_key']
            del request.session['lastfm_username']
            return redirect(lastfm_get_auth_url())

    result['listener'] = listener_model
    # get athlete from db (if exists) or from Strava API
    if not 'athlete_id' in request.session:
        athlete_model = strava_get_user_info(request.session['strava_token'])
    else:
        athlete_model = strava_get_user_info_by_id(request.session['athlete_id'])
        if athlete_model == None:
            athlete_model = strava_get_user_info(request.session['strava_token'])
    # get athlete from db (if exists) or from lastfm API
    result['athlete'] = athlete_model
    request.session['athlete_id'] = athlete_model.athlete_id
    

    resync = 'resync' in request.GET
    limit = 5
    if 'limit' in request.GET:
        limit = int(request.GET['limit'])
    if 'sync_id' in request.GET:
        request.session['sync_id'] = request.GET['sync_id']

    if resync:
        request.session['sync_id'],request.session['sync_todo_total'] = sync_efforts(request.session['lastfm_username'],request.session['strava_token'],limit=limit)        

    result['sessionss'] = {}
    for key in request.session.keys():
        result['sessionss'][key] = request.session[key]

    return render_to_response('top.html', result)

def get_sync_progress(request):
    response = ""
    if 'sync_id' in request.session:
        if request.session['sync_id'] != None:
            status,finished,count = strava_get_sync_progress(request.session['sync_id'])
            response = "SYNC {}: {} of {}".format(status,finished,count) 
    return HttpResponse(response)
