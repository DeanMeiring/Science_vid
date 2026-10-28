"""Live chats with Claude Code for the agent desk, through the Claude Agent SDK (same login as the `claude` command).

Each chat keeps its session, so follow-ups remember the conversation. While Claude works, every step shows up on
the page (its text, each file it reads, each command it runs). When it wants to do something that needs
permission, the page shows Allow once / Allow in this chat / Deny and Claude waits for the click.

Hard rules, whatever is clicked or allowed in settings: no git push, no merging, no posting (the studio's upload
endpoints and publish code). A PreToolUse hook enforces them, so they hold even for commands the settings allow.
"""
import asyncio, json, re, shutil, time, uuid
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, HookMatcher, PermissionResultAllow,
                              PermissionResultDeny, ResultMessage, SystemMessage, TextBlock, ToolResultBlock,
                              ToolUseBlock, UserMessage)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STORE = HERE / "chats.json"
WAIT = 30 * 60                       # seconds a permission question waits before it counts as "deny"
GUARD = ("You are running inside Dean's local 'agent desk' web page, in the Science_vid repo. Follow CLAUDE.md. "
         "Never push, merge, post or publish anything: if that's needed, tell Dean to do it himself. Dean answers "
         "permission requests with buttons on the page.")
BLOCK = re.compile(r"\bgit\s+push\b|\bgit\s+merge\b|\bgh\s+pr\s+merge\b|\bgh\s+api\b.*\bmerge|"
                   r"(localhost|127\.0\.0\.1):8765/api/(episode|post)|publish_reel|upload_video|publish[/\\.](youtube|instagram)",
                   re.I)
SHELL = ("Bash", "PowerShell")

CHATS = {}                            # id -> chat dict
RUNNING = {}                          # chat id -> ClaudeSDKClient while a turn runs
PERMS = {}                            # permission id -> (chat id, asyncio.Future)

def load():
    if STORE.exists():
        try:
            for c in json.loads(STORE.read_text(encoding="utf-8")):
                if c.get("status") == "running": c["status"] = "idle"
                for e in c["events"]:
                    if e["type"] == "perm" and e["state"] == "waiting": e["state"] = "expired"
                CHATS[c["id"]] = c
        except ValueError:
            pass
load()

def save():
    keep = [{k: v for k, v in c.items() if not k.startswith("_")} for c in CHATS.values()]   # "_turn" is live state
    STORE.write_text(json.dumps(keep), encoding="utf-8")

def new_chat(agent="claude"):
    c = dict(id=uuid.uuid4().hex[:10], agent=agent, title="New chat", session_id=None, created=time.time(), status="idle",
             events=[], always=[])
    CHATS[c["id"]] = c; save()
    return c

def add(chat, type_, **kw):
    e = dict(type=type_, t=time.time(), **kw); chat["events"].append(e)
    return e

def describe(name, inp):
    """A plain-language line for a tool call."""
    g = lambda k: str(inp.get(k, ""))
    rel = lambda p: p.replace(str(ROOT) + "\\", "").replace(str(ROOT) + "/", "")
    if name in SHELL: return f"Running: {g('command')}"
    if name == "Read": return f"Reading {rel(g('file_path'))}"
    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"): return f"{'Writing' if name == 'Write' else 'Editing'} {rel(g('file_path') or g('notebook_path'))}"
    if name in ("Glob", "Grep"): return f"Searching for {g('pattern')}"
    if name == "WebFetch": return f"Opening {g('url')}"
    if name == "WebSearch": return f"Searching the web: {g('query')}"
    if name in ("Task", "Agent"): return f"Starting a helper: {g('description')}"
    return f"{name} {json.dumps(inp)[:200]}"

def always_key(name, inp):
    return f"{name}:{inp.get('command')}" if name in SHELL else name

async def guard_hook(inp, tool_use_id, ctx):
    """Runs before every tool call, allowed or not: the hard no-push / no-merge / no-post rules."""
    name = inp.get("tool_name"); cmd = str((inp.get("tool_input") or {}).get("command", ""))
    if name in SHELL and BLOCK.search(cmd):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": "The agent desk never pushes, merges or posts. Ask Dean to do it."}}
    return {}

def make_permission(chat):
    async def can_use(name, inp, ctx):
        if name in SHELL and BLOCK.search(str(inp.get("command", ""))):
            return PermissionResultDeny(message="The agent desk never pushes, merges or posts. Ask Dean to do it.")
        key = always_key(name, inp)
        if key in chat["always"]:
            return PermissionResultAllow()
        pid = uuid.uuid4().hex[:10]
        fut = asyncio.get_running_loop().create_future(); PERMS[pid] = (chat["id"], fut)
        e = add(chat, "perm", id=pid, tool=name, what=describe(name, inp),
                why=getattr(ctx, "description", None) or getattr(ctx, "title", None) or "", state="waiting",
                detail=json.dumps(inp, indent=1)[:4000])
        save()
        try:
            decision = await asyncio.wait_for(fut, WAIT)
        except asyncio.TimeoutError:
            decision = "expired"
        PERMS.pop(pid, None)
        e["state"] = decision; save()
        if decision == "always": chat["always"].append(key)
        if decision in ("once", "always"): return PermissionResultAllow()
        return PermissionResultDeny(message="Dean said no." if decision == "deny" else "No answer from Dean in time.")
    return can_use

def answer(pid, decision):
    if pid not in PERMS: return False
    _, fut = PERMS[pid]
    if not fut.done(): fut.set_result(decision)
    return True

async def turn(chat, prompt, files):
    chat["status"] = "running"
    if chat["title"] == "New chat": chat["title"] = prompt.strip().splitlines()[0][:60]
    add(chat, "user", text=prompt, files=files); save()
    full = prompt
    if files: full += "\n\nFiles I attached (read them as needed): " + ", ".join(f"desk/uploads/{f}" for f in files)
    opts = ClaudeAgentOptions(
        cwd=str(ROOT), cli_path=shutil.which("claude"), permission_mode="default", resume=chat["session_id"],
        can_use_tool=make_permission(chat), setting_sources=["user", "project", "local"],
        system_prompt={"type": "preset", "preset": "claude_code", "append": GUARD},
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[guard_hook])]})
    t0 = time.time(); tools = {}
    try:
        async with ClaudeSDKClient(opts) as client:
            RUNNING[chat["id"]] = client
            await client.query(full)
            async for m in client.receive_response():
                if isinstance(m, SystemMessage) and m.subtype == "init":
                    chat["session_id"] = (getattr(m, "data", None) or {}).get("session_id") or chat["session_id"]
                elif isinstance(m, AssistantMessage):
                    for b in m.content:
                        if isinstance(b, TextBlock) and b.text.strip(): add(chat, "text", text=b.text)
                        elif isinstance(b, ToolUseBlock): tools[b.id] = add(chat, "tool", what=describe(b.name, b.input), out=None, ok=None)
                elif isinstance(m, UserMessage) and isinstance(m.content, list):
                    for b in m.content:
                        if isinstance(b, ToolResultBlock) and b.tool_use_id in tools:
                            c = b.content if isinstance(b.content, str) else "\n".join(
                                x.get("text", "") for x in (b.content or []) if isinstance(x, dict))
                            tools[b.tool_use_id].update(out=c[:3000], ok=not b.is_error)
                elif isinstance(m, ResultMessage):
                    chat["session_id"] = m.session_id or chat["session_id"]
                    stopped = chat["events"][-1].get("text") == "Stopped by Dean."
                    if m.is_error and m.subtype != "success" and not stopped: add(chat, "error", text=m.result or m.subtype)
                save()
        add(chat, "done", seconds=round(time.time() - t0))
    except asyncio.CancelledError:
        add(chat, "error", text="Stopped."); raise
    except Exception as ex:
        add(chat, "error", text=f"{type(ex).__name__}: {ex}"[:2000])
    finally:
        RUNNING.pop(chat["id"], None)
        for pid, (cid, fut) in list(PERMS.items()):
            if cid == chat["id"] and not fut.done(): fut.set_result("deny")
        chat["status"] = "idle"; save()

async def stop(chat_id):
    client = RUNNING.get(chat_id)
    for pid, (cid, fut) in list(PERMS.items()):
        if cid == chat_id and not fut.done(): fut.set_result("deny")
    if client:
        try: await client.interrupt()
        except Exception: pass
        if chat_id in CHATS: add(CHATS[chat_id], "error", text="Stopped by Dean."); save()
