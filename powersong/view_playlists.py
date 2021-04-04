from django.shortcuts import render_to_response, redirect, render

from powersong.view_main import get_all_data, NonAuthenticatedException
from powersong.view_home import demo


from powersong.models import *
from powersong.spotify_create_playlist import *

import logging

logger = logging.getLogger(__name__)


def create_activity_playlist(request,activity_id):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)    

    try:
        activity = Activity.objects.get(activity_id=activity_id)
        tracks = [i["song__original_song__spotify_id"] for i in Effort.objects.filter(activity = activity).values('song__original_song__spotify_id').order_by('start_time') if i["song__original_song__spotify_id"]]
        playlist_url = spotify_create_playlist("Activity {}".format(activity_id),"effortly:strava:activity:{}".format(activity_id),tracks)
    except Exception as e:
        playlist_url = ""
    result["playlist_link"] = playlist_url
    return render(request, "create_playlist.html", result)