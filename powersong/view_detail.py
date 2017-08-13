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

def activity(request,activity_id):
    data = {}

    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
        

    data['top'] = Effort.objects.filter(activity__activity_id = activity_id, activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_distance','distance','duration','avg_hr','start_time').order_by('start_time')
    if render == 'json':
        qs = data['top']
        data['top'] = []
        for q in qs:
            data['top'].append(q)
        return JsonResponse(data)
    else:
        return render_to_response('activity.html', data)

def song(request,song_id):
    data = {}

    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
        

    data['top'] = Effort.objects.filter(song__id = song_id, activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__artist__id','song__url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_distance','distance','duration','avg_hr','start_time').order_by('activity__start_date_local')[::-1]
    if render == 'json':
        qs = data['top']
        data['top'] = []
        for q in qs:
            data['top'].append(q)
        return JsonResponse(data)
    else:
        return render_to_response('activity.html', data)

def artist(request,artist_id):
    data = {}

    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])
        

    data['top'] = Effort.objects.filter(song__artist__id = artist_id, activity__athlete__athlete_id = request.session['athlete_id']).annotate(t_count=Count('song')).values('song','song__title','song__artist_name','song__url','song__artist__id').annotate(sort_value=Count('song')).annotate(diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),start_distance=Avg('start_distance'),distance=Avg('distance'),duration=Avg('duration'),start_time=Avg('start_time')).order_by('sort_value')[::-1]
    if render == 'json':
        qs = data['top']
        data['top'] = []
        for q in qs:
            data['top'].append(q)
        return JsonResponse(data)
    else:
        return render_to_response('activity.html', data)


def stats(request):
    data = {}
    render = 'html'
    if 'render' in request.GET:
        render = int(request.GET['render'])

    if render == 'json':
        qs = data['top']
        data['top'] = []
        for q in qs:
            data['top'].append(q)
        return JsonResponse(data)
    else:
        return render_to_response('activity.html', data)