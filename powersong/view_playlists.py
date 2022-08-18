from django.shortcuts import redirect, render

from powersong.utils import remove_flagged, remove_impossible
from powersong.view_main import get_all_data, NonAuthenticatedException
from powersong.spotify_create_playlist import *
from powersong.models import *

from django.db.models import Avg, Func, F, Count, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce

import logging

logger = logging.getLogger(__name__)

LIMIT = 25


# https://towardsdatascience.com/what-makes-a-song-likeable-dbfdb7abe404

def get_playlists(request):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    activity_type = result["activity_type"]
    activity_type_name = result["activity_type_name"]

    playlist_codes = ["effortly:user:me:top:score",
                      "effortly:user:me:top:bpm:175",
                      "effortly:user:me:top:speed",
                      "effortly:user:me:top:cadence",
                      "effortly:user:me:missed:score",
                      "effortly:global:top:score",
                      "effortly:global:top:bpm:175",
                      "effortly:global:top:speed",
                      "effortly:global:top:cadence"
                      ]
    result["playlists"] = []
    for playlist_code in playlist_codes:


        playlist = {}
        if "activity" in playlist_code:
            playlist["link"], playlist["name"], playlist["id"] = create_activity_playlist(playlist_code)
        elif "global" in playlist_code:
            playlist["link"], playlist["name"], playlist["id"] = create_global_playlist(playlist_code, activity_type, activity_type_name)
        elif "user" in playlist_code:
            playlist["link"], playlist["name"], playlist["id"] = create_user_playlist(playlist_code, poweruser, activity_type, activity_type_name)
        result["playlists"].append(playlist)

    return render(request, "playlists.html", result)


def get_playlist(request, playlist_code):
    if 'demo' in request.session or 'demo' in request.GET:
        return redirect('/')
    try:
        poweruser, result = get_all_data(request)
    except NonAuthenticatedException as e:
        logger.debug(e.message)
        return (e.destination)

    activity_type = result["activity_type"]
    activity_type_name = result["activity_type_name"]

    result["playlist_link"] = ""
    if "activity" in playlist_code:
        result["playlist_link"], playlist_name, playlist_id = create_activity_playlist(playlist_code)
    elif "global" in playlist_code:
        result["playlist_link"], playlist_name, playlist_id = create_global_playlist(playlist_code, activity_type, activity_type_name)
    elif "user" in playlist_code:
        result["playlist_link"], playlist_name, playlist_id = create_user_playlist(playlist_code, poweruser, activity_type, activity_type_name)

    return render(request, "get_playlist.html", result)


def create_activity_playlist(playlist_code):
    activity_id = playlist_code.split(":")[-1]
    playlist_name = "Effortly's Activity {}".format(activity_id)
    playlist_id = "effortly:strava:activity:{}".format(activity_id)
    try:
        activity = Activity.objects.get(activity_id=activity_id)
        tracks = [i["song__original_song__spotify_id"] for i in
                  Effort.objects.filter(activity=activity).values('song__original_song__spotify_id').order_by(
                      'start_time') if i["song__original_song__spotify_id"]]
        playlist_url, playlist_name, playlist_code = spotify_create_playlist(playlist_name, playlist_id, tracks)
    except Exception as e:
        playlist_url = ""
    return playlist_url, playlist_name, playlist_id


def create_global_playlist(playlist_code, activity_type, activity_type_name):
    try:

        tracks = []

        if "top:bpm" in playlist_code:
            desired_bpm = int(playlist_code.split(":")[-1])
            qs = Song.objects.exclude(bpm=None).exclude(original_song__spotify_id__isnull=True).annotate(
                score=(1 / Func((F('bpm') - desired_bpm), function="ABS")) * F(
                    "danceability")).order_by("-score")
            qs = qs[:LIMIT]
            tracks = [i.original_song.spotify_id for i in qs]
            playlist_name = "Efforty's Global {} Top BPM {}".format(activity_type_name, desired_bpm)
        elif "top:speed" in playlist_code:
            playlist_code += ":{}".format(activity_type)
            field = "avg_speed"
            tracks = playlist_from_efforts(activity_type, field, LIMIT)
            playlist_name = "Efforty's Global {} Top Speed".format(activity_type_name)
        elif "top:cadence" in playlist_code:
            playlist_code += ":{}".format(activity_type)
            field = "avg_cadence"
            tracks = playlist_from_efforts(activity_type, field, LIMIT)
            playlist_name = "Efforty's Global {} Top Cadence".format(activity_type_name)
        elif "top:score" in playlist_code:
            playlist_code += ":{}".format(activity_type)
            tracks = effortly_score_playlist(activity_type, LIMIT, use_popularity=False)
            playlist_name = "Efforty's Global {} Top Score".format(activity_type_name)
        else:
            raise

        playlist_url, playlist_name, playlist_code = spotify_create_playlist(playlist_name, playlist_code, tracks)
    except Exception as e:
        raise
    return playlist_url, playlist_name, playlist_code


def create_user_playlist(playlist_code, poweruser, activity_type, activity_type_name):
    try:
        limit = 25
        tracks = []

        if "user:me" in playlist_code:
            playlist_code_s = playlist_code.split(":")
            playlist_code_s[2] = str(poweruser.athlete.id)
            playlist_code = ":".join(playlist_code_s)
        athlete_id = int(playlist_code.split(":")[2])
        playlist_name = playlist_code

        if "top:bpm" in playlist_code:
            desired_bpm = int(playlist_code.split(":")[-1])
            playlist_name = "Efforty's {} {} Top BPM {}".format(poweruser.athlete.first_name, activity_type_name, desired_bpm)
            qs = Song.objects.exclude(bpm=None).exclude(original_song__spotify_id__isnull=True).annotate(
                score=(1 / Func((F('bpm') - desired_bpm), function="ABS")) * F(
                    "danceability")).order_by("-score")
            qs = qs[:limit]
            tracks = [i.original_song.spotify_id for i in qs]
        elif "top:speed" in playlist_code:
            playlist_name = "Efforty's {} {} Top Speed".format(poweruser.athlete.first_name, activity_type_name)
            playlist_code += ":{}".format(activity_type)
            field = "avg_speed"
            tracks = playlist_from_efforts(activity_type, field, limit, athlete_id)
        elif "top:cadence" in playlist_code:
            playlist_name = "Efforty's {} {} Top Cadence".format(
                poweruser.athlete.first_name, activity_type_name)
            playlist_code += ":{}".format(activity_type)
            field = "avg_cadence"
            tracks = playlist_from_efforts(activity_type, field, limit, athlete_id)
        elif "top:score" in playlist_code:
            playlist_name = "Efforty's {} {} Top Score".format(
                poweruser.athlete.first_name, activity_type_name)
            playlist_code += ":{}".format(activity_type)
            tracks = effortly_score_playlist(activity_type, limit, athlete_id)
        elif "missed:score" in playlist_code:
            playlist_name = "Efforty's {} {} Missed Score".format(
                poweruser.athlete.first_name, activity_type_name)
            playlist_code += ":{}".format(activity_type)
            tracks = effortly_score_playlist(activity_type, limit, athlete_id, max_count=3)

        playlist_url, playlist_name, playlist_code = spotify_create_playlist(playlist_name, playlist_code, tracks)
    except Exception as e:
        raise
    return playlist_url, playlist_name, playlist_code


def playlist_from_efforts(activity_type, field, limit, athlete_id=None):
    agg_type = 'song__original_song'
    min_count = 1
    qs = Effort.objects.filter(act_type=activity_type).exclude(song__original_song__spotify_id__isnull=True)
    if athlete_id:
        qs = qs.filter(activity__athlete_id=athlete_id)
        qs = remove_flagged(qs, Athlete.objects.get(id=athlete_id).poweruser_set.all()[0])
        qs = remove_impossible(qs, activity_type)

    qs = qs.values('song__original_song', 'song__original_song__spotify_id').annotate(
        t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field)).exclude(
        sort_value=None).order_by('-sort_value')[:limit]
    tracks = [i['song__original_song__spotify_id'] for i in
              qs if i['song__original_song__spotify_id']]
    return tracks


def effortly_score_playlist(activity_type, limit, athlete_id=None, use_popularity=False, min_count=1, max_count=None):
    qs = Effort.objects.filter(act_type=activity_type).exclude(song__original_song__spotify_id__isnull=True)

    if athlete_id is not None:
        qs = qs.filter(activity__athlete_id=athlete_id)
        qs = remove_flagged(qs, Athlete.objects.get(id=athlete_id).poweruser_set.all()[0])

    qs = remove_impossible(qs, activity_type)

    qs = qs.annotate(
        s1=(F('avg_speed') - F('activity__avg_speed')) + Coalesce('diff_last_speed', 0) + F('diff_avg_speed')).order_by(
        's1')

    res = np.array([q.s1 for q in qs])

    mean = np.mean(res)
    std_dev = np.std(res)

    # efforts = len(qs)
    # cutoff_top = qs[int(efforts * 0.99)].s1
    # cutoff_bottom = qs[int(efforts * 0.25)].s1

    cutoff_top = mean + std_dev * 3
    cutoff_bottom = mean - std_dev

    qs = qs.filter(s1__gte=cutoff_bottom, s1__lte=cutoff_top)
    qs = qs.values('song__original_song__spotify_id').annotate(
        t_count=Count('song__original_song__spotify_id')).filter(t_count__gt=(min_count - 1))
    if max_count:
        qs = qs.exclude(t_count__gt=max_count)

    if use_popularity:
        qs = qs.annotate(
            sort_value=ExpressionWrapper(Avg(
                Coalesce('diff_last_speed', 0) + F('diff_avg_speed')) * Func(
                't_count', function="log"), output_field=FloatField()))
    else:
        qs = qs.annotate(
            sort_value=ExpressionWrapper(Avg(
                Coalesce('diff_last_speed', 0) + F('diff_avg_speed')), output_field=FloatField()))

    qs = qs.exclude(
        sort_value=None).order_by(
        '-sort_value')[:limit]

    tracks = [i['song__original_song__spotify_id'] for i in
              qs if i['song__original_song__spotify_id']]
    return tracks
