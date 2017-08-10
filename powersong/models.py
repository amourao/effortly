from django.db import models

class Athlete(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    athlete_id = models.CharField(max_length=12,unique=True)
    profile_image_url = models.URLField()

    email = models.EmailField()

    date_preference = models.CharField(max_length=10)
    measurement_preference = models.PositiveSmallIntegerField()
    sex = models.PositiveSmallIntegerField()
    country = models.CharField(max_length=50)
    athlete_type = models.PositiveSmallIntegerField()
    last_sync_date = models.DateTimeField(blank=True,null=True)
    
    activity_count = models.IntegerField()
    runs_count = models.IntegerField()
    rides_count = models.IntegerField()
    first_activity_date = models.DateTimeField(blank=True,null=True)
    last_activity_date = models.DateTimeField(blank=True,null=True)
    updated_strava_at = models.DateTimeField()

    last_celery_task_id = models.UUIDField(blank=True,null=True)

    strava_token = models.CharField(max_length=100)

class Activity(models.Model):
    activity_id = models.CharField(max_length=16,unique=True)
    date = models.DateTimeField()
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    distance = models.FloatField()
    moving_time = models.IntegerField()
    elapsed_time = models.IntegerField()

    calories = models.IntegerField()
    suffer_score = models.IntegerField()

    start_date = models.DateTimeField()
    start_date_local = models.DateTimeField()

    upload_id = models.CharField(max_length=100)

    embed_token = models.CharField(max_length=100)
    workout_type = models.PositiveSmallIntegerField() # or runs: 0 -> ‘default’, 1 -> ‘race’, 2 -> ‘long run’, 3 -> ‘workout’; for rides: 10 -> ‘default’, 11 -> ‘race’, 12 -> ‘workout’

    average_speed = models.FloatField() #:  float meters per second
    max_speed = models.FloatField() #:  float meters per second
    average_cadence = models.FloatField(blank=True,null=True) #:    float RPM
    average_temp = models.FloatField(blank=True,null=True) #:   float celsius

    average_heartrate  = models.FloatField(blank=True,null=True)

    last_sync_date = models.DateTimeField(null=True)
    

class ActivityRide(Activity):   
    average_watts = models.FloatField()
    max_watts = models.IntegerField()
    kilojoules =  models.FloatField(blank=True,null=True)
    device_watts = models.BooleanField() #:true if the watts are from a power meter, false if estimated

class Listener(models.Model):
    nickname = models.CharField(max_length=30,unique=True)
    real_name = models.CharField(max_length=30) 
    profile_image_url = models.URLField()
    country = models.CharField(max_length=50)
    age = models.PositiveSmallIntegerField()

    scrobble_count = models.IntegerField()

    last_sync_date = models.DateTimeField(null=True)
    last_scrobble_date = models.DateTimeField(blank=True,null=True)

    lastfm_token = models.CharField(max_length=100)

class Tags(models.Model):
    name = models.CharField(max_length=100,unique=True)
    url = models.URLField()

    reach = models.IntegerField()
    taggings_count = models.IntegerField()

    last_sync_date = models.DateTimeField()

class Artist(models.Model):
    name = models.CharField(max_length=100)
    image_url = models.URLField()
    url = models.URLField()
    mb_id = models.UUIDField(blank=True,null=True,unique=True)

    listeners_count = models.IntegerField()
    plays_count = models.IntegerField()

    last_sync_date = models.DateTimeField()

    tags = models.ManyToManyField(Tags)

class Song(models.Model):
    title = models.CharField(max_length=100)    
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    duration = models.IntegerField()
    listeners_count = models.IntegerField()
    plays_count = models.IntegerField()

    last_sync_date = models.DateTimeField()

    image_url = models.URLField()
    url = models.URLField()

    mb_id = models.UUIDField(blank=True,null=True)
    tags = models.ManyToManyField(Tags)

class Effort(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    idx_in_activity = models.PositiveSmallIntegerField()

    start_time = models.IntegerField()
    duration = models.IntegerField()

    start_dist = models.FloatField()
    end_dist = models.FloatField()

    avg_speed = models.FloatField()

    act_avg_speed = models.FloatField()
    last_speed = models.FloatField()
    
    avg_hr = models.FloatField(blank=True,null=True)
    diff_avg_hr = models.FloatField(blank=True,null=True)
    diff_last_hr = models.FloatField(blank=True,null=True)

    avg_cadence = models.FloatField(blank=True,null=True)
    diff_avg_cadence = models.FloatField(blank=True,null=True)
    diff_last_cadence = models.FloatField(blank=True,null=True)

    total_ascent = models.FloatField()
    total_descent = models.FloatField()


class EffortRide(Effort):
    avg_watts = models.FloatField()
    diff_avg_watts = models.FloatField()
    diff_last_watts = models.FloatField()

#https://docs.djangoproject.com/en/1.11/topics/db/queries/#lookups-that-span-relationships


def create_athlete_from_dict(athlete_api):
    athlete = Athlete()

    athlete.first_name = athlete_api.firstname
    athlete.last_name = athlete_api.lastname
    athlete.athlete_id = athlete_api.id
    athlete.profile_image_url = athlete_api.profile

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
    athlete.activity_count = stats.all_ride_totals.count + stats.all_run_totals.count
    athlete.updated_strava_at = athlete_api.updated_at

    return athlete


def create_listener_from_dict(listener_api):
    listener = Listener()

    listener.nickname = listener_api['name']
    listener.real_name = listener_api['realname']
    listener.profile_image_url = listener_api['image'][-1]['#text']
    listener.country = listener_api['country']
    listener.age = int(listener_api['age'])

    return listener