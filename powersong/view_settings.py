from django.shortcuts import render_to_response, redirect
from django.conf import settings
from django.http import JsonResponse

from powersong.models import *
from powersong.view_detail import activity

import logging
import json

logger = logging.getLogger(__name__)


def flag_activity(request,activity_id):

    data = {}

    if not 'strava_token' in request.session and not 'demo' in request.session:
        return redirect("/")
    
    if 'demo' in request.session:
        return activity(requet,activity_id)
    else:
        poweruser = get_poweruser(request.session['strava_token'])

    if poweruser.listener_spotify:
        data['spotify_token'] = poweruser.listener_spotify.spotify_token

    activity = Activity.objects.filter(activity_id = activity_id)[0]
    
    if activity.athlete_id != poweruser.athlete.id:
        return render_to_response('access_denied.html', data)


    json_data = json.loads(request.body)
    if 'flagged_hr' in json_data and type(json_data['flagged_hr']) is bool:
        activity.flagged_hr = json_data['flagged_hr']
        activity.save()

    if 'flagged' in json_data and type(json_data['flagged']) is bool:
        activity.flagged = json_data['flagged']
        activity.save()
    
    return JsonResponse({})