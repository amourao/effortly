from django.shortcuts import render_to_response,redirect
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from powersong.strava_aux import strava_get_auth_url
from powersong.lastfm_aux import lastfm_get_auth_url
from powersong.spotify_aux import spotify_get_auth_url

from powersong.view_main import index as main_index

from powersong.models import get_poweruser, PowerUser

def index(request):
    
    result = {}
    
    if not 'strava_token' in request.session:
        result['strava_authorize_url'] = strava_get_auth_url()
    elif get_poweruser(request.session['strava_token']) != None:
        return main_index(request)

    if not 'lastfm_token' in request.session or request.session['lastfm_token'] == None:
        result['lastfm_authorize_url'] = lastfm_get_auth_url()

    if not 'spotify_token' in request.session or request.session['spotify_token'] == None:
        result['spotify_authorize_url'] = spotify_get_auth_url()

    #if "lastfm_token" in request.session and "strava_token" in request.session:
    #    result
    if not "lastfm_token" in request.session or not "strava_token" in request.session:
        return render_to_response('home.html', result)
    else:
        return main_index(request)

def home(request):
    return render_to_response('home.html', {'strava_authorize_url': "#", 'lastfm_authorize_url': "#", 'spotify_authorize_url': "#"})


def about(request):
    return render_to_response('about.html', {})    

def logout(request):
    request.session.flush()
    return redirect('/')
    