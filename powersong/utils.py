import math
from powersong.models import *


def generate_header(data, n, page, total_length):
    if page > 0:
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
