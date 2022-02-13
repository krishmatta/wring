import click
import json
import os
import time
import yaml

from datetime import datetime
from oauthlib.oauth2 import MissingTokenError
from ring_doorbell import Ring, Auth

@click.command()
def cli():
    log_print("Loading configuration...")
    config = load_config()
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
                log_print("New Ding Event!")
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
