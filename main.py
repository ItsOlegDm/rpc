import random
import requests
from pypresence import Presence
import threading
import time


JELLYFIN_SERVER = "http://localhost:8096"
JELLYFIN_PUBLIC_SERVER = "https://jelly.itsolegdm.com"
JELLY_ACCESS_TOKEN = ""
JELLY_CLIENT_ID = "1289639826936565790"
JELLY_USERNAME = "ItsOlegDm"

PM_CLIENT_ID = "868791075316326451"


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


def update_rpc():
    inactive_timer = 0
    inactivity_threshold = 60
    rpc = Presence(JELLY_CLIENT_ID)
    rpc_cleared = False

    try:
        rpc.connect()
    except Exception as e:
        print(f"Failed to connect to Discord RPC: {e}")
        return

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
                            rpc_cleared = False
                            break

            if not has_playing_session:
                inactive_timer += 15
                rpc.update()
                if inactive_timer >= inactivity_threshold and not rpc_cleared:
                    print("Disconnecting due to inactivity...")
                    rpc.clear()
                    rpc.close()
                    rpc_cleared = True
        except Exception as e:
            print(f"Error during playback check or Discord update: {e}")

        time.sleep(15)


def pm_rpc():
    rpc = Presence(PM_CLIENT_ID)
    rpc.connect()
    buttons = [
                {
                    "label": "AniList",
                    "url": "https://anilist.co/anime/20872/Plastic-Memories"
                },
                {
                    "label": "Shikimori",
                    "url": "https://shikimori.one/animes/y27775-plastic-memories"
                }
            ]

    while True:
        rpc.update(
            state="- I hope one day you'll be reunited with the one you cherish...",
            large_image=f"isla__{random.randint(0, 17)}",
            buttons=buttons
        )
        time.sleep(900)


if __name__ == "__main__":
    jelly_rpc = threading.Thread(target=update_rpc)
    jelly_rpc.start()

    plamemo_rpc = threading.Thread(target=pm_rpc)
    plamemo_rpc.start()
    plamemo_rpc.join()
