from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from django.http import JsonResponse

from powersong.models import *
from django.db.models import Avg,Sum,Max,Count
from django.db.models import Q

from django.core import serializers

from powersong.strava_aux import strava_get_user_info_by_id

import logging
import math

from django.forms.models import model_to_dict

logger = logging.getLogger(__name__)


from django.db.models.fields.related import ManyToManyField


def top_detailed_view(request):
    data = {}
    return JsonResponse(data)


def top(request):
    data = {}

    if not 'type' in request.GET:
        data['error'] = 'Missing type'
        return JsonResponse(data)

    g_type  = request.GET['type']

    if not g_type in ['top','avg','sum']:
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

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])

    if activity_type == None:
        if not 'athlete_type' in request.session:
            athlete = strava_get_user_info_by_id(request.session['athlete_id'])
            activity_type = athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    request.session['activity_type'] = activity_type

    workout_type = -1
    if 'workout_type' in request.GET:
        try:
            workout_type = int(request.GET['workout_type'])
        except:
            pass

    if activity_type == 0 and 'diff' in field and 'speed' in field:
        field += "_s"

    if activity_type == 0 and dispfield in speed:
        dispfield += "_s"
     
    #data = Effort.objects.only('song__original_song__title','song__original_song__artist__name','activity__start_date','idx_in_activity','start_time','duration','start_distance','distance','avg_speed','act_avg_speed','avg_hr','total_ascent','total_descent',field).order_by('activity__start_date')[::1]

    #results = []
    #for effort in data:
    #    results.append(to_dict(effort))

    #if latest:
    #    return JsonResponse(serializers.serialize("json", results),safe=False)
    max_speed_filter = 27 # bike max speed in meters per second
    if activity_type == 0:
        max_speed_filter = 8 # bike max speed in meters per second

    min_speed_filter = 2

    time_filter = 60

    distance_filter = 100

    diff_filter_min = 0.5
    diff_filter_max = 1.5

    poweruser = get_poweruser(request.session['strava_token'])

    
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
        qs = qs.filter(activity__flagged_hr=False,flagged_hr=False).exclude(avg_hr__isnull=True)
        if 'diff_last' in field:
            qs = qs.exclude(diff_last_hr__isnull=True)
        if 'diff_avg' in field:
            qs = qs.exclude(diff_avg_hr__isnull=True)

    flaggedsong_ids = [a[0] for a in FlaggedSong.objects.filter(poweruser=poweruser).values_list('song_id')]
    flaggedartist_ids = [a[0] for a in FlaggedArtist.objects.filter(poweruser=poweruser).values_list('artist_id')]

    qs = qs.exclude(song__original_song__in=flaggedsong_ids)
    qs = qs.exclude(song__original_song__artist__in=flaggedartist_ids)

    if g_type == 'top':
        qs = qs.filter(activity__flagged=False,flagged=False,distance__gt=distance_filter,duration__gt=time_filter,avg_speed__gt=min_speed_filter,avg_speed__lt=max_speed_filter,activity__athlete__athlete_id = request.session['athlete_id']).values('song__original_song','song__original_song__spotify_id','song__original_song__title','song__original_song__artist_name','song__original_song__url','song__original_song__image_url','song__original_song__artist__id','song__original_song__artist__image_url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_distance','distance','start_time','duration','avg_hr','diff_last_speed','diff_avg_speed','diff_last_speed_s','diff_avg_speed_s').annotate(sort_value=Avg(field)).exclude(sort_value__isnull=True).order_by(field)[::descending]
    elif g_type == 'avg':
        qs = qs.filter(activity__flagged=False,flagged=False,distance__gt=distance_filter,duration__gt=time_filter,avg_speed__gt=min_speed_filter,avg_speed__lt=max_speed_filter,activity__athlete__athlete_id = request.session['athlete_id']).values('song__original_song','song__original_song__spotify_id','song__original_song__title','song__original_song__artist_name','song__original_song__url','song__original_song__image_url','song__original_song__artist__id','song__original_song__artist__image_url').annotate(t_count=Count('song__original_song')).filter(t_count__gt=(min_count-1)).annotate(sort_value=Avg(field),diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_distance=Avg('start_distance'),distance=Avg('distance'),duration=Avg('duration'),start_time=Avg('start_time'),diff_last_speed=Avg('diff_last_speed'),diff_avg_speed=Avg('diff_avg_speed'),diff_last_speed_s=Avg('diff_last_speed_s'),diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(sort_value=None).order_by('sort_value')[::descending]
    elif g_type == 'sum':
        qs = qs.filter(activity__flagged=False,flagged=False,distance__gt=distance_filter,duration__gt=time_filter,avg_speed__gt=min_speed_filter,avg_speed__lt=max_speed_filter,activity__athlete__athlete_id = request.session['athlete_id']).values('song__original_song','song__original_song__spotify_id','song__original_song__title','song__original_song__artist_name','song__original_song__url','song__original_song__image_url','song__original_song__artist__id','song__original_song__artist__image_url').annotate(t_count=Count('song__original_song')).filter(t_count__gt=(min_count-1)).annotate(sort_value=Sum(field),diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_distance=Avg('start_distance'),distance=Avg('distance'),duration=Avg('duration'),start_time=Avg('start_time'),diff_last_speed=Avg('diff_last_speed'),diff_avg_speed=Avg('diff_avg_speed'),diff_last_speed_s=Avg('diff_last_speed_s'),diff_avg_speed_s=Avg('diff_avg_speed_s')).exclude(sort_value=None).order_by('sort_value')[::descending]

    total_length = len(qs)
    qs = qs[(n*page):(n*(page+1))]

    if header:
        data['header'] = "Page {} of {} - Total results: {}".format(page+1,math.ceil(total_length/n),total_length)

    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
    
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
        data['top'].append(effort_convert(q,units))

    if render == 'json':
        return JsonResponse(data)
    else:
        return render_to_response('top_table_effort.html', data)



def latest(request):
    data = {}

    if not 'strava_token' in request.session:
        return redirect("/")
    
    poweruser = get_poweruser(request.session['strava_token'])

    data['athlete'] = poweruser.athlete
    data['listener'] = poweruser.listener

    descending = -1
    if 'ascending' in request.GET:
        descending = 1

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'athlete_type' in request.session:
            athlete = strava_get_user_info_by_id(request.session['athlete_id'])
            activity_type = athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    data['activity_type'] = activity_type

    
    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])
    
    data['top'] = Activity.objects.filter(athlete__athlete_id = request.session['athlete_id']).annotate(ecount = Count('effort')).order_by('-start_date_local')[:n]

    return render_to_response('activities.html', data)
