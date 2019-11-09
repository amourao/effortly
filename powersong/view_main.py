from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse,HttpResponseForbidden
from django.http import JsonResponse

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info, lastfm_get_auth_url
from powersong.strava_aux import strava_get_auth_url,strava_get_user_info_by_id, strava_get_sync_progress, resync_activity, resync_activity_spotify
from powersong.spotify_aux import spotify_get_user_info
from powersong.view_detail import get_scrobble_details
from powersong.tasks import sync_efforts_lastfm, sync_efforts_spotify, strava_get_user_info, strava_send_song_activities

from powersong.models import get_poweruser, PowerUser, Athlete, Activity

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
        if not 'athlete_id' in request.session:
            raise NonAuthenticatedException("No strava session found", redirect(strava_get_auth_url()))
        poweruser = get_poweruser(request.session['athlete_id'])
        if poweruser:
            puid = poweruser.id

    if 'puid' in request.GET and poweruser and (poweruser.athlete.athlete_id == "9363354" or 'superuser' in request.session) and not 'demo' in request.session:
        request.session.flush()
        request.session['superuser'] = True
        puid = int(request.GET['puid'])
        powerusers = PowerUser.objects.filter(id=puid)
        poweruser = powerusers[0]
    #logger.debug(poweruser)
    if not poweruser:

        athlete_model = strava_get_user_info_by_id(request.session['athlete_id'])
        
        powerusers = PowerUser.objects.filter(athlete=athlete_model)
        if not powerusers:
            poweruser = PowerUser()
            poweruser.athlete = athlete_model
            poweruser.save()
        else:
            poweruser = powerusers[0]
        puid = poweruser.id
    #logger.debug([poweruser])
    #logger.debug(poweruser.listener_spotify)

    puid = poweruser.id
    powerusers = PowerUser.objects.filter(id=puid)
    poweruser = powerusers[0]
    #logger.debug([poweruser, puid])
    
    request.session['athlete_id'] = poweruser.athlete.athlete_id

    if not 'athlete' in result:
        result['athlete'] = poweruser.athlete
    if not 'listener' in result:
        result['listener'] = poweruser.listener
    if not 'listenerspotify'  in result:
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
    result['count_s'],result['count_a'] = get_scrobble_details(athlete_model.athlete_id,result['activity_type'])
    result['title'] = 'Top'
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
    result['countries'] = Athlete.objects.all().values_list('country',flat=True).distinct().order_by('country')
    return render_to_response('global_top.html', result)

def get_sync_id(request, poweruser):
    
    athlete_model = poweruser.athlete  

    if athlete_model.last_celery_task_id == None:
        request.session['sync_id'] = sync_id = None
        request.session['sync_todo_total'] = sync_todo_total = athlete_model.last_celery_task_count
    elif str(athlete_model.last_celery_task_id) == "00000000-0000-0000-0000-000000000000":
        request.session['sync_id'] = None
        request.session['sync_todo_total'] = 0
        sync_id = str(athlete_model.last_celery_task_id)
        sync_todo_total = athlete_model.last_celery_task_count
        athlete_model.last_celery_task_id = None
        athlete_model.last_celery_task_count = 0
        athlete_model.save()
    else:
        request.session['sync_id'] = sync_id = str(athlete_model.last_celery_task_id)
        request.session['sync_todo_total'] = sync_todo_total = athlete_model.last_celery_task_count


        
    return sync_id, sync_todo_total

def gen_sync_response(request):
    
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    sync_id, count = get_sync_id(request, poweruser)

    logger.debug(sync_id)
    logger.debug(count)

    spinner = ""
    if sync_id == None and count != -1:
        response = "SYNC IDLE"
    elif sync_id == "00000000-0000-0000-0000-000000000000" and count == 0:
        response = "NOTHING TO SYNC"
    else:
        status,finished,count = strava_get_sync_progress(sync_id,count)
        if count == -1:
            spinner = '<li class="nav-item"><img src="/static/spinner_dark.gif" width="40" height="40"></li>'
            response = status
        else:
            response = "SYNC {}: {} of {}".format(status,finished,count)
            if status != 'SUCCESS':
                spinner = '<li class="nav-item"><img src="/static/spinner_dark.gif" width="40" height="40"></li>'

    return HttpResponse('{}<li class="nav-item"><a class="nav-link">{}</a></li>'.format(spinner,response))  

def sync(request):
    #logger.debug('########## sync ##########')
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
        return HttpResponse('{}<li class="nav-item"><a class="nav-link">{}</a></li>'.format("","NO LISTENER TO SYNC"))  

def sync_spotify(request,poweruser):
    #logger.debug('########## sync ##########')
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    sync_id, count = get_sync_id(request, poweruser)

    if (sync_id == None and count != -1) or (sync_id == "00000000-0000-0000-0000-000000000000") or 'force' in request.GET:
        if 'athlete_id' in request.session and poweruser.listenerspotify:
            request.session['sync_id'] = None
            request.session['sync_todo_total'] = -1
            athlete = poweruser.athlete
            athlete.last_celery_task_id = None
            athlete.last_celery_task_count = -1
            athlete.save()
            sync_efforts_spotify.delay(request.session['athlete_id'],force=('force' in request.GET))
    
    return gen_sync_response(request)


def sync_lastfm(request,poweruser):
    #logger.debug('########## sync ##########')
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    sync_id, count = get_sync_id(request, poweruser)
   
    if (sync_id == None and count != -1) or (sync_id == "00000000-0000-0000-0000-000000000000") or 'force' in request.GET:
        if 'athlete_id' in request.session and poweruser.listener:
            request.session['sync_id'] = None
            request.session['sync_todo_total'] = -1
            athlete = poweruser.athlete
            athlete.last_celery_task_id = None
            athlete.last_celery_task_count = -1
            athlete.save()
            sync_efforts_lastfm.delay(request.session['athlete_id'],force=('force' in request.GET))
    
    return gen_sync_response(request)

def get_sync_progress(request):
    #logger.debug('########## get_sync_progress ##########')
    return gen_sync_response(request)      
    #return render_to_response('blank.html', {'message':response})



def send_song_info_to_strava(request,activity_id):
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)
    
    act = Activity.objects.filter(activity_id=activity_id)
    if not act:
        return JsonResponse({})

    act = act[0]
    if act.athlete_id != poweruser.athlete_id:
        return JsonResponse({})
    
    strava_send_song_activities((activity_id,))
    
    return JsonResponse({})
    

def resync_last_fm(request,activity_id):
    if 'demo' in request.session:
        return ""
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    resync_activity(activity_id,request.session['athlete_id'])
    
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
    
    resync_activity_spotify(activity_id,request.session['athlete_id'])

    #return render_to_response('blank.html', {'message':response})
    return redirect("/activity/" + activity_id)

def about(request):
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        result = {}
        result['viewer'] = True
    result['title'] = 'About'
    return render_to_response('about.html', result)
