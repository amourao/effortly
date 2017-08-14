import stravalib.client

from celery import shared_task
from datetime import datetime,timedelta

import time
import math
from bisect import bisect_left

import numpy as np

from django.conf import settings
import requests

from powersong.models import *
from urllib.error import HTTPError

import logging

logger = logging.getLogger(__name__)

@shared_task
def strava_download_activity(access_token,act):
    client = stravalib.client.Client()
    client.access_token = access_token
    
    logger.debug(act)
    stored_act = create_activity_from_dict(act)

    if stored_act == None:
        act_ign = ActivitiesToIgnore()
        act_ign.activity_id = act['id']
        act_ign.save()
        return None
    try:
        stream_keys = ['time','distance','heartrate','watts','altitude']
        #actStream = client.get_activity_streams(act['id'],types=['time','latlng','distance','altitude','velocity_smooth','heartrate','watts','moving','grade_smooth'])
        act_stream_api = client.get_activity_streams(act['id'],types=stream_keys)
        logger.error(act_stream_api)
        act_stream = {}
        for k in stream_keys:
            if k in act_stream_api:
                act_stream[k] = act_stream_api[k].data
    except Exception as e:
        logger.error("Exception on activity {}".format(act['id']))
        logger.error(e)

        act_ign = ActivitiesToIgnore()
        act_ign.activity_id = act['id']
        act_ign.save()
        return None
    return (act_stream, stored_act.activity_id)

@shared_task
def lastfm_download_activity_tracks(act_stream_stored_act,username):
    if act_stream_stored_act == None:
        return None

    (act_stream,stored_act_id) = act_stream_stored_act

    stored_act = strava_get_activity_by_id(stored_act_id)


    start = strava_get_start_timestamp(stored_act.start_date-timedelta(seconds=600))
    end = strava_get_start_timestamp(stored_act.start_date+timedelta(seconds=int(stored_act.elapsed_time)))

    method = 'user.getrecenttracks'
    url = settings.LASTFM_API_RECENT.format(method,settings.LASTFM_API_KEY,username,start,end)
    response = requests.get(url).json()
    lastfm_tracks = response
    return act_stream, stored_act_id, lastfm_tracks

@shared_task
def strava_activity_to_efforts(act_stream_stored_act_id_lastfm_tracks):
    if act_stream_stored_act_id_lastfm_tracks == None:
        return False
    act_stream, stored_act_id, lastfm_tracks = act_stream_stored_act_id_lastfm_tracks
    stored_act = strava_get_activity_by_id(stored_act_id)
    
    if lastfm_tracks:
        songs = lastfm_tracks['recenttracks']['track'][::-1]
    else:
        logger.debug("No songs in activity {}".format(stored_act_id))
        return {}

    act_avg_speed = stored_act.avg_speed
    act_avg_hr = stored_act.avg_hr

    start_time = stored_act.start_date
    elapsed_time = timedelta(seconds=int(stored_act.elapsed_time))

    act_start_timestamp = strava_get_start_timestamp(start_time)

    last_speed = 0
    last_hr = 0
    
    effort_idx_in_act = 0
    idx = 0
    while idx < len(songs):
        song_api = songs[idx]
        
        start = int(song_api['date']['uts']) - act_start_timestamp

        # multiple similar scrobbles protection
        while (idx+1) < len(songs) and song_api['url'] == songs[idx+1]['url']: # if the next song is the same, do not create new song
            song_api = songs[idx+1]
            idx+=1
                     
        if (idx+1) < len(songs):
            end = int(songs[idx+1]['date']['uts']) - act_start_timestamp
            if end > elapsed_time.seconds:
                end = elapsed_time.seconds
        else:
            end = elapsed_time.seconds
        
        idx+=1
        
        if start <= 0 and end >= 0:
            start = 0
        if start < 0 or end <= 0:
            continue
        if start > elapsed_time.seconds:
            continue

        if (end-start) > 0:
            song = create_song_from_dict(song_api)
        
            #stream_keys = ['time','distance','heartrate','watts','altitude']
            (effort_avg_speed, effort_start_dist, effort_end_dist) = get_avg_speed_in_interval(act_stream,start,end)
            (effort_avg_hr, effort_start_dist, effort_end_dist) = get_avg_in_interval(act_stream,start,end,'heartrate')
            (effort_avg_cad, effort_start_dist, effort_end_dist) = get_avg_in_interval(act_stream,start,end,'cadence')
            (effort_avg_watts, effort_start_dist, effort_end_dist) = get_avg_in_interval(act_stream,start,end,'watts')
            (effort_total_ascent,effort_total_descent, effort_start_dist, effort_end_dist) = get_ascent_in_interval(act_stream,start,end,'altitude')

            if effort_avg_speed > 0 and (effort_end_dist - effort_start_dist) > 100 or True:
                effort_diff_hr = 0
                effort_diff_speed = 0
                effort_diff_cad = 0
                effort_diff_watts = 0
                if (effort_end_dist-effort_start_dist) > 100 or True: #only use songs that play for more than 100 meters
                    
                    if effort_idx_in_act > 0: # ignore diff to last in the first activity of the session
                        effort_diff_hr = effort_avg_hr-last_hr
                        effort_diff_speed = effort_avg_speed-last_speed
                        effort_diff_cad = effort_avg_cad-last_cad
                        effort_diff_watts = effort_avg_watts-last_watts

                    effort = Effort()
                    
                    effort.act_type = stored_act.act_type
                    
                    effort.start_time = start
                    effort.duration = end - start

                    effort.start_distance = effort_start_dist
                    effort.distance = effort_end_dist-effort_start_dist
                                      
                    effort.avg_speed = effort_avg_speed

                    effort.diff_avg_speed = effort_avg_speed-act_avg_speed
                    effort.diff_last_speed = effort_avg_speed-last_speed

                    effort_avg_speed_s = 0
                    if effort_avg_speed != 0:
                        effort_avg_speed_s = 1.0/effort_avg_speed

                    act_avg_speed_s = 0
                    if act_avg_speed != 0:
                        act_avg_speed_s = 1.0/act_avg_speed

                    last_speed_s = 0
                    if last_speed != 0:
                        last_speed_s = 1.0/last_speed

                    effort.diff_avg_speed_s = act_avg_speed_s-effort_avg_speed_s
                    effort.diff_last_speed_s = last_speed_s-effort_avg_speed_s
                    
                    if (stored_act.avg_hr):
                        effort.avg_hr = effort_avg_hr
                        effort.diff_avg_hr = (effort_avg_hr - stored_act.avg_hr)
                        effort.diff_last_hr = effort_diff_hr

                    if (stored_act.avg_cadence):
                        effort.avg_cadence = effort_avg_cad
                        effort.diff_avg_cadence = (effort_avg_cad - stored_act.avg_cadence)
                        effort.diff_last_cadence = effort_diff_cad
                    
                    effort.idx_in_activity = effort_idx_in_act

                    effort.total_ascent = effort_total_ascent
                    effort.total_descent = effort_total_descent

                    effort.song = song
                    effort.activity = stored_act

                    if stored_act.act_type == 1:
                        if (stored_act.avg_watts) != None:
                            effort.avg_watts = effort_avg_watts
                            effort.diff_avg_watts = (effort_avg_watts - stored_act.avg_watts)
                            effort.diff_last_watts = effort_diff_watts

                    effort.save()
                    effort_idx_in_act+=1

                    last_hr = effort_avg_hr
                    last_speed = effort_avg_speed
                    last_cad = effort_avg_cad
                    last_watts = effort_avg_watts
    return True

@shared_task
def lastfm_download_track_info(track_id):
    return None

@shared_task
def lastfm_download_artist_info(track_id):
    return None

def strava_get_start_timestamp(st):
    return int(time.mktime(st.timetuple()))

def kmHToMinPerKm(kph):
    if kph == 0:
        return "0:00"
    return "{}:{:02.0f}".format(int((60.0/(kph))), int(((60.0/(kph))-(int(60.0/(kph))))*60)%60)    

def kmHToMinPerKmDec(kph):
    if kph == 0:
        return 0
    return 60.0/(kph)

def minPerKmDecToMinPerKm(mpk):
    if mpk == 0:
        return "0:00"
    return "{}:{:02.0f}".format(int(mpk), int((mpk-(int(mpk)))*60)%60)    


def take_closest_point(myList, myNumber):
    pos = bisect_left(myList, myNumber)
    if pos == 0:
        return 0
    if pos == len(myList):
        return len(myList)-1
    before = myList[pos - 1]
    after = myList[pos]
    if after - myNumber < myNumber - before:
        return pos
    else:
        return pos - 1

def get_avg_speed_in_interval(stream, start, end):
    start_pos = take_closest_point(stream['time'],start)
    end_pos = take_closest_point(stream['time'],end)
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    if(end_time-begin_time)==0:
        return (0,0,0)
    return (float(end_dist-begin_dist)/float(end_time-begin_time)),begin_dist,end_dist

def get_avg_in_interval(stream, start, end, key):
    
    if not key in stream:
        return 0,0,0

    start_pos = take_closest_point(stream['time'],start)
    end_pos = take_closest_point(stream['time'],end)
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    if(end_time-begin_time)==0:
        return 0,0,0
    
    last_time = 0
    
    if start_pos > 0:
        last_time = stream['time'][start_pos-1]
    
    sum_key_value = 0
    sum_time  = 0
    
    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos+idx] - last_time
        sum_time += time_diff
        last_time = stream['time'][start_pos+idx]
        sum_key_value += key_value*time_diff
    
    
    return sum_key_value/(sum_time),begin_dist,end_dist

def get_sum_in_interval(stream, start, end, key):
    
    if not key in stream:
        return 0,0,0

    start_pos = take_closest_point(stream['time'],start)
    end_pos = take_closest_point(stream['time'],end)
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    if(end_time-begin_time)==0:
        return 0,0,0
    
    last_time = 0
    
    if start_pos > 0:
        last_time = stream['time'][start_pos-1]
    
    sum_key_value = 0
    sum_time  = 0
    
    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos+idx] - last_time
        sum_time += time_diff
        last_time = stream['time'][start_pos+idx]
        sum_key_value += key_value
    
    
    return sum_key_value,begin_dist,end_dist

def get_ascent_in_interval(stream, start, end, key):
    
    if not key in stream:
        return 0,0,0,0

    start_pos = take_closest_point(stream['time'],start)
    end_pos = take_closest_point(stream['time'],end)
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    if(end_time-begin_time)==0:
        return 0,0,0,0
    
    last_key_val = 0
    last_time = 0
    
    if start_pos > 0:
        last_time = stream['time'][start_pos-1]
    
    sum_pos_key_value = 0
    sum_neg_key_value = 0
    sum_time  = 0
    
    last_key_val = stream[key][start_pos]
    for idx, key_value in enumerate(stream[key][start_pos:end_pos]):
        time_diff = stream['time'][start_pos+idx] - last_time
        sum_time += time_diff
        last_time = stream['time'][start_pos+idx]
        key_val_diff = key_value-last_key_val
        if key_val_diff > 0:
            sum_pos_key_value += key_val_diff
        else:
            sum_neg_key_value += key_val_diff
        last_key_val = key_value
    
    
    return sum_pos_key_value,sum_neg_key_value,begin_dist,end_dist
