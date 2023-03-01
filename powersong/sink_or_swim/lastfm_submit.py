from datetime import timedelta, datetime
from typing import Dict

import pylast

from powersong.local import LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_USERNAME, LASTFM_PASSWORD


def init():
    network = pylast.LastFMNetwork(
        api_key=LASTFM_API_KEY,
        api_secret=LASTFM_API_SECRET,
        username=LASTFM_USERNAME,
        password_hash=LASTFM_PASSWORD,
    )
    return network


def scrobble_track(track, timestamp, network):
    network.scrobble(
            track["artist"],
            track["title"],
            timestamp,
            album=track["album"],
            album_artist=track["album_artist"],
            track_number=track["track_number"],
            duration=track["duration"]
    )


def submit_tracks(tracks: Dict, start_date: datetime, total_duration: int, start_index: int, offset: int = 0):
    network = init()
    current_time: int = 0
    i = start_index
    if i == len(tracks):
        print("Rolling over to the start")
        i = 0

    track_count = 0
    total_duration += offset
    print(f"Setting {total_duration} seconds of music starting at {start_date}")
    while True:
        track = tracks[i]
        scrobble_time = start_date + timedelta(seconds=(current_time + offset))
        print(f"Submitting {track['artist']} - {track['title']} at {scrobble_time}")
        scrobble_track(track, scrobble_time.timestamp(), network)
        current_time += track["duration"]
        track_count += 1
        i += 1
        if current_time > total_duration:
            print(f"Submitted {track_count} tracks")
            return i

        # if it gets to the end, start over
        if i == len(tracks):
            print("Rolling over to the start")
            i = 0





