from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from django.contrib.sites.shortcuts import get_current_site

from django.conf import settings

from django.http import JsonResponse

from powersong.models import *
from django.db.models import Value,Avg,Sum,Max,Count,F,Case,When,IntegerField,FloatField


from django.core import serializers

from powersong.strava_aux import strava_get_user_info_by_id

import logging


logger = logging.getLogger(__name__)


from django.db.models.fields.related import ManyToManyField


def get_scrobble_details(athlete_id,activity_type):
    if activity_type != -1:
        qs = Effort.objects.filter(activity__athlete__athlete_id = athlete_id, act_type = activity_type)
    else:
        qs = Effort.objects.filter(activity__athlete__athlete_id = athlete_id)
    count_s = len(qs)
    count_a = len(qs.values('activity_id').annotate(t_count=Count('activity_id')))
    return count_s,count_a

def activity(request,activity_id):

    data = {}

    if not 'strava_token' in request.session:
        return redirect("/")
    
    poweruser = get_poweruser(request.session['strava_token'])

    data['athlete'] = poweruser.athlete
    data['listener'] = poweruser.listener

    qs = Effort.objects.filter(activity__activity_id = activity_id, activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url','diff_last_hr','diff_avg_hr','diff_last_speed','diff_avg_speed','avg_speed','start_distance','distance','duration','avg_hr','start_time','song__artist__id','diff_avg_speed','diff_last_speed','diff_avg_speed_s','diff_last_speed_s').order_by('start_time')
    activity = Activity.objects.filter(activity_id = activity_id)[0]
    data['activity_type'] = activity.act_type
    data['activity'] = activity

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
        if (activity.act_type == 0):
            q['sort_key'] = 'avg_speed_s'
            q['sort_value'] = q['avg_speed']
        else:
            q['sort_key'] = 'avg_speed'
            q['sort_value'] = q['avg_speed']
        data['top'].append(effort_convert(q,units))

    if render == 'json':
        return JsonResponse(data)
    else:
        return render_to_response('activity.html', data)

def song(request,song_id):

    data = {}

    if not 'strava_token' in request.session:
        return redirect("/")
    
    poweruser = get_poweruser(request.session['strava_token'])

    data['athlete'] = poweruser.athlete
    data['listener'] = poweruser.listener
    data['song'] = Song.objects.filter(id = song_id)[0]

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'activity_type' in request.session:
            activity_type = poweruser.athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    data['activity_type'] = activity_type
    request.session['activity_type'] = activity_type

    if data['activity_type'] != -1:
        qs = Effort.objects.filter(act_type = data['activity_type'])
    else:
        qs = Effort.objects
    
    qs = qs.filter(song__id = song_id, activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url','activity__activity_id','activity__name','activity__workout_type','activity__start_date_local','diff_last_hr','diff_avg_hr','avg_speed','start_distance','distance','duration','avg_hr','start_time','diff_avg_speed','diff_last_speed','diff_avg_speed_s','diff_last_speed_s').order_by('activity__start_date_local')

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

    avg_qs = None
    if qs.count() > 0:
        
        avg_qs = qs.aggregate(avg_diff_last_speed_s=Avg('diff_last_speed_s'),avg_diff_avg_speed_s=Avg('diff_avg_speed_s'),avg_diff_last_speed=Avg('diff_last_speed'),avg_diff_avg_speed=Avg('diff_avg_speed'),avg_diff_last_hr=Avg('diff_last_hr'),avg_diff_avg_hr=Avg('diff_avg_hr'),avg_avg_hr=Avg('avg_hr'),avg_avg_speed=Avg('avg_speed'),avg_start_distance=Avg('start_distance'),avg_distance=Avg('distance'),avg_duration=Avg('duration'),avg_start_time=Avg('start_time'))
        
        ## alternative method adjusted for effort duration

        #qs = qs.annotate(hr_duration=Sum(Case(When(avg_hr__gt=0.0, then='duration'),default=0,output_field=FloatField())))
        #qs = qs.annotate(ndiff_last_speed_s=(F('diff_last_speed_s') * F('distance')),ndiff_avg_speed_s=(F('diff_avg_speed_s') * F('distance')),ndiff_last_speed=(F('diff_last_speed') * F('distance')),ndiff_avg_speed=(F('diff_avg_speed') * F('distance')),ndiff_last_hr=(F('diff_last_hr') * F('duration')),ndiff_avg_hr=(F('diff_avg_hr') * F('duration')),navg_hr=(F('avg_hr') * F('duration')),navg_speed=(F('avg_speed') * F('distance')))
        #avg_qs = qs.aggregate(avg_diff_last_speed_s=Sum('ndiff_last_speed_s') / Sum('distance'),avg_diff_avg_speed_s=Sum('ndiff_avg_speed_s')/Sum('distance'),avg_diff_last_speed=Sum('ndiff_last_speed')/Sum('distance'),avg_diff_avg_speed=Sum('ndiff_avg_speed')/Sum('distance'),avg_diff_last_hr=Sum('ndiff_last_hr')/Sum('hr_duration'),avg_diff_avg_hr=Sum('ndiff_avg_hr')/Sum('hr_duration'),avg_avg_hr=Sum('navg_hr')/Sum('hr_duration'),avg_avg_speed=Sum('navg_speed')/Sum('distance'),avg_start_distance=Avg('start_distance'),avg_distance=Avg('distance'),avg_duration=Avg('duration'),avg_start_time=Avg('start_time'))
        
        data['effort_averages'] = effort_convert(avg_qs,units)
        data['effort_averages']['count'] = qs.count()
    
    data['top'] = []
    for q in qs:
        if (q['activity__workout_type'] == 0):
            q['sort_key'] = 'avg_speed_s'
            q['sort_value'] = q['avg_speed']
        else:
            q['sort_key'] = 'avg_speed'
            q['sort_value'] = q['avg_speed']
        data['top'].append(effort_convert(q,units))

    if render == 'json':
        return JsonResponse(data)
    else:
        return render_to_response('song.html', data)

def artist(request,artist_id):
    data = {}

    if not 'strava_token' in request.session:
        return redirect("/")
    
    poweruser = get_poweruser(request.session['strava_token'])

    data['athlete'] = poweruser.athlete
    data['listener'] = poweruser.listener
    data['artist'] = Artist.objects.filter(id = artist_id)[0]

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'activity_type' in request.session:
            activity_type = poweruser.athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    data['activity_type'] = activity_type
    request.session['activity_type'] = activity_type

    qs = Effort.objects.filter(song__artist__id = artist_id, activity__athlete__athlete_id = request.session['athlete_id'])
    
    if data['activity_type'] != -1:
        qs = qs.filter(act_type = data['activity_type'])  

    effort_count = qs.count()

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

    avg_qs = None
    if qs.count() > 0:
        
        avg_qs = qs.aggregate(avg_diff_last_speed_s=Avg('diff_last_speed_s'),avg_diff_avg_speed_s=Avg('diff_avg_speed_s'),avg_diff_last_speed=Avg('diff_last_speed'),avg_diff_avg_speed=Avg('diff_avg_speed'),avg_diff_last_hr=Avg('diff_last_hr'),avg_diff_avg_hr=Avg('diff_avg_hr'),avg_avg_hr=Avg('avg_hr'),avg_avg_speed=Avg('avg_speed'),avg_start_distance=Avg('start_distance'),avg_distance=Avg('distance'),avg_duration=Avg('duration'),avg_start_time=Avg('start_time'))

        ## alternative method adjusted for effort duration        
        
        #qs = qs.annotate(hr_duration=Sum(Case(When(avg_hr__gt=0.0, then='duration'),default=0,output_field=FloatField())))
        #qs = qs.annotate(ndiff_last_speed_s=(F('diff_last_speed_s') * F('distance')),ndiff_avg_speed_s=(F('diff_avg_speed_s') * F('distance')),ndiff_last_speed=(F('diff_last_speed') * F('distance')),ndiff_avg_speed=(F('diff_avg_speed') * F('distance')),ndiff_last_hr=(F('diff_last_hr') * F('duration')),ndiff_avg_hr=(F('diff_avg_hr') * F('duration')),navg_hr=(F('avg_hr') * F('duration')),navg_speed=(F('avg_speed') * F('distance')))
        #avg_qs = qs.aggregate(avg_diff_last_speed_s=Sum('ndiff_last_speed_s') / Sum('distance'),avg_diff_avg_speed_s=Sum('ndiff_avg_speed_s')/Sum('distance'),avg_diff_last_speed=Sum('ndiff_last_speed')/Sum('distance'),avg_diff_avg_speed=Sum('ndiff_avg_speed')/Sum('distance'),avg_diff_last_hr=Sum('ndiff_last_hr')/Sum('hr_duration'),avg_diff_avg_hr=Sum('ndiff_avg_hr')/Sum('hr_duration'),avg_avg_hr=Sum('navg_hr')/Sum('hr_duration'),avg_avg_speed=Sum('navg_speed')/Sum('distance'),avg_start_distance=Avg('start_distance'),avg_distance=Avg('distance'),avg_duration=Avg('duration'),avg_start_time=Avg('start_time'))
        
        data['effort_averages'] = effort_convert(avg_qs,units)
        data['effort_averages']['effort_count'] = effort_count
        data['effort_averages']['song_count'] = qs.values('song').distinct().count()

    qs = qs.annotate(t_count=Count('song')).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url').annotate(sort_value=Count('song')).annotate(diff_last_hr=Avg('diff_last_hr'),diff_avg_hr=Avg('diff_avg_hr'),avg_hr=Avg('avg_hr'),avg_speed=Avg('avg_speed'),diff_last_speed=Avg('diff_last_speed'),diff_avg_speed=Avg('diff_avg_speed'),diff_last_speed_s=Avg('diff_last_speed_s'),diff_avg_speed_s=Avg('diff_avg_speed_s'),start_distance=Avg('start_distance'),distance=Avg('distance'),duration=Avg('duration'),start_time=Avg('start_time')).order_by('sort_value')[::-1]
    
    
    data['top'] = []
    for q in qs:
        data['top'].append(effort_convert(q,units))

    if render == 'json':
        return JsonResponse(data)
    else:
        return render_to_response('artist.html', data)


def artists(request):
    data = {}

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'activity_type' in request.session:
            athlete = strava_get_user_info_by_id(request.session['athlete_id'])
            activity_type = athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    data['activity_type'] = activity_type
    request.session['activity_type'] = activity_type

    n = 5
    if 'n' in request.GET:
        n = int(request.GET['n'])

    
    if data['activity_type'] != -1:
        qs = Effort.objects.filter(act_type = data['activity_type'])
    else:
        qs = Effort.objects

    qs = qs.filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song__artist_name','song__artist__image_url','song__artist__url','song__artist__id').annotate(sort_value=Count('song__artist')).order_by('sort_value')[::-1][:n]
    
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
        return render_to_response('top_table_artist.html', data)

def songs(request):
    data = {}

    activity_type = None
    if 'activity_type' in request.GET:
        activity_type = int(request.GET['activity_type'])
    if activity_type == None:
        if not 'activity_type' in request.session:
            athlete = strava_get_user_info_by_id(request.session['athlete_id'])
            activity_type = athlete.athlete_type
        else:
            activity_type = request.session['activity_type']

    data['activity_type'] = activity_type
    request.session['activity_type'] = activity_type

    n = 5
    if 'n' in request.GET:
        n = int(request.GET['n'])

    if data['activity_type'] != -1:
        qs = Effort.objects.filter(act_type = data['activity_type'])
    else:
        qs = Effort.objects

    qs = qs.filter(activity__athlete__athlete_id = request.session['athlete_id']).values('song','song__title','song__artist_name','song__url','song__image_url','song__artist__id','song__artist__image_url').annotate(sort_value=Count('song')).order_by('sort_value')[::-1][:n]
    
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
        return render_to_response('top_table_song.html', data)

