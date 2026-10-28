"""Claude + Codex side by side for the agent desk: a "pair" is one Claude chat and one Codex chat on a split
screen. Dean can message one or both, or:

- "Collaborate for N rounds": they take turns on his task, each turn getting the other's last reply, until both
  start a reply with AGREED: or the rounds run out.
- "Build together": the same, but they build it, in its own git worktree on a new branch, in phases. At the start
  of each phase they split the work between them (a task list with owners), as evenly as they can: every turn
  each sees how much of both their usage limits is used, so neither runs out long before the other. When one
  gets stuck it hands the problem to the other (STUCK:) and they solve it together. When one hits its usage
  limit, the other carries on alone until it's back. When a phase is done they stop with PHASE READY: and
  the files Dean should look at; the page shows them, and nothing goes on until Dean presses Continue (with notes).

Both chats are ordinary desk chats (claude_chat.py / codex_chat.py): while building, edits and test runs inside
the build folder don't ask, everything else still does, and pushing, merging and posting stay refused.
"""
import asyncio, json, os, re, subprocess, time, uuid
from pathlib import Path

import claude_chat as CC
import codex_chat as XC

STORE = CC.HERE / "pairs.json"
PAIRS = {}                       # id -> pair dict
TASKS = {}                       # pair id -> the running collaboration task
REVIEWS = {}                     # pair id -> future Dean's Continue / Stop resolves
NOTES = {}                       # pair id -> {agent: [Dean's messages waiting for its next turn]}
NAME = {"claude": "Claude", "codex": "Codex"}
MOD = {"claude": CC, "codex": XC}
MAX_REPLY = 6000                 # characters of one agent's reply passed to the other

def load():
    if STORE.exists():
        try:
            for p in json.loads(STORE.read_text(encoding="utf-8")):
                if p.get("collab") and p["collab"]["state"] == "running":      # a review or a pause that was waiting still is
                    p["collab"]["state"] = "stopped"; p["collab"]["note"] = "the desk restarted"
                PAIRS[p["id"]] = p
        except ValueError:
            pass
load()

def save():
    STORE.write_text(json.dumps([{k: v for k, v in p.items() if not k.startswith("_")} for p in PAIRS.values()]),
                     encoding="utf-8")

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

def last_turn(c):
    """The agent's last turn: (everything it said + the files it changed, its last message, stopped?)."""
    ev = c["events"]
    start = max((i for i, e in enumerate(ev) if e["type"] == "user"), default=-1)
    texts = [e["text"] for e in ev[start + 1:] if e["type"] == "text"]
    changed = [e["what"] for e in ev[start + 1:] if e["type"] == "tool" and e.get("ok")
               and e["what"].startswith(("Writing ", "Editing "))]
    out = "\n\n".join(texts).strip() or "(no reply)"
    if changed: out += "\n\n[Files changed this turn: " + "; ".join(changed) + "]"
    stopped = any(e["type"] == "error" for e in ev[start + 1:])
    return out[:MAX_REPLY], (texts[-1] if texts else ""), stopped

LIMIT = re.compile(r"(?i)hit your .{0,40}limit|usage limit|rate limit (reached|exceeded)|out of (extra )?usage|"
                   r"limit reached|quota exceeded")

def limit_hit(c):
    """If the agent's last turn ran into its usage limit: its short message (e.g. "...limit · resets 12:30pm")."""
    ev = c["events"]; start = max((i for i, e in enumerate(ev) if e["type"] == "user"), default=-1)
    for e in ev[start + 1:]:
        t = (e.get("text") or "").strip()
        if e["type"] in ("text", "error") and len(t) < 600 and LIMIT.search(t): return t
    return None

RESETS = re.compile(r"(?i)resets?\s+(?:at\s+)?(\d{1,2})(?::(\d\d))?\s*([ap]m)?")

def back_at(agent, msg):
    """When an agent that hit its limit can work again (unix time), from what it reported, or None."""
    now = time.time()
    hit = [w.get("resets") for w in CC.LIMITS[agent].values()
           if w.get("resets") and w["resets"] > now and (w.get("status") == "rejected" or (w.get("used") or 0) >= 99)]
    if hit: return max(hit)
    m = RESETS.search(msg or "")                          # "...limit · resets 12:30pm (Africa/Johannesburg)"
    if not m: return None
    h, mi = int(m.group(1)) % 12 if m.group(3) else int(m.group(1)), int(m.group(2) or 0)
    if (m.group(3) or "").lower() == "pm": h += 12
    lt = time.localtime(now)
    at = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, h, mi, 0, 0, 0, -1))
    return at + 86400 if at <= now else at

# ---------------- keeping the load even ----------------
WINDOW = {"five_hour": "5-hour", "seven_day": "weekly", "seven_day_opus": "weekly Opus", "seven_day_sonnet": "weekly Sonnet"}

def usage(p):
    """Each agent's usage right now: % of its fullest limit window (if it reported one) and this pair's tokens."""
    now = time.time(); out = {}
    for a in ("claude", "codex"):
        wins = [(n, w) for n, w in CC.LIMITS[a].items() if w.get("used") is not None and (w.get("resets") or now + 1) > now]
        n, w = max(wins, key=lambda x: x[1]["used"]) if wins else (None, {})
        tok = (chat(p, a) or {}).get("tokens") or {}
        out[a] = dict(pct=w.get("used"), window=n, resets=w.get("resets"), read=tok.get("read", 0),
                      wrote=tok.get("wrote", 0), cached=tok.get("cached", 0))
    return out

def cost(x):
    """Roughly what a build's tokens weigh against a usage limit: re-read (cached) tokens count about a tenth."""
    return x["read"] + 5 * x["wrote"] + x["cached"] / 10

def kilo(n):
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{round(n / 1e3)}k"

def balance_note(p):
    """A short paragraph for each build turn: both usage numbers, and who should take the next heavy task."""
    u = usage(p); parts = []
    for a in ("claude", "codex"):
        x = u[a]; bits = []
        if x["pct"] is not None: bits.append(f"{x['pct']:.0f}% of its {WINDOW.get(x['window'], x['window'])} limit used")
        bits.append(f"{kilo(x['read'] + x['wrote'])} new tokens and {kilo(x['cached'])} re-read in this build")
        parts.append(f"{NAME[a]} {', '.join(bits)}")
    s = "USAGE: " + "; ".join(parts) + ". "
    pc, px = u["claude"]["pct"], u["codex"]["pct"]
    if pc is not None and px is not None:             # the plans differ, so compare how full each one's limit is
        low, even = ("claude" if pc < px else "codex"), abs(pc - px) < 10
    else:                                             # no limit numbers yet: compare tokens
        tc, tx = (cost(u[a]) for a in ("claude", "codex"))
        low, even = ("claude" if tc < tx else "codex"), max(tc, tx) < 1.25 * max(1, min(tc, tx))
    if even: return s + "That's about even: keep splitting the work half and half."
    return (s + f"{NAME[low]} has used less, so {NAME[low]} takes the next heavy tasks (writing code, running sims, "
                "long edits) and the other reviews, until it's even again.")

def last_reply(c):
    out, _, stopped = last_turn(c)
    return out, stopped

def starts(text, word):
    """Does the message start with WORD (ignoring markdown like ** around it)?"""
    return re.match(r"^[\s*_#>`]*" + word + r"\b", text or "", re.I) is not None

def phase_ready(text):
    """'PHASE READY: <name>' ... 'OUTPUT: <path>' lines -> (name, [paths]), or None."""
    m = re.match(r"^[\s*_#>`]*PHASE READY[*_`]*\s*:?\s*[*_`]*\s*(.*)", text or "", re.I)
    if not m: return None
    name = m.group(1).strip().strip("*_`").strip() or "this phase"
    outs = [o.strip().strip("`*").strip() for o in re.findall(r"^[\s*_`-]*OUTPUT[*_`]*\s*:\s*(.+)$", text, re.I | re.M)]
    return name[:120], [o for o in outs if o][:20]

def first_prompt(agent, task, rounds, other_reply=None):
    me, other = NAME[agent], NAME["codex" if agent == "claude" else "claude"]
    s = (f"Dean wants you ({me}) and {other} to work on this together, taking turns, for up to {rounds} "
         f"round{'s' if rounds > 1 else ''} each:\n\n{task}\n\n"
         f"Each turn you get {other}'s last reply. Split the work, check each other's work, and say clearly what you "
         "did. Changing files or running commands asks Dean first. Keep replies short. When you both agree the job "
         "is done, start your reply with AGREED: and a one-line summary.")
    if other_reply is None: return s + "\n\nYou go first."
    return s + f"\n\n{other} went first and said:\n\n{other_reply}\n\nYour turn (round 1 of {rounds})."

PHASES = ("Work in phases and stop for Dean after each one. For an episode the phases are: (1) facts and "
          "simulation: a short .md table of every number the video will claim and how it was checked; (2) the "
          "episode script; (3) the voice-over (george); (4) a style sample: a few half-size stills; (5) a half-size "
          "draft video; (6) the full render. For other builds, choose sensible phases and list them in your first "
          "turn. Never start a phase Dean hasn't reached (no voice before he's approved the script, no Blender "
          "before he's approved the voice).\n\n"
          "SPLIT THE WORK EVENLY: Dean wants you both to last as long as possible on your usage limits, so the "
          "load must be as equal as you can make it. At the start of each phase, Claude posts a short task list for "
          "the phase, each task with an owner (Claude or Codex): about half the tasks and half the heavy work "
          "(writing code, running sims, long edits) each, e.g. one writes the sim while the other writes the checks "
          "and the facts table, or one writes the script while the other checks every fact in it. Claude only keeps "
          "what only it can do: the git commits and the Blender renders. Each turn starts with a USAGE line showing "
          "how much both of you have used: if one is ahead, move the next heavy tasks to the other. Codex can change "
          "the list in its reply. Each turn, do your own open tasks, mark them done, and review what the other just "
          "did (keep reviews short: a review shouldn't cost more than the work).\n\n"
          "HELP EACH OTHER: if you hit a problem you can't fix in a couple of tries (an error, a wrong number, a "
          "design question), don't keep going round in circles: start that part of your reply with STUCK:, say what "
          "you tried and what you saw, and hand it over. The other one then helps solve it first, before its own "
          "tasks. Agree the fix between you; only ask Dean if you both can't settle it.\n\n"
          "WHEN A PHASE IS DONE and you've both checked it, start your reply with `PHASE READY: <phase name>`, then "
          "a short summary for Dean, then one line `OUTPUT: <path>` for each file he should look at (images, audio, "
          "video, the script, the facts table). Then stop: Dean reviews it and either says continue or asks for "
          "changes. When the whole build is done, start your reply with AGREED: and a summary for Dean.")

def build_first(agent, task, rounds, context, other_reply=None, handover=None):
    me, other = NAME[agent], NAME["codex" if agent == "claude" else "claude"]
    s = (f"Dean wants you ({me}) and {other} to BUILD this together, taking turns (up to {rounds} round"
         f"{'s' if rounds > 1 else ''} each per phase):\n\n{task}\n\n")
    if context: s += f"What you two agreed earlier in this chat:\n\n{context}\n\n"
    if handover: s += handover + "\n\n"
    s += ("Claude makes the git commits on the branch (Codex's sandbox can't write git), after each working step. "
          "Follow CLAUDE.md: every fact checked by simulation or a solid source, gentle on the laptop.\n\n" + PHASES)
    if other_reply is None:
        return s + ("\n\nYou go first: catch up, then post the task list for the next phase (or for what's left of "
                    "this one), then start yours." if handover else
                    "\n\nYou go first: list the phases, then the task list for phase 1, then start yours.")
    return s + f"\n\n{other} went first and said:\n\n{other_reply}\n\nYour turn (round 1 of {rounds})."

def handover_text(col):
    """For a fresh session: what the build is up to, and where to read the rest (instead of a long chat history)."""
    done = col.get("phases_done") or []
    return ("THIS IS A FRESH SESSION: to save usage, the build starts a new chat after each phase instead of "
            "re-reading the whole old one at every step. Nothing is lost: the work is in the build folder. Phases "
            f"done and approved by Dean: {', '.join(done) if done else 'none yet'}. Catch up from the files, briefly "
            "(don't re-read everything): `git log --oneline origin/main..HEAD`, `git status`, the facts table and "
            "the episode script in docs/ and episodes/, and the other's reply below.")

def fresh_sessions(p):
    """Both agents start a new chat (Claude a new session, Codex a new thread); the page keeps the old messages."""
    for a in ("claude", "codex"):
        c = chat(p, a)
        c["session_id"] = None
        CC.add(c, "dean", text="(Fresh session from here, to save usage: the old chat isn't re-read any more.)",
               files=[], how="desk")
    CC.save()

def after_review(col, name, decision):
    """Dean answered a PHASE READY: the notes each agent gets next, or None if he ended the build."""
    if decision["action"] == "stop":
        col.update(state="done", note=f"Dean ended the build after: {name}"); return None
    if decision["action"] == "carry":                  # picking up a build that stopped or paused mid-phase
        said = decision.get("notes") or "Carry on where you left off."
        head = f"Dean is picking the build back up. It had stopped ({col.get('note') or 'stopped'}).\n\n{said}\n\n"
        col.update(state="running", phase=None, outputs=[], note=""); col.pop("solo", None); col.pop("away", None)
        return {"claude": head + "Look at where the current phase stands (git status, the files, the other's last "
                                 "reply) and carry on with it.", "codex": head.strip()}
    col["phases_done"].append(name)
    if col.get("away") and not col["away"].get("until"):     # no reset time known: let it try again next phase
        col.pop("solo", None); col.pop("away", None)
    said = decision.get("notes") or "Looks good. Go on to the next phase."
    head = f"Dean reviewed \"{name}\" and said:\n\n{said}\n\n"
    col.update(state="running", phase=None, outputs=[])
    return {"claude": head + "Start the next round: act on Dean's notes (or go on to the next phase, with its task list).",
            "codex": head.strip()}

async def collaborate(p, task, files, rounds, build=None, resume=None):
    """build=None: talk it through. build=str (earlier agreement, may be empty): build it in phases.
    resume={action, notes}: carry on a build whose review was answered after the desk restarted,
    or (action "carry") one that stopped or paused mid-phase."""
    building = build is not None or resume is not None
    if resume is None:
        col = p["collab"] = dict(task=task, rounds=rounds, round=1, turn="claude", state="running", note="",
                                 mode="build" if building else "talk", phase=None, outputs=[], phases_done=[])
    else:
        col = p["collab"]
    for a in ("claude", "codex"): chat(p, a)["auto"] = building
    save()
    replies = {"claude": None, "codex": None}; lasts = {"claude": "", "codex": ""}
    t = 0; total = 0                     # turns in this phase, turns in all
    note = {}                            # agent -> Dean's review notes it hasn't seen yet
    solo_msg = "\0"                      # what the one carrying on alone was told (dropped if it never went)
    side = None; side_for = None          # the other's side turn while one runs a long command (once per turn)
    handed = False                       # fresh sessions after a phase: the first two turns get a handover briefing
    if resume is not None:
        replies = {a: last_turn(chat(p, a))[0] for a in ("claude", "codex")}; total = 2
        if resume.get("rounds"): col["rounds"] = rounds = resume["rounds"]
        note = after_review(col, col.get("phase") or "the last phase", resume)
        if note is None: save(); return
        if building: fresh_sessions(p); total = 0; handed = True
    try:
        while True:
            away = col.get("away")
            if away and away.get("until") and time.time() >= away["until"]:     # its limit has reset: back in
                back = away["agent"]; col.pop("away", None); col.pop("solo", None)
                o = col_other(back)
                if note.get(o, "").startswith(solo_msg): note[o] = note[o][len(solo_msg):].strip()   # never went alone
                if not note.get(o): note.pop(o, None)
                note[back] = (f"Your usage limit has reset, so you're back. While you were out, {NAME[col_other(back)]} "
                              "carried on alone (its last reply is below): pick your share of the work back up.")
                if (t % 2 == 0) != (back == "claude"): t += 1          # the one coming back goes next
            solo = col.get("solo")
            agent = solo or ("claude" if t % 2 == 0 else "codex"); other = col_other(agent)
            r = t // 2 + 1
            col.update(round=r, turn=agent); save()
            if total < 2 and handed:
                h = handover_text(col)
                if total == 0: h += f"\n\n{NAME[other]}'s last reply before the fresh start:\n\n{replies[other]}"
                prompt = build_first(agent, col["task"], rounds, "", replies[other] if total else None, handover=h)
            elif total < 2:
                prompt = (build_first(agent, task, rounds, build, replies[other]) if building
                          else first_prompt(agent, task, rounds, replies[other]))
            elif solo:
                prompt = f"Your turn (round {r} of {rounds} in this phase), still working alone."
            else:
                prompt = f"{NAME[other]} replied:\n\n{replies[other]}\n\nYour turn (round {r} of {rounds}" + \
                         (" in this phase)." if building else ").")
            if building: prompt = balance_note(p) + "\n\n" + prompt
            if agent in note: prompt = note.pop(agent) + "\n\n" + prompt
            waiting = NOTES.get(p["id"], {}).pop(agent, None)
            if waiting: prompt = "Dean's messages to you since your last turn:\n\n" + "\n\n".join(waiting) + "\n\n" + prompt
            if not building and r == rounds and agent == "codex":
                prompt += " This is the last turn: finish up and sum up what was done and what's left for Dean."
            if building and r == rounds and agent == "codex":
                prompt += (" This is the last turn of this phase: if the phase is done, say PHASE READY; if not, "
                           "sum up where it stands for Dean.")
            c = chat(p, agent)
            while c["status"] == "running": await asyncio.sleep(1)      # Dean messaged it by hand: wait
            job = asyncio.create_task(MOD[agent].turn(c, prompt, files if total < 2 and not handed else []))
            while not job.done():                     # while it's busy with a long command, the other works alongside
                await asyncio.wait({job}, timeout=POLL)
                busy = long_step(c)
                if busy and building and not solo and not col.get("away") and (side is None or side.done())                         and side_for != id(job) and chat(p, other)["status"] == "idle":
                    side = asyncio.create_task(side_turn(p, col, other, agent, busy)); side_for = id(job)
            await job
            replies[agent], last, stopped = last_turn(c); lasts[agent] = last
            total += 1; t += 2 if solo else 1          # alone, each turn is a whole round
            hit = limit_hit(c)
            if hit and building and not solo:
                # don't stop the build: the other one carries on alone, and hands back when the limit resets
                until = back_at(agent, hit)
                at = f" until about {time.strftime('%H:%M', time.localtime(until))}" if until else ""
                col.update(solo=other, away=dict(agent=agent, until=until, msg=hit[:160]),
                           note=f"{NAME[agent]} hit its usage limit{at}; {NAME[other]} carries on alone")
                solo_msg = (f"{NAME[agent]} has hit its usage limit{at}. Carry on alone with everything you can "
                            "do (code, sims, checks, the facts table, docs) so the build keeps moving. "
                            + ("Leave the git commits and Blender renders for Claude: list them at the end of "
                               "your reply under FOR CLAUDE:. " if other == "codex" else "Make the commits as usual. ")
                            + "When the phase is done, say PHASE READY.")
                note[other] = solo_msg + ("\n\n" + note[other] if other in note else "")   # keep Dean's notes
                if (t % 2 == 0) != (other == "claude"): t += 1
                save(); continue
            if hit:                                   # both out (or just talking): pause, don't pass turns back and forth
                col.pop("solo", None); col.pop("away", None)
                col.update(state="paused", note=f"{NAME[agent]} hit its usage limit: {hit[:160]}"); return
            if stopped:
                col.update(state="stopped", note=f"{NAME[agent]}'s turn stopped or failed"); return
            if starts(last, "AGREED") and (solo or starts(lasts[other], "AGREED")):        # both said so, one after the other
                col.update(state="agreed", note=f"{'Build finished' if building else 'Both agreed'} (round {r})"); return
            ready = phase_ready(last) if building else None
            if building and (ready or t >= 2 * rounds):
                name, outs = ready or ("Rounds ran out before the phase was finished", [])
                col.update(state="review", phase=name, outputs=outs, by=agent, note=""); save()
                fut = REVIEWS[p["id"]] = asyncio.get_running_loop().create_future()
                decision = await fut
                REVIEWS.pop(p["id"], None)
                note = after_review(col, name, decision)
                if note is None: return
                t = 0; lasts = {"claude": "", "codex": ""}
                fresh_sessions(p); total = 0; handed = True     # a new phase: new chats, short handover
                continue
            if not building and t >= 2 * rounds:
                col.update(state="done", note=f"Finished {rounds} round{'s' if rounds > 1 else ''}"); return
    except asyncio.CancelledError:
        if side and not side.done(): side.cancel()
        col.update(state="stopped", note="Stopped by Dean"); raise
    finally:
        f = REVIEWS.pop(p["id"], None)
        if f and not f.done(): f.cancel()
        for a in ("claude", "codex"):
            if chat(p, a): chat(p, a)["auto"] = False
        TASKS.pop(p["id"], None); CC.save(); save()

LONG = 90                                # seconds a single command runs before the other gets a side turn
POLL = 5                                 # how often (seconds) to look whether it is busy with one

def long_step(c):
    """The command an agent has been running for over LONG seconds (a render, a long sim), or None."""
    if c["status"] != "running": return None
    for e in reversed(c["events"][-4:]):
        if e["type"] == "tool" and e.get("out") is None and time.time() - e["t"] > LONG: return e["what"]
    return None

async def side_turn(p, col, me, busy_agent, what):
    """A turn for `me` alongside the other's long command: its own tasks, on other files, never a render."""
    c = chat(p, me); c["_side"] = True; col["side"] = me; save()
    prompt = (balance_note(p) + "\n\n" + f"SIDE TURN: {NAME[busy_agent]} is busy with a long command, so you don't "
              f"have to wait for it: {what[:300]}\n\nWhile it runs, do your own open tasks from the task list, or "
              "useful prep for what comes next (checks, the next script or step). Rules for a side turn: work only on "
              f"files {NAME[busy_agent]} isn't changing; don't start Blender or any render (one at a time on this "
              "laptop); no git commits. Keep it short and say what you did: it's passed on in your next turn.")
    if not c.get("session_id"):                    # a fresh session that hasn't had a turn yet: brief it first
        prompt = (f"You ({NAME[me]}) and {NAME[busy_agent]} are building this for Dean, taking turns:\n\n{col['task']}"
                  f"\n\n{handover_text(col)}\n\n" + prompt)
    try:
        await MOD[me].turn(c, prompt, [])
    except Exception:
        pass
    finally:
        c["_side"] = False; col.pop("side", None); save()

def col_other(agent):
    return "codex" if agent == "claude" else "claude"

def start_collab(p, task, files, rounds):
    TASKS[p["id"]] = asyncio.create_task(collaborate(p, task, files, rounds))

def queue(p, agent, text, files=()):
    """A message from Dean for an agent that's waiting for its turn in a collaboration."""
    full = text + ("\n(Files: " + ", ".join(f"desk/uploads/{f}" for f in files) + ")" if files else "")
    NOTES.setdefault(p["id"], {}).setdefault(agent, []).append(full)
    CC.add(chat(p, agent), "dean", text=text, files=list(files), how="for its next turn"); CC.save()

# ---------------- progress updates ----------------
def digest_chat(c, n=30):
    """The last steps of a chat as compact text, for a progress summary."""
    now = time.time(); rows = [f"{NAME.get(c.get('agent'), 'Claude')}: {'WORKING' if c['status'] == 'running' else 'idle'}"]
    for e in c["events"][-n:]:
        at = time.strftime("%H:%M:%S", time.localtime(e["t"]))
        if e["type"] == "tool":
            state = "RUNNING for %ds" % (now - e["t"]) if e.get("out") is None and c["status"] == "running" else \
                    ("ok" if e.get("ok") else "failed")
            rows.append(f"{at} step: {e['what'][:200]} [{state}]" + (f" -> {e['out'][:300]}" if e.get("out") else ""))
        elif e["type"] == "perm": rows.append(f"{at} asked Dean: {e['what'][:200]} [{e['state']}]")
        elif e["type"] in ("text", "user", "dean", "error"): rows.append(f"{at} {e['type']}: {e.get('text', '')[:900]}")
        elif e["type"] == "done": rows.append(f"{at} turn finished")
    if c.get("_live"): rows.append(f"now writing: {c['_live'][-600:]}")
    return "\n".join(rows)

def digest_pair(p):
    col = p.get("collab") or {}
    head = (f"{'Build' if col.get('mode') == 'build' else 'Collaboration'} on: {col.get('task', '')[:300]}\n"
            f"state: {col.get('state')}, round {col.get('round')} of {col.get('rounds')}, {col.get('turn')}'s turn; "
            f"phase waiting for Dean: {col.get('phase')}; phases done: {col.get('phases_done')}") if col else "no collaboration"
    return head + "\n\n" + "\n\n".join(digest_chat(chat(p, a), 25) for a in ("claude", "codex") if chat(p, a))

async def summarise(digest):
    from claude_agent_sdk import AssistantMessage as AM, ClaudeAgentOptions as Opts, TextBlock as TB, query
    import shutil
    ask = ("Dean is watching Claude and/or Codex work on his science-video project from a local page, and asks "
           "\"how's it going?\". From the log below, answer in 3 to 6 short bullets of plain English: where they are "
           "(phase, round, whose turn), what they're doing right now and for how long, what's done, anything stuck, "
           "failing or waiting for Dean, and what comes next. Use the numbers from the log; don't guess. Builds already "
           "run on their own branch in a separate folder, so don't comment on git or process rules. Times are "
           f"local; it's now {time.strftime('%H:%M:%S')}.\n\nLOG:\n{digest}")
    out = []
    async for m in query(prompt=ask, options=Opts(model="haiku", max_turns=1, allowed_tools=[], setting_sources=[],
                                                  cli_path=shutil.which("claude"), cwd=str(CC.HERE))):
        if isinstance(m, AM): out += [b.text for b in m.content if isinstance(b, TB)]
    return "\n".join(out).strip() or "(no answer)"

def review(p, action, notes):
    """Dean's answer to PHASE READY: continue (with optional notes) or stop. Call it from the event loop."""
    decision = {"action": action, "notes": notes.strip()}
    f = REVIEWS.get(p["id"])
    if f and not f.done():
        f.set_result(decision); return True
    col = p.get("collab") or {}
    if col.get("state") == "review" and p["id"] not in TASKS:            # the desk restarted while it waited
        TASKS[p["id"]] = asyncio.create_task(collaborate(p, col["task"], [], col["rounds"], resume=decision))
        return True
    return False

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
            "Work only in that folder. renders/, .venv and the third-party assets are shared with Dean's main folder "
            "(linked in): run Python as .venv\\Scripts\\python.exe from the build folder, not by the main folder's path. "
            "Its files and CLAUDE.md are main's: work that isn't merged yet lives on other branches (read it with git show). "
            "Edits and test runs in this folder don't ask Dean; Blender, installs, deletes and the network still do. "
            "Claude makes the git commits on this branch; Codex never runs git commands that change anything. "
            "Nobody pushes: Dean does that.")

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
    old = p.get("build") or {}
    p["build"] = dict(branch=branch, path=str(path),
                      started=old.get("started") if old.get("path") == str(path) else time.time())
    CC.save(); save()

def start_build(p, task, files, rounds, branch):
    context = p.pop("_context", "")
    TASKS[p["id"]] = asyncio.create_task(collaborate(p, task, files, rounds, build=context))

# ---------------- what a build has made (for the Outputs panel) ----------------
BIG_DIR = 60                      # a folder with more new files than this (frames) shows as one line

def allowed_roots():
    return [(CC.ROOT / "renders").resolve()] + [Path(p["build"]["path"]).resolve() for p in PAIRS.values() if p.get("build")]

def outputs(p):
    b = p.get("build")
    if not b: return []
    root = Path(b["path"]); since = b.get("started") or 0; seen = {}
    def add(f, src):
        try: st = f.stat()
        except OSError: return
        if f.is_file(): seen[str(f.resolve())] = dict(path=str(f.resolve()), name=f.name, src=src, size=st.st_size, mtime=st.st_mtime)
    try:                                                     # files the build changed or added, committed or not
        names = set(git("diff", "--name-only", "origin/main...HEAD", cwd=root).splitlines())
        names |= {l[3:].strip().strip('"') for l in git("status", "--porcelain", "-uall", cwd=root).splitlines() if len(l) > 3}
        for n in names:
            if not n.startswith(("renders/", ".venv/")): add(root / n, "build")
    except RuntimeError:
        pass
    renders = CC.ROOT / "renders"                            # renders made since the build started
    for d in (renders.iterdir() if renders.exists() else []):
        try:
            if not d.is_dir() or d.stat().st_mtime < since: continue
        except OSError: continue
        for dirpath, dirs, fs in os.walk(d):
            new = []
            for f in fs:
                try:
                    if (Path(dirpath) / f).stat().st_mtime >= since: new.append(Path(dirpath) / f)
                except OSError: pass
            if len(new) > BIG_DIR:
                last = max(new, key=lambda f: f.stat().st_mtime)
                add(last, "renders")
                seen[str(last.resolve())]["name"] = f"{last.name} (newest of {len(new)} files in {Path(dirpath).name}/)"
            else:
                for f in new: add(f, "renders")
    for o in (p.get("collab") or {}).get("outputs") or []:  # what the agents pointed Dean to
        f = Path(o) if Path(o).is_absolute() else root / o
        add(f, "phase")
        if str(f.resolve()) in seen: seen[str(f.resolve())]["flag"] = True
    return sorted(seen.values(), key=lambda x: -x["mtime"])[:200]

# ---------------- how long a render has left ----------------
FRAME = (".jpg", ".png", ".exr")
FRAMES_OF = re.compile(r"frame \d+\s*/\s*(\d+)")         # render scripts log "frame 207/1058 ..."
ETA_CACHE = {}                                            # pair id -> (when, answer): the page asks every second

def render_eta(p):
    """While Blender renders for a build: frames done of the whole video, seconds per frame, time left.
    Counts the frames saved so far (a stopped render picks up where it left off, so batches add up)."""
    hit = ETA_CACHE.get(p["id"])
    if hit and time.time() - hit[0] < 5: return hit[1]
    ETA_CACHE[p["id"]] = (time.time(), None)
    cmds = [e["what"] for a in ("claude", "codex") if chat(p, a)
            for e in chat(p, a)["events"][-6:] if e["type"] == "tool" and e.get("out") is None and "blender" in e["what"].lower()]
    if not p.get("build") or not cmds: return None
    renders = CC.ROOT / "renders"; best = None
    for ep in (renders.iterdir() if renders.exists() else []):             # the frames folder written to last
        for d in ([ep] + [x for x in ep.iterdir() if x.is_dir()]) if ep.is_dir() else []:
            try: newest = max((f.stat().st_mtime for f in d.iterdir() if f.suffix.lower() in FRAME), default=0)
            except OSError: continue
            if newest > time.time() - 180 and (not best or newest > best[0]): best = (newest, d)
    if not best: return None
    d = best[1]
    times = sorted(f.stat().st_mtime for f in d.iterdir() if f.suffix.lower() in FRAME)
    gaps = sorted(b - a for a, b in zip(times[-31:], times[-30:]))
    per = gaps[len(gaps) // 2] if gaps else None          # the median: a pause between batches doesn't skew it
    total = None
    for log in sorted((d.parent if d.parent != renders else d).glob("*.log"), key=lambda f: -f.stat().st_mtime)[:1]:
        found = FRAMES_OF.findall(log.read_text(encoding="utf-8", errors="replace")[-20000:])
        if found: total = int(found[-1])
    if not total:                                         # else the batch's --end (0 means "to the end": unknown)
        ends = [int(x) for x in re.findall(r"--end\D{1,4}(\d+)", cmds[-1]) if int(x) > 0]
        total = max(ends) if ends else None
    done = len(times)
    left = max(0, total - done) * per if total and per else None
    ans = dict(folder=str(d.relative_to(renders)), done=done, total=total, per=per, left=left,
               finish=time.time() + left if left is not None else None)
    ETA_CACHE[p["id"]] = (time.time(), ans)
    return ans

def resolve_output(p, path):
    """Where a PHASE READY output path points (relative ones are inside the build folder)."""
    f = Path(path)
    if not f.is_absolute() and p.get("build"): f = Path(p["build"]["path"]) / f
    return f.resolve()

def carry_on(p, notes, rounds):
    """Pick a stopped or paused build back up in its own folder, on its own branch (no new folder)."""
    col = p.get("collab") or {}
    if p["id"] in TASKS: return "they're already working"
    if not p.get("build") or col.get("mode") != "build": return "there's no build to carry on"
    if col.get("state") == "review": return "a phase is waiting for your review: use Continue on its card"
    if not Path(p["build"]["path"]).is_dir(): return "the build folder is gone"
    TASKS[p["id"]] = asyncio.create_task(collaborate(p, col["task"], [], rounds, resume={
        "action": "carry", "notes": notes.strip(), "rounds": rounds}))
    return None

async def stop(p):
    review(p, "stop", "")
    for a in ("claude", "codex"):                  # interrupt the agents first, then end the loop
        c = chat(p, a)
        if c and c["status"] == "running": await MOD[a].stop(c["id"])
    t = TASKS.get(p["id"])
    if t: t.cancel()

def delete(p):
    for a in ("claude", "codex"): CC.CHATS.pop(p[a], None)
    PAIRS.pop(p["id"], None); CC.save(); save()
