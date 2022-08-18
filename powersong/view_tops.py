from django.shortcuts import render, redirect
from django.template import RequestContext
from django.forms.models import model_to_dict

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from django.http import JsonResponse

from powersong.models import *
from django.db.models import Avg, Sum, Max, Count
from django.db.models import Q, F

from django.core import serializers

from powersong.strava_aux import strava_get_user_info_by_id

import logging
import math
from datetime import datetime, timedelta

from django.forms.models import model_to_dict

from powersong.utils import generate_header, remove_flagged, get_user_activity_type, get_workout_type, get_unit_type, \
    remove_impossible

logger = logging.getLogger(__name__)


def top_activities(request):
    data = {}

    if not 'type' in request.GET:
        data['error'] = 'Missing type'
        return JsonResponse(data)

    u_type = request.GET['type']

    field = None
    if not 'field' in request.GET:
        data['error'] = 'Missing field'
        return JsonResponse(data)
    elif 'field' in request.GET:
        field = request.GET['field']

    g_type = 'avg'
    if field in ['effort']:
        g_type = 'count'

    min_count = 3
    if 'min_count' in request.GET:
        min_count = int(request.GET['min_count'])

    dispfield = field
    if 'dispfield' in request.GET:
        dispfield = request.GET['dispfield']

    header = False
    if 'header' in request.GET:
        header = True

    page = 0
    if 'page' in request.GET and request.GET['page']:
        try:
            page = int(request.GET['page'])
        except:
            pass

    descending = -1
    if 'ascending' in request.GET:
        descending = 1

    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])

    units = None
    if 'units' in request.GET:
        units = request.GET['units']
    if not units:
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        units = athlete.measurement_preference
    else:
        units = 0

    activity_type = get_user_activity_type(request)
    request.session['activity_type'] = activity_type
    workout_type = get_workout_type(request)
    dispfield, field = get_unit_type(activity_type, dispfield, field)

    poweruser = get_poweruser(request.session['athlete_id'])

    qs = Activity.objects

    if activity_type != -1:
        qs = qs.filter(act_type=activity_type)

    if workout_type != -1:
        if workout_type == 0:
            qs = qs.filter((Q(workout_type=10) | Q(workout_type=0)))
        elif workout_type == 1:
            qs = qs.filter((Q(workout_type=11) | Q(workout_type=1)))
        elif workout_type == 3:
            qs = qs.filter((Q(workout_type=12) | Q(workout_type=3)))
        else:
            qs = qs.filter(workout_type=workout_type)

    if 'hr' in field:
        qs = qs.filter(flagged_hr=False).exclude(avg_hr__isnull=True)

    if 'days' in request.GET:
        try:
            days = int(request.GET['days'])
            if days != -1:
                d = datetime.today() - timedelta(days=days)
                comb = datetime.combine(d, datetime.min.time())
                qs = qs.filter(start_date__gt=comb)
        except:
            pass

    if field == 'start_date_local':
        qs = qs.filter(athlete__athlete_id=request.session['athlete_id']).annotate(sort_value=F(field),
                                                                                   ecount=Count('effort')).exclude(
            sort_value__isnull=True).filter(ecount__gt=(min_count - 1)).order_by(field)[::descending]
    elif field == 'effort':
        qs = qs.filter(athlete__athlete_id=request.session['athlete_id']).annotate(sort_value=Count('effort')).annotate(
            ecount=F('sort_value')).filter(ecount__gt=(min_count - 1)).order_by('sort_value')[::descending]
    elif g_type == 'avg':
        qs = qs.filter(athlete__athlete_id=request.session['athlete_id']).annotate(sort_value=Avg(field),
                                                                                   ecount=Count('effort')).exclude(
            sort_value__isnull=True).filter(ecount__gt=(min_count - 1)).order_by(field)[::descending]
    elif g_type == 'count':
        qs = qs.filter(athlete__athlete_id=request.session['athlete_id']).annotate(sort_value=Count(field),
                                                                                   ecount=Count('effort')).exclude(
            sort_value__isnull=True).filter(ecount__gt=(min_count - 1)).order_by(field)[::descending]

    total_length = len(qs)
    qs = qs[(n * page):(n * (page + 1))]

    data['top'] = []
    for q in qs:
        qa = model_to_dict(q)
        qa['sort_value'] = q.sort_value
        qa['sort_key'] = dispfield
        qa = effort_convert(qa, units)
        data['top'].append((q, qa))

    if header:
        data['header'] = generate_header(n, page, total_length)

    return render(request,'top_table_detail_activity.html', data)


def top_global_song_artist(request):
    data = {}

    if not 'type' in request.GET:
        data['error'] = 'Missing type'
        return JsonResponse(data)

    u_type = request.GET['type']

    field = None
    if not 'field' in request.GET:
        data['error'] = 'Missing field'
        return JsonResponse(data)
    elif 'field' in request.GET:
        field = request.GET['field']

    g_type = 'avg'
    if field in ['count', 'count_users']:
        g_type = 'count'

    min_count = 1
    if 'min_count' in request.GET:
        min_count = int(request.GET['min_count'])

    dispfield = field
    if 'dispfield' in request.GET:
        dispfield = request.GET['dispfield']

    header = False
    if 'header' in request.GET:
        header = True

    page = 0
    if 'page' in request.GET and request.GET['page']:
        try:
            page = int(request.GET['page'])
        except:
            pass

    descending = -1
    if 'ascending' in request.GET:
        descending = 1

    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])

    units = None
    if 'units' in request.GET:
        units = request.GET['units']
    if not units:
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        units = athlete.measurement_preference
    else:
        units = 0

    activity_type = get_user_activity_type(request)
    request.session['activity_type'] = activity_type
    workout_type = get_workout_type(request)
    dispfield, field = get_unit_type(activity_type, dispfield, field)

    country = 'All'
    if 'country' in request.GET:
        country = request.GET['country']

    # data = Effort.objects.only('song__original_song__title','song__original_song__artist__name','activity__start_date','idx_in_activity','start_time','duration','start_distance','distance','avg_speed','act_avg_speed','avg_hr','total_ascent','total_descent',field).order_by('activity__start_date')[::1]

    # results = []
    # for effort in data:
    #    results.append(to_dict(effort))

    # if latest:
    #    return JsonResponse(serializers.serialize("json", results),safe=False)

    qs = Effort.objects

    if activity_type != -1:
        qs = qs.filter(act_type=activity_type)

    if country != 'All':
        qs = qs.filter(activity__athlete__country=country)

    if workout_type != -1:
        if workout_type == 0:
            qs = qs.filter((Q(activity__workout_type=10) | Q(activity__workout_type=0)))
        elif workout_type == 1:
            qs = qs.filter((Q(activity__workout_type=11) | Q(activity__workout_type=1)))
        elif workout_type == 3:
            qs = qs.filter((Q(activity__workout_type=12) | Q(activity__workout_type=3)))
        else:
            qs = qs.filter(activity__workout_type=workout_type)

    if 'hr' in field:
        qs = qs.filter(activity__flagged_hr=False, flagged_hr=False).exclude(avg_hr__isnull=True)
        if 'diff_last' in field:
            qs = qs.exclude(diff_last_hr__isnull=True)
        if 'diff_avg' in field:
            qs = qs.exclude(diff_avg_hr__isnull=True)

    if 'days' in request.GET:
        try:
            days = int(request.GET['days'])
            if days != -1:
                d = datetime.today() - timedelta(days=days)
                comb = datetime.combine(d, datetime.min.time())
                qs = qs.filter(activity__start_date__gt=comb)
        except:
            pass

    distinct = False
    agg_type = None
    if u_type == 'song':
        agg_type = 'song__original_song'
    elif u_type == 'artist':
        agg_type = 'song__original_song__artist_id'

    if field == 'count_users':
        agg_type = 'activity__athlete__athlete_id'
        distinct = True

    order_by_key = 'sort_value'
    if descending == -1:
        order_by_key = '-sort_value'

    qs = remove_flagged(qs, None)
    qs = remove_impossible(qs, activity_type)

    if g_type == 'count':
        if u_type == 'song':
            if field == 'count_users':
                qs = qs.values('song__original_song',
                               'song__original_song__spotify_id',
                               'song__original_song__title',
                               'song__original_song__artist_name',
                               'song__original_song__url',
                               'song__original_song__image_url',
                               'song__original_song__artist__id',
                               'song__original_song__artist__image_url').annotate(
                    sort_value=Count(agg_type, distinct=distinct)).filter(sort_value__gt=(min_count - 1)).annotate(
                    diff_last_hr=Avg('diff_last_hr'), diff_avg_hr=Avg('diff_avg_hr'), avg_hr=Avg('avg_hr'),
                    avg_speed=Avg('avg_speed'), start_distance=Avg('start_distance'), distance=Avg('distance'),
                    duration=Avg('duration'), start_time=Avg('start_time'), diff_last_speed=Avg('diff_last_speed'),
                    diff_avg_speed=Avg('diff_avg_speed'), diff_last_speed_s=Avg('diff_last_speed_s'),
                    diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(sort_value=None).order_by(order_by_key,
                                                                                                'song__original_song__title')
            else:
                qs = qs.values('song__original_song',
                               'song__original_song__spotify_id',
                               'song__original_song__title',
                               'song__original_song__artist_name',
                               'song__original_song__url',
                               'song__original_song__image_url',
                               'song__original_song__artist__id',
                               'song__original_song__artist__image_url').annotate(
                    t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(
                    sort_value=Count(agg_type, distinct=distinct), diff_last_hr=Avg('diff_last_hr'),
                    diff_avg_hr=Avg('diff_avg_hr'), avg_hr=Avg('avg_hr'), avg_speed=Avg('avg_speed'),
                    start_distance=Avg('start_distance'), distance=Avg('distance'), duration=Avg('duration'),
                    start_time=Avg('start_time'), diff_last_speed=Avg('diff_last_speed'),
                    diff_avg_speed=Avg('diff_avg_speed'), diff_last_speed_s=Avg('diff_last_speed_s'),
                    diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(sort_value=None).order_by(order_by_key,
                                                                                                'song__original_song__title')
        elif u_type == 'artist':
            if field == 'count_users':
                qs = qs.values('song__original_song__artist_name',
                                                                      'song__original_song__artist__id',
                                                                      'song__original_song__artist__image_url').annotate(
                    sort_value=Count(agg_type, distinct=distinct)).filter(sort_value__gt=(min_count - 1)).annotate(
                    diff_last_hr=Avg('diff_last_hr'), diff_avg_hr=Avg('diff_avg_hr'), avg_hr=Avg('avg_hr'),
                    avg_speed=Avg('avg_speed'), start_distance=Avg('start_distance'), distance=Avg('distance'),
                    duration=Avg('duration'), start_time=Avg('start_time'), diff_last_speed=Avg('diff_last_speed'),
                    diff_avg_speed=Avg('diff_avg_speed'), diff_last_speed_s=Avg('diff_last_speed_s'),
                    diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(sort_value=None).order_by(order_by_key,
                                                                                                'song__original_song__artist_name')
            else:
                qs = qs.values('song__original_song__artist_name',
                               'song__original_song__artist__id',
                               'song__original_song__artist__image_url').annotate(
                    t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(
                    sort_value=Count(agg_type, distinct=distinct), diff_last_hr=Avg('diff_last_hr'),
                    diff_avg_hr=Avg('diff_avg_hr'), avg_hr=Avg('avg_hr'), avg_speed=Avg('avg_speed'),
                    start_distance=Avg('start_distance'), distance=Avg('distance'), duration=Avg('duration'),
                    start_time=Avg('start_time'), diff_last_speed=Avg('diff_last_speed'),
                    diff_avg_speed=Avg('diff_avg_speed'), diff_last_speed_s=Avg('diff_last_speed_s'),
                    diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(sort_value=None).order_by(order_by_key,
                                                                                                'song__original_song__artist_name')
    elif g_type == 'avg':
        if u_type == 'song':
            qs = qs.values('song__original_song',
                           'song__original_song__spotify_id',
                           'song__original_song__title',
                           'song__original_song__artist_name',
                           'song__original_song__url',
                           'song__original_song__image_url',
                           'song__original_song__artist__id',
                           'song__original_song__artist__image_url').annotate(
                t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field),
                                                                                      diff_last_hr=Avg('diff_last_hr'),
                                                                                      diff_avg_hr=Avg('diff_avg_hr'),
                                                                                      avg_hr=Avg('avg_hr'),
                                                                                      avg_speed=Avg('avg_speed'),
                                                                                      start_distance=Avg(
                                                                                          'start_distance'),
                                                                                      distance=Avg('distance'),
                                                                                      duration=Avg('duration'),
                                                                                      start_time=Avg('start_time'),
                                                                                      diff_last_speed=Avg(
                                                                                          'diff_last_speed'),
                                                                                      diff_avg_speed=Avg(
                                                                                          'diff_avg_speed'),
                                                                                      diff_last_speed_s=Avg(
                                                                                          'diff_last_speed_s'),
                                                                                      diff_avg_speed_s=Avg(
                                                                                          'diff_avg_speed_s')).exclude(
                sort_value=None).order_by(order_by_key, 'song__original_song__title')
        elif u_type == 'artist':
            qs = qs.values('song__original_song__artist_name',
                                                                  'song__original_song__artist__id',
                                                                  'song__original_song__artist__image_url').annotate(
                t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field),
                                                                                      diff_last_hr=Avg('diff_last_hr'),
                                                                                      diff_avg_hr=Avg('diff_avg_hr'),
                                                                                      avg_hr=Avg('avg_hr'),
                                                                                      avg_speed=Avg('avg_speed'),
                                                                                      start_distance=Avg(
                                                                                          'start_distance'),
                                                                                      distance=Avg('distance'),
                                                                                      duration=Avg('duration'),
                                                                                      start_time=Avg('start_time'),
                                                                                      diff_last_speed=Avg(
                                                                                          'diff_last_speed'),
                                                                                      diff_avg_speed=Avg(
                                                                                          'diff_avg_speed'),
                                                                                      diff_last_speed_s=Avg(
                                                                                          'diff_last_speed_s'),
                                                                                      diff_avg_speed_s=Avg(
                                                                                          'diff_avg_speed_s')).exclude(
                sort_value=None).order_by(order_by_key, 'song__original_song__artist_name')

    total_length = len(qs)
    qs = qs[(n * page):(n * (page + 1))]

    if header:
        data['header'] = generate_header(n, page, total_length)

    render_format = 'html'
    if 'render' in request.GET:
        render_format = int(request.GET['render'])

    data['activity_type'] = activity_type
    data['top'] = []
    for q in qs:
        if dispfield:
            q['sort_key'] = dispfield
            if dispfield.startswith("diff"):
                q["diff"] = True
                q["signal"] = ""
                if 'sort_value' in q:
                    if q['sort_value'] < 0:
                        if 'speed' in q['sort_key']:
                            q["diff"] = "slower"
                        else:
                            q["diff"] = "fewer"
                    else:
                        if 'speed' in q['sort_key']:
                            q["diff"] = "faster"
                        else:
                            q["diff"] = "more"

                        q["signal"] = "+"

                if "last" in dispfield:
                    q["last"] = True
                elif "avg" in dispfield:
                    q["average"] = True
        if g_type == 'avg':
            q["average"] = True
        data['top'].append(effort_convert(q, units))

    if render_format == 'json':
        return JsonResponse(data)
    else:
        return render(request,'top_table_effort.html', data)


def top_song_artist(request):
    data = {}

    if not 'type' in request.GET:
        data['error'] = 'Missing type'
        return JsonResponse(data)

    u_type = request.GET['type']

    field = None
    if not 'field' in request.GET:
        data['error'] = 'Missing field'
        return JsonResponse(data)
    elif 'field' in request.GET:
        field = request.GET['field']

    g_type = 'avg'
    if field in ['count']:
        g_type = 'count'

    min_count = 3
    if 'min_count' in request.GET:
        min_count = int(request.GET['min_count'])

    dispfield = field
    if 'dispfield' in request.GET:
        dispfield = request.GET['dispfield']

    header = False
    if 'header' in request.GET:
        header = True

    page = 0
    if 'page' in request.GET and request.GET['page']:
        try:
            page = int(request.GET['page'])
        except:
            pass

    descending = -1
    if 'ascending' in request.GET:
        descending = 1

    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])

    units = None
    if 'units' in request.GET:
        units = request.GET['units']
    if not units:
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        units = athlete.measurement_preference
    else:
        units = 0

    activity_type = get_user_activity_type(request)
    request.session['activity_type'] = activity_type
    workout_type = get_workout_type(request)
    dispfield, field = get_unit_type(activity_type, dispfield, field)

    # data = Effort.objects.only('song__original_song__title','song__original_song__artist__name','activity__start_date','idx_in_activity','start_time','duration','start_distance','distance','avg_speed','act_avg_speed','avg_hr','total_ascent','total_descent',field).order_by('activity__start_date')[::1]

    # results = []
    # for effort in data:
    #    results.append(to_dict(effort))

    # if latest:
    #    return JsonResponse(serializers.serialize("json", results),safe=False)
    max_speed_filter = 27  # bike max speed in meters per second
    if activity_type == 0:
        max_speed_filter = 8  # bike max speed in meters per second

    min_speed_filter = 2

    time_filter = 60

    distance_filter = 100

    diff_filter_min = 0.5
    diff_filter_max = 1.5

    poweruser = get_poweruser(request.session['athlete_id'])

    qs = Effort.objects

    if activity_type != -1:
        qs = qs.filter(act_type=activity_type)

    if workout_type != -1:
        if workout_type == 0:
            qs = qs.filter((Q(activity__workout_type=10) | Q(activity__workout_type=0)))
        elif workout_type == 1:
            qs = qs.filter((Q(activity__workout_type=11) | Q(activity__workout_type=1)))
        elif workout_type == 3:
            qs = qs.filter((Q(activity__workout_type=12) | Q(activity__workout_type=3)))
        else:
            qs = qs.filter(activity__workout_type=workout_type)

    if 'hr' in field:
        qs = qs.filter(activity__flagged_hr=False, flagged_hr=False).exclude(avg_hr__isnull=True)
        if 'diff_last' in field:
            qs = qs.exclude(diff_last_hr__isnull=True)
        if 'diff_avg' in field:
            qs = qs.exclude(diff_avg_hr__isnull=True)

    qs = remove_flagged(qs, poweruser)

    if 'days' in request.GET:
        try:
            days = int(request.GET['days'])
            if days != -1:
                d = datetime.today() - timedelta(days=days)
                comb = datetime.combine(d, datetime.min.time())
                qs = qs.filter(activity__start_date__gt=comb)
        except:
            pass

    agg_type = None
    if u_type == 'song':
        agg_type = 'song__original_song'
    elif u_type == 'artist':
        agg_type = 'song__original_song__artist_id'

    qs = remove_impossible(qs, activity_type)

    if g_type == 'count':
        if u_type == 'song':
            qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values('song__original_song',
                                                                                               'song__original_song__spotify_id',
                                                                                               'song__original_song__title',
                                                                                               'song__original_song__artist_name',
                                                                                               'song__original_song__url',
                                                                                               'song__original_song__image_url',
                                                                                               'song__original_song__artist__id',
                                                                                               'song__original_song__artist__image_url').annotate(
                t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Count(agg_type),
                                                                                      diff_last_hr=Avg('diff_last_hr'),
                                                                                      diff_avg_hr=Avg('diff_avg_hr'),
                                                                                      avg_hr=Avg('avg_hr'),
                                                                                      avg_speed=Avg('avg_speed'),
                                                                                      start_distance=Avg(
                                                                                          'start_distance'),
                                                                                      distance=Avg('distance'),
                                                                                      duration=Avg('duration'),
                                                                                      start_time=Avg('start_time'),
                                                                                      diff_last_speed=Avg(
                                                                                          'diff_last_speed'),
                                                                                      diff_avg_speed=Avg(
                                                                                          'diff_avg_speed'),
                                                                                      diff_last_speed_s=Avg(
                                                                                          'diff_last_speed_s'),
                                                                                      diff_avg_speed_s=Avg(
                                                                                          'diff_avg_speed_s')).exclude(
                sort_value=None).order_by('sort_value')[::descending]
        elif u_type == 'artist':
            qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values(
                'song__original_song__artist_name', 'song__original_song__artist__id',
                'song__original_song__artist__image_url').annotate(t_count=Count(agg_type)).filter(
                t_count__gt=(min_count - 1)).annotate(sort_value=Count(agg_type), diff_last_hr=Avg('diff_last_hr'),
                                                      diff_avg_hr=Avg('diff_avg_hr'), avg_hr=Avg('avg_hr'),
                                                      avg_speed=Avg('avg_speed'), start_distance=Avg('start_distance'),
                                                      distance=Avg('distance'), duration=Avg('duration'),
                                                      start_time=Avg('start_time'),
                                                      diff_last_speed=Avg('diff_last_speed'),
                                                      diff_avg_speed=Avg('diff_avg_speed'),
                                                      diff_last_speed_s=Avg('diff_last_speed_s'),
                                                      diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(
                sort_value=None).order_by('sort_value')[::descending]
    elif g_type == 'avg':
        if u_type == 'song':
            qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values('song__original_song',
                                                                                               'song__original_song__spotify_id',
                                                                                               'song__original_song__title',
                                                                                               'song__original_song__artist_name',
                                                                                               'song__original_song__url',
                                                                                               'song__original_song__image_url',
                                                                                               'song__original_song__artist__id',
                                                                                               'song__original_song__artist__image_url').annotate(
                t_count=Count(agg_type)).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field),
                                                                                      diff_last_hr=Avg('diff_last_hr'),
                                                                                      diff_avg_hr=Avg('diff_avg_hr'),
                                                                                      avg_hr=Avg('avg_hr'),
                                                                                      avg_speed=Avg('avg_speed'),
                                                                                      start_distance=Avg(
                                                                                          'start_distance'),
                                                                                      distance=Avg('distance'),
                                                                                      duration=Avg('duration'),
                                                                                      start_time=Avg('start_time'),
                                                                                      diff_last_speed=Avg(
                                                                                          'diff_last_speed'),
                                                                                      diff_avg_speed=Avg(
                                                                                          'diff_avg_speed'),
                                                                                      diff_last_speed_s=Avg(
                                                                                          'diff_last_speed_s'),
                                                                                      diff_avg_speed_s=Avg(
                                                                                          'diff_avg_speed_s')).exclude(
                sort_value=None).order_by('sort_value')[::descending]
        elif u_type == 'artist':
            qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values(
                'song__original_song__artist_name', 'song__original_song__artist__id',
                'song__original_song__artist__image_url').annotate(t_count=Count(agg_type)).filter(
                t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field), diff_last_hr=Avg('diff_last_hr'),
                                                      diff_avg_hr=Avg('diff_avg_hr'), avg_hr=Avg('avg_hr'),
                                                      avg_speed=Avg('avg_speed'), start_distance=Avg('start_distance'),
                                                      distance=Avg('distance'), duration=Avg('duration'),
                                                      start_time=Avg('start_time'),
                                                      diff_last_speed=Avg('diff_last_speed'),
                                                      diff_avg_speed=Avg('diff_avg_speed'),
                                                      diff_last_speed_s=Avg('diff_last_speed_s'),
                                                      diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(
                sort_value=None).order_by('sort_value')[::descending]

    total_length = len(qs)
    qs = qs[(n * page):(n * (page + 1))]

    if header:
        data['header'] = generate_header(n, page, total_length)

    render_format = 'html'
    if 'render' in request.GET:
        render_format = int(request.GET['render'])

    data['activity_type'] = activity_type
    data['top'] = []
    for q in qs:
        if dispfield:
            q['sort_key'] = dispfield
            if dispfield.startswith("diff"):
                q["diff"] = True
                q["signal"] = ""
                if 'sort_value' in q:
                    if q['sort_value'] < 0:
                        if 'speed' in q['sort_key']:
                            q["diff"] = "slower"
                        else:
                            q["diff"] = "fewer"
                    else:
                        if 'speed' in q['sort_key']:
                            q["diff"] = "faster"
                        else:
                            q["diff"] = "more"

                        q["signal"] = "+"

                if "last" in dispfield:
                    q["last"] = True
                elif "avg" in dispfield:
                    q["average"] = True
        if g_type == 'avg':
            q["average"] = True
        data['top'].append(effort_convert(q, units))

    if render_format == 'json':
        return JsonResponse(data)
    else:
        return render(request,'top_table_effort.html', data)


def top(request):
    data = {}

    if not 'type' in request.GET:
        data['error'] = 'Missing type'
        return JsonResponse(data)

    g_type = request.GET['type']

    if not g_type in ['top', 'avg', 'sum', 'count']:
        data['error'] = 'Invalid type'
        return JsonResponse(data)

    field = None
    if not 'field' in request.GET:
        data['error'] = 'Missing field'
        return JsonResponse(data)
    elif 'field' in request.GET:
        field = request.GET['field']

    dispfield = field
    if 'dispfield' in request.GET:
        dispfield = request.GET['dispfield']

    header = False
    if 'header' in request.GET:
        header = True

    page = 0
    if 'page' in request.GET and request.GET['page']:
        try:
            page = int(request.GET['page'])
        except:
            pass

    min_count = 3
    if 'min_count' in request.GET:
        min_count = int(request.GET['min_count'])

    descending = -1
    if 'ascending' in request.GET:
        descending = 1

    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])

    units = None
    if 'units' in request.GET:
        units = request.GET['units']
    if not units:
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        units = athlete.measurement_preference
    else:
        units = 0

    activity_type = get_user_activity_type(request)
    request.session['activity_type'] = activity_type
    workout_type = get_workout_type(request)
    dispfield, field = get_unit_type(activity_type, dispfield, field)

    # data = Effort.objects.only('song__original_song__title','song__original_song__artist__name','activity__start_date','idx_in_activity','start_time','duration','start_distance','distance','avg_speed','act_avg_speed','avg_hr','total_ascent','total_descent',field).order_by('activity__start_date')[::1]

    # results = []
    # for effort in data:
    #    results.append(to_dict(effort))

    # if latest:
    #    return JsonResponse(serializers.serialize("json", results),safe=False)

    poweruser = get_poweruser(request.session['athlete_id'])

    qs = Effort.objects

    if activity_type != -1:
        qs = qs.filter(act_type=activity_type)

    if workout_type != -1:
        if workout_type == 0:
            qs = qs.filter((Q(activity__workout_type=10) | Q(activity__workout_type=0)))
        elif workout_type == 1:
            qs = qs.filter((Q(activity__workout_type=11) | Q(activity__workout_type=1)))
        elif workout_type == 3:
            qs = qs.filter((Q(activity__workout_type=12) | Q(activity__workout_type=3)))
        else:
            qs = qs.filter(activity__workout_type=workout_type)

    if 'hr' in field:
        qs = qs.filter(activity__flagged_hr=False, flagged_hr=False).exclude(avg_hr__isnull=True)
        if 'diff_last' in field:
            qs = qs.exclude(diff_last_hr__isnull=True)
        if 'diff_avg' in field:
            qs = qs.exclude(diff_avg_hr__isnull=True)


    if 'days' in request.GET:
        try:
            days = int(request.GET['days'])
            if days != -1:
                d = datetime.today() - timedelta(days=days)
                comb = datetime.combine(d, datetime.min.time())
                qs = qs.filter(activity__start_date__gt=comb)
        except:
            pass


    qs = remove_impossible(qs, activity_type)
    qs = remove_flagged(qs, poweruser)

    if g_type == 'top':
        qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values('song__original_song',
                                                                                           'song__original_song__spotify_id',
                                                                                           'song__original_song__title',
                                                                                           'song__original_song__artist_name',
                                                                                           'song__original_song__url',
                                                                                           'song__original_song__image_url',
                                                                                           'song__original_song__artist__id',
                                                                                           'song__original_song__artist__image_url',
                                                                                           'activity__activity_id',
                                                                                           'activity__name',
                                                                                           'activity__workout_type',
                                                                                           'activity__start_date_local',
                                                                                           'diff_last_hr',
                                                                                           'diff_avg_hr', 'avg_speed',
                                                                                           'start_distance', 'distance',
                                                                                           'start_time', 'duration',
                                                                                           'avg_hr', 'diff_last_speed',
                                                                                           'diff_avg_speed',
                                                                                           'diff_last_speed_s',
                                                                                           'diff_avg_speed_s').annotate(
            sort_value=Avg(field)).exclude(sort_value__isnull=True).order_by(field)[::descending]
    elif g_type == 'count':
        qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values('song__original_song',
                                                                                           'song__original_song__spotify_id',
                                                                                           'song__original_song__title',
                                                                                           'song__original_song__artist_name',
                                                                                           'song__original_song__url',
                                                                                           'song__original_song__image_url',
                                                                                           'song__original_song__artist__id',
                                                                                           'song__original_song__artist__image_url').annotate(
            t_count=Count('song__original_song')).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Count(field),
                                                                                               diff_last_hr=Avg(
                                                                                                   'diff_last_hr'),
                                                                                               diff_avg_hr=Avg(
                                                                                                   'diff_avg_hr'),
                                                                                               avg_hr=Avg('avg_hr'),
                                                                                               avg_speed=Avg(
                                                                                                   'avg_speed'),
                                                                                               start_distance=Avg(
                                                                                                   'start_distance'),
                                                                                               distance=Avg('distance'),
                                                                                               duration=Avg('duration'),
                                                                                               start_time=Avg(
                                                                                                   'start_time'),
                                                                                               diff_last_speed=Avg(
                                                                                                   'diff_last_speed'),
                                                                                               diff_avg_speed=Avg(
                                                                                                   'diff_avg_speed'),
                                                                                               diff_last_speed_s=Avg(
                                                                                                   'diff_last_speed_s'),
                                                                                               diff_avg_speed_s=Avg(
                                                                                                   'diff_avg_speed_s')).exclude(
            sort_value=None).order_by('sort_value')[::descending]
    elif g_type == 'avg':
        qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values('song__original_song',
                                                                                           'song__original_song__spotify_id',
                                                                                           'song__original_song__title',
                                                                                           'song__original_song__artist_name',
                                                                                           'song__original_song__url',
                                                                                           'song__original_song__image_url',
                                                                                           'song__original_song__artist__id',
                                                                                           'song__original_song__artist__image_url').annotate(
            t_count=Count('song__original_song')).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Avg(field),
                                                                                               diff_last_hr=Avg(
                                                                                                   'diff_last_hr'),
                                                                                               diff_avg_hr=Avg(
                                                                                                   'diff_avg_hr'),
                                                                                               avg_hr=Avg('avg_hr'),
                                                                                               avg_speed=Avg(
                                                                                                   'avg_speed'),
                                                                                               start_distance=Avg(
                                                                                                   'start_distance'),
                                                                                               distance=Avg('distance'),
                                                                                               duration=Avg('duration'),
                                                                                               start_time=Avg(
                                                                                                   'start_time'),
                                                                                               diff_last_speed=Avg(
                                                                                                   'diff_last_speed'),
                                                                                               diff_avg_speed=Avg(
                                                                                                   'diff_avg_speed'),
                                                                                               diff_last_speed_s=Avg(
                                                                                                   'diff_last_speed_s'),
                                                                                               diff_avg_speed_s=Avg(
                                                                                                   'diff_avg_speed_s')).exclude(
            sort_value=None).order_by('sort_value')[::descending]
    elif g_type == 'sum':
        qs = qs.filter(activity__athlete__athlete_id=request.session['athlete_id']).values('song__original_song',
                                                                                           'song__original_song__spotify_id',
                                                                                           'song__original_song__title',
                                                                                           'song__original_song__artist_name',
                                                                                           'song__original_song__url',
                                                                                           'song__original_song__image_url',
                                                                                           'song__original_song__artist__id',
                                                                                           'song__original_song__artist__image_url').annotate(
            t_count=Count('song__original_song')).filter(t_count__gt=(min_count - 1)).annotate(sort_value=Sum(field),
                                                                                               diff_last_hr=Avg(
                                                                                                   'diff_last_hr'),
                                                                                               diff_avg_hr=Avg(
                                                                                                   'diff_avg_hr'),
                                                                                               avg_hr=Avg('avg_hr'),
                                                                                               avg_speed=Avg(
                                                                                                   'avg_speed'),
                                                                                               start_distance=Avg(
                                                                                                   'start_distance'),
                                                                                               distance=Avg('distance'),
                                                                                               duration=Avg('duration'),
                                                                                               start_time=Avg(
                                                                                                   'start_time'),
                                                                                               diff_last_speed=Avg(
                                                                                                   'diff_last_speed'),
                                                                                               diff_avg_speed=Avg(
                                                                                                   'diff_avg_speed'),
                                                                                               diff_last_speed_s=Avg(
                                                                                                   'diff_last_speed_s'),
                                                                                               diff_avg_speed_s=Avg(
                                                                                                   'diff_avg_speed_s')).exclude(
            sort_value=None).order_by('sort_value')[::descending]

    total_length = len(qs)
    qs = qs[(n * page):(n * (page + 1))]

    if header:
        data['header'] = generate_header(n, page, total_length)

    render_format = 'html'
    if 'render' in request.GET:
        render_format = int(request.GET['render'])

    data['activity_type'] = activity_type
    data['top'] = []
    for q in qs:
        if dispfield:
            q['sort_key'] = dispfield
            if dispfield.startswith("diff"):
                q["diff"] = True
                q["signal"] = ""
                if 'sort_value' in q:
                    if q['sort_value'] < 0:
                        if 'speed' in q['sort_key']:
                            q["diff"] = "slower"
                        else:
                            q["diff"] = "fewer"
                    else:
                        if 'speed' in q['sort_key']:
                            q["diff"] = "faster"
                        else:
                            q["diff"] = "more"

                        q["signal"] = "+"

                if "last" in dispfield:
                    q["last"] = True
                elif "avg" in dispfield:
                    q["average"] = True
        if g_type == 'avg':
            q["average"] = True
        data['top'].append(effort_convert(q, units))

    if render_format == 'json':
        return JsonResponse(data)
    else:
        return render(request,'top_table_effort.html', data)


def latest(request):
    data = {}

    if not 'athlete_id' in request.session:
        return redirect("/")

    poweruser = get_poweruser(request.session['athlete_id'])

    data['athlete'] = poweruser.athlete
    data['listener'] = poweruser.listener

    descending = -1
    if 'ascending' in request.GET:
        descending = 1

    activity_type = get_user_activity_type(request)
    data['activity_type'] = activity_type

    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])

    data['top'] = Activity.objects.filter(athlete__athlete_id=request.session['athlete_id']).annotate(
        ecount=Count('effort')).order_by('-start_date_local')[:n]

    return render(request,'activities.html', data)
