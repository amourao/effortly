from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse,HttpResponseForbidden

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info, lastfm_get_auth_url
from powersong.strava_aux import strava_get_auth_url,strava_get_user_info, strava_get_user_info_by_id, sync_efforts_lastfm, sync_efforts_spotify, strava_get_sync_progress, resync_activity, resync_activity_spotify
from powersong.spotify_aux import spotify_get_user_info
from powersong.view_detail import get_scrobble_details

from powersong.models import get_poweruser, PowerUser, Athlete

import logging


logger = logging.getLogger(__name__)


class NonAuthenticatedException(Exception):
    def __init__(self, message, destination=None):
        self.message = message
        self.destination = destination
    def __str__(self):
        return str(self.message) 

def get_all_data(request):
    result = {}

    if 'demo' in request.session or 'demo' in request.GET:
        poweruser = PowerUser.objects.filter(athlete__athlete_id=9363354)[0]
        puid = poweruser.id
        result['demo'] = True
        request.session['demo'] = True
    else:
        if not 'strava_token' in request.session:
            raise NonAuthenticatedException("No strava session found", redirect(strava_get_auth_url()))
    
        poweruser = get_poweruser(request.session['strava_token'])

    if 'puid' in request.GET and poweruser and (poweruser.athlete.athlete_id == "9363354" or 'superuser' in request.session) and not 'demo' in request.session:
        request.session['superuser'] = True
        puid = int(request.GET['puid'])
        powerusers = PowerUser.objects.filter(id=puid)
        poweruser = powerusers[0]

    if poweruser == None:
        # exchange lastfm_key per token on first run
        # if invalid, go back to home for reauthorization
        # check if stored lastfm session is valid
        
        if not 'athlete_id' in request.session:
            athlete_model = strava_get_user_info(request.session['strava_token'])
        else:
            athlete_model = strava_get_user_info_by_id(request.session['athlete_id'])
        
        if athlete_model == None:
            athlete_model = strava_get_user_info(request.session['strava_token'])
        
        poweruser = PowerUser()
        poweruser.athlete = athlete_model
        poweruser.save()
        puid = poweruser.id

    if poweruser.listener_spotify:
        request.session['spotify_code'] = poweruser.listener_spotify.spotify_code
        request.session['spotify_token'] = poweruser.listener_spotify.spotify_token
        request.session['spotify_refresh_token'] = poweruser.listener_spotify.spotify_refresh_token

    if poweruser.listener:
        request.session['lastfm_key'] = poweruser.listener.lastfm_token
        request.session['lastfm_username'] = poweruser.listener.nickname

    if 'spotify_code' in request.session:
        result['listenerspotify'] = spotify_get_user_info(request.session['spotify_code'],request.session['spotify_token'],request.session['spotify_refresh_token'],poweruser.athlete.id)

    if 'lastfm_username' in request.session:
        result['listener'] = lastfm_get_user_info(request.session['lastfm_username'],request.session['lastfm_key'],poweruser.athlete.id)
    
    puid = poweruser.id
    powerusers = PowerUser.objects.filter(id=puid)
    poweruser = powerusers[0]

    request.session['strava_token'] = poweruser.athlete.strava_token
    request.session['athlete_id'] = poweruser.athlete.athlete_id

    result['athlete'] = poweruser.athlete
    result['listener'] = poweruser.listener
    result['listenerspotify'] = poweruser.listener_spotify

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'activity_type' in request.session:
            activity_type = poweruser.athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    request.session['activity_type'] = activity_type
    result['activity_type'] = activity_type


    return poweruser, result


def index(request):

    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    
    
    athlete_model = poweruser.athlete
    listener_model = poweruser.listener
    listenerspotify_model = poweruser.listener_spotify
        
    result['syncing'] = False
    if 'sync_id' in request.session:
        if request.session['sync_id'] != None:
            status,finished,count = strava_get_sync_progress(request.session['sync_id'])
            if count > 0 and status != 'SUCCESS':
                result['syncing'] = True

    result['count_s'],result['count_a'] = get_scrobble_details(athlete_model.athlete_id,result['activity_type'])
    
    return render_to_response('top.html', result)


def detailed(request):

    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    
    result['title'] = 'Detailed View'
    return render_to_response('detailed.html', result)

def global_top(request):

    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    
    result['title'] = 'Global Top'
    result['countries'] = Athlete.objects.all().values_list('country',flat=True).distinct()
    return render_to_response('global_top.html', result)

def get_sync_id(request, poweruser):
    
    athlete_model = poweruser.athlete

    sync_id = None

    if 'sync_id' in request.session and request.session['sync_id'] != None:
        sync_id = request.session['sync_id']
        if sync_id != "":
            athlete_model.last_celery_task_id = sync_id
            athlete_model.save()
    elif athlete_model.last_celery_task_id != None:
        sync_id = athlete_model.last_celery_task_id
        request.session['sync_id'] = str(sync_id)

    return sync_id

def gen_sync_response(request):
    
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    sync_id = get_sync_id(request, poweruser)
    spinner = ""
    if sync_id == None:
        response = "SYNC IDLE"
        request.session['sync_id'] = None
    else:
        status,finished,count = strava_get_sync_progress(request.session['sync_id'])
        if count == 0:
            response = "NOTHING TO SYNC"
            request.session['sync_id'] = None
        else:
            response = "SYNC {}: {} of {}".format(status,finished,count)
            if status == 'SUCCESS':
                request.session['sync_id'] = None
            else:
                spinner = '<li class="nav-item"><img src="/static/spinner_dark.gif" width="40" height="40"></li>'

    if not 'athlete_id' in request.session:
        athlete_model = strava_get_user_info(request.session['strava_token'])
    else:
        athlete_model = strava_get_user_info_by_id(request.session['athlete_id'])
        if athlete_model == None:
            athlete_model = strava_get_user_info(request.session['strava_token'])

    athlete_model.last_celery_task_id = request.session['sync_id']
    athlete_model.save()

    return HttpResponse('{}<li class="nav-item"><a class="nav-link">{}</a></li>'.format(spinner,response))  

def sync(request):
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    if poweruser.listener:
        return sync_lastfm(request,poweruser)
    elif poweruser.listener_spotify:
        return sync_spotify(request,poweruser)
    else:
        return gen_sync_response(request)  

def sync_spotify(request,poweruser):
    sync_id = get_sync_id(request, poweruser)

    if sync_id == None or 'force' in request.GET:
        if 'spotify_token' in request.session and 'strava_token' in request.session:
            token = request.session['spotify_token']
            reftoken = request.session['spotify_refresh_token']
            code = request.session['spotify_code']
            request.session['sync_id'],request.session['sync_todo_total'] = sync_efforts_spotify(code,token,reftoken,request.session['strava_token'],limit=9999)        
    
    return gen_sync_response(request)


def sync_lastfm(request,poweruser):
    sync_id = get_sync_id(request, poweruser)

    if sync_id == None or 'force' in request.GET:
        if 'lastfm_username' in request.session and 'strava_token' in request.session:
            request.session['sync_id'],request.session['sync_todo_total'] = sync_efforts_lastfm(request.session['lastfm_username'],request.session['strava_token'],limit=9999)        
    
    return gen_sync_response(request)

def get_sync_progress(request):
    return gen_sync_response(request)      
    #return render_to_response('blank.html', {'message':response})
    

def resync_last_fm(request,activity_id):
    if 'demo' in request.session:
        return ""

    if (not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) and not 'strava_token' in request.session:
        return redirect(lastfm_get_auth_url())

    if not 'strava_token' in request.session:
        return redirect(strava_get_auth_url())
    
    poweruser = get_poweruser(request.session['strava_token'])

    request.session['lastfm_key'] = poweruser.listener.lastfm_token
    request.session['lastfm_username'] = poweruser.listener.nickname
    request.session['strava_token'] = poweruser.athlete.strava_token
    request.session['athlete_id'] = poweruser.athlete.athlete_id
        
    resync_activity(request.session['lastfm_username'],request.session['strava_token'],activity_id,request.session['athlete_id'])
    
    #return render_to_response('blank.html', {'message':response})
    return redirect("/activity/" + activity_id)

def resync_spotify(request,activity_id):
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    if (not 'spotify_token' in request.session):
        return redirect(strava_get_auth_url())
    
    spotify_get_user_info(request.session['spotify_code'],request.session['spotify_token'],request.session['spotify_refresh_token'],poweruser.id)

    request.session['strava_token'] = poweruser.athlete.strava_token
    request.session['spotify_token'] = poweruser.listener_spotify.spotify_token
    request.session['spotify_refresh_token'] = poweruser.listener_spotify.spotify_refresh_token
    request.session['spotify_code'] = poweruser.listener_spotify.spotify_code    
    request.session['athlete_id'] = poweruser.athlete.athlete_id
        
    resync_activity_spotify(request.session['spotify_code'],request.session['spotify_token'],request.session['spotify_refresh_token'],request.session['strava_token'],activity_id,request.session['athlete_id'])

    poweruser = get_poweruser(request.session['strava_token'])
    request.session['spotify_token'] = poweruser.listener_spotify.spotify_token

    #return render_to_response('blank.html', {'message':response})
    return redirect("/activity/" + activity_id)

def about(request):
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    
    result['title'] = 'About'
    return render_to_response('about.html', result)
