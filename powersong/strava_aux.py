import stravalib.client

from django.conf import settings

from datetime import datetime,timedelta
from powersong.tasks import strava_get_user_info
from powersong.tasks import strava_task,spotify_task,lastfm_task,activity_to_efforts,strava_generate_nops,count_finished

import copy
import time
import math
from bisect import bisect_left

import numpy as np

from celery import shared_task
from celery import chain, group
from celery.result import AsyncResult,GroupResult
from celery import current_app

from powersong.models import *

import logging

logger = logging.getLogger(__name__)


cache = {}

def strava_get_auth_url():
    client = stravalib.client.Client()
    return client.authorization_url(settings.STRAVA_CLIENT_ID, redirect_uri = settings.STRAVA_CALLBACK_URL,scope = ['activity:read_all','profile:read_all','activity:write'])

def strava_get_user_info_by_id(athlete_id):
    athletes = Athlete.objects.filter(athlete_id=athlete_id)

    if athletes:
        return athletes[0]

    return None

def strava_get_sync_progress(task_id,total_count):
    if task_id == "00000000-0000-0000-0000-000000000000":
        return 'SUCCESS', total_count, total_count
    if total_count == -1:
        return 'CHECKING FOR NEW ACTIVITIES', 0, -1
    try:
        res = current_app.AsyncResult(task_id)
        pending, success, failure, total = count_finished(res)
        if total == total_count:
            return 'SUCCESS', success, total
        else:
            return 'IN PROGRESS', success, total_count
    except:
        return 'FAILED', 0, 0




def resync_activity(activity_id,athlete_id):
    ath = strava_get_user_info(id=athlete_id)

    client = stravalib.client.Client()
    client.access_token = ath.strava_token
    client.refresh_token = ath.strava_refresh_token
    client.token_expires_at = ath.strava_token_expires_at

    if not athlete.strava_token_expires_at:
        return "00000000-0000-0000-0000-000000000000", 0
    
    activity = strava_get_activity_by_id(activity_id)

    if athlete_id != activity.athlete.athlete_id:
        return None, None

    efforts_to_delete = Effort.objects.filter(activity__activity_id = activity_id)
    efforts_to_delete.delete()
    act_p = {}
    act_p['id'] = activity_id
    act_p['athlete_id'] = athlete_id
    download_chain = chain(strava_task.si('strava_download_activity',(act_p,)),
                            lastfm_task.s('lastfm_download_activity_tracks',()),
                            activity_to_efforts.s()
                    )
    job_result = download_chain.delay()
    
    return job_result.id, 1

def resync_activity_spotify(activity_id,athlete_id):
    ath = strava_get_user_info(id=athlete_id)

    client = stravalib.client.Client()
    client.access_token = ath.strava_token
    client.refresh_token = ath.strava_refresh_token
    client.token_expires_at = ath.strava_token_expires_at

    if not athlete.strava_token_expires_at:
        return "00000000-0000-0000-0000-000000000000", 0

    activity = strava_get_activity_by_id(activity_id)

    if athlete_id != activity.athlete.athlete_id:
        return None, None

    efforts_to_delete = Effort.objects.filter(activity__activity_id = activity_id)
    efforts_to_delete.delete()
    act_p = {}
    act_p['id'] = activity_id
    act_p['athlete_id'] = athlete_id
    download_chain = chain(strava_task.si('strava_download_activity',(act_p,)),
                            spotify_task.s('spotify_download_activity_tracks',(True,)),
                            activity_to_efforts.s()
                    )
    job_result = download_chain.delay()

    return job_result.id, 1
