from django.shortcuts import redirect
from django.template import RequestContext

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

import stravalib.client

import sys, json

import spotipy

import requests

from django.http import JsonResponse, HttpResponse


from powersong.view_main import get_all_data, NonAuthenticatedException
from powersong.view_home import index
from powersong.models import get_poweruser, Activity
from powersong.spotify_aux import spotify_refresh_token
from powersong.strava_aux import sync_one_activity
from powersong.lastfm_aux import lastfm_get_session_id, lastfm_get_user_info

import logging

logger = logging.getLogger(__name__)


@csrf_exempt
def strava_webhooks_callback(request):
    if request.method == 'GET':
        raw = request.GET
        try:
            client = stravalib.client.Client()
            response = client.handle_subscription_callback(raw, verify_token=settings.STRAVA_VERIFY_TOKEN)
            logger.debug("STRAVA WEBHOOK ACCEPT OK")
            return HttpResponse(json.dumps({'hub.challenge': raw['hub.challenge']}))
        except Exception as e:
            logger.error("STRAVA WEBHOOK ACCEPT ERROR")
            logger.error(str(e))
            pass
        return HttpResponse("INVALID_REQUEST")    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            if data["subscription_id"] != settings.STRAVA_SUBSCRIPTION_ID:
                raise Exception("Invalid subscription_id")
            if data["aspect_type"] == "create" and data["object_type"] == "activity":               
                sync_one_activity(data["object_id"], data["owner_id"])
            elif data["aspect_type"] == "delete" and data["object_type"] == "activity":
                Activity.objects.filter(activity_id=data["object_id"],athlete__athlete_id=data["owner_id"]).delete()
        except Exception as e:
            logger.debug(e)
            logger.debug("STRAVA WEBHOOK PARSE ERROR")
            pass
        client = stravalib.client.Client()
        return HttpResponse("EVENT_RECEIVED")

        
def strava_webhook_create_sub():
    client = stravalib.client.Client()
    callback_url = settings.HOME_URL + '/strava_webhooks/'
    client.create_subscription(settings.STRAVA_CLIENT_ID, settings.STRAVA_CLIENT_SECRET, callback_url, object_type='activity', aspect_type='create', verify_token=settings.STRAVA_VERIFY_TOKEN)

def strava_webhook_list_sub():
    client = stravalib.client.Client()
    return client.list_subscriptions(settings.STRAVA_CLIENT_ID, settings.STRAVA_CLIENT_SECRET)
    
