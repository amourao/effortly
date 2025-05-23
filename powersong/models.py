from django.db import models
from datetime import datetime, date
from django.db.models import Q

from powersong.unit_conversion import *
from picklefield.fields import PickledObjectField

import numpy as np
import logging

import requests

speed = ['activity__avg_speed', 'activity__max_speed', 'avg_speed', 'diff_avg_speed', 'diff_last_speed',
         'avg_avg_speed', 'avg_diff_avg_speed', 'avg_diff_last_speed']

# units that are computed as diffs in m/s
speed_small_diff_computed = ['activity__avg_speed', 'activity__max_speed', 'avg_speed', 'avg_avg_speed']
speed_small = ['activity__avg_speed_s', 'activity__max_speed_s', 'avg_speed_s', 'diff_avg_speed_s', 'diff_last_speed_s',
           'avg_avg_speed_s', 'avg_diff_avg_speed_s', 'avg_diff_last_speed_s']


distanceSmall = ['total_ascent', 'total_descent', 'distance', 'avg_distance']
distanceBig = ['activity__distance', 'start_distance', 'avg_start_distance']
temperature = ['activity__avg_temp']
timeBig = ['start_time', 'elapsed_time', 'duration', 'avg_duration']
timeSmall = []
count = ['count', 'effort']
count_users = ['count_users']

heartrate = ['avg_avg_hr', 'avg_diff_avg_hr', 'avg_diff_last_hr', 'avg_hr', 'diff_avg_hr', 'diff_last_hr',
             'activity__avg_hr', 'activity__max_hr']

cadence = ['avg_cadence', 'diff_avg_cadence', 'diff_last_cadence', 'activity__avg_cadence']

watts = ['avg_watts', 'diff_avg_watts', 'diff_last_watts', 'activity__avg_watts', 'activity__max_watts']

common = {'timeBig': '', 'timeSmall': 'sec', 'heartrate': 'bpm', 'cadence': 'spm', 'watts': 'W', 'count': 'count',
          'count_users': 'listener(s)'}

logger = logging.getLogger(__name__)


class Athlete(models.Model):

    def __str__(self):
        return '{}:{} - {} {}'.format(self.id, self.athlete_id, self.first_name, self.last_name)

    ATHELETE_TYPE = (
        (0, 'Running'),
        (1, 'Cycling'),
        (2, 'Swimming'),
        (3, 'Other'),
    )
    SHARE_SONG_TIME = (
        (0, 'Simple'),
        (1, 'Time'),
        (2, 'Distance'),
        (3, 'Time + Distance'),
    )
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    athlete_id = models.CharField(max_length=12, unique=True)
    profile_image_url = models.URLField()

    first_login = models.BooleanField()

    email = models.EmailField(blank=True, null=True)

    date_preference = models.CharField(max_length=10)
    measurement_preference = models.PositiveSmallIntegerField()
    sex = models.PositiveSmallIntegerField(null=True)
    country = models.CharField(max_length=50, null=True)
    athlete_type = models.PositiveSmallIntegerField(choices=ATHELETE_TYPE)
    last_sync_date = models.DateTimeField(blank=True, null=True)
    activity_count = models.IntegerField()
    runs_count = models.IntegerField()
    rides_count = models.IntegerField()
    swims_count = models.IntegerField()
    first_activity_date = models.DateTimeField(blank=True, null=True)
    last_activity_date = models.DateTimeField(blank=True, null=True)
    updated_strava_at = models.DateTimeField()

    last_celery_task_id = models.UUIDField(blank=True, null=True)
    last_celery_task_count = models.IntegerField(blank=True, null=True)

    strava_token = models.CharField(max_length=100)
    strava_refresh_token = models.CharField(max_length=100, blank=True, null=True)
    strava_token_expires_at = models.CharField(max_length=100, blank=True, null=True)
    share_activity_songs = models.BooleanField(default=True)
    share_activity_songs_mode = models.PositiveSmallIntegerField(default=0, choices=SHARE_SONG_TIME)
    share_activity_link = models.BooleanField(default=True)


class ListenerSpotify(models.Model):

    def __str__(self):
        return '{} - {}, {}'.format(self.id, self.nickname, self.real_name)

    nickname = models.CharField(max_length=30, unique=True)
    real_name = models.CharField(max_length=30)
    profile_image_url = models.URLField(null=True)
    url = models.URLField(null=True)
    product = models.CharField(max_length=10, null=True)

    spotify_code = models.CharField(max_length=100, blank=True, null=True)
    spotify_token = models.CharField(max_length=100, blank=True, null=True)
    spotify_refresh_token = models.CharField(max_length=100, blank=True, null=True)


class ActivitiesToIgnore(models.Model):
    activity_id = models.CharField(max_length=16, unique=True)


class Activity(models.Model):

    def __str__(self):
        return '{}:{} - {}, {}'.format(self.id, self.activity_id, self.name, self.athlete.id)

    athlete = models.ForeignKey(Athlete, on_delete=models.CASCADE)

    activity_id = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True, null=True)

    act_type = models.PositiveSmallIntegerField()

    distance = models.FloatField()
    moving_time = models.IntegerField()
    elapsed_time = models.IntegerField()

    calories = models.IntegerField(blank=True, null=True)
    suffer_score = models.IntegerField(blank=True, null=True)

    start_date = models.DateTimeField()
    start_date_local = models.DateTimeField()

    upload_id = models.CharField(max_length=100, blank=True, null=True)

    embed_token = models.CharField(max_length=100, blank=True, null=True)
    workout_type = models.PositiveSmallIntegerField(default=0,
                                                    blank=True)  # or runs: 0 -> ‘default’, 1 -> ‘race’, 2 -> ‘long run’, 3 -> ‘workout’; for rides: 10 -> ‘default’, 11 -> ‘race’, 12 -> ‘workout’

    avg_speed = models.FloatField()  #:  float meters per second
    max_speed = models.FloatField()  #:  float meters per second
    avg_cadence = models.FloatField(blank=True, null=True)  #:    float RPM

    avg_temp = models.FloatField(blank=True, null=True)  #:   float celsius

    avg_hr = models.FloatField(blank=True, null=True)
    max_hr = models.IntegerField(blank=True, null=True)

    last_sync_date = models.DateTimeField(null=True)

    avg_watts = models.FloatField(blank=True, null=True)
    max_watts = models.IntegerField(blank=True, null=True)

    detailed_vectors = PickledObjectField(blank=True, null=True)

    total_ascent = models.FloatField(blank=True, null=True)
    total_descent = models.FloatField(blank=True, null=True)

    flagged = models.BooleanField(default=False, blank=True)
    flagged_hr = models.BooleanField(default=False, blank=True)

    @property
    def age_in_days(self):
        return (timestamp.now().date() - self.start_date_local.date()).days

    @property
    def avg_speed_pretty_units(self):
        return get_speed_pretty_units(self.athlete.measurement_preference, self.act_type)

    @property
    def avg_speed_pretty(self):
        return get_speed_pretty(self.avg_speed, self.athlete.measurement_preference, self.act_type)

    @property
    def distance_big_pretty_units(self):
        if (self.athlete.measurement_preference == 0):
            return metric_legends['distanceBig']
        elif (self.athlete.measurement_preference == 1):
            return imperial_legends['distanceBig']

    @property
    def distance_small_pretty_units(self):
        if (self.athlete.measurement_preference == 0):
            return metric_legends['distanceSmall']
        elif (self.athlete.measurement_preference == 1):
            return imperial_legends['distanceSmall']

    @property
    def distance_pretty(self):
        if (self.athlete.measurement_preference == 0):
            return metersToKm(self.distance)
        else:
            return metersToMiles(self.distance)

    @property
    def moving_time_pretty(self):
        return secondsToMinutesSecs(self.moving_time)

    @property
    def elapsed_time_pretty(self):
        return secondsToMinutesSecs(self.elapsed_time)

    @property
    def start_date_local_pretty(self):
        if (self.athlete.measurement_preference == 0):
            return metersToKm(self.distance)
        else:
            return metersToMiles(self.distance)

    @property
    def footer_message(self):
        if self.athlete.share_activity_songs:
            return "Find out more detailed information at https://effortly.run/activity/{}\n".format(self.activity_id)
        else:
            return "- by https://effortly.run\n"

    @property
    def activity_share_message(self):
        if self.effort_set.all():
            text = "Songs listened during activity:\n"
            for e in self.effort_set.all():
                if self.athlete.share_activity_songs_mode == 0:
                    text += "{} {}: {} - {}\n".format(e.avg_speed_pretty, e.avg_speed_pretty_units, e.song.artist_name,
                                                      e.song.title)
                elif self.athlete.share_activity_songs_mode == 1:
                    text += "{} {} {}: {} - {}\n".format(e.start_time_pretty_hours, e.avg_speed_pretty,
                                                         e.avg_speed_pretty_units, e.song.artist_name, e.song.title)
                elif self.athlete.share_activity_songs_mode == 2:
                    text += "{} {} {}: {} - {}\n".format(e.start_distance_pretty, e.avg_speed_pretty,
                                                         e.avg_speed_pretty_units, e.song.artist_name, e.song.title)
                elif self.athlete.share_activity_songs_mode == 3:
                    text += "{} {} {} {}: {} - {}\n".format(e.start_time_pretty_hours, e.start_distance_pretty,
                                                            e.avg_speed_pretty, e.avg_speed_pretty_units,
                                                            e.song.artist_name, e.song.title)
            text += "##########################\n"
            text += self.footer_message
        else:
            text = "No songs found.\n- by https://effortly.run\n"
        return text


class Listener(models.Model):

    def __str__(self):
        return '{} - {}, {}'.format(self.id, self.nickname, self.real_name)

    nickname = models.CharField(max_length=30, unique=True)
    real_name = models.CharField(max_length=30, null=True)
    profile_image_url = models.URLField(null=True)
    country = models.CharField(max_length=50, null=True)
    age = models.PositiveSmallIntegerField(null=True)

    scrobble_count = models.IntegerField(null=True)

    last_sync_date = models.DateTimeField(null=True)
    last_scrobble_date = models.DateTimeField(blank=True, null=True)

    lastfm_token = models.CharField(max_length=100)


class PowerUser(models.Model):

    def __str__(self):
        return '{} - {}, {},'.format(self.id, self.athlete, self.listener, self.listener_spotify)

    athlete = models.ForeignKey(Athlete, models.SET_NULL, blank=True, null=True)
    listener = models.ForeignKey(Listener, models.SET_NULL, blank=True, null=True)
    listener_spotify = models.ForeignKey(ListenerSpotify, models.SET_NULL, blank=True, null=True)
    join_date = models.DateTimeField(auto_now=True, null=True)


class Tags(models.Model):

    def __str__(self):
        return '{} - {}, {}'.format(self.name, self.reach, self.taggings_count)

    name = models.CharField(max_length=100, unique=True)
    url = models.URLField()

    reach = models.IntegerField()
    taggings_count = models.IntegerField()

    last_sync_date = models.DateTimeField()


class Artist(models.Model):

    def __str__(self):
        return '{}: {}'.format(self.id, self.name)

    name = models.CharField(max_length=100)
    image_url = models.URLField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    mb_id = models.UUIDField(blank=True, null=True, unique=True)

    listeners_count = models.IntegerField(blank=True, null=True)
    plays_count = models.IntegerField(blank=True, null=True)

    last_sync_date = models.DateTimeField(blank=True, null=True)
    spotify_id = models.CharField(max_length=22, blank=True, null=True)
    tags = models.ManyToManyField(Tags)


class Song(models.Model):

    def __str__(self):
        return '{}: {} - {}'.format(self.id, self.title, self.artist.name)

    title = models.CharField(max_length=100)
    artist_name = models.CharField(max_length=100)
    album_name = models.CharField(max_length=100, blank=True, null=True)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    duration = models.IntegerField(blank=True, null=True)
    listeners_count = models.IntegerField(blank=True, null=True)
    plays_count = models.IntegerField(blank=True, null=True)

    last_sync_date = models.DateTimeField(blank=True, null=True)

    image_url = models.URLField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    mb_id = models.UUIDField(blank=True, null=True)
    spotify_id = models.CharField(max_length=22, blank=True, null=True)
    tags = models.ManyToManyField(Tags)

    danceability = models.FloatField(blank=True, null=True)
    energy = models.FloatField(blank=True, null=True)
    key = models.SmallIntegerField(blank=True, null=True)
    loudness = models.FloatField(blank=True, null=True)
    mode = models.SmallIntegerField(blank=True, null=True)
    speechiness = models.FloatField(blank=True, null=True)
    acousticness = models.FloatField(blank=True, null=True)
    instrumentalness = models.FloatField(blank=True, null=True)
    liveness = models.FloatField(blank=True, null=True)
    valence = models.FloatField(blank=True, null=True)
    bpm = models.FloatField(blank=True, null=True)
    time_signature = models.SmallIntegerField(blank=True, null=True)

    original_song = models.ForeignKey("self", models.SET_NULL, blank=True, null=True)

    @property
    def duration_pretty(self):
        return secondsToMinutesSecs(self.duration / 1000.0)


class AthleteSongCadence(models.Model):

    def __str__(self):
        return '{}: {} - {}'.format(self.id, self.poweruser.athlete, self.song)

    poweruser = models.ForeignKey(PowerUser, null=True, on_delete=models.SET_NULL)
    song = models.ForeignKey(Song, null=True, on_delete=models.SET_NULL)
    cadence = models.FloatField()
    listen_count = models.IntegerField()
    act_type = models.PositiveSmallIntegerField()


class FlaggedArtist(models.Model):

    def __str__(self):
        return '{}: {}'.format(self.poweruser, self.artist)

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    poweruser = models.ForeignKey(PowerUser, on_delete=models.CASCADE)


class FlaggedSong(models.Model):

    def __str__(self):
        return '{}: {}'.format(self.poweruser, self.song)

    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    poweruser = models.ForeignKey(PowerUser, on_delete=models.CASCADE)


class Effort(models.Model):

    def __str__(self):
        return '{}: {}'.format(self.song, self.activity)

    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)

    act_type = models.PositiveSmallIntegerField()

    idx_in_activity = models.PositiveSmallIntegerField()

    start_time = models.IntegerField()
    duration = models.IntegerField()

    start_distance = models.FloatField()
    distance = models.FloatField()

    avg_speed = models.FloatField()
    diff_last_speed = models.FloatField(blank=True, null=True)  # m/s
    diff_avg_speed = models.FloatField()  # m/s

    diff_last_speed_s = models.FloatField(blank=True, null=True)  # s/m
    diff_avg_speed_s = models.FloatField()  # s/m

    avg_hr = models.FloatField(blank=True, null=True)
    diff_avg_hr = models.FloatField(blank=True, null=True)
    diff_last_hr = models.FloatField(blank=True, null=True)

    avg_cadence = models.FloatField(blank=True, null=True)
    diff_avg_cadence = models.FloatField(blank=True, null=True)
    diff_last_cadence = models.FloatField(blank=True, null=True)

    total_ascent = models.FloatField()
    total_descent = models.FloatField()

    avg_watts = models.FloatField(blank=True, null=True)
    diff_avg_watts = models.FloatField(blank=True, null=True)
    diff_last_watts = models.FloatField(blank=True, null=True)

    data = models.BinaryField(blank=True, null=True)
    hr = models.BinaryField(blank=True, null=True)
    time = models.BinaryField(blank=True, null=True)

    flagged = models.BooleanField(default=False, blank=True)
    flagged_hr = models.BooleanField(default=False, blank=True)

    @property
    def full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    @property
    def data_array(self):
        return np.fromstring(self.data, dtype=np.float16)

    @property
    def time_array(self):
        return np.fromstring(self.time, dtype=np.uint8)

    @property
    def avg_speed_pretty_units(self):
        return get_speed_pretty_units(self.activity.athlete.measurement_preference, self.activity.act_type)

    @property
    def avg_speed_pretty(self):
        return get_speed_pretty(self.avg_speed, self.activity.athlete.measurement_preference, self.activity.act_type)

    @property
    def diff_avg_speed_pretty(self):
        return get_speed_pretty(self.diff_avg_speed, self.activity.athlete.measurement_preference, self.activity.act_type)

    @property
    def diff_last_speed_pretty(self):
        return get_speed_pretty(self.diff_last_speed, self.activity.athlete.measurement_preference, self.activity.act_type)

    @property
    def distance_big_pretty_units(self):
        if (self.activity.athlete.measurement_preference == 0):
            return metric_legends['distanceBig']
        elif (self.activity.athlete.measurement_preference == 1):
            return imperial_legends['distanceBig']

    @property
    def distance_small_pretty_units(self):
        if (self.activity.athlete.measurement_preference == 0):
            return metric_legends['distanceSmall']
        elif (self.activity.athlete.measurement_preference == 1):
            return imperial_legends['distanceSmall']

    @property
    def distance_pretty(self):
        if (self.activity.athlete.measurement_preference == 0):
            return metersToKm(self.distance)
        else:
            return metersToMiles(self.distance)

    @property
    def start_distance_pretty(self):
        if (self.activity.athlete.measurement_preference == 0):
            return metersToKm(self.start_distance) + " " + self.distance_big_pretty_units
        else:
            return metersToMiles(self.start_distance) + " " + self.distance_big_pretty_units

    @property
    def duration_pretty(self):
        return secondsToMinutesSecs(self.duration)

    @property
    def start_time_pretty(self):
        return secondsToMinutesSecs(self.start_time)

    @property
    def start_time_pretty_hours(self):
        return secondsToHoursMinutesSecs(self.start_time)


def get_poweruser(athlete_id):
    powerusers = PowerUser.objects.filter(athlete__athlete_id=athlete_id)
    if powerusers:
        return powerusers[0]


def create_athlete_from_dict(athlete_api):
    athlete = Athlete()

    athlete.first_name = athlete_api.firstname
    athlete.last_name = athlete_api.lastname
    athlete.athlete_id = athlete_api.id
    athlete.profile_image_url = athlete_api.profile

    athlete.first_login = True

    athlete.email = athlete_api.email

    athlete.date_preference = athlete_api.date_preference

    if athlete_api.measurement_preference == 'meters':
        athlete.measurement_preference = 0
    else:
        athlete.measurement_preference = 1

    if athlete_api.sex == None:
        athlete.sex = 0
    elif athlete_api.sex == 'M':
        athlete.sex = 1
    elif athlete_api.sex == 'F':
        athlete.sex = 2
    else:
        athlete.sex = 3

    if athlete_api.athlete_type == 'runner':
        athlete.athlete_type = 0
    elif athlete_api.athlete_type == 'cyclist':
        athlete.athlete_type = 1
    else:
        athlete.athlete_type = 2

    athlete.country = athlete_api.country

    stats = athlete_api.stats

    athlete.activity_count = stats.all_ride_totals.count
    athlete.runs_count = stats.all_run_totals.count
    athlete.rides_count = stats.all_ride_totals.count
    athlete.swims_count = stats.all_swim_totals.count
    athlete.activity_count = stats.all_ride_totals.count + stats.all_run_totals.count + stats.all_swim_totals.count
    athlete.updated_strava_at = athlete_api.updated_at

    return athlete


def create_listener_from_dict(listener_api, key):
    listener = Listener()

    listener.nickname = listener_api['name']

    if 'realname' in listener_api:
        listener.real_name = listener_api['realname']

    if 'country' in listener_api:
        listener.country = listener_api['country']

    if 'age' in listener_api:
        listener.age = listener_api['age']

    if 'playcount' in listener_api:
        listener.scrobble_count = int(listener_api['playcount'])

    listener.profile_image_url = listener_api['image'][-1]['#text']
    listener.lastfm_token = key

    return listener


def clear_dead_images():
    for track in Song.objects.all():
        if track.image_url:
            r = requests.head(track.image_url)
            if r.status_code == 404:
                track.image_url = None
                track.save()
    for track in Artist.objects.all():
        if track.image_url:
            r = requests.head(track.image_url)
            if r.status_code == 404:
                track.image_url = None
                track.save()


def lastfm_get_largest_image(image_list):
    order = ['extralarge', 'large', 'medium', 'small', '', 'mega']
    if not "#text" in image_list[-1] or not image_list[-1]["#text"].strip() != "":
        return None
    for size in order:
        for image in image_list[::-1]:
            if image["#text"].endswith('2a96cbd8b46e442fc41c2b86b821562f.png'):
                return None
            if image["size"] == size and image["#text"].strip() != "":
                return image["#text"]
    return image_list[-1]["#text"]


def create_song_from_dict(song_api):
    songs = Song.objects.filter(artist_name__iexact=song_api['artist']['name'], title__iexact=song_api['name'])

    if songs:
        song = songs[0]
        if ('spotify_id' in song_api and song_api['spotify_id'].strip() != ""):
            song.spotify_id = song_api['spotify_id']
            song.save()
        return song

    song = Song()

    song.title = song_api['name']
    song.url = song_api['url']
    song.artist_name = song_api['artist']['name']
    song.album_name = song_api['album']['#text']

    if ('spotify_id' in song_api and song_api['spotify_id'].strip() != ""):
        song.spotify_id = song_api['spotify_id']

    if ('mbid' in song_api and song_api['mbid'].strip() != ""):
        song.mb_id = song_api['mbid']

    if len(song_api['image']) > 0:
        song.image_url = lastfm_get_largest_image(song_api['image'])

    if ('mbid' in song_api['artist'] and song_api['artist']['mbid'].strip() != ""):
        artist_mb_id = song_api['artist']['mbid']
        artists = Artist.objects.filter(Q(name__iexact=song_api['artist']['name']) | Q(mb_id=artist_mb_id))
    else:
        artists = Artist.objects.filter(name__iexact=song_api['artist']['name'])

    if artists:
        artist = artists[0]
        if ('spotify_id' in song_api['artist'] and song_api['artist']['spotify_id'].strip() != ""):
            artist.spotify_id = song_api['artist']['spotify_id']
            artist.save()
        if not artist.image_url and len(song_api['artist']['image']) > 0:
            artist.image_url = lastfm_get_largest_image(song_api['artist']['image'])
            artist.save()
    else:
        artist = Artist()
        artist.name = song_api['artist']['name']
        if ('mbid' in song_api['artist'] and song_api['artist']['mbid'].strip() != ""):
            artist.mb_id = song_api['artist']['mbid']
        if ('spotify_id' in song_api['artist'] and song_api['artist']['spotify_id'].strip() != ""):
            artist.spotify_id = song_api['artist']['spotify_id']

        if len(song_api['artist']['image']) > 0:
            artist.image_url = lastfm_get_largest_image(song_api['artist']['image'])

        artist.save()

    song.artist = artist

    song.save()

    song.original_song = song
    song.save()

    return song


def create_activity_from_dict(activity_api, dry_run=False):
    activities = Activity.objects.filter(activity_id=activity_api['id'])

    if activities:
        return activities[0]
    logger.debug(activity_api)
    activity = Activity()
    if activity_api['type'] == 'Ride':
        activity.act_type = 1
    elif activity_api['type'] == 'Run':
        activity.act_type = 0
    elif activity_api['type'] == 'Swim':
        activity.act_type = 2
    else:
        return None

    athletes = Athlete.objects.filter(athlete_id=activity_api['athlete_id'])

    if athletes:
        athlete = athletes[0]
    else:
        return None

    activity.athlete = athlete
    activity.activity_id = activity_api['id']

    activity.date = activity_api['start_date']
    activity.name = activity_api['name']
    activity.description = activity_api['description']
    activity.distance = float(activity_api['total_distance'])
    activity.moving_time = int(activity_api['moving_time'])
    activity.elapsed_time = int(activity_api['elapsed_time'])

    activity.start_date = activity_api['start_date']
    activity.start_date_local = activity_api['start_date_local']

    activity.upload_id = activity_api['upload_id']

    activity.embed_token = activity_api['embed_token']

    activity.workout_type = 0
    if 'workout_type' in activity_api and activity_api['workout_type']:
        activity.workout_type = int(activity_api['workout_type'])

    activity.avg_speed = float(activity_api['average_speed'])
    activity.max_speed = float(activity_api['max_speed'])

    if activity_api['calories']:
        activity.calories = int(activity_api['calories'])
    if activity_api['suffer_score']:
        activity.suffer_score = int(activity_api['suffer_score'])

    if activity_api['average_cadence']:
        activity.avg_cadence = float(activity_api['average_cadence'])

    if activity_api['average_temp']:
        activity.avg_temp = float(activity_api['average_temp'])

    if activity_api['average_heartrate']:
        activity.avg_hr = float(activity_api['average_heartrate'])
    if activity_api['max_heartrate']:
        activity.max_hr = int(activity_api['max_heartrate'])

    activity.last_sync_date = datetime.now()

    if activity_api['type'] == 'Ride':
        if activity_api['average_watts']:
            activity.avg_watts = float(activity_api['average_watts'])
        if activity_api['max_watts']:
            activity.max_watts = int(activity_api['max_watts'])

    if not dry_run:
        activity.save()
    return activity


def lastfm_get_artist(name, mbid=None):
    if mbid == None or mbid == "":
        artists = Artist.objects.filter(name=name)
    else:
        artists = Artist.objects.filter(mb_id=mbid)

    if artists:
        return artists[0]


def lastfm_get_track(artist, name):
    songs = Song.objects.filter(title=name, artist_name=artist)

    if songs:
        song = songs[0]
        if song.original_song:
            return song.original_song
        else:
            return song


def strava_get_activity_by_id(act_id):
    if strava_is_activity_to_ignore(act_id):
        return None

    activities = Activity.objects.filter(activity_id=act_id)

    if activities:
        return activities[0]

    return None


def strava_is_activity_to_ignore(act_id):
    activities = ActivitiesToIgnore.objects.filter(activity_id=act_id)

    if activities:
        return True
    return False


def effort_convert(effort_dict, units):
    if units == 1:
        effort_dict = effort_to_imperial(effort_dict)
    else:
        effort_dict = effort_to_metric(effort_dict)
    return effort_commom(effort_dict)


def effort_commom(effort_dict):
    if 'sort_key' in effort_dict and effort_dict['sort_key'] in heartrate and 'sort_value' in effort_dict:
        effort_dict['sort_value'] = "{:.2f}".format(effort_dict['sort_value'])
        effort_dict['sort_value_unit'] = common['heartrate']
    elif 'sort_key' in effort_dict and effort_dict['sort_key'] in cadence and 'sort_value' in effort_dict:
        effort_dict['sort_value'] = "{}".format(int(effort_dict['sort_value']))
        effort_dict['sort_value_unit'] = common['cadence']
    elif 'sort_key' in effort_dict and effort_dict['sort_key'] in watts and 'sort_value' in effort_dict:
        effort_dict['sort_value'] = "{}".format(int(effort_dict['sort_value']))
        effort_dict['sort_value_unit'] = common['watts']
    elif 'sort_key' in effort_dict and effort_dict['sort_key'] in count and 'sort_value' in effort_dict:
        effort_dict['sort_value_unit'] = common['count']
    elif 'sort_key' in effort_dict and effort_dict['sort_key'] in count_users and 'sort_value' in effort_dict:
        effort_dict['sort_value_unit'] = common['count_users']
    return effort_dict


def effort_to_metric(effort_dict):
    if effort_dict == None:
        new_effort_dict = {}
        new_effort_dict["units"] = {**metric_legends, **common}
        return new_effort_dict

    new_effort_dict = effort_dict

    for key in speed_small_diff_computed:
        if key in effort_dict and effort_dict[key] != None:
            new_effort_dict[key + '_s'] = invertTimeDistance(effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key + '_s':
            new_effort_dict['sort_value'] = new_effort_dict[key + '_s']
            new_effort_dict['sort_value_unit'] = metric_legends['speed_s']

    for key in speed_small:
        if key in effort_dict and effort_dict[key] != None:
            # logger.error(key + " a " + str(effort_dict[key]))
            new_effort_dict[key + "_pretty"] = secondsPerMeterToMinPerKm(new_effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = secondsPerMeterToMinPerKm(new_effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = metric_legends['speed_s']

    for key in speed:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = metersPerSecondToKmH(effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = metersPerSecondToKmH(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = metric_legends['speed']

    for key in timeBig:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = secondsToMinutesSecs(effort_dict[key])
        if 'sort_key' in effort_dict and effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = secondsToMinutesSecs(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = common['timeBig']

    for key in distanceBig:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = metersToKm(effort_dict[key])
        if 'sort_key' in effort_dict and effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = metersToKm(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = metric_legends['distanceBig']

    for key in distanceSmall:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = metersToMeters(effort_dict[key])
        if 'sort_key' in effort_dict and effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = metersToMeters(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = metric_legends['distanceSmall']

    new_effort_dict["units"] = {**metric_legends, **common}

    return new_effort_dict


def effort_to_imperial(effort_dict):
    if effort_dict == None:
        new_effort_dict = {}
        new_effort_dict["units"] = {**imperial_legends, **common}
        return new_effort_dict

    new_effort_dict = effort_dict

    for key in speed_small_diff_computed:
        if key in effort_dict and effort_dict[key] != None:
            new_effort_dict[key + '_s'] = invertTimeDistance(effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key + '_s':
            new_effort_dict['sort_value'] = new_effort_dict[key + '_s']
            new_effort_dict['sort_value_unit'] = imperial_legends['speed_s']

    for key in speed_small:
        if key in effort_dict and effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = secondsPerMeterToMinPerMi(new_effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = secondsPerMeterToMinPerMi(new_effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = imperial_legends['speed_s']

    for key in speed:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = metersPerSecondToMiH(effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = metersPerSecondToMiH(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = imperial_legends['speed']

    for key in timeBig:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = secondsToMinutesSecs(effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = secondsToMinutesSecs(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = common['timeBig']

    for key in distanceBig:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = metersToMiles(effort_dict[key])
        if 'sort_key' in new_effort_dict and new_effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = metersToMiles(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = imperial_legends['distanceBig']

    for key in distanceSmall:
        if key in new_effort_dict and new_effort_dict[key] != None:
            new_effort_dict[key + "_pretty"] = metersToFeet(effort_dict[key])
        if 'sort_key' in effort_dict and effort_dict['sort_key'] == key:
            new_effort_dict['sort_value'] = metersToFeet(effort_dict['sort_value'])
            new_effort_dict['sort_value_unit'] = imperial_legends['distanceSmall']

    new_effort_dict["units"] = {**imperial_legends, **common}

    return new_effort_dict
