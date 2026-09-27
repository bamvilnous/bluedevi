print("task started", flush=True)

import os
import json
import time
import random
from datetime import datetime, timezone
import requests

PLACE_IDS = [
    1818,
    47324,
    25415,
    14403,
    192800,
    189707,
    18164449,
    863266079,
    142823291,
    13822889,
    9689581,
    606849621,
    537413528,
    920587237,
    2727067538,
    4623386862,
    8481844229,
    13772394625,
    15101393044,
    126884695634066,
    74205509034203,

    91376754318794, # RobloxReplicatedStorage (testing)
]
WEBHOOK_URL = ""
POLL_INTERVAL_SECONDS = 25
STATE_FILE = "state.json"

COOKIE = ""

EMBED_COLORS = [0x00B2FF, 0x57F287, 0xFEE75C, 0xEB459E, 0xED4245, 0xFFA500]

def get_csrf_token(cookie):
    try:
        r = requests.post(
            "https://auth.roblox.com/v2/logout",
            cookies={".ROBLOSECURITY": cookie},
        )
        return r.headers.get("x-csrf-token")
    except requests.RequestException:
        return None


CSRF_TOKEN = get_csrf_token(COOKIE)


def refresh_csrf_token():
    global CSRF_TOKEN
    CSRF_TOKEN = get_csrf_token(COOKIE)
    print("refreshed csrf token", flush=True)


def auth_cookies():
    return {".ROBLOSECURITY": COOKIE} if COOKIE else {}


def auth_headers():
    return {"x-csrf-token": CSRF_TOKEN} if CSRF_TOKEN else {}


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_universe_id(place_id):
    try:
        r = requests.get(f"https://apis.roblox.com/universes/v1/places/{place_id}/universe")
        return r.json().get("universeId")
    except requests.RequestException:
        return None


def get_universe_places(universe_id):
    try:
        r = requests.get(
            f"https://develop.roblox.com/v2/universes/{universe_id}/places",
            params={"limit": 50, "extendedSettings": "true"},
            cookies=auth_cookies(),
        )
        return r.json().get("data", [])
    except requests.RequestException:
        return []


def get_saved_version(place):
    if "currentSavedVersion" in place:
        return place.get("currentSavedVersion")
    return (place.get("extendedSettings") or {}).get("currentSavedVersion")


def _check_published(place_id, latest_saved_version):
    r = requests.post(
        "https://develop.roblox.com/v1/assets/latest-versions",
        json={"assetIds": [place_id], "versionStatus": "Published"},
        headers=auth_headers(),
        cookies=auth_cookies(),
    )
    data = r.json()

    latest_published_version = data.get("results")[0].get('versionNumber')
    return latest_published_version == latest_saved_version


def is_latest_version_published(place_id, latest_saved_version):
    try:
        return _check_published(place_id, latest_saved_version)
    except (requests.RequestException, AttributeError, IndexError, TypeError):
        print("likely cookie/token error on POST https://develop.roblox.com/v1/assets/latest-versions, retrying", flush=True)
        refresh_csrf_token()
        try:
            return _check_published(place_id, latest_saved_version)
        except (requests.RequestException, AttributeError, IndexError, TypeError):
            print("retry with fresh token also failed", flush=True)
            return None


def send_webhook(place_id, name, version):
    print(f"posting webhook for {place_id}")

    if not WEBHOOK_URL:
        return
    url = f"https://www.roblox.com/games/{place_id}"

    payload = {
        "embeds": [{
            "title": "</> 1 game was published!",
            "description": f"**{name}**\n[Place Link]({url})\nUpdated: <t:{int(time.time())}:R>",
            "color": random.choice(EMBED_COLORS),
            "footer": {"text": f"Place ID: {place_id} • v{version}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
    }
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except requests.RequestException:
        pass

def send_start_message():
    if not WEBHOOK_URL:
        return
    payload = {
        "embeds": [{
            "title": "</> blue devi started!",
            "description": "if he was green he'd be dead",
            "color": random.choice(EMBED_COLORS),
            "footer": {"text": f"made by bamvilnous (<3 zeg)"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
    }
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except requests.RequestException:
        pass

def main():
    print("init main", flush=True)
    send_start_message()

    universe_ids = set()
    for pid in PLACE_IDS:
        universe_id = get_universe_id(pid)
        if universe_id:
            universe_ids.add(universe_id)

    state = load_state()

    print("starting scan loop", flush=True)
    while True:
        #print("running scan loop", flush=True)

        for universe_id in universe_ids:
            places = get_universe_places(universe_id)
            if not places:
                continue

            root = next((p for p in places if p.get("isRootPlace")), places[0])
            root_name = root.get("name", "Unknown game")

            for p in places:
                place_id = p["id"]
                version = get_saved_version(p)
                key = str(place_id)

                #print(f"scanning {place_id}", flush=True)
                #print(f"{state.get(key)} v {version}", flush=True)

                #published_version = is_latest_version_published(place_id, version)
                #print(published_version)

                if key in state and state[key] != version:
                    if is_latest_version_published(place_id, version):
                        send_webhook(place_id, root_name, version)

                state[key] = version

        save_state(state)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
