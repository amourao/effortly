from django.shortcuts import render_to_response, redirect
from django.conf import settings
from django.http import JsonResponse

from powersong.models import *
from powersong.view_detail import activity
from powersong.view_main import get_all_data, NonAuthenticatedException
from powersong.view_home import demo


from powersong.strava_aux import strava_get_auth_url
from powersong.lastfm_aux import lastfm_get_auth_url
from powersong.spotify_aux import spotify_get_auth_url


import logging
import json

logger = logging.getLogger(__name__)


def setting(request):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    if not poweruser.athlete:
        result['strava_authorize_url'] = strava_get_auth_url()

    if not poweruser.listener:
        result['lastfm_authorize_url'] = lastfm_get_auth_url()

    if not poweruser.listener_spotify:
        result['spotify_authorize_url'] = spotify_get_auth_url()

    result['title'] = 'Settings'

    return render_to_response('settings.html', result) 

def delete_account(request):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    if poweruser.athlete:
        poweruser.athlete.delete()
    if poweruser.listener:
        poweruser.listener.delete()
    if poweruser.listener_spotify:
        poweruser.listener_spotify.delete()
    poweruser.delete()
    return redirect('/logout/')



def remove_spotify(request):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    if not poweruser.listener_spotify:
        return redirect('/settings/')

    if 'spotify_token' in request.session:
        del request.session['spotify_token']
    if 'spotify_code' in request.session:
        del request.session['spotify_code']
    if 'spotify_refresh_token' in request.session:
        del request.session['spotify_refresh_token']

    poweruser.listener_spotify.delete()

    return redirect('/settings/')

def remove_lastfm(request):
    if 'demo' in request.session or 'demo' in request.GET:
        return demo(request)
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    if not poweruser.listener:
        return redirect('/settings/')


    if 'lastfm_token' in request.session:
        del request.session['lastfm_token']
    if 'lastfm_key' in request.session:
        del request.session['lastfm_key']
    if 'lastfm_username' in request.session:
        del request.session['lastfm_username']

    poweruser.listener.delete()

    return redirect('/settings/')

def flag_activity(request,activity_id):

    if not 'strava_token' in request.session and not 'demo' in request.session:
        return redirect("/")
    
    if 'demo' in request.session:
        return activity(request, activity_id)
    else:
        poweruser = get_poweruser(request.session['strava_token'])

    activity = Activity.objects.filter(activity_id=activity_id)
    
    if not activity:
        return JsonResponse({})

    activity = activity[0]

    if activity.athlete_id != poweruser.athlete.id:
        return render_to_response('access_denied.html', {})


    json_data = json.loads(request.body)
    if 'flagged_hr' in json_data and type(json_data['flagged_hr']) is bool:
        activity.flagged_hr = json_data['flagged_hr']
        activity.save()

    if 'flagged' in json_data and type(json_data['flagged']) is bool:
        activity.flagged = json_data['flagged']
        activity.save()
    
    return JsonResponse({})


def flag_effort(request,effort_id):

    if not 'strava_token' in request.session and not 'demo' in request.session:
        return redirect("/")
    
    if 'demo' in request.session:
        return activity(request, effort.activity.activity_id)
    else:
        poweruser = get_poweruser(request.session['strava_token'])

    effort = Effort.objects.filter(id=effort_id)
    
    if not effort:
        return JsonResponse({})

    effort = effort[0]

    if effort.activity.athlete_id != poweruser.athlete.id:
        return render_to_response('access_denied.html', {})


    json_data = json.loads(request.body)
    if 'flagged_hr' in json_data and type(json_data['flagged_hr']) is bool:
        effort.flagged_hr = json_data['flagged_hr']
        effort.save()

    if 'flagged' in json_data and type(json_data['flagged']) is bool:
        effort.flagged = json_data['flagged']
        effort.save()
    
    return JsonResponse({})



def flag_song(request,song_id):

    data = {}

    if not 'strava_token' in request.session and not 'demo' in request.session:
        return redirect("/")
    
    if 'demo' in request.session or 'demo' in request.GET:
        return JsonResponse({})
    else:
        poweruser = get_poweruser(request.session['strava_token'])

    song = Song.objects.filter(id=song_id)

    if not song:
        return JsonResponse({})
    song = song[0]
    
    json_data = json.loads(request.body)
    if 'flagged' in json_data and type(json_data['flagged']) is bool:
        flagged = json_data['flagged']
        matching = FlaggedSong.objects.filter(song=song, poweruser=poweruser)
        if not flagged:
            matching.delete()
        elif not matching:
            flagged_song = FlaggedSong(song=song, poweruser=poweruser)
            flagged_song.save()
    
    return JsonResponse({})

def flag_artist(request,artist_id):

    data = {}

    if not 'strava_token' in request.session and not 'demo' in request.session:
        return redirect("/")
    
    if 'demo' in request.session or 'demo' in request.GET:
        return JsonResponse({})
    else:
        poweruser = get_poweruser(request.session['strava_token'])

    artist = Artist.objects.filter(id=artist_id)

    if not artist:
        return JsonResponse({})
    
    artist = artist[0]
    
    json_data = json.loads(request.body)
    if 'flagged' in json_data and type(json_data['flagged']) is bool:
        flagged = json_data['flagged']
        matching = FlaggedArtist.objects.filter(artist=artist, poweruser=poweruser)
        if not flagged:
            matching.delete()
        elif not matching:
            flagged_artist = FlaggedSong(artist=artist, poweruser=poweruser)
            flagged_artist.save()
    
    return JsonResponse({})
