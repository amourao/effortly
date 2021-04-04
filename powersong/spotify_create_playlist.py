from django.conf import settings

import requests

from powersong.models import *
from powersong.spotify_aux import spotify_refresh_token


import logging

logger = logging.getLogger(__name__)


def spotify_get_effortly_user_token():    
    listener_spotify = ListenerSpotify.objects.get(id=settings.SPOTIFY_EFFORTLY_LISTENER_ID)
    token = spotify_refresh_token(listener_spotify.spotify_code,listener_spotify.spotify_token,listener_spotify.spotify_refresh_token, "")
    return token

def spotify_find_playlist(name,description,token):
    listener_spotify = ListenerSpotify.objects.get(id=settings.SPOTIFY_EFFORTLY_LISTENER_ID)
    r_find = requests.get("https://api.spotify.com/v1/users/{}/playlists".format(listener_spotify.nickname), headers={'Authorization': 'Bearer  ' + token})
    out = r_find.json()
    for playlist in out["items"]:
        if playlist["description"] == description:
            playlist_id = playlist["id"]
            r_tracks = requests.get("https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id), headers={'Authorization': 'Bearer  ' + token})
            out = r_tracks.json()
            track_ids = {"uris": ["spotify:track:{}".format(i["track"]["id"]) for i in out["items"]]}
            r_delete = requests.delete("https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id), headers={'Authorization': 'Bearer  ' + token}, json=track_ids)
            return playlist_id    

    data = {
        "name": name,
        "description": description,
        "public": True
    }
    r_create = requests.post("https://api.spotify.com/v1/users/{}/playlists".format(listener_spotify.nickname), headers={'Authorization': 'Bearer  ' + token}, json=data)
    out = r_create.json()    
    playlist_id = out["id"]
    return playlist_id


def spotify_create_playlist(name,description,tracks):
    listener_spotify = ListenerSpotify.objects.get(id=settings.SPOTIFY_EFFORTLY_LISTENER_ID)
    token = spotify_get_effortly_user_token()
    playlist_id = spotify_find_playlist(name,description,token)
    if tracks:        
        data = {"uris": ["spotify:track:{}".format(t) for t in tracks]}
        r_add = requests.post("https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id), headers={'Authorization': 'Bearer  ' + token}, json=data)
    return playlist_id

