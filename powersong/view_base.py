from django.shortcuts import render_to_response
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

import stravalib.client

from django.conf import settings


def index(request):

    result = {}
    
    if not "strava_token" in request.session:
        strava_client = stravalib.client.Client()
        strava_authorize_url = strava_client.authorization_url(settings.STRAVA_CLIENT_ID, redirect_uri = settings.STRAVA_CALLBACK_URL,scope = 'view_private')
        result['strava_authorize_url'] = strava_authorize_url
    if not "lastfm_token" in request.session:
        result['lastfm_authorize_url'] = settings.LASTFM_BASE + settings.LASTFM_API_KEY  

    return render_to_response('home.html', result)