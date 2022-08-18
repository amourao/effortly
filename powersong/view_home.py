from django.shortcuts import render, redirect
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from powersong.strava_aux import strava_get_auth_url
from powersong.lastfm_aux import lastfm_get_auth_url
from powersong.spotify_aux import spotify_get_auth_url

from powersong.view_main import index as main_index
from powersong.view_main import get_all_data, NonAuthenticatedException

from powersong.models import get_poweruser, PowerUser

import logging

logger = logging.getLogger(__name__)

def demo(request):
    request.session.flush()
    request.session['demo'] = True
    return main_index(request)


def index(request):
    
    result = {}
    if 'demo' in request.session or 'demo' in request.GET:
        return demo(request)
    
    if not 'athlete_id' in request.session:
        result['strava_authorize_url'] = strava_get_auth_url()
        return render(request, 'home.html', result)
    elif get_poweruser(request.session['athlete_id']) != None:
        return main_index(request)

    if not "athlete_id" in request.session:
        return render(request, 'home.html', result)
    else:
        return main_index(request)

def home(request):
    return render(request, 'home.html', {'strava_authorize_url': "#", 'lastfm_authorize_url': "#", 'spotify_authorize_url': "#"})

def logout(request):
    request.session.flush()
    return redirect('/')
    