import math
from powersong.models import *
from powersong.strava_aux import strava_get_user_info_by_id


def generate_header(n, page, total_length):
    if total_length > 0:
        page += 1
    return "Page {} of {} - Total results: {}".format(page, math.ceil(total_length / n), total_length)


def filter_user(qs, request):
    return qs.filter(activity__athlete__athlete_id=request.session['athlete_id'])


def remove_flagged(poweruser, qs):
    flaggedsong_ids = [a[0] for a in FlaggedSong.objects.filter(poweruser=poweruser).values_list('song_id')]
    flaggedartist_ids = [a[0] for a in FlaggedArtist.objects.filter(poweruser=poweruser).values_list('artist_id')]
    qs = qs.exclude(song__original_song__in=flaggedsong_ids)
    qs = qs.exclude(song__original_song__artist__in=flaggedartist_ids)
    qs = qs.exclude(flagged=True)
    qs = qs.exclude(activity__flagged=True)
    return qs


def get_unit_type(activity_type, dispfield, field):
    if activity_type == 0 and 'diff' in field and 'speed' in field:
        field += "_s"
    if activity_type == 0 and dispfield in speed:
        dispfield += "_s"
    return dispfield, field


def get_workout_type(request):
    workout_type = -1
    if 'workout_type' in request.GET:
        try:
            workout_type = int(request.GET['workout_type'])
        except:
            pass
    return workout_type


def get_user_activity_type(request):
    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'athlete_type' in request.session:
            athlete = strava_get_user_info_by_id(request.session['athlete_id'])
            activity_type = athlete.athlete_type
        else:
            activity_type = request.session['activity_type']
    return activity_type
