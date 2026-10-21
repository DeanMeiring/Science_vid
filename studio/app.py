"""Science_vid studio: watch each episode's video and post it to YouTube and Instagram.

Run:  .venv/Scripts/python studio/app.py      then open http://localhost:8765
Only listens on this laptop (127.0.0.1). Logins are kept in .tokens/ (gitignored).
"""
import json, secrets, sys, threading, time, traceback
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "pipeline"))
from common import load_env, load_episode
from publish import instagram, youtube

load_env()
PORT = 8765
BASE = f"http://localhost:{PORT}"
TOKENS = ROOT / ".tokens"
yt_store = youtube.TokenStore(TOKENS / "youtube_token.json")
ig_store = instagram.TokenStore(TOKENS / "instagram_token.json")
app = FastAPI()
_states: dict = {}           # OAuth CSRF state -> (time, which)
_jobs: dict = {}             # post job id -> {"state", "log", "result", "error"}


def _episode(name: str):
    p = ROOT / "episodes" / f"{name}.py"
    if "/" in name or "\\" in name or not p.exists():
        raise HTTPException(404, "unknown episode")
    return p, load_episode(p), ROOT / "renders" / name


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _video(d: Path, name: str):
    final, draft = d / f"{name}.mp4", d / f"{name}_draft.mp4"
    return (final, False) if final.exists() else (draft, True) if draft.exists() else (None, None)


@app.get("/", response_class=HTMLResponse)
def page():
    return (Path(__file__).parent / "studio.html").read_text(encoding="utf-8")


@app.get("/api/state")
def state():
    eps = []
    for p in sorted((ROOT / "episodes").glob("ep*.py")):
        ep = load_episode(p); d = ROOT / "renders" / p.stem
        video, draft = _video(d, p.stem)
        saved = _read(d / "post.json", {})
        frames = len(list((d / "frames").glob("f_*.jpg"))) if (d / "frames").exists() else 0
        tm = _read(d / "timing.json", {})
        eps.append({"name": p.stem, "experiment": getattr(ep, "EXPERIMENT", None),
                    "title": saved.get("title", getattr(ep, "TITLE", p.stem)),
                    "description": saved.get("description", getattr(ep, "DESCRIPTION", "")),
                    "video": f"/video/{p.stem}?v={int(video.stat().st_mtime)}" if video else None,
                    "draft": draft, "duration": tm.get("duration"),
                    "frames": frames, "frames_total": int(tm.get("duration", 0) * 30),
                    "posted": _read(d / "posted.json", {})})
    return {"episodes": eps,
            "youtube": {**yt_store.status(), "configured": youtube.is_configured()},
            "instagram": {**ig_store.status(), "configured": instagram.is_configured()}}


@app.get("/video/{name}")
def video(name: str):
    _, _, d = _episode(name)
    v, _ = _video(d, name)
    if not v: raise HTTPException(404, "not rendered yet")
    return FileResponse(v, media_type="video/mp4")


class Draft(BaseModel):
    title: str
    description: str


@app.post("/api/episode/{name}/save")
def save(name: str, body: Draft):
    _, _, d = _episode(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "post.json").write_text(json.dumps(body.model_dump(), indent=1), encoding="utf-8")
    return {"ok": True}


# ---------- logins ----------
def _new_state(which):
    for s, (t, _) in list(_states.items()):
        if t < time.time() - 600: _states.pop(s, None)
    s = secrets.token_urlsafe(24); _states[s] = (time.time(), which)
    return s


def _take_state(state, which):
    got = _states.pop(state, None)
    if not got or got[1] != which or time.time() - got[0] > 600:
        raise HTTPException(400, "Login attempt expired -- press Connect again.")


@app.get("/auth/youtube/login")
def yt_login():
    if not youtube.is_configured():
        raise HTTPException(400, "Add YOUTUBE_OAUTH_CLIENT_ID and YOUTUBE_OAUTH_CLIENT_SECRET to .env first.")
    return RedirectResponse(youtube.authorize_url(f"{BASE}/auth/youtube/callback", _new_state("yt")))


@app.get("/auth/youtube/callback")
def yt_callback(code: str = "", state: str = "", error: str = ""):
    if error: return RedirectResponse(f"/?error={error}")
    _take_state(state, "yt")
    token = youtube.exchange_code(code, f"{BASE}/auth/youtube/callback")
    try:
        token["channel"] = youtube.own_channel(token["access_token"])
    except Exception:
        pass
    yt_store.save(token)
    return RedirectResponse("/?connected=youtube")


@app.get("/auth/instagram/login")
def ig_login():
    if not instagram.is_configured():
        raise HTTPException(400, "Add INSTAGRAM_APP_ID and INSTAGRAM_APP_SECRET to .env first.")
    return RedirectResponse(instagram.authorize_url(f"{BASE}/auth/instagram/callback", _new_state("ig")))


@app.get("/auth/instagram/callback")
def ig_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    if error or not code: return RedirectResponse(f"/?error={error or 'no_code'}")
    _take_state(state, "ig")
    try:
        ig_store.save(instagram.exchange_code(code.split("#")[0], f"{BASE}/auth/instagram/callback"))
    except instagram.InstagramError as e:
        from urllib.parse import quote
        return RedirectResponse(f"/?error={quote(str(e)[:300])}")
    return RedirectResponse("/?connected=instagram")


@app.post("/api/disconnect/{which}")
def disconnect(which: str):
    {"youtube": yt_store, "instagram": ig_store}[which].clear()
    return {"ok": True}


# ---------- posting (runs in the background; the page polls the job) ----------
class Post(BaseModel):
    title: str
    description: str
    privacy: str = "private"
    publish_at: str = ""        # RFC 3339 UTC, schedules a YouTube upload
    synthetic: bool = False


def _run(job_id, fn):
    job = _jobs[job_id]
    try:
        job["result"] = fn(lambda *a: job["log"].append(" ".join(map(str, a))))
        job["state"] = "done"
    except Exception as e:
        traceback.print_exc()
        job["error"] = str(e); job["state"] = "error"


def _start(fn):
    job_id = secrets.token_hex(6)
    _jobs[job_id] = {"state": "running", "log": [], "result": None, "error": None}
    threading.Thread(target=_run, args=(job_id, fn), daemon=True).start()
    return {"job": job_id}


def _mark(d: Path, key: str, value: dict):
    posted = _read(d / "posted.json", {}); posted[key] = {**value, "at": time.strftime("%Y-%m-%d %H:%M")}
    (d / "posted.json").write_text(json.dumps(posted, indent=1), encoding="utf-8")


@app.post("/api/episode/{name}/youtube")
def post_youtube(name: str, body: Post):
    _, _, d = _episode(name)
    v, draft = _video(d, name)
    if not v or draft: raise HTTPException(400, "Only the finished video can be posted (not the draft).")
    token = yt_store.access_token()
    if not token: raise HTTPException(400, "Connect YouTube first.")
    save(name, Draft(title=body.title, description=body.description))
    def work(log):
        try:   # the channel may have been renamed since connecting (1 quota unit)
            ch = youtube.own_channel(token)
            if ch:
                data = yt_store.load(); data["channel"] = ch; yt_store.path.write_text(json.dumps(data))
                log("channel:", ch["title"])
        except Exception:
            pass
        log("uploading", v.name)
        vid = youtube.upload_video(token, v, body.title, body.description, body.privacy,
                                   body.synthetic, body.publish_at or None)
        log("uploaded", vid)
        thumb = v.with_suffix(".jpg")
        if thumb.exists():
            try:
                youtube.set_thumbnail(token, vid, thumb); log("thumbnail set")
            except youtube.UploadError as e:
                log("thumbnail skipped:", e)
        res = {"id": vid, "url": f"https://youtube.com/shorts/{vid}",
               "privacy": "scheduled" if body.publish_at else body.privacy}
        _mark(d, "youtube", res)
        return res
    return _start(work)


@app.post("/api/episode/{name}/instagram")
def post_instagram(name: str, body: Post):
    _, _, d = _episode(name)
    v, draft = _video(d, name)
    if not v or draft: raise HTTPException(400, "Only the finished video can be posted (not the draft).")
    token = ig_store.load()
    if not token: raise HTTPException(400, "Connect Instagram first.")
    save(name, Draft(title=body.title, description=body.description))
    def work(log):
        res = instagram.publish_reel(token, v, instagram.caption_for(body.title, body.description), log=log)
        res["url"] = res.get("permalink")
        _mark(d, "instagram", res)
        return res
    return _start(work)


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    if job_id not in _jobs: raise HTTPException(404, "unknown job")
    return _jobs[job_id]


if __name__ == "__main__":
    import uvicorn
    print(f"Science_vid studio: {BASE}")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
