from django.shortcuts import render_to_response
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

import stravalib.client

from django.conf import settings

from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info
from powersong.strava_aux import strava_get_user_info, strava_get_activities, strava_get_sync_progress

def index(request):
    result = {}
    if (not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) or not 'strava_token' in request.session:
        return render_to_response('home.html', result)
    if not 'lastfm_key' in request.session:
        username, key = lastfm_get_session_id(request.session['lastfm_token'])
        request.session['lastfm_key'] = key
        request.session['lastfm_username'] = username
        del request.session['lastfm_token']
        request.session.modified = True

    if not 'athlete' in request.session:
        request.session['athlete'] = strava_get_user_info(request.session['strava_token'])
        
    if not 'listener' in request.session:
        request.session['listener'] = lastfm_get_user_info(request.session['lastfm_username'])
        

    result['listener'] = request.session['listener']
    result['athlete'] = request.session['athlete']

    if not 'sync_status' in request.session or 'resync' in request.GET:
        request.session['sync_id'] = strava_get_activities(request.session['lastfm_username'],request.session['strava_token'])
        status,count,output = strava_get_sync_progress(request.session['sync_id'])
        request.session['sync_status'] = status
        request.session['sync_completed'] = count
        result['sync_results'] = output
    else:
        status,count,output = strava_get_sync_progress(request.session['sync_id'])
        result['sync_results'] = output
        if request.session['sync_status'] != "SUCCESS":
            request.session['sync_status'] = status
            request.session['sync_completed'] = count
        else:
            request.session['sync_status'] = status
            request.session['sync_completed'] = count
    
    result['sessionss'] = {}
    for key in request.session.keys():
        result['sessionss'][key] = request.session[key]

    return render_to_response('top.html', result)

