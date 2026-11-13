# Internet Archive — Kodi Addon v1.0.0 — Kodi 21 Omega video addon
# Browse, search and play Internet Archive items; favorites are kept on
# this device; optional Real-Debrid resolving using the token YOU enter
# in the addon settings.
import json
import os
import sys
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib import archive, realdebrid

ADDON = xbmcaddon.Addon()
ADDON_HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]
PAGE_SIZE = 50


COLLECTIONS = [
    ("Movies", "movies"),
    ("Feature Films", "feature_films"),
    ("Animation & Cartoons", "animationandcartoons"),
    ("TV", "television"),
    ("Concerts & Live Music", "opensource_audio"),
    ("Classic TV Commercials", "classic_tv_commercials"),
]


def build_url(query):
    return BASE_URL + "?" + urlencode(query)


def _fav_path():
    folder = xbmcvfs.translatePath(ADDON.getAddonInfo("profile"))
    if not xbmcvfs.exists(folder):
        xbmcvfs.mkdirs(folder)
    return os.path.join(folder, "favorites.json")


def load_favorites():
    try:
        with open(_fav_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_favorites(favs):
    try:
        with open(_fav_path(), "w", encoding="utf-8") as fh:
            json.dump(favs, fh)
    except Exception:
        pass


def _item_li(row):
    identifier = row.get("identifier")
    label = row.get("title") or identifier
    li = xbmcgui.ListItem(label=label)
    li.setInfo("video", {"title": label, "plot": row.get("description", ""), "year": row.get("year")})
    art = "https://archive.org/services/img/" + identifier
    li.setArt({"thumb": art, "icon": art, "fanart": art})
    li.setProperty("IsPlayable", "true")
    li.addContextMenuItems([
        ("Add to Favorites", "RunPlugin(" + build_url({"mode": "fav_add", "id": identifier, "title": label}) + ")"),
    ])
    return li


def root_menu():
    items = [
        ("Search the Archive", {"mode": "search"}, True),
        ("Most Downloaded This Week", {"mode": "top"}, True),
        ("My Favorites", {"mode": "favorites"}, True),
    ]
    items += [(label, {"mode": "browse", "collection": cid, "title": label}, True) for label, cid in COLLECTIONS]
    for label, query, is_folder in items:
        li = xbmcgui.ListItem(label=label)
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, build_url(query), li, isFolder=is_folder)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def list_items(query, title, page=1, sort=None):
    sort = sort or ADDON.getSetting("sort_order") or "relevance"
    rows = archive.search(query, rows=PAGE_SIZE, page=page, sort=sort)
    for row in rows:
        if not row.get("identifier"):
            continue
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, build_url({"mode": "play", "id": row["identifier"]}), _item_li(row), isFolder=False)
    if len(rows) == PAGE_SIZE:
        li = xbmcgui.ListItem(label=">> Next page")
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, build_url({"mode": "page", "q": query, "title": title, "page": page + 1, "sort": sort}), li, isFolder=True)
    xbmcplugin.setContent(ADDON_HANDLE, "videos")
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def do_search():
    kb = xbmc.Keyboard("", "Search Internet Archive")
    kb.doModal()
    if kb.isConfirmed() and kb.getText():
        list_items('title:("' + kb.getText() + '") AND mediatype:movies', "Search results")


def list_favorites():
    favs = load_favorites()
    if not favs:
        xbmcgui.Dialog().notification("Internet Archive — Kodi Addon", "No favorites yet — use the context menu on any title", xbmcgui.NOTIFICATION_INFO)
    for fav in favs:
        li = _item_li({"identifier": fav.get("id", ""), "title": fav.get("title", "")})
        li.addContextMenuItems([
            ("Remove from Favorites", "RunPlugin(" + build_url({"mode": "fav_remove", "id": fav.get("id", "")}) + ")"),
        ], replaceItems=True)
        xbmcplugin.addDirectoryItem(ADDON_HANDLE, build_url({"mode": "play", "id": fav.get("id", "")}), li, isFolder=False)
    xbmcplugin.setContent(ADDON_HANDLE, "videos")
    xbmcplugin.endOfDirectory(ADDON_HANDLE)


def play(identifier):
    files = archive.playable_files(identifier)
    if not files:
        xbmcgui.Dialog().notification("Internet Archive — Kodi Addon", "No playable file found for this item", xbmcgui.NOTIFICATION_WARNING)
        return
    url = files[0]
    # If the user added their own Real-Debrid token, resolve through it.
    token = ADDON.getSetting("rd_token")
    if token:
        resolved = realdebrid.unrestrict(token, url)
        if resolved:
            url = resolved
    li = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, li)


def router(params):
    mode = params.get("mode")
    if mode == "search":
        do_search()
    elif mode == "browse":
        collection = params.get("collection", "movies")
        list_items("collection:" + collection + " AND mediatype:movies", params.get("title", "Browse"))
    elif mode == "top":
        list_items("mediatype:movies", "Most Downloaded", sort="downloads")
    elif mode == "page":
        list_items(params.get("q", "mediatype:movies"), params.get("title", "Browse"), page=int(params.get("page", "1")), sort=params.get("sort") or None)
    elif mode == "favorites":
        list_favorites()
    elif mode == "fav_add":
        favs = load_favorites()
        if not any(f.get("id") == params.get("id") for f in favs):
            favs.append({"id": params.get("id", ""), "title": params.get("title", "")})
            save_favorites(favs)
        xbmcgui.Dialog().notification("Internet Archive — Kodi Addon", "Added to Favorites", xbmcgui.NOTIFICATION_INFO)
    elif mode == "fav_remove":
        save_favorites([f for f in load_favorites() if f.get("id") != params.get("id")])
        xbmc.executebuiltin("Container.Refresh")
    elif mode == "play":
        play(params.get("id", ""))
    else:
        root_menu()


if __name__ == "__main__":
    router(dict(parse_qsl(sys.argv[2][1:])))
