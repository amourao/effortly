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


logger = logging.getLogger(__name__)


from django.db.models.fields.related import ManyToManyField

def top(request):
    data = {}

    if not 'type' in request.GET:
        data['error'] = 'Missing type'
        return JsonResponse(data)

    g_type  = request.GET['type']

    if not g_type in ['top','avg','sum','latest']:
        data['error'] = 'Invalid type'
        return JsonResponse(data)

    if not 'field' in request.GET and g_type != 'latest':
        data['error'] = 'Missing field'
        return JsonResponse(data)
    elif 'field' in request.GET:
        field = request.GET['field']

    min_count = 3
    if 'min_count' in request.GET:
        min_count = int(request.GET['min_count'])
    
    n = 10
    if 'n' in request.GET:
        n = int(request.GET['n'])

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if not activity_type and g_type != 'latest':
        athlete = strava_get_user_info_by_id(request.session['athlete_id'])
        activity_type = athlete.athlete_type


    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
        
    #data = Effort.objects.only('song__title','song__artist__name','activity__start_date','idx_in_activity','start_time','duration','start_dist','end_dist','avg_speed','act_avg_speed','avg_hr','total_ascent','total_descent',field).order_by('activity__start_date')[::1]

    #results = []
    #for effort in data:
    #    results.append(to_dict(effort))

    #if latest:
    #    return JsonResponse(serializers.serialize("json", results),safe=False)
    if g_type == 'top':
        data['top'] = Effort.objects.filter(act_type=activity_type).filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_dist','end_dist','start_time','duration','avg_hr').order_by(field)[::-1][:n]
        data['sort_key'] = field
    elif g_type == 'avg':
        data['top'] = Effort.objects.filter(act_type=activity_type).filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url').annotate(t_count=Count('song')).filter(t_count__gt=(min_count-1)).annotate(sort_value=Avg(field),diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_dist=Avg('start_dist'),end_dist=Avg('end_dist'),duration=Avg('duration'),start_time=Avg('start_time')).order_by('sort_value')[::-1][:n]
        data['sort_value'] = 'sort_value'
    elif g_type == 'sum':
        data['top'] = Effort.objects.filter(act_type=activity_type).filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url').annotate(t_count=Count('song')).filter(t_count__gt=(min_count-1)).annotate(sort_value=Sum(field),diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_dist=Avg('start_dist'),end_dist=Avg('end_dist'),duration=Avg('duration'),start_time=Avg('start_time')).order_by('sort_value')[::-1][:n]
        data['sort_value'] = 'sort_value'
    elif g_type == 'latest':
        if activity_type:
            data['top'] = Effort.objects.filter(act_type=activity_type).filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_dist','end_dist','duration','avg_hr').order_by('activity__start_date')[:n]
        else:
            data['top'] = Effort.objects.filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_dist','end_dist','duration','avg_hr').order_by('activity__start_date')[:n]
    if render == 'json':
        return JsonResponse(data,safe=False)
    else:
        return render_to_response('top_table.html', data)