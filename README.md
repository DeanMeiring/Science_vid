# Science_vid

YouTube Shorts (later long-form) of maths and science experiments: simple
rules, surprising results. Each video is one "experiment", explained by a
narrator while it runs: zoomed in on the rules first, then zooming out as it
speeds up. Each episode changes one thing from the last.

First episode: **Experiment #1, Langton's Ant** (prototype in `prototypes/`).

## Set up the laptop (once)

1. Install:
   - [VS Code](https://code.visualstudio.com/) and the **Claude Code**
     extension (Extensions panel, search "Claude Code").
   - [Git](https://git-scm.com/downloads).
   - [Python 3.11](https://www.python.org/downloads/). On Windows, tick
     "Add python.exe to PATH" in the installer.
   - [ffmpeg](https://ffmpeg.org/download.html). On Windows, run
     `winget install Gyan.FFmpeg`. On Mac, run `brew install ffmpeg`.
   - [Blender](https://www.blender.org/download/) (latest LTS).
2. Clone the repo and open it in VS Code:

   ```
   git clone https://github.com/DeanMeiring/Science_vid.git
   cd Science_vid
   code .
   ```

3. Make a Python environment and install the packages:

   ```
   python -m venv .venv
   # Windows:  .venv\Scripts\activate
   # Mac:      source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. For the voice cloning, set up a free Hugging Face account:
   - Sign up at huggingface.co.
   - Accept the terms at huggingface.co/kyutai/pocket-tts.
   - Make a read token (Settings → Access Tokens).
   - Claude will ask for it when setting up the voice.
5. Open Claude Code in VS Code and say:
   "read CLAUDE.md and let's continue".

## Make an episode

Each episode is a file in `episodes/` (narration lines, rule cards, title and
description). Blender is the portable 4.5 LTS in
`%LOCALAPPDATA%\Programs\Blender\blender-4.5.10-windows-x64\blender.exe`.

```
.venv/Scripts/python pipeline/voice.py episodes/ep01_farm.py      # narration + timing (seconds)
blender -b -P blender/render_video.py -- episodes/ep01_farm.py --scale 50 --every 30   # quick draft frames
.venv/Scripts/python pipeline/compose.py episodes/ep01_farm.py --draft                # draft video
blender -b -P blender/render_video.py -- episodes/ep01_farm.py   # full size (~35-60 min, low priority)
.venv/Scripts/python pipeline/compose.py episodes/ep01_farm.py   # final video + thumbnail
```

Everything lands in `renders/<episode>/`. A stopped render picks up where it
left off. One still for checking the look: `blender -b -P blender/ant_scene.py
-- --step 12 --theme farm`.

## Studio: watch and post

```
.venv/Scripts/python studio/app.py        # then open http://localhost:8765
```

Watch each episode, edit the title and description, and post it to YouTube
and Instagram. It only runs on this laptop; logins are kept in `.tokens/`
(never committed). The keys go in `.env`:

**YouTube** (the same Google Cloud project as CLIPPER is fine):
1. Google Cloud Console → APIs & Services → Credentials → your OAuth client
   (type "Web application") → add the redirect URI
   `http://localhost:8765/auth/youtube/callback`.
2. Make sure "YouTube Data API v3" is enabled.
3. Put `YOUTUBE_OAUTH_CLIENT_ID=...` and `YOUTUBE_OAUTH_CLIENT_SECRET=...`
   in `.env`.
4. If the consent screen is still in "Testing", add your Google account as a
   test user. Google ends Testing-mode logins after 7 days, so press Connect
   again then (or publish the consent screen).

**Instagram** (the same Meta app as CLIPPER is fine):
1. The Instagram account must be a professional (creator or business)
   account, linked to a Facebook Page.
2. Meta app → Facebook Login → Settings → Valid OAuth Redirect URIs: add
   `http://localhost:8765/auth/instagram/callback`.
3. Put `INSTAGRAM_APP_ID=...` and `INSTAGRAM_APP_SECRET=...` in `.env`
   (optional: `INSTAGRAM_FB_CONFIG_ID=...`).

## Agent desk: ask Claude and Codex

```
.venv/Scripts/python desk/app.py          # then open http://localhost:8770
```

One page on this laptop to ask Claude Code, Codex or both the same question (with files attached), and a
"You two talk to each other" button: they take turns on a topic, reading the conversation so far, and stop
when they agree. It drives the `claude` and `codex` command-line tools you're already logged in to (no extra
cost). Read-only unless "Allow file edits" is ticked; it never pushes, merges or posts. It only listens on
127.0.0.1: never put it on the internet. Uploads and history stay in `desk/` (gitignored).

The **Chats** tab works like Claude Code itself: live chats with Claude or Codex that remember the
conversation and show every step. Before changing a file or running a command that isn't a plain read, the
page asks with Allow once / Allow in this chat / Deny. Push, merge and post commands are refused whatever is
clicked. Claude runs through the Claude Agent SDK (`desk/claude_chat.py`), Codex through `codex app-server`
(`desk/codex_chat.py`, in its workspace-write sandbox: writes only inside the repo, no network).
**Start Claude + Codex** opens both side by side: send a message to one or both, or type a task and press
**Collaborate for N rounds**. They take turns (Claude first), each getting the other's last reply, and stop
early when both start a reply with AGREED (`desk/pair_chat.py`). Every change still asks first.

## Run the prototypes

```
python prototypes/ant_3d.py experiment_1_3d.mp4      # 3D look (~5-10 min)
python prototypes/ant_3d.py out.mp4 60,700,1050      # just 3 preview frames
python prototypes/ant_2d.py experiment_1_2d.mp4      # flat look (~3 min)
python prototypes/gallery.py ideas.jpg               # stills of 9 experiments
```

Renders (`*.mp4`, `*.wav`) and voice samples (`voices/`) are kept out of git.

## Fonts

Anton, Inter and Source Serif 4 are in `assets/fonts`, under the SIL Open
Font License (see the `OFL-*.txt` files).
