import json
import os
import pickle

from powersong.settings import BASE_DIR

AVAILABLE_EXTENSIONS = {"mp3", "mp4", "flac", "m4a", "wma"}

OUTPUT_DIR = os.path.join(BASE_DIR, 'sink_or_swim')


def save_pickled_tracks(tracks):
    with open(f'{OUTPUT_DIR}/tracks.pickle', 'wb') as handle:
        pickle.dump(tracks, handle, protocol=pickle.HIGHEST_PROTOCOL)
    with open(f'{OUTPUT_DIR}/tracks.txt', 'w') as out:
        for i, data in enumerate(tracks):
            if data["file_extension"] in AVAILABLE_EXTENSIONS:
                out.write(f'{i:02}: {data["output_filename"]}\n')


def load_pickled_tracks():
    with open(f'{OUTPUT_DIR}/tracks.pickle', 'rb') as handle:
        tracks = pickle.load(handle)
        return tracks


def save_lastest_start(index):
    with open(f'{OUTPUT_DIR}/index.txt', 'w') as handle:
        handle.write(str(index))
        handle.write("\n")


def load_lastest_start():
    try:
        with open(f'{OUTPUT_DIR}/index.txt', 'r') as handle:
            for row in handle:
                return int(row.strip())
    except:
        print("No index file found, defaulting to start at track 0")
        return 0
