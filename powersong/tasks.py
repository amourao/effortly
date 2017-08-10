import stravalib.client

from celery import shared_task
from datetime import datetime,timedelta

import time
import math
from bisect import bisect_left

import numpy as np

from django.conf import settings
import requests

@shared_task
def strava_download_activity(access_token,act):
    client = stravalib.client.Client()
    client.access_token = access_token
    try:
        stream_keys = ['time','distance','heartrate','watts','altitude']
        #actStream = client.get_activity_streams(act['id'],types=['time','latlng','distance','altitude','velocity_smooth','heartrate','watts','moving','grade_smooth'])
        actStream = client.get_activity_streams(act['id'],types=stream_keys)
        for k in stream_keys:
            if k in actStream:
                act[k] = actStream[k].data
    except Exception as e:
        print(e)
    return (act)

@shared_task
def lastfm_download_activity_tracks(act,username):
    start = strava_get_start_timestamp(strava_get_parse_timestamp(act['start_date'])-timedelta(seconds=600))
    end = strava_get_start_timestamp(strava_get_parse_timestamp(act['start_date'])+timedelta(seconds=int(act['elapsed_time'])))

    method = 'user.getrecenttracks'
    url = settings.LASTFM_API_RECENT.format(method,settings.LASTFM_API_KEY,username,start,end)
    response = requests.get(url).json()
    act["lastfm_tracks"] = response
    return act

@shared_task
def strava_activity_to_efforts(act):
    grouped = {}

    if 'lastfm_tracks' in act:
        songs = act['lastfm_tracks']['recenttracks']['track'][::-1]
    else:
        print("no songs in " + str(act['id']))
        songs = []

    actAvgSpeed = getActAvgSpeed(act)
    actAvgHr = getActAvgHR(act)

    start_time = strava_get_parse_timestamp(act['start_date'])
    elapsed_time = timedelta(seconds=int(act['elapsed_time']))

    actStartTimestamp = strava_get_start_timestamp(start_time)
    a2 = strava_get_start_timestamp(start_time + elapsed_time)
    lastSpeed = 0
    lastHr = 0
    
    internalIdx = 0
    for idx, song in enumerate(songs):
        #duration=song.track.get_duration()/1000
        start = int(song['date']['uts']) - actStartTimestamp
        
        if idx+1<len(songs):
            end = int(songs[idx+1]['date']['uts']) - actStartTimestamp
            if end > elapsed_time.seconds:
                end = elapsed_time.seconds
        else:
            end = elapsed_time.seconds
        
        if start < 0 and end > 0:
            start = 0
        if start < 0 and end < 0:
            continue
        if start > elapsed_time.seconds:
            continue


        k = (song['name']+";"+song['artist']['name'])


        if(end-start)>20 or True: #only use songs that play for more than 20 seconds
            if not k in grouped:
                grouped[k] = []
            songData = {}
            (songAvgSpeed,startDist,endDist) = getAvgSpeed(act,start,end)
            if songAvgSpeed > 0 and (endDist-startDist)>100:
                (songAvgHr,startDist,endDist) = getAvgHR(act,start,end)
                diffHr = 0
                diffSpeed = 0
                diffSpeedSec = 0
                if (endDist-startDist)>100 or True: #only use songs that play for more than 100 meters
                    if internalIdx > 0: # ignore diff to last in the first activity of the session
                        diffHr = songAvgHr-lastHr
                        diffSpeed = songAvgSpeed-lastSpeed
                        diffSpeedSec = kmHToMinPerKmDec(lastSpeed)-kmHToMinPerKmDec(songAvgSpeed)

                    lastHr=songAvgHr
                    lastSpeed=songAvgSpeed
                    
                    songData['start'] = start
                    songData['end'] = end
                    songData['duration'] = end-start
                    songData['avgSpeed'] = songAvgSpeed
                    
                    songData['diffAvgSpeedMin'] = kmHToMinPerKmDec(actAvgSpeed)-kmHToMinPerKmDec(songAvgSpeed)
                    songData['diffAvgSpeed'] = (songAvgSpeed-actAvgSpeed)

                    songData['songTitle'] = song['name']
                    songData['songArtist'] = song['artist']['name']
                    songData['name'] = act['name']
                    songData['id'] = act['id']
                    songData['startDist'] = startDist
                    songData['endDist'] = endDist
                    songData['avgHr'] = songAvgHr
                    songData['diffAvgHr'] = (songAvgHr-actAvgHr)
                    
                    songData['diffLastSpeedMin'] = diffSpeedSec
                    songData['diffLastSpeed'] = diffSpeed
                    songData['diffLastHr'] = diffHr
                    songData['songIdx'] = internalIdx

                    grouped[k].append(songData)
                    internalIdx+=1
    return grouped

@shared_task
def lastfm_download_track_info(track_id):
    return None

@shared_task
def lastfm_download_artist_info(track_id):
    return None


#2017-07-22T09:34:27Z
def strava_get_parse_timestamp(st):
    return datetime.strptime(st,'%Y-%m-%dT%H:%M:%SZ')


def strava_get_start_timestamp(st):
    return int(time.mktime(st.timetuple()))

def metersPerSecondToKmH(mps):
    return mps*3.6

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


def takeClosest(myList, myNumber):
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

def getActAvgSpeed(stream):
    start_pos = 0
    end_pos = len(stream['time'])-1
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    if(end_time-begin_time)==0:
        return 0
    return metersPerSecondToKmH(float(end_dist-begin_dist)/float(end_time-begin_time))

def getAvgSpeed(stream, start, end):
    start_pos = takeClosest(stream['time'],start)
    end_pos = takeClosest(stream['time'],end)
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    if(end_time-begin_time)==0:
        return (0,0,0)
    return metersPerSecondToKmH(float(end_dist-begin_dist)/float(end_time-begin_time)),begin_dist,end_dist

def getActAvgHR(stream):
    
    if not 'heartrate' in stream:
        return 0
    
    lastTime = 0
    sumHr = 0
    sumTime  = 0
    
    for idx, hr in enumerate(stream['heartrate']):
        timeD = stream['time'][idx] - lastTime
        sumTime+=timeD
        lastTime = stream['time'][idx]
        sumHr += hr*timeD
    
    if(lastTime == 0):
        return 0
    
    return sumHr/sumTime

def getAvgHR(stream, start, end):
    
    if not 'heartrate' in stream:
        return 0,0,0
    start_pos = takeClosest(stream['time'],start)
    end_pos = takeClosest(stream['time'],end)
    
    begin_time = stream['time'][start_pos]
    end_time = stream['time'][end_pos]
    
    begin_dist = stream['distance'][start_pos]
    end_dist = stream['distance'][end_pos]
    
    if(end_time-begin_time)==0:
        return 0
    
    startHr = 0
    
    startTime = 0
    
    if start_pos > 0:
        startTime = stream['time'][start_pos-1]
    
    lastTime = startTime
    sumHr = 0
    sumTime  = 0
    
    for idx, hr in enumerate(stream['heartrate'][start_pos:end_pos]):
        timeD = stream['time'][start_pos+idx] - lastTime
        sumTime+=timeD
        lastTime = stream['time'][start_pos+idx]
        sumHr += hr*timeD
    
    
    return sumHr/(sumTime),begin_dist,end_dist
