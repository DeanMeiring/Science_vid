"""Agent desk: ask Claude Code and Codex from one page, on this laptop only.

Usage: .venv/Scripts/python desk/app.py      # then open http://localhost:8770

- Ask Claude, Codex or both the same question, with files attached (saved in desk/uploads/).
- "You two talk to each other": Claude and Codex take turns on a topic, each reading the conversation so far.
- Read-only by default: Claude runs with --permission-mode dontAsk (anything not already allowed is refused),
  Codex with --sandbox read-only. "Allow file edits" switches to acceptEdits / workspace-write. Pushing,
  merging and posting are never done from here (the prompt says so, and Claude's git push is blocked).
- Listens on 127.0.0.1 only: both agents can read the repo, so this page must never be on the internet.
- History is kept in desk/history.jsonl (gitignored).
- "Chat with Claude": live chats that remember the conversation, show every step, and ask permission with
  buttons on the page (desk/claude_chat.py, the Claude Agent SDK; chats kept in desk/chats.json, gitignored).
"""
import asyncio, base64, json, os, re, shutil, subprocess, sys, threading, time, uuid
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat as CC

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPLOADS = HERE / "uploads"; UPLOADS.mkdir(exist_ok=True)
HISTORY = HERE / "history.jsonl"
PORT = 8770
TIMEOUT = 15 * 60                     # seconds per answer
LOW = 0x00004000 if sys.platform == "win32" else 0      # below-normal priority (gentle on the laptop)
IMAGE = (".png", ".jpg", ".jpeg", ".gif", ".webp")

def find_codex():
    exe = shutil.which("codex")
    if exe: return exe
    for p in (Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages").glob("OpenAI.Codex*/codex-*windows*.exe"):
        return str(p)
    return None
AGENTS = {"claude": shutil.which("claude"), "codex": find_codex()}
NAME = {"claude": "Claude", "codex": "Codex"}
ABOUT = {"claude": "Claude Code, Anthropic's coding agent", "codex": "Codex, OpenAI's coding agent"}

GUARD = ("You are being asked from Dean's local 'agent desk' page, in the Science_vid repo (read CLAUDE.md for "
         "context). Never push, merge, post or publish anything from here: if that's needed, say so and stop. "
         "Answer in plain, short language.")

# ---------------- jobs ----------------
LOCK = threading.Lock()
JOBS = []                     # newest last; each a dict (see new_job)
PROCS = {}                    # job id -> Popen
BUSY = {"claude": None, "codex": None}
TALKS = {}                    # talk id -> {"stop": bool}

def load_history():
    if HISTORY.exists():
        for line in HISTORY.read_text(encoding="utf-8").splitlines():
            try: j = json.loads(line)
            except ValueError: continue
            if j.get("status") == "running": j["status"] = "stopped"
            JOBS[:] = [x for x in JOBS if x["id"] != j["id"]] + [j]      # a job is saved again when it changes
load_history()

def save(job):
    with HISTORY.open("a", encoding="utf-8") as f: f.write(json.dumps(job) + "\n")

def new_job(agent, prompt, files, edits, talk=None):
    job = dict(id=uuid.uuid4().hex[:10], agent=agent, prompt=prompt, files=files, edits=edits, talk=talk,
               status="running", text="", started=time.time(), finished=None)
    with LOCK: JOBS.append(job)
    return job

def finish(job, status, text):
    job.update(status=status, text=text.strip(), finished=time.time())
    with LOCK:
        if BUSY[job["agent"]] == job["id"]: BUSY[job["agent"]] = None
        PROCS.pop(job["id"], None)
    save(job)

def files_note(files):
    if not files: return ""
    return "Files Dean attached (read them as needed): " + ", ".join(f"desk/uploads/{f}" for f in files) + "\n"

def run(job, full_prompt):
    """Run one agent on one prompt (sent on stdin, so long transcripts are fine). Returns the answer text."""
    agent, edits = job["agent"], job["edits"]
    exe = AGENTS[agent]
    if not exe: raise RuntimeError(f"{NAME[agent]} isn't installed on this laptop")
    out_file = None
    if agent == "claude":
        cmd = [exe, "-p", "--output-format", "json", "--permission-mode", "acceptEdits" if edits else "dontAsk",
               "--disallowedTools", "Bash(git push:*)", "Bash(git merge:*)", "Bash(gh pr merge:*)"]
    else:
        out_file = HERE / f".codex_{job['id']}.txt"
        cmd = [exe, "exec", "-s", "workspace-write" if edits else "read-only", "-C", str(ROOT), "--skip-git-repo-check",
               "-o", str(out_file)]
        for f in job["files"]:
            if f.lower().endswith(IMAGE): cmd += ["-i", str(UPLOADS / f)]
        cmd.append("-")
    p = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         creationflags=LOW, text=True, encoding="utf-8", errors="replace")
    with LOCK: PROCS[job["id"]] = p
    try:
        out, err = p.communicate(full_prompt, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        p.kill(); raise RuntimeError(f"no answer after {TIMEOUT // 60} minutes")
    if job["status"] == "stopped": return ""
    if agent == "claude":
        try:
            r = json.loads(out)
            if r.get("is_error"): raise RuntimeError(r.get("result") or "Claude reported an error")
            return r.get("result", "")
        except ValueError:
            raise RuntimeError((err or out or "no output")[-1500:])
    text = out_file.read_text(encoding="utf-8", errors="replace") if out_file.exists() else ""
    out_file.unlink(missing_ok=True)
    if not text.strip(): raise RuntimeError((err or out or "no output")[-1500:])
    return text

def recent(agent, n=2):
    """The last n finished answers this agent gave on the desk, as context for a follow-up."""
    done = [j for j in JOBS if j["agent"] == agent and j["status"] == "done" and not j.get("talk")][-n:]
    return "".join(f"\nEarlier, Dean asked: {j['prompt'][:1500]}\nYou answered: {j['text'][:2000]}\n" for j in done)

def ask_thread(job, context):
    prompt = f"{GUARD}\n{recent(job['agent']) if context else ''}\n{files_note(job['files'])}Dean asks: {job['prompt']}"
    try:
        text = run(job, prompt)
        if job["status"] != "stopped": finish(job, "done", text)
    except Exception as e:
        if job["status"] != "stopped": finish(job, "error", str(e))

TALK = """{guard}
You are {me}, in a conversation with {other} ({about}) about the Science_vid project. Dean started it and is reading along.
Dean's topic: {topic}
{files}
Conversation so far:
{transcript}

Write your next message to {other}. Build on, question or push back on the last message: be concrete and honest, and
say when you disagree. Under 180 words. Read files if it helps, but don't change any. If you both agree and nothing
is left to add, start with "AGREED:" and sum up the conclusion for Dean in a few lines."""

def talk_thread(tid, topic, files, rounds):
    lines = []
    order = ["claude", "codex"] * rounds
    for i, agent in enumerate(order):
        if TALKS[tid]["stop"]: break
        while True:                                   # wait for the agent to be free
            with LOCK:
                if BUSY[agent] is None: break
            time.sleep(1)
        other = "codex" if agent == "claude" else "claude"
        job = new_job(agent, f"(turn {i + 1} of {len(order)})", files, False, talk=tid)
        with LOCK: BUSY[agent] = job["id"]
        transcript = "\n\n".join(lines) or "(nothing yet: you open the conversation)"
        prompt = TALK.format(guard=GUARD, me=NAME[agent], other=NAME[other], about=ABOUT[other], topic=topic,
                             files=files_note(files), transcript=transcript)
        try:
            text = run(job, prompt)
            if job["status"] == "stopped": break
            finish(job, "done", text)
        except Exception as e:
            if job["status"] != "stopped": finish(job, "error", str(e))
            break
        if job["status"] == "stopped": break
        lines.append(f"{NAME[agent]}: {job['text']}")
        if job["text"].lstrip().upper().startswith("AGREED") and i >= 1:
            break
    TALKS[tid]["done"] = True

# ---------------- web ----------------
app = FastAPI()

class Ask(BaseModel):
    prompt: str
    agents: list[str]
    files: list[str] = []
    edits: bool = False
    context: bool = True

class Talk(BaseModel):
    topic: str
    files: list[str] = []
    rounds: int = 3

class Upload(BaseModel):
    name: str
    data: str              # base64

@app.get("/", response_class=HTMLResponse)
def page():
    return (HERE / "desk.html").read_text(encoding="utf-8")

@app.get("/api/state")
def state():
    with LOCK:
        jobs = [dict(j) for j in JOBS[-120:]]
        busy = dict(BUSY)
    talks = {t: dict(v) for t, v in TALKS.items()}
    return dict(jobs=jobs, busy=busy, talks=talks, installed={k: bool(v) for k, v in AGENTS.items()},
                uploads=sorted(p.name for p in UPLOADS.iterdir() if p.is_file()))

# ---------------- live chats with Claude ----------------
TASKS = set()

class Send(BaseModel):
    prompt: str
    files: list[str] = []

class Decision(BaseModel):
    decision: str            # once / always / deny

@app.get("/api/chats")
def chats():
    out = []
    for c in sorted(CC.CHATS.values(), key=lambda c: -c["created"]):
        waiting = sum(1 for e in c["events"] if e["type"] == "perm" and e["state"] == "waiting")
        out.append(dict(id=c["id"], title=c["title"], status=c["status"], created=c["created"], waiting=waiting,
                        n=len(c["events"])))
    return out

@app.post("/api/chats")
def chat_new():
    return CC.new_chat()

@app.get("/api/chats/{cid}")
def chat_get(cid: str):
    if cid not in CC.CHATS: raise HTTPException(404, "no such chat")
    return CC.CHATS[cid]

@app.post("/api/chats/{cid}/send")
async def chat_send(cid: str, m: Send):
    c = CC.CHATS.get(cid)
    if not c: raise HTTPException(404, "no such chat")
    if c["status"] == "running": raise HTTPException(409, "Claude is still working in this chat: wait or press Stop")
    if not m.prompt.strip(): raise HTTPException(400, "type a message first")
    c["status"] = "running"           # at once, so a second click is refused
    task = asyncio.create_task(CC.turn(c, m.prompt.strip(), m.files)); TASKS.add(task); task.add_done_callback(TASKS.discard)
    return {"ok": True}

@app.post("/api/chats/{cid}/stop")
async def chat_stop(cid: str):
    await CC.stop(cid)
    return {"ok": True}

@app.post("/api/chats/{cid}/delete")
def chat_delete(cid: str):
    c = CC.CHATS.get(cid)
    if c and c["status"] == "running": raise HTTPException(409, "stop it first")
    CC.CHATS.pop(cid, None); CC.save()
    return {"ok": True}

@app.post("/api/permission/{pid}")
async def permission(pid: str, d: Decision):
    if d.decision not in ("once", "always", "deny"): raise HTTPException(400, "once, always or deny")
    if not CC.answer(pid, d.decision): raise HTTPException(404, "that question has already been answered")
    return {"ok": True}

@app.post("/api/upload")
def upload(u: Upload):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(u.name).name)[:80] or "file"
    data = base64.b64decode(u.data.split(",")[-1])
    if len(data) > 25 * 1024 * 1024: raise HTTPException(413, "files up to 25 MB")
    path = UPLOADS / name
    if path.exists(): path = UPLOADS / f"{path.stem}_{uuid.uuid4().hex[:4]}{path.suffix}"
    path.write_bytes(data)
    return {"name": path.name}

@app.post("/api/ask")
def ask(a: Ask):
    if not a.prompt.strip(): raise HTTPException(400, "type a question first")
    started = []
    for agent in a.agents:
        if agent not in AGENTS: raise HTTPException(400, f"unknown agent {agent}")
        with LOCK:
            if BUSY[agent]: raise HTTPException(409, f"{NAME[agent]} is still answering; wait or press Stop")
    for agent in a.agents:
        job = new_job(agent, a.prompt.strip(), a.files, a.edits)
        with LOCK: BUSY[agent] = job["id"]
        threading.Thread(target=ask_thread, args=(job, a.context), daemon=True).start()
        started.append(job["id"])
    return {"started": started}

@app.post("/api/talk")
def talk(t: Talk):
    if not t.topic.strip(): raise HTTPException(400, "type a topic first")
    with LOCK:
        if any(BUSY.values()): raise HTTPException(409, "wait until both are free (or press Stop)")
    tid = uuid.uuid4().hex[:8]
    TALKS[tid] = dict(topic=t.topic.strip(), stop=False, done=False, started=time.time())
    threading.Thread(target=talk_thread, args=(tid, t.topic.strip(), t.files, max(1, min(6, t.rounds))), daemon=True).start()
    return {"talk": tid}

@app.post("/api/stop/{job_id}")
def stop(job_id: str):
    with LOCK:
        job = next((j for j in JOBS if j["id"] == job_id), None)
        p = PROCS.get(job_id)
    if not job: raise HTTPException(404, "no such job")
    if job.get("talk") in TALKS: TALKS[job["talk"]]["stop"] = True
    job["status"] = "stopped"
    if p: p.kill()
    finish(job, "stopped", job.get("text", ""))
    return {"ok": True}

@app.post("/api/stop_talk/{tid}")
def stop_talk(tid: str):
    if tid not in TALKS: raise HTTPException(404, "no such conversation")
    TALKS[tid]["stop"] = True
    with LOCK: running = [j["id"] for j in JOBS if j.get("talk") == tid and j["status"] == "running"]
    for jid in running: stop(jid)
    return {"ok": True}

if __name__ == "__main__":
    print(f"agent desk: http://localhost:{PORT}  (Claude: {AGENTS['claude'] or 'not found'}; Codex: {AGENTS['codex'] or 'not found'})")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
