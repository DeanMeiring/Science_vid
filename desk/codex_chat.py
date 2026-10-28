"""Live chats with Codex for the agent desk, through `codex app-server` (the JSON-RPC mode Codex's VS Code
extension uses; same ChatGPT login as the `codex` command).

Works like claude_chat.py and shares its chat list and permission buttons. Codex runs in its workspace-write
sandbox (it can only write inside the repo, no network) and asks before every command that isn't a plain read,
and before every file change. Allow once / Allow in this chat / Deny map to accept / acceptForSession / decline.

Hard rules: commands that push, merge or post are declined without asking (same BLOCK as Claude's chats).
"""
import asyncio, json, os, re, subprocess, sys, time, uuid
from pathlib import Path

import claude_chat as CC

ROOT = CC.ROOT
LOW = subprocess.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 0   # gentle on the laptop
IMAGE = (".png", ".jpg", ".jpeg", ".gif", ".webp")
GUARD = CC.GUARD
READ_ONLY = {"read", "listFiles", "search"}       # command actions that run without asking
DECISION = {"once": "accept", "always": "acceptForSession"}

def find_codex():
    import shutil
    exe = shutil.which("codex")
    if exe: return exe
    for p in (Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages").glob("OpenAI.Codex*/codex-*windows*.exe"):
        return str(p)
    return None

def short(cmd):
    """Codex wraps commands in `powershell.exe -Command "..."`: show only the inside."""
    m = re.match(r'^"?[^"]*powershell(\.exe)?"?\s+-Command\s+(["\'])(.*)\2\s*$', cmd or "", re.S | re.I)
    return (m.group(3).replace("\\\\", "\\") if m else cmd or "").strip()      # and un-double its backslashes

def rel(p):
    return str(p).replace(str(ROOT) + "\\", "").replace(str(ROOT) + "/", "")

class Server:
    """One `codex app-server` process for all Codex chats. Started on first use, restarted if it dies."""
    def __init__(self):
        self.proc = None; self.n = 0; self.waiters = {}; self.threads = {}   # codex thread id -> chat
        self.loaded = set(); self.lock = asyncio.Lock()

    async def ensure(self):
        async with self.lock:
            if self.proc and self.proc.returncode is None: return
            exe = find_codex()
            if not exe: raise RuntimeError("Codex isn't installed")
            self.proc = await asyncio.create_subprocess_exec(
                exe, "app-server", stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, limit=2 ** 24, creationflags=LOW)
            self.loaded = set(); self.waiters = {}
            asyncio.create_task(self.read(self.proc))
            await self.call("initialize", {"clientInfo": {"name": "agent_desk", "title": "Agent Desk", "version": "0.1"}})
            self.send({"method": "initialized"})
            try: rate_limits((await self.call("account/rateLimits/read", None)).get("rateLimits"))
            except Exception: pass                                 # an older Codex: the numbers come with each turn

    def send(self, msg):
        self.proc.stdin.write((json.dumps({"jsonrpc": "2.0", **msg}) + "\n").encode())

    async def call(self, method, params):
        self.n += 1; i = self.n
        f = asyncio.get_running_loop().create_future(); self.waiters[i] = f
        self.send({"id": i, "method": method, "params": params}); await self.proc.stdin.drain()
        r = await f
        if "error" in r: raise RuntimeError(r["error"].get("message", str(r["error"])))
        return r["result"]

    async def read(self, proc):
        while line := await proc.stdout.readline():
            try: m = json.loads(line)
            except ValueError: continue
            if "method" not in m:                                  # a response to one of our calls
                f = self.waiters.pop(m.get("id"), None)
                if f and not f.done(): f.set_result(m)
                continue
            p = m.get("params") or {}
            chat = self.threads.get(p.get("threadId"))
            if m["method"] == "account/rateLimits/updated": rate_limits(p.get("rateLimits")); continue
            if m["method"] == "thread/tokenUsage/updated":
                if chat: tokens(chat, p.get("threadId"), (p.get("tokenUsage") or {}).get("total") or {})
                continue
            if "id" in m:                                          # Codex asks us something
                asyncio.create_task(self.request(chat, m["id"], m["method"], p))
            elif chat:
                on_event(chat, m["method"], p)
        for f in self.waiters.values():                            # the process died
            if not f.done(): f.set_result({"error": {"message": "Codex stopped unexpectedly"}})
        for chat in self.threads.values():
            t = chat.get("_turn")
            if t and not t["done"].is_set():
                CC.add(chat, "error", text="Codex stopped unexpectedly."); t["done"].set()

    async def request(self, chat, rid, method, p):
        try:
            if chat and method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
                result = {"decision": await approve(chat, method, p)}
                self.send({"id": rid, "result": result})
            else:                                                  # questions the desk can't answer (yet)
                self.send({"id": rid, "error": {"code": -32601, "message": "The agent desk doesn't support this."}})
            await self.proc.stdin.drain()
        except Exception:
            pass

SERVER = Server()

def rate_limits(snap):
    """Codex's plan limits: primary (the 5-hour window) and secondary (the weekly one), each a % used."""
    for w in ("primary", "secondary"):
        x = (snap or {}).get(w)
        if not x: continue
        mins = x.get("windowDurationMins") or (300 if w == "primary" else 10080)
        name = {300: "five_hour", 10080: "seven_day"}.get(mins, f"{mins}_min")
        CC.note_limit("codex", name, x.get("usedPercent"), x.get("resetsAt"),
                      "rejected" if (snap.get("rateLimitReachedType") and (x.get("usedPercent") or 0) >= 100) else None)

def tokens(chat, tid, total):
    """Codex reports each thread's running total: add what's new since the last report."""
    seen = (chat.setdefault("cx_seen", {}).get(tid) or []) + [0, 0, 0]
    cached = total.get("cachedInputTokens") or 0                # inputTokens includes the cached part
    now = [(total.get("inputTokens") or 0) - cached, total.get("outputTokens") or 0, cached]
    CC.add_tokens(chat, *(max(0, n - o) for n, o in zip(now, seen)))
    chat["cx_seen"][tid] = now

async def approve(chat, method, p):
    t = chat.get("_turn") or {}
    item = t.get("items", {}).get(p.get("itemId"), {})
    if method.startswith("item/commandExecution"):
        cmd = short(p.get("command") or item.get("command"))
        if CC.BLOCK.search(cmd):
            CC.add(chat, "error", text=f"Refused without asking: {cmd} (the desk never pushes, merges or posts)."); CC.save()
            return "decline"
        if chat.get("auto") and not p.get("reason") and not p.get("networkApprovalContext") and not CC.ASK.search(cmd):
            return "accept"                                        # building: runs inside the sandbox, no question
        acts = p.get("commandActions") or item.get("commandActions") or []
        if acts and all(a.get("type") in READ_ONLY for a in acts):
            return "accept"                                        # plain reads: like Claude, no question
        key = f"Bash:{cmd}"
        what, detail = f"Running: {cmd}", f"{cmd}\n\nin {p.get('cwd') or ROOT}"
    else:
        changes = item.get("changes") or []
        roots = [Path(chat.get("cwd") or ROOT).resolve(), (ROOT / "renders").resolve()]
        if chat.get("auto") and changes and all(CC.inside(c["path"], roots) for c in changes):
            return "accept"                                        # building: edits inside the build folder
        key = "Edit:" + ",".join(sorted(c["path"] for c in changes))
        what = "Editing " + ", ".join(rel(c["path"]) for c in changes) if changes else "Changing files"
        detail = "\n\n".join(f"{rel(c['path'])}\n{c.get('diff', '')}" for c in changes)[:4000]
    if key in chat["always"]: return "acceptForSession"
    pid = uuid.uuid4().hex[:10]
    fut = asyncio.get_running_loop().create_future(); CC.PERMS[pid] = (chat["id"], fut)
    e = CC.add(chat, "perm", id=pid, tool=method, what=what, why=p.get("reason") or "", state="waiting", detail=detail[:4000])
    CC.save()
    try: decision = await asyncio.wait_for(fut, CC.WAIT)
    except asyncio.TimeoutError: decision = "expired"
    CC.PERMS.pop(pid, None)
    e["state"] = decision
    if decision == "always": chat["always"].append(key)
    CC.save()
    return DECISION.get(decision, "decline")

def on_event(chat, method, p):
    t = chat.get("_turn")
    if not t: return
    if method == "item/agentMessage/delta":                 # Codex's words as it writes them
        chat["_live"] = chat.get("_live", "") + (p.get("delta") or ""); return
    item = p.get("item") or {}; kind = item.get("type"); iid = item.get("id")
    if method == "item/started":
        t["items"][iid] = item
        if kind == "commandExecution":
            t["events"][iid] = CC.add(chat, "tool", what=f"Running: {short(item.get('command'))}", out=None, ok=None)
        elif kind == "fileChange":
            names = ", ".join(rel(c["path"]) for c in item.get("changes") or []) or "files"
            t["events"][iid] = CC.add(chat, "tool", what=f"Editing {names}", out=None, ok=None)
        elif kind == "webSearch":
            t["events"][iid] = CC.add(chat, "tool", what=f"Searching the web: {item.get('query', '')}", out=None, ok=None)
        elif kind == "mcpToolCall":
            t["events"][iid] = CC.add(chat, "tool", what=f"{item.get('server')}: {item.get('tool')}", out=None, ok=None)
    elif method == "item/completed":
        t["items"][iid] = item
        if kind == "agentMessage":
            chat["_live"] = ""
            if (item.get("text") or "").strip(): CC.add(chat, "text", text=item["text"])
        elif iid in t["events"]:
            e = t["events"][iid]
            if kind == "commandExecution":
                e.update(out=(item.get("aggregatedOutput") or "")[:3000],
                         ok=item.get("status") == "completed" and item.get("exitCode") in (0, None))
            elif kind == "fileChange":
                e.update(out="\n\n".join(c.get("diff", "") for c in item.get("changes") or [])[:3000],
                         ok=item.get("status") == "completed")
            else:
                act = item.get("action") or {}
                if kind == "webSearch":                          # the query is only known once it's done
                    q = item.get("query") or "; ".join(act.get("queries") or []) or act.get("url") or ""
                    e["what"] = ("Opening " if act.get("type") == "openPage" else "Searching the web: ") + q
                e.update(out=json.dumps(item.get("result") or act or "")[:3000], ok=item.get("status") != "failed")
    elif method == "turn/completed":
        turn = p.get("turn") or {}
        if turn.get("status") == "failed":
            CC.add(chat, "error", text=str((turn.get("error") or {}).get("message") or "Codex failed")[:2000])
        t["done"].set()
    elif method == "error":
        err = p.get("error") or {}
        if not p.get("willRetry"): CC.add(chat, "error", text=str(err.get("message") or err)[:2000])
    else:
        return
    CC.save()

async def turn(chat, prompt, files):
    chat["status"] = "running"
    if chat["title"] == "New chat": chat["title"] = prompt.strip().splitlines()[0][:60]
    CC.add(chat, "user", text=prompt, files=files); CC.save()
    full = prompt
    others = [f for f in files if not f.lower().endswith(IMAGE)]
    if others: full += "\n\nFiles I attached (read them as needed): " + ", ".join(f"desk/uploads/{f}" for f in others)
    inp = [{"type": "text", "text": full}] + [{"type": "localImage", "path": str(CC.HERE / "uploads" / f)}
                                               for f in files if f.lower().endswith(IMAGE)]
    t0 = time.time(); chat["_turn"] = t = dict(items={}, events={}, done=asyncio.Event(), id=None)
    try:
        await SERVER.ensure()
        tid = chat.get("session_id")
        cwd = str(chat.get("cwd") or ROOT)
        opts = dict(cwd=cwd, approvalPolicy="untrusted", sandbox="workspace-write", developerInstructions=GUARD + chat.get("guard_extra", ""))
        if tid and tid not in SERVER.loaded:
            try: await SERVER.call("thread/resume", dict(threadId=tid, **opts))
            except RuntimeError: tid = None                       # the old thread is gone: start over
        if not tid:
            tid = (await SERVER.call("thread/start", opts))["thread"]["id"]
        chat["session_id"] = tid; SERVER.loaded.add(tid); SERVER.threads[tid] = chat
        policy = {"type": "workspaceWrite", "networkAccess": False, "writableRoots": [cwd, str(ROOT / "renders")]}
        r = await SERVER.call("turn/start", {"threadId": tid, "input": inp, "cwd": cwd, "sandboxPolicy": policy})
        t["id"] = r["turn"]["id"]
        await t["done"].wait()
        CC.add(chat, "done", seconds=round(time.time() - t0))
    except Exception as ex:
        CC.add(chat, "error", text=f"{type(ex).__name__}: {ex}"[:2000])
    finally:
        for pid, (cid, fut) in list(CC.PERMS.items()):
            if cid == chat["id"] and not fut.done(): fut.set_result("deny")
        chat.pop("_turn", None); chat["_live"] = ""; chat["status"] = "idle"; CC.save()

async def steer(chat, text, files=()):
    """A message from Dean while Codex is working: added to the running turn (turn/steer)."""
    t = chat.get("_turn")
    if not t or not t.get("id"): return False
    full = text + ("\n\nFiles I attached: " + ", ".join(f"desk/uploads/{f}" for f in files) if files else "")
    try:
        await SERVER.call("turn/steer", {"threadId": chat["session_id"], "expectedTurnId": t["id"],
                                         "input": [{"type": "text", "text": "Dean, while you were working: " + full}]})
    except Exception:
        return False                                           # the turn just ended: send it as a new message
    CC.add(chat, "dean", text=text, files=list(files), how="sent while working"); CC.save()
    return True

async def stop(chat_id):
    chat = CC.CHATS.get(chat_id)
    if not chat: return
    for pid, (cid, fut) in list(CC.PERMS.items()):
        if cid == chat_id and not fut.done(): fut.set_result("deny")
    t = chat.get("_turn")
    if t:
        CC.add(chat, "error", text="Stopped by Dean."); CC.save()
        if t["id"]:
            try: await asyncio.wait_for(SERVER.call("turn/interrupt", {"threadId": chat["session_id"], "turnId": t["id"]}), 10)
            except Exception: pass
        t["done"].set()
