from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.http import HttpResponse,HttpResponseForbidden

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info, lastfm_get_auth_url
from powersong.strava_aux import strava_get_auth_url,strava_get_user_info, strava_get_user_info_by_id, sync_efforts, strava_get_sync_progress, resync_activity, resync_activity_spotify
from powersong.spotify_aux import spotify_get_user_info
from powersong.view_detail import get_scrobble_details

from powersong.models import get_poweruser, PowerUser

import logging


logger = logging.getLogger(__name__)

def index(request):

    result = {}

    if 'demo' in request.session:
        poweruser = PowerUser.objects.filter(id=1)[0]
        result['demo'] = True
    else:
        if ((not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) or (not 'spotify_token' in request.session)) and not 'strava_token' in request.session:
            return render_to_response('home.html', result)

        if not 'strava_token' in request.session:
            return redirect(strava_get_auth_url())
    
        poweruser = get_poweruser(request.session['strava_token'])


    if 'puid' in request.GET and poweruser and (poweruser.athlete.athlete_id == "9363354" or 'superuser' in request.session):
        request.session['superuser'] = True
        puid = int(request.GET['puid'])
        powerusers = PowerUser.objects.filter(id=puid)
        poweruser = powerusers[0]

    if poweruser == None:
        # exchange lastfm_key per token on first run
        # if invalid, go back to home for reauthorization
        if not 'lastfm_key' in request.session and not 'spotify_token' in request.session:
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
        
        if not 'athlete_id' in request.session:
            athlete_model = strava_get_user_info(request.session['strava_token'])
        else:
            athlete_model = strava_get_user_info_by_id(request.session['athlete_id'])
        if athlete_model == None:
            athlete_model = strava_get_user_info(request.session['strava_token'])
        

        poweruser = PowerUser()
        poweruser.athlete = athlete_model
        
        if listener_model:
            poweruser.listener = listener_model
        
        if listenerspotify_model:
            poweruser.listener_spotify = listenerspotify_model
        
        poweruser.save()

    if 'spotify_code' in request.session:
        spotify_get_user_info(request.session['spotify_code'],request.session['spotify_token'],request.session['spotify_refresh_token'],poweruser.id)


    if poweruser.listener_spotify:
        request.session['spotify_code'] = poweruser.listener_spotify.spotify_code
        request.session['spotify_token'] = poweruser.listener_spotify.spotify_token
        request.session['spotify_refresh_token'] = poweruser.listener_spotify.spotify_refresh_token

    if poweruser.listener:
        request.session['lastfm_key'] = poweruser.listener.lastfm_token
        request.session['lastfm_username'] = poweruser.listener.nickname
    
    request.session['strava_token'] = poweruser.athlete.strava_token
    request.session['athlete_id'] = poweruser.athlete.athlete_id
    
    athlete_model = poweruser.athlete
    result['athlete'] = athlete_model

    listener_model = poweruser.listener
    result['listener'] = listener_model

    listenerspotify_model = poweruser.listener_spotify
    result['listenerspotify'] = listenerspotify_model
    # get athlete from db (if exists) or from Strava API
    
    result['first_login'] = athlete_model.first_login
    if athlete_model.first_login:
        request.session['sync_id'],request.session['sync_todo_total'] = sync_efforts(request.session['lastfm_username'],request.session['strava_token'],limit=9999)
        athlete_model.first_login = False
        athlete_model.save()

    # get athlete from db (if exists) or from lastfm API
    result['athlete'] = athlete_model
    request.session['athlete_id'] = athlete_model.athlete_id
    
    
    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'activity_type' in request.session:
            activity_type = athlete_model.athlete_type
        else:
            activity_type = request.session['activity_type']

    request.session['activity_type'] = activity_type
    result['activity_type'] = activity_type

    result['syncing'] = False
    if 'sync_id' in request.session:
        if request.session['sync_id'] != None:
            status,finished,count = strava_get_sync_progress(request.session['sync_id'])
            if count > 0 and status != 'SUCCESS':
                result['syncing'] = True

    result['count_s'],result['count_a'] = get_scrobble_details(athlete_model.athlete_id,result['activity_type'])
    
    return render_to_response('top.html', result)


def get_sync_id(request):
    if 'demo' in request.session:
        return None

    if not 'athlete_id' in request.session:
        athlete_model = strava_get_user_info(request.session['strava_token'])
    else:
        athlete_model = strava_get_user_info_by_id(request.session['athlete_id'])
        if athlete_model == None:
            athlete_model = strava_get_user_info(request.session['strava_token'])

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
 
    sync_id = get_sync_id(request)
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

def sync_spotify(request):
    #spotify_dump(request.session['spotify_token'])
    return gen_sync_response(request)


def sync(request):
    if 'demo' in request.session:
        return ""

    if (not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) and not 'strava_token' in request.session:
        return redirect('home.html')

    if not 'strava_token' in request.session:
        return redirect(strava_get_auth_url())
    
    poweruser = get_poweruser(request.session['strava_token'])

    request.session['lastfm_key'] = poweruser.listener.lastfm_token
    request.session['lastfm_username'] = poweruser.listener.nickname
    request.session['strava_token'] = poweruser.athlete.strava_token
    request.session['athlete_id'] = poweruser.athlete.athlete_id

    sync_id = get_sync_id(request)

    if sync_id == None or 'force' in request.GET:
        if 'lastfm_username' in request.session and 'strava_token' in request.session:
            request.session['sync_id'],request.session['sync_todo_total'] = sync_efforts(request.session['lastfm_username'],request.session['strava_token'],limit=9999)        
    
    return gen_sync_response(request)

def get_sync_progress(request):
    return gen_sync_response(request)      
    #return render_to_response('blank.html', {'message':response})
    

def resync_last_fm(request,activity_id):
    if 'demo' in request.session:
        return ""

    if (not 'lastfm_token' in request.session and not 'lastfm_key' in request.session) and not 'strava_token' in request.session:
        return redirect('home.html')

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

    if (not 'spotify_token' in request.session) and not 'strava_token' in request.session:
        return redirect('home.html')

    if not 'strava_token' in request.session:
        return redirect(strava_get_auth_url())
    
    poweruser = get_poweruser(request.session['strava_token'])

    listenerspotify_model = spotify_get_user_info(request.session['spotify_code'],request.session['spotify_token'],request.session['spotify_refresh_token'],poweruser.id)

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
