import random
import requests
from pypresence import Presence
import threading
import time
import os
import json

JELLYFIN_SERVER = "http://192.168.1.115:8096"
JELLYFIN_PUBLIC_SERVER = "https://jelly.itsolegdm.com"
JELLY_ACCESS_TOKEN = ""
JELLY_APP_ID = "1289639826936565790"
JELLY_USERNAME = "ItsOlegDm"


ABS_SERVER = "https://audiobooks.itsolegdm.com/"
ABS_TOKEN = ""
ABS_APP_ID = "1370801035156918362"

PM_APP_ID = "868791075316326451"
START_TIME_FILE = "start_time_sf.json"

def save_start_time(start_time):
    with open(START_TIME_FILE, "w") as f:
        json.dump({"start_time": start_time}, f)

def load_start_time():
    if os.path.exists(START_TIME_FILE):
        with open(START_TIME_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("start_time")
            except json.JSONDecodeError:
                return None
    return None

def get_current_playback():
    headers = {
        "X-Emby-Token": JELLY_ACCESS_TOKEN
    }
    response = requests.get(f"{JELLYFIN_SERVER}/Sessions", headers=headers)
    response.raise_for_status()
    return response.json()

def get_episode(series_id, episode_id):
    response = requests.get(f"{JELLYFIN_SERVER}/Shows/{series_id}/Episodes",
                            headers={"X-Emby-Token": JELLY_ACCESS_TOKEN}).json()
    episode_index = -1

    for index, item in enumerate(response['Items']):
        if item['Id'] == episode_id:
            episode_index = index
            break
    return (episode_index, len(response['Items']))


def get_external_links(series_id):
    response = requests.get(f"{JELLYFIN_SERVER}/Items?ids={series_id}&fields=ExternalUrls",
                            headers={"X-Emby-Token": JELLY_ACCESS_TOKEN}).json()
    return response["Items"][0]["ExternalUrls"]


def convert_external_links_to_buttons(input_list):
    limited_list = input_list[:2]
    btns = [{"label": item["Name"], "url": item["Url"]} for item in limited_list]
    return btns


def jelly_update_rpc():
    inactive_timer = 0
    inactivity_threshold = 60
    rpc = Presence(JELLY_APP_ID)
    rpc_closed = True

    while True:
        try:
            playback_info = get_current_playback()
            has_playing_session = False
            external_links = name = description = banner_url = time_left = None

            if playback_info:
                for session in playback_info:
                    if session.get("UserName") == JELLY_USERNAME:
                        if session.get("NowPlayingItem"):
                            item_type = session["NowPlayingItem"].get("Type")

                            if item_type == "Episode":
                                series_id = session["NowPlayingItem"].get("SeriesId")
                                episode_id = session["NowPlayingItem"].get("Id")
                                name = session["NowPlayingItem"].get("SeriesName")
                                banner_image_tag = session["NowPlayingItem"].get("SeriesPrimaryImageTag")
                                external_links = get_external_links(series_id)
                                banner_url = f"{JELLYFIN_PUBLIC_SERVER}/Items/{series_id}/Images/Primary?tag={banner_image_tag}" if banner_image_tag else None
                                episode = get_episode(series_id=series_id, episode_id=episode_id)
                                description = f"{episode[0]+1}/{episode[1]}" if episode[1] > 1 else None

                            elif item_type == "Movie":
                                name = session["NowPlayingItem"].get("Name")
                                movie_id = session["NowPlayingItem"].get("Id")
                                banner_image_tag = session["NowPlayingItem"].get("ImageTags").get("Primary")
                                banner_url = f"{JELLYFIN_PUBLIC_SERVER}/Items/{movie_id}/Images/Primary?tag={banner_image_tag}" if banner_image_tag else None
                                external_links = get_external_links(movie_id)

                            elif item_type == "Audio":
                                name = session["NowPlayingItem"].get("Name")
                                music_id = session["NowPlayingItem"].get("AlbumId")
                                banner_image_tag = session["NowPlayingItem"].get("AlbumPrimaryImageTag")
                                banner_url = f"{JELLYFIN_PUBLIC_SERVER}/Items/{music_id}/Images/Primary?tag={banner_image_tag}" if banner_image_tag else None
                                external_links = get_external_links(music_id)
                                description = session["NowPlayingItem"].get("Album")

                            progress = session.get("PlayState").get("PositionTicks")
                            length = session.get("NowPlayingItem").get("RunTimeTicks")

                            if progress and length:
                                time_left = (length - progress) / 10_000_000
                            is_paused = session.get("PlayState").get("IsPaused")
                            if rpc_closed:
                                rpc.connect()
                                rpc_closed = False
                            rpc.update(
                                state=description,
                                details=name,
                                large_image=banner_url if banner_url else "jelly",
                                buttons=convert_external_links_to_buttons(external_links) if external_links else None,
                                start=int(time.time()) if time_left and not is_paused else None,
                                end=int(time.time()) + time_left if time_left and not is_paused else None
                            )

                            has_playing_session = True
                            inactive_timer = 0
                            break

            if not has_playing_session:
                inactive_timer += 15
                if not rpc_closed:
                    rpc.clear()
                    if inactive_timer >= inactivity_threshold:
                        print("Disconnecting due to inactivity...")
                        rpc.close()
                        rpc_closed = True
        except Exception as e:
            # raise e
            print(f"Error during playback check or Discord update: {e}")

        time.sleep(15)


def pm_rpc():
    rpc = Presence(PM_APP_ID)
    start_time = load_start_time()
    if not start_time:
        start_time = int(time.time())
        save_start_time(start_time)
    try:
        rpc.connect()
        buttons = [
            {
                "label": "Join",
                "url": "app://jp.utopia.sf/joinparty/394786234"
            }
        ]

        while True:
            try:
                rpc.update(
                    details = "Thirdrema",
                    state="AFK",
                    large_image=f"sf",
                    start=start_time,
                    buttons=buttons
                )
            except BrokenPipeError:
                rpc.connect()
                continue
            time.sleep(900)
    except Exception as e:
        print(e)
        time.sleep(10)
        pm_rpc()

def format_time(seconds: float) -> str:
    s = int(seconds)
    h, m = divmod(s, 3600)
    m, s = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"

def get_current_listening_info_abs() -> dict:
    headers = {'Authorization': f'Bearer {ABS_TOKEN}'}
    url = f'{ABS_SERVER}/api/me/listening-sessions'
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        now = int(time.time() * 1000)
        for s in data.get("sessions", []):
            if now - s.get("updatedAt", 0) < 60000:
                m = s.get("mediaMetadata", {})
                cur = s.get("currentTime", 0)
                dur = s.get("duration", 0)
                start_ts = s.get("startedAt", 0)
                end_ts = start_ts + int(dur * 1000)
                return {
                    "title": m.get("title") or "",
                    "series": m.get("series", [{}])[0].get("name") or "",
                    "author": s.get("displayAuthor") or "",
                    "cover": ABS_SERVER + f"/audiobookshelf/api/items/{s.get('libraryItemId')}/cover" if s.get("coverPath") and s.get('libraryItemId') else "",
                    "current_time": format_time(cur),
                    "duration": format_time(dur),
                    "start_time": start_ts,
                    "end_time": end_ts
                }
    except:
        pass
    return {}

def abs_update_rpc():
    rpc_closed = True
    rpc = Presence(ABS_APP_ID)
    while True:
        status = get_current_listening_info_abs()
        if not status or not status.get("title"):
            if not rpc_closed:
                rpc.clear()
                rpc.close()
                rpc_closed = True
            time.sleep(10)
            continue

        if rpc_closed:
            rpc.connect()
            rpc_closed = False
        series = status.get("series")
        title = status.get("title", "")
        author = status.get("author"),
        if series:
            if series in title:
                title = title.replace(series, "")
                if any(title.startswith(x) for x in (" ", ",", ".")):
                    title = title.lstrip(" ,.")
                title = title.capitalize()
            if author:
                series = f"{', '.join(author)}, {series}"
        else:
            series = title
            title = None

        rpc.update(
            state=title,
            details=series,
            large_image= status.get("cover") if status.get("cover") else "logo",
            start=status.get("start_time"),
            end=status.get("end_time"),
        )
        time.sleep(5)



if __name__ == "__main__":
    jelly_rpc = threading.Thread(target=jelly_update_rpc)
    jelly_rpc.start()

    abs_rpc = threading.Thread(target=abs_update_rpc)
    abs_rpc.start()

    plamemo_rpc = threading.Thread(target=pm_rpc)
    plamemo_rpc.start()
    plamemo_rpc.join()
