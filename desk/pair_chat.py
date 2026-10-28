"""Claude + Codex side by side for the agent desk: a "pair" is one Claude chat and one Codex chat on a split
screen. Dean can message one or both, or press "Collaborate for N rounds": they take turns on his task, each
turn getting the other's last reply, until both start a reply with AGREED: or the rounds run out.

Both chats are ordinary desk chats (claude_chat.py / codex_chat.py), so every change still asks Dean with the
Allow / Deny buttons, and pushing, merging and posting stay refused.
"""
import asyncio, json, time, uuid

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

async def collaborate(p, task, files, rounds):
    col = p["collab"] = dict(task=task, rounds=rounds, round=1, turn="claude", state="running", note="")
    save()
    replies = {"claude": None, "codex": None}
    try:
        for r in range(1, rounds + 1):
            for agent in ("claude", "codex"):
                other = "codex" if agent == "claude" else "claude"
                col.update(round=r, turn=agent); save()
                if r == 1:
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
        TASKS.pop(p["id"], None); save()

def start_collab(p, task, files, rounds):
    TASKS[p["id"]] = asyncio.create_task(collaborate(p, task, files, rounds))

async def stop(p):
    for a in ("claude", "codex"):                  # interrupt the agents first, then end the loop
        c = chat(p, a)
        if c and c["status"] == "running": await MOD[a].stop(c["id"])
    t = TASKS.get(p["id"])
    if t: t.cancel()

def delete(p):
    for a in ("claude", "codex"): CC.CHATS.pop(p[a], None)
    PAIRS.pop(p["id"], None); CC.save(); save()
