import stravalib.client

from django.conf import settings

from datetime import datetime,timedelta
from powersong.lastfm_aux import lastfm_get_tracks

import time


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
    return info

def strava_get_start_timestamp(st):
    return int(time.mktime(st.timetuple()))


def strava_get_activities(username,access_token):
    client = stravalib.client.Client()
    client.access_token = access_token

    actStreams = []
    actScrobs = []
    acts = []
    for act in client.get_activities(limit=15):
        actId = act.id
        try:
            actStream = client.get_activity_streams(actId,types=['time','latlng','distance','altitude','velocity_smooth','heartrate','watts','moving','grade_smooth'])
            actStreams.append(actStream)
            
            acts.append(act)
                    
            a1 = strava_get_start_timestamp(act.start_date-timedelta(seconds=240))
            a2 = strava_get_start_timestamp(act.start_date+act.elapsed_time)
            scrob = lastfm_get_tracks(username,a1,a2)
        
            actScrobs.append(scrob)
        except:
            pass
    return acts,actStreams,actScrobs
        

