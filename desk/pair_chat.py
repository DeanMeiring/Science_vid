"""Claude + Codex side by side for the agent desk: a "pair" is one Claude chat and one Codex chat on a split
screen. Dean can message one or both, or press "Collaborate for N rounds": they take turns on his task, each
turn getting the other's last reply, until both start a reply with AGREED: or the rounds run out.

Both chats are ordinary desk chats (claude_chat.py / codex_chat.py), so every change still asks Dean with the
Allow / Deny buttons, and pushing, merging and posting stay refused.
"""
import asyncio, json, os, subprocess, time, uuid

import claude_chat as CC
import codex_chat as XC

STORE = CC.HERE / "pairs.json"
PAIRS = {}                       # id -> pair dict
TASKS = {}                       # pair id -> the running collaboration task
NAME = {"claude": "Claude", "codex": "Codex"}
MOD = {"claude": CC, "codex": XC}
MAX_REPLY = 6000                 # characters of one agent's reply passed to the other

def load():
    if STORE.exists():
        try:
            for p in json.loads(STORE.read_text(encoding="utf-8")):
                if p.get("collab") and p["collab"]["state"] == "running": p["collab"]["state"] = "stopped"
                PAIRS[p["id"]] = p
        except ValueError:
            pass
load()

def save():
    STORE.write_text(json.dumps(list(PAIRS.values())), encoding="utf-8")

def new_pair():
    pid = uuid.uuid4().hex[:10]
    ids = {}
    for a in ("claude", "codex"):
        c = CC.new_chat(a); c["pair"] = pid; ids[a] = c["id"]
    CC.save()
    p = dict(id=pid, title="Claude + Codex", created=time.time(), collab=None, **ids)
    PAIRS[pid] = p; save()
    return p

def chat(p, agent):
    return CC.CHATS.get(p[agent])

def last_reply(c):
    """What the agent said in its last turn, plus the files it changed: the part the other one gets to read."""
    ev = c["events"]
    start = max((i for i, e in enumerate(ev) if e["type"] == "user"), default=-1)
    texts = [e["text"] for e in ev[start + 1:] if e["type"] == "text"]
    changed = [e["what"] for e in ev[start + 1:] if e["type"] == "tool" and e.get("ok")
               and e["what"].startswith(("Writing ", "Editing "))]
    out = "\n\n".join(texts).strip() or "(no reply)"
    if changed: out += "\n\n[Files changed this turn: " + "; ".join(changed) + "]"
    stopped = any(e["type"] == "error" for e in ev[start + 1:])
    return out[:MAX_REPLY], stopped

def first_prompt(agent, task, rounds, other_reply=None):
    me, other = NAME[agent], NAME["codex" if agent == "claude" else "claude"]
    s = (f"Dean wants you ({me}) and {other} to work on this together, taking turns, for up to {rounds} "
         f"round{'s' if rounds > 1 else ''} each:\n\n{task}\n\n"
         f"Each turn you get {other}'s last reply. Split the work, check each other's work, and say clearly what you "
         "did. Changing files or running commands asks Dean first. Keep replies short. When you both agree the job "
         "is done, start your reply with AGREED: and a one-line summary.")
    if other_reply is None: return s + "\n\nYou go first."
    return s + f"\n\n{other} went first and said:\n\n{other_reply}\n\nYour turn (round 1 of {rounds})."

async def collaborate(p, task, files, rounds, build=None):
    """build=None: talk it through. build=str (earlier agreement, may be empty): build it, without asking for edits."""
    col = p["collab"] = dict(task=task, rounds=rounds, round=1, turn="claude", state="running", note="",
                           mode="talk" if build is None else "build")
    for a in ("claude", "codex"): chat(p, a)["auto"] = build is not None
    save()
    replies = {"claude": None, "codex": None}
    try:
        for r in range(1, rounds + 1):
            for agent in ("claude", "codex"):
                other = "codex" if agent == "claude" else "claude"
                col.update(round=r, turn=agent); save()
                if r == 1 and build is not None:
                    prompt = build_first(agent, task, rounds, build, replies[other])
                elif r == 1:
                    prompt = first_prompt(agent, task, rounds, replies[other])
                else:
                    prompt = f"{NAME[other]} replied:\n\n{replies[other]}\n\nYour turn (round {r} of {rounds})."
                if r == rounds and agent == "codex":
                    prompt += " This is the last turn: finish up and sum up what was done and what's left for Dean."
                c = chat(p, agent)
                while c["status"] == "running": await asyncio.sleep(1)      # Dean messaged it by hand: wait
                await MOD[agent].turn(c, prompt, files if r == 1 else [])
                replies[agent], stopped = last_reply(c)
                if stopped:
                    col.update(state="stopped", note=f"{NAME[agent]}'s turn stopped or failed"); return
                if replies[agent].startswith("AGREED") and (replies[other] or "").startswith("AGREED"):
                    col.update(state="agreed", note=f"Both agreed in round {r}"); return
        col.update(state="done", note=f"Finished {rounds} round{'s' if rounds > 1 else ''}")
    except asyncio.CancelledError:
        col.update(state="stopped", note="Stopped by Dean"); raise
    finally:
        for a in ("claude", "codex"):
            if chat(p, a): chat(p, a)["auto"] = False
        TASKS.pop(p["id"], None); CC.save(); save()

def start_collab(p, task, files, rounds):
    TASKS[p["id"]] = asyncio.create_task(collaborate(p, task, files, rounds))

# ---------------- building together ----------------
BUILDS = CC.ROOT.parent / "Science_vid_builds"
SHARED = [".venv", "renders", "assets/thirdparty", "voices"]   # gitignored folders a build needs: linked, not copied

def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd or CC.ROOT, capture_output=True, text=True)
    if r.returncode: raise RuntimeError(f"git {' '.join(args)}: {(r.stderr or r.stdout).strip()[:400]}")
    return r.stdout.strip()

def make_worktree(branch):
    """A separate copy of the repo for this build, on a new branch from origin/main, so Dean's main folder (and
    the desk running from it) never changes branch. The big gitignored folders are linked in (junctions)."""
    path = BUILDS / branch.split("/")[-1]
    if (path / ".git").exists():
        if git("rev-parse", "--abbrev-ref", "HEAD", cwd=path) != branch: raise RuntimeError(f"{path} is on another branch")
        return path
    git("fetch", "-q", "origin", "main")
    BUILDS.mkdir(exist_ok=True)
    git("worktree", "add", "-b", branch, str(path), "origin/main")
    for d in SHARED:
        src, dst = CC.ROOT / d, path / d
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], capture_output=True)
    if (CC.ROOT / ".env").exists() and not (path / ".env").exists():
        os.link(CC.ROOT / ".env", path / ".env")          # the HF token for the voice; posting tokens stay out
    return path

def build_extra(path, branch):
    return (f"\n\nYOU ARE BUILDING in a separate copy of the repo: {path}, on branch {branch} (cut from origin/main). "
            "Work only in that folder. renders/, .venv and the third-party assets are shared with Dean's main folder. "
            "Its CLAUDE.md is main's (up to Experiment 11; Experiment 12 is on an unmerged branch). "
            "Edits and test runs in this folder don't ask Dean; Blender, installs, deletes and the network still do. "
            "Claude makes the git commits on this branch; Codex never runs git commands that change anything. "
            "Nobody pushes: Dean does that.")

def build_first(agent, task, rounds, context, other_reply=None):
    me, other = NAME[agent], NAME["codex" if agent == "claude" else "claude"]
    s = (f"Dean wants you ({me}) and {other} to BUILD this together, taking turns, for up to {rounds} round"
         f"{'s' if rounds > 1 else ''} each:\n\n{task}\n\n")
    if context: s += f"What you two agreed earlier in this chat:\n\n{context}\n\n"
    s += ("Roles: Claude writes most of the code and commits each working step on the branch. Codex reviews each "
          "change, runs the checks and tests, and fixes the bugs it finds (Claude commits those too). Follow CLAUDE.md: "
          "every fact checked by simulation or a solid source, gentle on the laptop, no full renders and no voice "
          "without Dean. Each turn do one solid chunk, then say what you did, what you checked, and what the other "
          "should do next. When the build is done and checked, start your reply with AGREED: and a summary for Dean.")
    if other_reply is None: return s + "\n\nYou go first."
    return s + f"\n\n{other} went first and said:\n\n{other_reply}\n\nYour turn (round 1 of {rounds})."

def start_build_prepare(p, branch):
    """Runs in a worker thread (git fetch can take a while): make the build folder and point both chats at it."""
    path = make_worktree(branch)
    p["_context"] = "\n\n".join(f"{NAME[a]}: {last_reply(chat(p, a))[0]}" for a in ("claude", "codex")
                                if any(e["type"] == "text" for e in chat(p, a)["events"]))
    for a in ("claude", "codex"):
        c = chat(p, a)
        if c.get("cwd") != str(path):
            c["cwd"] = str(path)
            if a == "claude": c["session_id"] = None       # Claude keeps sessions per folder: start fresh there
        c["guard_extra"] = build_extra(path, branch)
    p["build"] = dict(branch=branch, path=str(path)); CC.save(); save()

def start_build(p, task, files, rounds, branch):
    context = p.pop("_context", "")
    TASKS[p["id"]] = asyncio.create_task(collaborate(p, task, files, rounds, build=context))

async def stop(p):
    for a in ("claude", "codex"):                  # interrupt the agents first, then end the loop
        c = chat(p, a)
        if c and c["status"] == "running": await MOD[a].stop(c["id"])
    t = TASKS.get(p["id"])
    if t: t.cancel()

def delete(p):
    for a in ("claude", "codex"): CC.CHATS.pop(p[a], None)
    PAIRS.pop(p["id"], None); CC.save(); save()
