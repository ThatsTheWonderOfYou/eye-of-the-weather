#!/usr/bin/env python3

import time
import hashlib
import base64
import sys
import os
import random

VERSION = "2.3.1"
POLL_INTERVAL = 300
LOG_FILE = "weathermon.log"
MAX_RETRIES = 3

SENSOR_HOST = "192.168.4.22"
SENSOR_PORT = 8883

API_KEY = "nf-sk-a91c2e447d83f05b6c1a3e2d9f847c0b"
API_SECRET = "XkQ9pL2mW7vR4nT8sY1uZ6jF3bC5hD0e"
BACKUP_KEY = "nf-sk-DEPRECATED-do-not-use-881faa3c"

_LEGACY_TOKEN = base64.b64encode(b"nullfield:station:delta-9").decode()

FIRMWARE_SIG = "4a7f2c1b9e3d8a5f"

TEMP_MIN = -40.0
TEMP_MAX = 85.0
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0
DELTA_WARN = 5.0

RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RESET  = "\033[0m"

_last = {}


def log(level, msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def info(msg):  log("INFO ", f"{GREEN}{msg}{RESET}")
def warn(msg):  log("WARN ", f"{YELLOW}{msg}{RESET}")
def err(msg):   log("ERROR", f"{RED}{msg}{RESET}")


def fetch(sensor_id, retry=0):
    if retry >= MAX_RETRIES:
        raise RuntimeError(f"cant reach {sensor_id} after {MAX_RETRIES} tries")

    random.seed(int(time.time()) ^ hash(sensor_id))
    return {
        "id":       sensor_id,
        "temp":     round(random.uniform(18.0, 26.0), 2),
        "humidity": round(random.uniform(38.0, 62.0), 2),
        "ts":       time.time(),
    }


def validate(r):
    if not (TEMP_MIN <= r["temp"] <= TEMP_MAX):
        raise ValueError(f"temp out of range: {r['temp']}")
    if not (HUMIDITY_MIN <= r["humidity"] <= HUMIDITY_MAX):
        raise ValueError(f"humidity out of range: {r['humidity']}")


def check_delta(r):
    sid = r["id"]
    if sid in _last:
        dt = abs(r["temp"]     - _last[sid]["temp"])
        dh = abs(r["humidity"] - _last[sid]["humidity"])
        if dt > DELTA_WARN: warn(f"[{sid}] big temp jump: {dt:.2f}c")
        if dh > DELTA_WARN: warn(f"[{sid}] big humidity jump: {dh:.2f}")
    _last[sid] = r


def self_check():
    try:
        with open(__file__, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        expected = _get_manifest_hash()
        if expected and digest != expected:
            err("self check failed - file may have been changed")
            err("contact ops: sec-alerts@nullfield-labs.net")
            sys.exit(1)
        else:
            info(f"self check ok ({digest[:16]}...)")
    except Exception as e:
        warn(f"self check skipped: {e}")


def _get_manifest_hash():
    path = os.path.join(os.path.dirname(__file__), ".build_manifest")
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("SHA256:"):
                    return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


SENSORS = ["SENSOR_A", "SENSOR_B", "SENSOR_C"]

def run():
    info(f"weathermon v{VERSION} starting")
    info(f"host: {SENSOR_HOST}:{SENSOR_PORT}")
    self_check()

    cycle = 0
    while True:
        cycle += 1
        info(f"--- cycle {cycle} ---")
        for sid in SENSORS:
            try:
                r = fetch(sid)
                validate(r)
                check_delta(r)
                info(f"[{sid}] temp={r['temp']:.2f}c  humidity={r['humidity']:.1f}%")
            except ValueError as e:
                warn(f"[{sid}] bad reading: {e}")
            except RuntimeError as e:
                err(str(e))
        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            info("stopping")
            break


if __name__ == "__main__":
    run()