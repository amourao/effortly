import stravalib.client

from django.conf import settings

from datetime import datetime,timedelta
from powersong.tasks import strava_download_activity,lastfm_download_activity_tracks,strava_activity_to_efforts



import copy
import time
import math
from bisect import bisect_left

import numpy as np

from celery import chain, group
from celery.result import AsyncResult,GroupResult
from celery import current_app

from powersong.models import *

import logging

logger = logging.getLogger(__name__)


cache = {}

def strava_get_auth_url():
    client = stravalib.client.Client()
    logger.debug("generating strava auth url")
    return client.authorization_url(settings.STRAVA_CLIENT_ID, redirect_uri = settings.STRAVA_CALLBACK_URL,scope = 'view_private')

def strava_get_user_info(access_token):
    athletes = Athlete.objects.filter(strava_token=access_token)
    logger.debug("Getting athlete with token {}".format(access_token))

    if athletes:
        athlete = athletes[0]
        logger.debug("Athlete {} found with current token".format(athlete.athlete_id))
        return athlete

    client = stravalib.client.Client()
    client.access_token = access_token
    athlete_api = client.get_athlete()
    
    athletes = Athlete.objects.filter(athlete_id=athlete_api.id)

    if athletes:
        logger.debug("Athlete {} found with invalid token. Updating token.".format(athlete.athlete_id))
        athlete = athletes[0]
        athlete.strava_token = access_token
        athlete.save()
        return athlete

    logger.debug("Athlete {} not in database, creating new.".format(athlete_api.id))
    athlete = create_athlete_from_dict(athlete_api)
    athlete.strava_token = access_token
    
    athlete.save()

    return athlete

def strava_get_user_info_by_id(athlete_id):
    athletes = Athlete.objects.filter(athlete_id=athlete_id)

    if athletes:
        return athletes[0]

    return None

def strava_get_sync_progress(task_id):
    if task_id == "":
        return 'SUCCESS', 0, 0
    try:
        res = current_app.GroupResult.restore(task_id)
        if res.ready() == True:
            return 'SUCCESS', res.completed_count(), len(res)
        elif res.waiting():
            return 'IN PROGRESS', res.completed_count(), len(res)
        else:
            return 'FAILED', res.completed_count(), len(res)
    except Exception as e:
        logger.debug(e)
        results = current_app.AsyncResult(task_id) 
        if results is None:
            return 'FAILED', 0, 0
        elif results.state == 'FAILURE':
            return 'FAILED', 0, 1
        elif results.ready():
            return 'SUCCESS', 1, 1
        else:
            return 'IN PROGRESS', 0, 1

def sync_efforts(username,access_token,limit=None):
    client = stravalib.client.Client()
    client.access_token = access_token

    athlete = strava_get_user_info(access_token)

    athlete_api = client.get_athlete()
    stats = athlete_api.stats

    athlete.activity_count = stats.all_ride_totals.count
    athlete.runs_count = stats.all_run_totals.count
    athlete.rides_count = stats.all_ride_totals.count
    athlete.activity_count = stats.all_ride_totals.count + stats.all_run_totals.count
    athlete.updated_strava_at = athlete_api.updated_at
    athlete.save()

    all_activities = client.get_activities(limit=limit)
    new_activities = []
    for act in all_activities:
        if not strava_is_activity_to_ignore(act.id) and not strava_get_activity_by_id(act.id):
            act_p = strava_parse_base_activity(act)
            download_chain = chain(strava_download_activity.s(access_token,act_p),
                                    lastfm_download_activity_tracks.s(username),
                                    strava_activity_to_efforts.s()
                            )
            new_activities.append(download_chain)
    if len(new_activities) == 0:
        return "", 0

    if len(new_activities) > 1:
        promise = group(*new_activities)
        job_result = promise.delay()
        job_result.save()
    else:
        promise = new_activities[0]
        job_result = promise.delay()
    
    return job_result.id, len(new_activities)

def resync_activity(username,access_token,activity_id,):
    client = stravalib.client.Client()
    client.access_token = access_token

    activity = strava_get_activity_by_id(activity_id)

    if athlete_id != activity.athlete.athlete_id:
        return None, None

    efforts_to_delete = Effort.objects.filter(activity__activity_id = activity_id)
    efforts_to_delete.delete()
    act_p = {}
    act_p['id'] = activity_id
    download_chain = chain(strava_download_activity.s(access_token,act_p),
                            lastfm_download_activity_tracks.s(username),
                            strava_activity_to_efforts.s()
                    )
    job_result = download_chain.delay()
    
    return job_result.id, 1

def strava_parse_base_activity(act):
    actFinal = {}

    actFinal['achievement_count'] = act.achievement_count
    actFinal['athlete_id'] = act.athlete.id
    actFinal['average_cadence'] = act.average_cadence
    actFinal['average_heartrate'] = act.average_heartrate
    actFinal['average_speed'] = float(act.average_speed)
    actFinal['average_temp'] = act.average_temp
    actFinal['average_watts'] = act.average_watts
    
    actFinal['calories'] = act.calories
    actFinal['description'] = act.description
    actFinal['total_distance'] = float(act.distance)
    actFinal['elapsed_time'] = float(act.elapsed_time.total_seconds())
    actFinal['moving_time'] = float(act.moving_time.total_seconds())
    actFinal['elev_high'] = act.elev_high
    actFinal['elev_low'] = act.elev_low
    actFinal['embed_token'] = act.embed_token
    actFinal['end_latlng'] = act.end_latlng
    
    actFinal['gear'] = act.gear
    actFinal['gear_id'] = act.gear_id
    
    actFinal['has_heartrate'] = act.has_heartrate
    actFinal['has_kudoed'] = act.has_kudoed
    
    actFinal['id'] = act.id
    #actFinal['kudos'] = [k for k in a.kudos] 
    actFinal['kudos_count'] = act.kudos_count
    
    #actFinal['laps'] = [k for k in a.laps]
    
    actFinal['location_city'] = act.location_city
    actFinal['location_country'] = act.location_country
    actFinal['location_state'] = act.location_state
    
    actFinal['manual'] = act.manual
    actFinal['max_heartrate'] = act.max_heartrate
    actFinal['max_speed'] = float(act.max_speed)
    actFinal['max_watts'] = act.max_watts
    
    actFinal['name'] = act.name
    actFinal['photo_count'] = act.photo_count
    actFinal['segment_efforts'] = act.segment_efforts
    actFinal['start_date'] = act.start_date
    actFinal['start_date_local'] = act.start_date_local
    
    actFinal['start_latitude'] = act.start_latitude
    actFinal['start_longitude'] = act.start_longitude
    
    actFinal['start_latlng'] = act.start_latlng
    
    actFinal['suffer_score'] = act.suffer_score
    #actFinal['timezone'] = act.timezone
    actFinal['total_elevation_gain'] = float(act.total_elevation_gain)
    actFinal['trainer'] = act.trainer
    actFinal['type'] = act.type
    
    actFinal['upload_id'] = act.upload_id
    
    actFinal['weighted_average_watts'] = act.weighted_average_watts
    actFinal['workout_type'] = act.workout_type
    
    return actFinal
   
