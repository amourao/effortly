import stravalib.client

from django.conf import settings

from datetime import datetime,timedelta
from powersong.lastfm_aux import lastfm_get_tracks
from powersong.tasks import strava_get_activity

import time
import math
from bisect import bisect_left

import numpy as np

from celery import group
from celery.result import AsyncResult,GroupResult
from celery import current_app

def strava_get_auth_url():
    client = stravalib.client.Client()
    return client.authorization_url(settings.STRAVA_CLIENT_ID, redirect_uri = settings.STRAVA_CALLBACK_URL,scope = 'view_private')

def strava_get_user_info(access_token):
    client = stravalib.client.Client()
    client.access_token = access_token
    athlete = client.get_athlete()
    info = {}
    info['id'] = athlete.id
    info['firstname'] = athlete.firstname
    info['lastname'] = athlete.lastname
    info['profile'] = athlete.profile
    info['activity_count'] = len(list(client.get_activities()))
    return info

def strava_get_start_timestamp(st):
    return int(time.mktime(st.timetuple()))

def metersPerSecondToKmH(mps):
    return mps*3.6

def kmHToMinPerKm(kph):
    return "{}:{:02.0f}".format(int((60.0/(kph))), int(((60.0/(kph))-(int(60.0/(kph))))*60)%60)    


def strava_do_final_group(acts):
    grouped = {}
    for act in acts:
        if 'parsed' in act:
            for key in act['parsed']:
                print(key)
                if not key in grouped:
                    grouped[key] = []
                grouped[key]+=(act['parsed'][key])

    ff = 'avgSpeed'
    ff = 'count'
    ff = 'duration'
    ff = 'diffAvgHr'
    ff = 'diffAvgSpeed'
    ff = 'avgSpeed'
    #ff = 'diffLastHr'
    for k in grouped:
        print(grouped[k])
    l = sortFastestSongEver(grouped,ff,aggregateDups=False,minCount=1)[:100]

    i=1

    parsed = []
    for song in l:
        song["main_key"] = song[ff]
        song["rank"] = i
        song['avgSpeedMinKm'] = kmHToMinPerKm(song['avgSpeed'])
        parsed.append(song)
        i+=1
    return parsed

def strava_get_sync_progress(task_id):
    res = current_app.GroupResult.restore(task_id)
    if res.ready() == True:
        return 'SUCCESS',res.completed_count(),strava_do_final_group(res.join())
    else:
        return 'STARTED',res.completed_count(),[]

def strava_get_activities(username,access_token):
    client = stravalib.client.Client()
    client.access_token = access_token
    promise = group([strava_get_activity.s(username,access_token,strava_parse_base_activity(act)) for act in client.get_activities()])
    job_result = promise.delay()
    print(job_result.backend)
    job_result.save()
    return job_result.id

def strava_parse_base_activity(act):
    actFinal = {}
    actFinal['achievement_count'] = act.achievement_count
    actFinal['athlete'] = act.athlete.id
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
   


doNothing=['name','songTitle','songArtist','id','duration','count']

def sortFastestSongEver(ranks,f,rev=True,aggregateDups=True,minCount=1):
    agg = []
    for k,v in ranks.items():
        if aggregateDups and len(v) >= minCount:
            for v1 in v:
                v1['count'] = len(v)
                agg.append(v1)                
        elif len(v) >= minCount:
            index=np.argmax([float(vv[f]) for vv in v])
            v[index]['count'] = len(v)
            agg.append(v[index])
    return sorted(agg, key=lambda x: float(x[f]), reverse=rev)

def sortFastestSongAvg(ranks,f,rev=True,minCount=1):
    agg = []
    for k,v in ranks.items():
        if len(v) >= minCount:
            v[0]['count'] = len(v)
            for k in v[0]:
                if not k in doNothing:
                    v[0][k]=np.average([float(vv[k]) for vv in v])
            agg.append(v[0])
    return sorted(agg, key=lambda x: float(x[f]), reverse=rev)

def sortFastestSongSum(ranks,f,rev=True,minCount=1):
    agg = []
    for k,v in ranks.items():
        if len(v) >= minCount:
            index=np.sum([vv[f] for vv in v])
            v[0][f] = index
            v[0]['count'] = len(v)
            for k in v[0]:
                if k != f and not k in doNothing:
                    v[0][k]=np.average([float(vv[k]) for vv in v])
            agg.append(v[0])
    return sorted(agg, key=lambda x: float(x[f]), reverse=rev)