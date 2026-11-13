# Real-Debrid unrestrict — uses the token from the addon settings only.
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def unrestrict(token, link):
    body = urlencode({"link": link}).encode("utf-8")
    req = Request("https://api.real-debrid.com/rest/1.0/unrestrict/link", data=body,
                  headers={"Authorization": "Bearer " + token})
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("download")
    except Exception:
        return None
