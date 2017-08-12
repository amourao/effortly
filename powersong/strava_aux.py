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


def metersPerSecondToKmH(mps):
    return mps*3.6

def kmHToMinPerKm(kph):
    if kph == 0:
        return "0:00"
    elif kph > 0:
        return "{}:{:02.0f}".format(int((60.0/(kph))), int(((60.0/(kph))-(int(60.0/(kph))))*60)%60)    
    else:
        kph=-kph
        return "-{}:{:02.0f}".format(int((60.0/(kph))), int(((60.0/(kph))-(int(60.0/(kph))))*60)%60)    

def minPerKmDecToMinPerKm(mpk):
    if mpk == 0:
        return "0:00"
    elif mpk > 0:
        return "{}:{:02.0f}".format(int(mpk), int((mpk-(int(mpk)))*60)%60)    
    else:
        mpk=-mpk
        return "-{}:{:02.0f}".format(int(mpk), int((mpk-(int(mpk)))*60)%60)    


def strava_do_final_group(acts):
    act_grouped = {}
    for act in acts:
        for key in act:
                if not key in act_grouped:
                    act_grouped[key] = []
                act_grouped[key]+=(act['parsed'][key])
    return act_grouped


def sortFastestSongEver(ranks,sort_key,rev=True,aggregateDups=True,minCount=1):
    agg = []
    for song, plays in ranks.items():
        if aggregateDups and len(plays) >= minCount:
            for play in plays:
                v1['count'] = len(plays)
                agg.append(v1)                
        elif len(plays) >= minCount:
            index=np.argmax([float(play[sort_key]) for play in plays])
            plays[index]['count'] = len(plays)
            agg.append(plays[index])
    return sorted(agg, key=lambda x: float(x[sort_key]), reverse=rev)

def sortFastestSongAvg(ranks,sort_key,rev=True,minCount=1):
    doNothing=['name','songTitle','songArtist','id','duration','count']
    agg = []
    for song, plays in ranks.items():
        if len(plays) >= minCount:
            play_result = copy.deepcopy(plays[0])
            play_result['count'] = len(plays)
            for key in plays[0]:
                if not key in doNothing:
                    play_result[key] = np.average([float(play[key]) for play in plays])
                play_result[key+"Agg"] = [(play[key]) for play in plays if key in play ]
            agg.append(play_result)
    return sorted(agg, key=lambda x: float(x[sort_key]), reverse=rev)

def sortFastestSongSum(ranks,sort_key,rev=True,minCount=1):
    doNothing=['name','songTitle','songArtist','id','duration','count']
    special = 'diffLast'
    agg = []
    for song, plays in ranks.items():
        if len(plays) >= minCount:
            play_result = copy.deepcopy(plays[0])
            play_result[sort_key] = index
            play_result['count'] = len(plays)
            for key in plays[0]:
                if key != sort_key and not key in doNothing:
                    play_result[key] = np.average([float(play[key]) for play in plays])
                play_result[key+"Agg"] = [(play[key]) for play in plays if key in play ]
            agg.append(play_result)
    return sorted(agg, key=lambda x: float(x[sort_key]), reverse=rev)

def strava_prettify_list_for_template(l,sort_key):
    dokmHToMinPerKm=['avgSpeed','diffAvgSpeed','diffLastSpeed']
    doMinPerKmDecToMinPerKm=['diffAvgSpeedMin','diffLastSpeedMin']
    qualifiers = {  'avgSpeed': 'km/h',
                    'diffAvgSpeed': 'km/h',
                    'diffLastSpeed': 'km/h',
                    'avgHr': 'bpm',
                    'diffAvgHr': 'bpm',
                    'diffLastHr': 'bpm',

                    'sort_valueP': '/km',
    }
    decPlaces = {   'avgSpeed': 2,
                    'diffAvgSpeed': 2,
                    'diffLastSpeed': 2,
                    'diffAvgSpeedMin': 2,
                    'diffLastSpeedMin': 2,
                    'avgHr': 1,
                    'count': 0,
                    'diffAvgHr': 2,
                    'diffLastHr': 2
    }
    i = 1
    parsed = []
    for old_song in l:
        song = copy.deepcopy(old_song)
        song["sort_key"] = sort_key
        song["sort_value"] = str(song[sort_key])
        if sort_key in decPlaces:            
            song["sort_value"] = str(round(song[sort_key], decPlaces[sort_key]))
        if sort_key in qualifiers:
            song["sort_value"] += " " + qualifiers[sort_key]

        if sort_key in dokmHToMinPerKm:
            song["sort_valueP"] = kmHToMinPerKm(song[sort_key]) + " " +qualifiers["sort_valueP"]
        if sort_key in doMinPerKmDecToMinPerKm:
            song["sort_valueP"] = minPerKmDecToMinPerKm(song[sort_key]) + " " +qualifiers["sort_valueP"]

        song["rank"] = i
        for k in dokmHToMinPerKm:
            song[k+'P'] = kmHToMinPerKm(song[k])+" "+qualifiers["sort_valueP"]
        for k in doMinPerKmDecToMinPerKm:
            song[k+'P'] = minPerKmDecToMinPerKm(song[k])+" "+qualifiers["sort_valueP"]
            
        parsed.append(song)
        i+=1
    return parsed

def strava_get_fastest_ever_single(act_grouped,sort_key,n=10,minCount=3,aggregateDups=False):
    l = sortFastestSongEver(act_grouped,sort_key,aggregateDups=aggregateDups,minCount=minCount)[:n]
    return strava_prettify_list_for_template(l,sort_key)

def strava_get_fastest_ever_groupA(act_grouped,sort_key,n=10,minCount=3):
    l = sortFastestSongAvg(act_grouped,sort_key,minCount=minCount)[:n]
    return strava_prettify_list_for_template(l,sort_key)

def strava_get_sync_progress(task_id):
    res = current_app.GroupResult.restore(task_id)
    if res is None:
        return 'FAILED', 0, 0
    elif res.ready() == True:
        return 'SUCCESS', res.completed_count(), len(res)
    else:
        return 'IN PROGRESS', res.completed_count(), len(res)


def strava_get_sync_result(task_id):
    res = current_app.GroupResult.restore(task_id)
    if res is None:
        return None
    if res.ready() == True:
        return strava_do_final_group(res.get())
    else:
        return None

def sync_efforts(username,access_token,limit=None):
    client = stravalib.client.Client()
    client.access_token = access_token

    all_activities = client.get_activities(limit=limit)
    new_activities = []
    for act in all_activities:
        if not strava_get_activity_by_id(act.id):
            act_p = strava_parse_base_activity(act)
            download_chain = chain(strava_download_activity.s(access_token,act_p),
                                    lastfm_download_activity_tracks.s(username),
                                    strava_activity_to_efforts.s()
                            )
            new_activities.append(download_chain)

    if len(new_activities) == 0:
        return None, 0

    promise = group(*new_activities)
    job_result = promise.delay()
    
    job_result.save()
    
    return job_result.id, len(new_activities)

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
   
