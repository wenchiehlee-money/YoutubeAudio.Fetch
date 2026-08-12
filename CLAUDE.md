# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`YoutubeAudio.Fetch` is a data/working-space repo (not an app) that holds financial-YouTube audio
sources and the ground-truth/final transcripts produced for them. It does not run a transcription
pipeline itself — it triggers one asynchronously on a separate Mac-mini repo via GitHub issues, and
receives the results back via `git pull`.

It shares the same Mac-mini whisper pipeline as the `InvestorConference` repo (法說會音訊). The only
differences are `WHISPER_SOURCE_TYPE=youtube` and the stem naming convention (see below).

## Commands

```bash
pip install -r requirements.txt   # also requires yt-dlp and ffmpeg CLIs on PATH

# 1. Fetch newest N videos' audio from a channel, publish as Release assets, update the manifest
python skills/skill-youtube-channel-fetch/scripts/channel_fetch.py fetch \
    https://www.youtube.com/@fubonsec --limit 5

# 2. Open/close generate-FIN issues for every stem in the manifest that doesn't have a FIN.srt yet
python skills/skill-mlx-api-client-whisper/scripts/whisper_issue_client.py sync audio_manifest.json
# (or pass --sync to the channel_fetch.py call above to do both in one step)

# Check whether a single stem's FIN.srt has landed
python skills/skill-mlx-api-client-whisper/scripts/whisper_issue_client.py status <channel>_<video_id>

# 3. Once FIN.srt exists: find chart/diagram moments in the transcript and save frame PNGs
python skills/skill-srt-keyframe-extract/scripts/keyframe_extract.py extract <stem> \
    --srt data/<channel>/<stem>_FIN.srt \
    --video-url https://www.youtube.com/watch?v=<video_id>

# Update a skill to the latest version from the skills registry
python skills/<skill-name>/self_update.py
```

There is no test suite, lint config, or build step in this repo.

## Architecture

### Data layout (the actual "product" of this repo)

```
data/{channel}/{channel}_{video_id}_GT.srt   # human-corrected ground truth (single source of truth)
data/{channel}/{channel}_{video_id}_FIN.srt  # pipeline-selected final transcript (by CER)
```

`video_id` is always the 11-char YouTube ID. `stem = {channel}_{video_id}`.

### Issue-driven async pipeline (`skills/skill-mlx-api-client-whisper/scripts/whisper_issue_client.py`)

Unlike a typical API client, `WhisperIssueClient` does not call an HTTP endpoint — whisper
transcription takes ~1–1.5 hours per stem and is stateful (multi-experiment transcription →
LLM postprocess → CER scoring → git commit). Instead:

1. This repo opens a `generate-FIN`-labeled issue on `WHISPER_TARGET_REPO` (the Mac-mini repo),
   with YAML metadata in the issue body (`task_type`, `source_repo`, `source_type`, `stem`,
   `audio_url`, `expected_fin_srt_path`, optionally `stock_id`).
2. A self-hosted runner on the Mac-mini (`run-pipeline.yml`) picks it up on the `labeled` event.
   **Labels must be added in a separate API call after issue creation** — GitHub does not fire a
   `labeled` webhook for labels set inline at creation time, only for labels added afterward. This
   caused a real 3-week-stuck issue (Mac-mini issue #21); don't "simplify" `open_fin_request` back
   to a single inline-labeled create call.
3. When done, the Mac-mini pipeline commits `FIN.srt`/`GT.srt` back into *this* repo's `data/` tree.
4. `check_fin_status()` only checks whether the file exists locally (post-`git pull`) — it never
   calls the GitHub API to check completion. `close_if_done()` then comments and closes the issue.

`sync_manifest()` is the main entry point: for every `{stem: audio_url}` in `audio_manifest.json`,
it closes the issue if `FIN.srt` already landed, otherwise opens a `generate-FIN` issue if none is
already open (idempotent — checks `list_open_issues()` by title first).

To re-score an existing `GT.srt` that was hand-corrected (without re-transcribing), call
`open_fin_request(stem, audio_url, task_type="refine_fin_srt")` instead of the default
`generate_fin_srt`.

### Stem parsing (`parse_stem`, `STEM_PATTERNS`)

`source_type` determines both the stem regex and how `group_id` (and thus the `data/{group_id}/`
directory) is derived — this must stay symmetric with the parsing rules in the Mac-mini repo's
`skill-mlx-api-server-whisper`:

- `youtube`: `{channel}_{video_id}` (video_id fixed 11 chars) → `group_id = channel`
- `investor_conference`: `{stock_id}_{year}_q{quarter}` → `group_id = stock_id`

This repo always uses `youtube` (set via `WHISPER_SOURCE_TYPE` in `.env`).

### Config (`.env`, see `.env.example`)

- `WHISPER_TARGET_REPO` — Mac-mini repo that runs the pipeline (e.g. `ZhongZheng782/Mac-mini`)
- `WHISPER_SOURCE_REPO` — this repo (`wenchiehlee-money/YoutubeAudio.Fetch`)
- `WHISPER_SOURCE_TYPE` — `youtube` for this repo
- `REPO_FILE_SYNC_ZHONGZHENG782_MONEY` — PAT scoped to `WHISPER_TARGET_REPO` only, `Issues: Read and
  write`. No `Contents` access is needed on either repo — issue creation only needs write on the
  target repo, and completion is detected via local file existence, not the API. Falls back to
  `GH_TOKEN` if no `REPO_FILE_SYNC_*` var is set.

### Upstream of the pipeline: channel fetch and keyframe extraction

Two additional vendored skills bracket the whisper pipeline described above:

- **`skills/skill-youtube-channel-fetch`** (`scripts/channel_fetch.py`) runs *before* the
  whisper pipeline. It lists a channel's newest videos via `yt-dlp`, downloads audio for any
  stem not already in the manifest or already transcribed, publishes each audio file as a
  GitHub Release asset on `WHISPER_SOURCE_REPO` (tag `audio-{stem}`) — because the Mac-mini
  pipeline fetches audio via `gh release download` and only falls back to a raw `audio_url` —
  and writes `{stem: browser_download_url}` into `audio_manifest.json`. Needs a separate PAT
  (`REPO_FILE_SYNC_WENCHIEHLEE_MONEY`, falling back to `YOUTUBE_FETCH_TOKEN`/`GH_TOKEN`) scoped
  to Contents: Read/write on *this* repo — distinct from and broader than the Issues-only PAT
  `whisper_issue_client.py` uses on the *target* repo.
- **`skills/skill-srt-keyframe-extract`** (`scripts/keyframe_extract.py`) runs *after* a
  `FIN.srt` exists. It sends the SRT transcript through the shared `../llm` package
  (`LLMClient.generate_json`, provider fallback chain `codex -> gemini -> mlx` — not a direct
  Anthropic API call) to semantically identify moments where on-screen charts/slides/numbers are
  likely referenced, then downloads the source video with `yt-dlp` (temp-only, deleted after
  use — the whisper pipeline never touches video, only audio) and uses `ffmpeg -ss <timestamp>`
  to grab one frame per identified moment, saved as
  `data/{channel}/{stem}_keyframes/{stem}_{HHMMSS}.png`.

### The `skills/` directory

`skills/skill-mlx-api-client-whisper` is a vendored copy of a skill from a central skills registry
(`wenchiehlee/skills`, `common/skill-mlx-api-client-whisper`). The registry copy is the source of
truth; this repo's copy and `InvestorConference`'s copy are both deployments kept in sync via
`self_update.py` (see `metadata.json` for version and deployment list). Don't hand-edit
`whisper_issue_client.py` here expecting changes to persist — fix it upstream in the registry repo
and re-run `self_update.py`, unless you're doing a one-off local experiment.

Full design details (issue metadata schema, stem parsing rules, company-configs tuning / GT
correction loop) live in the Mac-mini repo's `skills/skill-mlx-api-server-whisper/SKILL.md`, not
in this repo.
