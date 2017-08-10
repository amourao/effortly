from django.conf import settings
from hashlib import md5

from powersong.models import Listener

import requests

import logging

logger = logging.getLogger(__name__)

def lastfm_get_auth_url():
    return settings.LASTFM_BASE + settings.LASTFM_API_KEY

def lastfm_get_session_id(token):
    method = 'auth.getSession'
    #api_key: Your 32-character API Key.
    #token: The authentication token received at your callback url as a GET variable.
    #api_sig: Your 32-character API method signature, as explained in Section 8. 
    api_sig = lastfm_get_sig(settings.LASTFM_API_KEY,method,token,settings.LASTFM_API_SECRET)
    
    #LASTFM_API_AUTHBASE = 'http://ws.audioscrobbler.com/2.0/?method={}&api_key={}&token={}&api_sig={}&format=json'
    #return settings.LASTFM_API_AUTHBASE.format(method,settings.LASTFM_API_KEY,token,api_sig)
    url = settings.LASTFM_API_AUTHBASE.format(method,settings.LASTFM_API_KEY,token,api_sig)
    response = requests.get(url).json()
    if not 'session' in response:
        return None,None
    return (response['session']['name'], response['session']['key'])

def create_listener_from_dict(listener_api):
    listener =  Listener()

    listener.nickname = listener_api['name']
    listener.real_name = listener_api['realname']
    listener.profile_image_url = listener_api['image'][-1]['#text']
    listener.country = listener_api['country']
    listener.age = int(listener_api['age'])

    return listener


def lastfm_get_user_info(username,key):

    listeners = Listener.objects.filter(nickname=username)
    logger.debug("Getting listener with username {}".format(username))

    if listeners:
        listener = listeners[0]
        logger.debug("Listener {} found in DB".format(username))
        return listeners[0]


    logger.debug("Listener {} not in DB, creating new.".format(username))
    
    method = 'user.getinfo'
    url = settings.LASTFM_API_BASE.format(method,settings.LASTFM_API_KEY,username)
    response = requests.get(url).json()

    if not 'user' in response:
        #invalid key, must get new
        return None

    response = response['user']

    listener = create_listener_from_dict(response)
    
    listener.save()

    return listener




def lastfm_get_sig(api_key,method,token,secret):
    return md5('api_key{}method{}token{}{}'.format(api_key,method,token,secret).encode()).hexdigest()

def lastfm_get_tracks(username,start,end):
    method = 'user.getrecenttracks'
    url = settings.LASTFM_API_RECENT.format(method,settings.LASTFM_API_KEY,username,start,end)
    response = requests.get(url).json()
    return response
