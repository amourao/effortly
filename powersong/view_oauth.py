from django.shortcuts import redirect
from django.template import RequestContext

from django.conf import settings

import stravalib.client


from powersong.view_home import index

def strava_oauth(request):
    if not 'code' in request.GET:
        return redirect(index)
        
    code = request.GET['code']

    strava_client = stravalib.client.Client()
    token = strava_client.exchange_code_for_token(client_id=settings.STRAVA_CLIENT_ID, client_secret=settings.STRAVA_CLIENT_SECRET, code=code)

    request.session['strava_token'] = token
    return redirect(index)

def lastfm_oauth(request):
    if not 'token' in request.GET:
        return redirect(index)

    token = request.GET['token']

    request.session['lastfm_token'] = token
    return redirect(index)
