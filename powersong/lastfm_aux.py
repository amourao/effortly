from django.conf import settings
from hashlib import md5

import requests

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


#"https://ws.audioscrobbler.com/2.0/?method=user.getinfo&user=ANd_PT&api_key=00fe106503668ad4436d05755b9e79b8&format=json

def lastfm_get_user_info(username):
	method = 'user.getinfo'
	url = settings.LASTFM_API_BASE.format(method,settings.LASTFM_API_KEY,username)
	response = requests.get(url).json()
	response = response['user']
	response['image_url'] = response['image'][-1]['#text']
	return response

def lastfm_get_sig(api_key,method,token,secret):
	return md5('api_key{}method{}token{}{}'.format(api_key,method,token,secret).encode()).hexdigest()

def lastfm_get_tracks(username,start,end):
	method = 'user.getrecenttracks'
	url = settings.LASTFM_API_RECENT.format(method,settings.LASTFM_API_KEY,username,start,end)
	response = requests.get(url).json()
	return response
