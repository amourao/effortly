from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from django.http import JsonResponse

from powersong.models import *
from django.db.models import Avg,Sum,Max,Count

from django.core import serializers

from powersong.strava_aux import strava_get_user_info_by_id

import logging

from django.forms.models import model_to_dict

logger = logging.getLogger(__name__)


from django.db.models.fields.related import ManyToManyField

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
    if not activity_type:
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        activity_type = athlete.athlete_type

    if activity_type == 0 and dispfield in speed:
        dispfield += "_s"
     
    #data = Effort.objects.only('song__title','song__artist__name','activity__start_date','idx_in_activity','start_time','duration','start_distance','distance','avg_speed','act_avg_speed','avg_hr','total_ascent','total_descent',field).order_by('activity__start_date')[::1]

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
    
    if g_type == 'top':
        qs = Effort.objects.filter(distance__gt=distance_filter,duration__gt=time_filter,avg_speed__gt=min_speed_filter,avg_speed__lt=max_speed_filter,act_type=activity_type,activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_distance','distance','start_time','duration','avg_hr').annotate(sort_value=Avg(field)).order_by(field)[::descending][:n]
    elif g_type == 'avg':
        qs = Effort.objects.filter(distance__gt=distance_filter,duration__gt=time_filter,avg_speed__gt=min_speed_filter,avg_speed__lt=max_speed_filter,act_type=activity_type,activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url').annotate(t_count=Count('song')).filter(t_count__gt=(min_count-1)).annotate(sort_value=Avg(field),diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_distance=Avg('start_distance'),distance=Avg('distance'),duration=Avg('duration'),start_time=Avg('start_time')).order_by('sort_value')[::descending][:n]
    elif g_type == 'sum':
        qs = Effort.objects.filter(distance__gt=distance_filter,duration__gt=time_filter,avg_speed__gt=min_speed_filter,avg_speed__lt=max_speed_filter,act_type=activity_type,activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url').annotate(t_count=Count('song')).filter(t_count__gt=(min_count-1)).annotate(sort_value=Sum(field),diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_distance=Avg('start_distance'),distance=Avg('distance'),duration=Avg('duration'),start_time=Avg('start_time')).order_by('sort_value')[::descending][:n]

    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
        

    
    data['top'] = []
    for q in qs:
        if dispfield:
            q['sort_key'] = dispfield
        data['top'].append(effort_convert(q,units))

    if render == 'json':
        return JsonResponse(data)
    else:
        return render_to_response('top_table_effort.html', data)



def latest(request):
    data = {}

    descending = -1
    if 'ascending' in request.GET:
        descending = 1
    
    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])
    
    qs = Activity.objects.filter(athlete__athlete_id = request.session['athlete_id']).values('name','activity_id','workout_type','start_date_local').order_by('start_date_local')[::descending][:n]
    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
        
    units = None
    if 'units' in request.GET:
        units = request.GET['units']
    if not units:
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        units = athlete.measurement_preference
    else:
        units = 0
    
    data['top'] = []
    for q in qs:
        data['top'].append(effort_convert(q,units))

    if render == 'json':
        return JsonResponse(data)
    else:
        return render_to_response('top_summary_table.html', data)
