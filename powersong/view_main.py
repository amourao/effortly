from django.shortcuts import render_to_response
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

import stravalib.client

from django.conf import settings

from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info
from powersong.strava_aux import strava_get_user_info, strava_get_activities, strava_get_sync_progress, strava_get_sync_result,strava_get_fastest_ever_single,strava_get_fastest_ever_groupA

def index(request):

    result = {}

    if (not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) or not 'strava_token' in request.session:
        return render_to_response('home.html', result)
    if not 'lastfm_key' in request.session:
        username, key = lastfm_get_session_id(request.session['lastfm_token'])
        if username == None or key ==None:
            request.session['lastfm_token'] = None
            del request.session['lastfm_token']
            return render_to_response('home.html', {})
        request.session['lastfm_key'] = key
        request.session['lastfm_username'] = username
        del request.session['lastfm_token']




    if not 'athlete' in request.session:
        request.session['athlete'] = strava_get_user_info(request.session['strava_token'])
        
    if not 'listener' in request.session:
        request.session['listener'] = lastfm_get_user_info(request.session['lastfm_username'])
        

    result['listener'] = request.session['listener']
    result['athlete'] = request.session['athlete']

    
    resync = 'resync' in request.GET
    limit = None
    if 'limit' in request.GET:
        limit = int(request.GET['limit'])
    if 'sync_id' in request.GET:
        request.session['sync_id'] = request.GET['sync_id']

    if not 'sync_status' in request.session or resync:
        request.session['sync_id'] = strava_get_activities(request.session['lastfm_username'],request.session['strava_token'],limit=limit)
        status,count = strava_get_sync_progress(request.session['sync_id'])
        request.session['sync_status'] = status
        request.session['sync_completed'] = count
        request.session['sync_results'] = None

    if request.session['sync_status'] != "SUCCESS" and request.session['sync_status'] != "FAILED":   
        status,count = strava_get_sync_progress(request.session['sync_id'])
        request.session['sync_status'] = status
        request.session['sync_completed'] = count
        request.session['sync_results'] = None

    if request.session['sync_status'] == "FAILED":
        request.session['sync_id'] = None

    if request.session['sync_status'] == "SUCCESS":
        status,count = strava_get_sync_progress(request.session['sync_id'])
        output = strava_get_sync_result(request.session['sync_id'])
        request.session['sync_status'] = status
        request.session['sync_completed'] = count
        request.session['sync_results'] = output
        result['tops'] = {}
        result['tops']['top_pace'] = strava_get_fastest_ever_single(output,'avgSpeed')
        result['tops']['top_hr'] = strava_get_fastest_ever_single(output,'avgHr')
        result['tops']['popular_tracks'] = strava_get_fastest_ever_groupA(output,'count')
        result['tops']['diff_apace'] = strava_get_fastest_ever_groupA(output,'diffAvgSpeedMin')
        result['tops']['diff_ahr'] = strava_get_fastest_ever_groupA(output,'diffAvgHr')
        result['tops']['diff_lpace'] = strava_get_fastest_ever_groupA(output,'diffLastSpeedMin')
        result['tops']['diff_lhr'] = strava_get_fastest_ever_groupA(output,'diffLastHr')
        request.session['top_pace'] = result['tops']['top_pace'] 
        request.session['top_hr'] = result['tops']['top_hr'] 
        request.session['popular_tracks'] = result['tops']['popular_tracks'] 
        request.session['diff_ahr'] = result['tops']['diff_ahr'] 
        request.session['diff_apace'] = result['tops']['diff_apace'] 
        request.session['diff_lhr'] = result['tops']['diff_lhr'] 
        request.session['diff_lpace'] = result['tops']['diff_lpace']   

    result['sessionss'] = {}
    for key in request.session.keys():
        result['sessionss'][key] = request.session[key]

    return render_to_response('top.html', result)

