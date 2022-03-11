import click
import cv2
import face_recognition
import json
import numpy as np
import os
import requests
import time
import yaml

from datetime import datetime
from oauthlib.oauth2 import MissingTokenError
from ring_doorbell import Ring, Auth

@click.command()
def cli():
    log_print("Loading configuration...")
    config = load_config()
    log_print("Loading faces...")
    known_face_encodings, known_face_names = load_face_encodings(os.path.join(os.environ["HOME"], ".config/wring/img"))
    log_print("Connecting to Ring...")
    cache_dir_path = os.path.join(os.environ["HOME"], ".cache/wring")
    if not os.path.isdir(cache_dir_path):
        os.mkdir(cache_dir_path)
    ring = connect_ring(config, os.path.join(cache_dir_path, "cache"))
    prev_ding_event_ids = {}
    for doorbell in ring.devices()["doorbots"]:
        prev_ding_event = doorbell.history(kind="ding", limit=1)
        prev_ding_event_id = prev_ding_event[0]["id"] if prev_ding_event else None
        prev_ding_event_ids[doorbell.id] = prev_ding_event_id
    while True:
        for doorbell in ring.devices()["doorbots"]:
            curr_event = doorbell.history(kind="ding", limit=1)
            curr_event = curr_event[0] if curr_event else None
            if curr_event and curr_event["id"] != prev_ding_event_ids[doorbell.id]:
                log_print(f"Doorbell '{doorbell.name}' has been rung")
                time.sleep(5)
                download_video(doorbell, cache_dir_path)
                log_print(f"Downloaded ring video for doorbell '{doorbell.name}'")
                log_print(f"Analyzing video for faces...")
                found_known_faces = recognize_video_faces(os.path.join(cache_dir_path, "curr_ding.mp4"), known_face_encodings, known_face_names)
                for name in found_known_faces:
                    if found_known_faces[name]:
                        if name == "Unknown":
                            log_print(f"An unknown person is at doorbell {doorbell.name}!")
                        else:
                            log_print(f"{name} is at {doorbell.name}!")
                prev_ding_event_ids[doorbell.id] = curr_event["id"]
        time.sleep(1)
    
def log_print(msg):
    click.echo(f"[{datetime.now()}] {msg}")

def load_config():
    config_file_path = os.path.join(os.environ["HOME"], ".config/wring/config.yml")
    with open(config_file_path, "r") as f:
        return yaml.safe_load(f)

def connect_ring(config, cache_file):
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            auth = Auth("wring/1.0", json.loads(f.read()), lambda token: update_token(token, cache_file))
    else:
        auth = Auth("wring/1.0", None, lambda token: update_token(token, cache_file))
        try:
            auth.fetch_token(config["ring"]["email"], config["ring"]["password"])
        except MissingTokenError:
            auth.fetch_token(config["ring"]["email"], config["ring"]["password"], str(config["ring"]["verification_code"]))
    ring = Ring(auth)
    ring.update_data()
    return ring

def update_token(token, cache_file):
    with open(cache_file, "w") as f:
        f.write(json.dumps(token))

def download_video(doorbell, out_dir):
    r = requests.get(doorbell.recording_url(doorbell.last_recording_id), stream=True)
    with open(os.path.join(out_dir, "curr_ding.mp4"), "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

def load_face_encodings(img_dir):
    known_face_encodings = []
    known_face_names = []
    for root, dirs, files in os.walk(img_dir):
        if files:
            for file in files:
                known_face_encodings.append(face_recognition.face_encodings(face_recognition.load_image_file(os.path.join(root, file)))[0])
                known_face_names.append(os.path.basename(root))
    return known_face_encodings, known_face_names

def recognize_video_faces(video_path, known_face_encodings, known_face_names):
    cap = cv2.VideoCapture(video_path)
    found_known_faces = {x: False for x in known_face_names}
    found_known_faces["Unknown"] = False

    process_frame = True
    while cap.isOpened():
        ret, frame = cap.read()
        if ret and known_face_encodings:
            frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            frame = frame[:, :, ::-1]
            if process_frame:
                face_locations = face_recognition.face_locations(frame)
                face_encodings = face_recognition.face_encodings(frame, face_locations)
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    curr_name = "Unknown"

                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        curr_name = known_face_names[best_match_index]
                        # Optimize facial recognition by removing already found faces
                        known_face_encodings = known_face_encodings[:best_match_index] + known_face_encodings[best_match_index + 1:]
                        known_face_names = known_face_names[:best_match_index] + known_face_names[best_match_index + 1:]
                    found_known_faces[curr_name] = True
            process_frame = not process_frame
        else:
            break
    cap.release()
    return found_known_faces
