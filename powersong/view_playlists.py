from django.shortcuts import render_to_response, redirect, render

from powersong.view_main import get_all_data, NonAuthenticatedException
from powersong.spotify_create_playlist import *

from django.db.models import Avg, Func, F, Count

import logging

logger = logging.getLogger(__name__)


# https://towardsdatascience.com/what-makes-a-song-likeable-dbfdb7abe404

def get_playlist(request, playlist_code):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    result["playlist_link"] = ""
    if "activity" in playlist_code:
        result["playlist_link"] = create_activity_playlist(playlist_code)
    elif "global" in playlist_code:
        result["playlist_link"] = create_global_playlist(playlist_code)

    return render(request, "create_playlist.html", result)


def create_activity_playlist(playlist_code):
    activity_id = playlist_code.split(":")[-1]
    try:
        activity = Activity.objects.get(activity_id=activity_id)
        tracks = [i["song__original_song__spotify_id"] for i in
                  Effort.objects.filter(activity=activity).values('song__original_song__spotify_id').order_by(
                      'start_time') if i["song__original_song__spotify_id"]]
        playlist_url = spotify_create_playlist("Activity {}".format(activity_id),
                                               "effortly:strava:activity:{}".format(activity_id), tracks)
    except Exception as e:
        playlist_url = ""
    return playlist_url


def create_global_playlist(playlist_code):
    try:
        limit = 25
        tracks = []
        if "top:bpm" in playlist_code:
            desired_bpm = int(playlist_code.split(":")[-1])
            qs = Song.objects.exclude(bpm=None).exclude(original_song__spotify_id__isnull=True).annotate(
                score=(1 / Func((F('bpm') - desired_bpm), function="ABS")) * F(
                    "danceability")).order_by("-score")
            qs = qs[:limit]
            tracks = [i.original_song.spotify_id for i in qs]
        elif "top:speed" in playlist_code:
            activity_type = int(playlist_code.split(":")[-1])
            field = "avg_speed"
            tracks = playlist_from_efforts(activity_type, field, limit)
        elif "top:cadence" in playlist_code:
            activity_type = int(playlist_code.split(":")[-1])
            field = "avg_cadence"
            tracks = playlist_from_efforts(activity_type, field, limit)

        playlist_url = spotify_create_playlist(playlist_code, playlist_code, tracks)
    except Exception as e:
        raise
    return playlist_url


def create_user_playlist(playlist_code):
    try:
        limit = 25
        tracks = []
        if "top:bpm" in playlist_code:
            desired_bpm = int(playlist_code.split(":")[-1])
            qs = Song.objects.exclude(bpm=None).exclude(original_song__spotify_id__isnull=True).annotate(
                score=(1 / Func((F('bpm') - desired_bpm), function="ABS")) * F(
                    "danceability")).order_by("-score")
            qs = qs[:limit]
            tracks = [i.original_song.spotify_id for i in qs]
        elif "top:speed" in playlist_code:
            activity_type = int(playlist_code.split(":")[-1])
            field = "avg_speed"
            tracks = playlist_from_efforts(activity_type, field, limit)
        elif "top:cadence" in playlist_code:
            activity_type = int(playlist_code.split(":")[-1])
            field = "avg_cadence"
            tracks = playlist_from_efforts(activity_type, field, limit)

        playlist_url = spotify_create_playlist(playlist_code, playlist_code, tracks)
    except Exception as e:
        raise
    return playlist_url


def playlist_from_efforts(activity_type, field, limit, athlete_id=None):
    agg_type = 'song__original_song'
    min_count = 1
    qs = Effort.objects.filter(act_type=activity_type)
    if athlete_id:
        qs = qs.filter(activity__athlete_id=athlete_id)
    qs = qs.values('song__original_song', 'song__original_song__spotify_id').annotate(
        t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field)).exclude(
        sort_value=None).order_by('-sort_value')[:limit]
    tracks = [i['song__original_song__spotify_id'] for i in
              qs if i['song__original_song__spotify_id']]
    return tracks

