"""Post a finished Short as an Instagram Reel.

Login copied from CLIPPER (clipper/instagram.py, "facebook" mode): the Instagram
professional account is linked to a Facebook Page; signing in with Facebook keeps the
Page's token (it doesn't expire) and the linked Instagram account's id.

Unlike CLIPPER (which gives Instagram a public URL to download), this runs on a laptop
with no public address, so it uses the resumable upload: create a container with
upload_type=resumable, send the file to rupload.facebook.com, wait until it's FINISHED,
then publish. That route needs Facebook Login (not Instagram Login).

Setup (.env): INSTAGRAM_APP_ID / INSTAGRAM_APP_SECRET (the Meta app's id and secret;
CLIPPER's app works), INSTAGRAM_USERNAME (which account to post to, when the
Facebook login manages several), optional INSTAGRAM_FB_CONFIG_ID, and the redirect URI
http://localhost:8765/auth/instagram/callback allowed in the app's Facebook Login settings.
Limit: 100 API posts per account per 24 hours.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

API_VERSION = "v25.0"
FB_DIALOG = f"https://www.facebook.com/{API_VERSION}/dialog/oauth"
FB_GRAPH = f"https://graph.facebook.com/{API_VERSION}"
RUPLOAD = f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}"
FB_SCOPES = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement,business_management"
CAPTION_MAX = 2200


class InstagramError(Exception):
    pass


def is_configured() -> bool:
    return bool(os.environ.get("INSTAGRAM_APP_ID") and os.environ.get("INSTAGRAM_APP_SECRET"))


def authorize_url(redirect_uri: str, state: str) -> str:
    params = {"client_id": os.environ["INSTAGRAM_APP_ID"], "redirect_uri": redirect_uri,
              "response_type": "code", "state": state}
    config = os.environ.get("INSTAGRAM_FB_CONFIG_ID", "").strip()
    if config:
        params["config_id"] = config        # Facebook Login for Business configuration
    else:
        params["scope"] = FB_SCOPES
    return FB_DIALOG + "?" + urlencode(params)


def _check(resp) -> dict:
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if resp.status_code >= 400 or "error" in data:
        err = data.get("error") if isinstance(data.get("error"), dict) else {}
        msg = err.get("error_user_msg") or err.get("message") or resp.text[:300] or f"HTTP {resp.status_code}"
        if err.get("code") == 190:
            msg = "The Instagram connection has expired or was removed -- connect it again. (" + msg + ")"
        raise InstagramError(msg)
    return data


def exchange_code(code: str, redirect_uri: str) -> dict:
    """Code -> user token -> long-lived user token -> the Page token of the first Page
    with a linked Instagram professional account."""
    import requests
    app = {"client_id": os.environ["INSTAGRAM_APP_ID"], "client_secret": os.environ["INSTAGRAM_APP_SECRET"]}
    short = _check(requests.get(f"{FB_GRAPH}/oauth/access_token", params={
        **app, "redirect_uri": redirect_uri, "code": code}, timeout=30))["access_token"]
    long = _check(requests.get(f"{FB_GRAPH}/oauth/access_token", params={
        **app, "grant_type": "fb_exchange_token", "fb_exchange_token": short}, timeout=30))["access_token"]
    pages = _check(requests.get(f"{FB_GRAPH}/me/accounts", params={
        "fields": "id,name,access_token,instagram_business_account{id,username}",
        "access_token": long, "limit": 100}, timeout=30)).get("data") or []
    linked = [p for p in pages if p.get("instagram_business_account")]
    if not linked:
        names = ", ".join(p.get("name", "?") for p in pages) or "none"
        raise InstagramError("None of your Facebook Pages has an Instagram professional account linked "
                             f"(Pages the app can see: {names}). Link the Instagram account to a Page "
                             "(Page settings -> Linked accounts -> Instagram) and connect again.")
    # Several Pages can have Instagram linked (e.g. CLIPPER's): never guess, pick the one in .env
    want = os.environ.get("INSTAGRAM_USERNAME", "").strip().lstrip("@").lower()
    if want:
        linked = [p for p in linked if (p["instagram_business_account"].get("username") or "").lower() == want]
        if not linked:
            raise InstagramError(f"@{want} wasn't among the Instagram accounts Facebook shared. Connect again and "
                                 "tick its Page (and the Instagram account) when Facebook asks.")
    elif len(linked) > 1:
        names = ", ".join("@" + (p["instagram_business_account"].get("username") or "?") for p in linked)
        raise InstagramError(f"Facebook shared several Instagram accounts ({names}). Set INSTAGRAM_USERNAME in .env "
                             "to the one to post to, then connect again.")
    page = linked[0]; ig = page["instagram_business_account"]
    return {"access_token": page["access_token"], "obtained_at": time.time(),
            "ig_id": str(ig["id"]), "username": ig.get("username"), "page": page.get("name")}


class TokenStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def load(self) -> Optional[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    def status(self) -> dict:
        data = self.load()
        return {"connected": bool(data), "username": (data or {}).get("username")}


def caption_for(title: str, description: str) -> str:
    """Title + description as a caption, without the YouTube-only #Shorts tag."""
    text = "\n\n".join(p for p in ((title or "").strip(), (description or "").strip()) if p)
    return re.sub(r"(?i)[ \t]*#shorts\b", "", text).strip()[:CAPTION_MAX]


def publish_reel(token: dict, video_path: Path, caption: str, log=None, poll: float = 8.0,
                 timeout: float = 900.0) -> dict:
    """Upload a local mp4 as a Reel and publish it. Returns {"media_id", "permalink"}.
    Blocks while Instagram processes the video (usually a minute or two)."""
    import requests
    log = log or (lambda *_: None)
    auth = {"Authorization": f"OAuth {token['access_token']}"}
    ig = token["ig_id"]
    container = _check(requests.post(f"{FB_GRAPH}/{ig}/media", headers=auth, data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption[:CAPTION_MAX],
        "share_to_feed": "true"}, timeout=60))["id"]
    log("container", container)
    size = video_path.stat().st_size
    with video_path.open("rb") as f:
        up = requests.post(f"{RUPLOAD}/{container}", data=f, timeout=900,
                           headers={**auth, "offset": "0", "file_size": str(size)})
    if not _check(up).get("success"):
        raise InstagramError(f"Instagram didn't accept the upload: {up.text[:300]}")
    log("uploaded", size)
    deadline = time.time() + timeout
    while True:
        st = _check(requests.get(f"{FB_GRAPH}/{container}", headers=auth,
                                 params={"fields": "status_code,status"}, timeout=30))
        code = st.get("status_code"); log("status", code)
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Instagram couldn't process the video: {st.get('status') or code}")
        if time.time() > deadline:
            raise InstagramError("Instagram took too long to process the video -- try again later.")
        time.sleep(poll)
    media_id = _check(requests.post(f"{FB_GRAPH}/{ig}/media_publish", headers=auth,
                                    data={"creation_id": container}, timeout=60))["id"]
    permalink = None
    try:
        permalink = _check(requests.get(f"{FB_GRAPH}/{media_id}", headers=auth,
                                        params={"fields": "permalink"}, timeout=30)).get("permalink")
    except InstagramError:
        pass
    return {"media_id": media_id, "permalink": permalink}
