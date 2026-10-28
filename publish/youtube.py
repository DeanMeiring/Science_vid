"""Post a finished Short to the connected YouTube channel.

Copied from CLIPPER (clipper/youtube_oauth.py + clipper/youtube_upload.py) and trimmed:
OAuth login with a stored refresh token, then the Data API v3 resumable upload.

Setup (.env): YOUTUBE_OAUTH_CLIENT_ID / YOUTUBE_OAUTH_CLIENT_SECRET from a Google Cloud
OAuth "Web application" client with the redirect URI http://localhost:8765/auth/youtube/callback
(CLIPPER's client works too once that URI is added to it).

An upload costs 1,600 of the default 10,000 daily quota units: one deliberate click per
video, never a loop.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Optional

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]
SCIENCE_CATEGORY_ID = "28"          # Science & Technology
DESCRIPTION_MAX = 5000


class UploadError(RuntimeError):
    """Message is safe to show as-is."""


def is_configured() -> bool:
    return bool(os.environ.get("YOUTUBE_OAUTH_CLIENT_ID") and os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET"))


def authorize_url(redirect_uri: str, state: str) -> str:
    return AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": os.environ["YOUTUBE_OAUTH_CLIENT_ID"], "redirect_uri": redirect_uri,
        "response_type": "code", "scope": " ".join(SCOPES), "access_type": "offline",
        # always hand back a refresh token, and always ask which account (or brand channel)
        "prompt": "consent select_account", "state": state})


def _token_request(data: dict) -> dict:
    import requests
    resp = requests.post(TOKEN_URL, data={"client_id": os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
                                          "client_secret": os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"], **data},
                         timeout=15)
    resp.raise_for_status()
    return resp.json()


def exchange_code(code: str, redirect_uri: str) -> dict:
    return _token_request({"code": code, "redirect_uri": redirect_uri, "grant_type": "authorization_code"})


def own_channel(access_token: str) -> Optional[dict]:
    """The connected channel's id and title (1 quota unit)."""
    import requests
    r = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                     headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    items = r.json().get("items") if r.ok else None
    return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]} if items else None


class TokenStore:
    """The one stored token, refreshed when it's (nearly) expired."""

    def __init__(self, path: Path):
        self.path = path

    def save(self, token: dict) -> None:
        data = dict(token); data["obtained_at"] = time.time()
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
        if not data or not data.get("refresh_token"):
            return {"connected": False}
        return {"connected": True, "channel": (data.get("channel") or {}).get("title")}

    def access_token(self) -> Optional[str]:
        data = self.load()
        if not data or not data.get("refresh_token"):
            return None
        if time.time() < data.get("obtained_at", 0) + data.get("expires_in", 0) - 60:
            return data["access_token"]
        try:
            fresh = _token_request({"refresh_token": data["refresh_token"], "grant_type": "refresh_token"})
        except Exception:
            return None
        fresh.setdefault("refresh_token", data["refresh_token"])
        if data.get("channel"): fresh["channel"] = data["channel"]
        self.save(fresh)
        return fresh["access_token"]


def with_shorts_tag(description: str) -> str:
    """API uploads only reliably land in Shorts with #Shorts in the title or description."""
    if re.search(r"#shorts\b", description, re.IGNORECASE):
        return description[:DESCRIPTION_MAX]
    suffix = "\n\n#Shorts"
    return description[:DESCRIPTION_MAX - len(suffix)] + suffix


def _unauthorized_message(resp) -> str:
    try:
        err = resp.json().get("error") or {}
    except ValueError:
        err = {}
    reasons = {e.get("reason") for e in err.get("errors") or [] if isinstance(e, dict)}
    if "youtubeSignupRequired" in reasons:
        return ("The connected Google account has no YouTube channel. Reconnect and pick the account "
                "(or the channel's brand account) that owns the channel.")
    detail = f" (YouTube said: {err.get('message')})" if err.get("message") else ""
    return "YouTube didn't accept the connection -- reconnect and try again." + detail


def upload_video(access_token: str, video_path: Path, title: str, description: str,
                 privacy_status: str = "private", synthetic_media: bool = False,
                 publish_at: Optional[str] = None) -> str:
    """Upload as a Short; returns the video id. `publish_at` (RFC 3339, UTC) schedules it:
    uploaded private, YouTube makes it public at that time by itself.
    `synthetic_media` ticks YouTube's "altered or synthetic content" box."""
    import requests

    if privacy_status not in ("public", "unlisted", "private"):
        raise ValueError(f"invalid privacy_status: {privacy_status!r}")
    if not video_path.exists():
        raise UploadError(f"{video_path.name} doesn't exist")
    size = video_path.stat().st_size
    status = {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False,
              "containsSyntheticMedia": bool(synthetic_media)}
    if publish_at:
        status["privacyStatus"] = "private"; status["publishAt"] = publish_at
    try:
        init = requests.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                             headers={"Authorization": f"Bearer {access_token}",
                                      "Content-Type": "application/json; charset=UTF-8",
                                      "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                             json={"snippet": {"title": title[:100], "description": with_shorts_tag(description),
                                               "categoryId": SCIENCE_CATEGORY_ID},
                                   "status": status}, timeout=30)
    except requests.RequestException as e:
        raise UploadError(f"Could not reach YouTube to start the upload: {e}") from e
    if init.status_code == 401:
        raise UploadError(_unauthorized_message(init))
    if init.status_code == 403:
        raise UploadError("YouTube refused the upload: reconnect to grant upload access, "
                          "or today's upload quota is used up.")
    if init.status_code != 200 or not init.headers.get("Location"):
        raise UploadError(f"Could not start the upload ({init.status_code}): {init.text[:500]}")
    try:
        with video_path.open("rb") as f:
            put = requests.put(init.headers["Location"], data=f,
                               headers={"Content-Type": "video/mp4", "Content-Length": str(size)}, timeout=900)
    except requests.RequestException as e:
        raise UploadError(f"Upload to YouTube failed partway through: {e}") from e
    if put.status_code not in (200, 201):
        raise UploadError(f"Upload failed ({put.status_code}): {put.text[:500]}")
    vid = (put.json() or {}).get("id")
    if not vid:
        raise UploadError(f"Upload seemed to finish but YouTube returned no video id: {put.text[:500]}")
    return vid


def set_thumbnail(access_token: str, video_id: str, image_path: Path) -> None:
    """Custom thumbnail (JPEG under 2 MB). Needs a phone-verified channel; a 403 says so."""
    import requests
    resp = requests.post("https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
                         params={"videoId": video_id, "uploadType": "media"},
                         headers={"Authorization": f"Bearer {access_token}", "Content-Type": "image/jpeg"},
                         data=image_path.read_bytes(), timeout=120)
    if resp.status_code == 403:
        raise UploadError("YouTube didn't allow a custom thumbnail: verify the channel with your phone "
                          "(YouTube Studio -> Settings -> Channel -> Feature eligibility).")
    if resp.status_code not in (200, 201):
        raise UploadError(f"Couldn't set the thumbnail ({resp.status_code}): {resp.text[:300]}")
