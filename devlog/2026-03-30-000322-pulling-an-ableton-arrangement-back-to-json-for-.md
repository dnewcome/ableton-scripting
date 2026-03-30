# Pulling an Ableton arrangement back to JSON for a full round-trip

_2026-03-30_

## What happened

The push side worked well, but to make this genuinely useful I needed to be able to read a session back out too — so you can pull what's in Ableton, edit the JSON (manually or with an LLM), and push changes back. The first version of `pull_song.py` read from the session view using scene names and follow actions to reconstruct sections, which worked but was fragile and complex. Today I rewrote it to read directly from `arrangement_clips` instead. The arrangement gives you positions and lengths directly — no heuristics needed. You lose section names on the way out (arrangement clips don't store them, so sections come back as A, B, C…) but that's a fine trade. The workflow is now: `setup_song.py` to push, edit JSON or let an LLM touch it, `setup_song.py` again to re-render. Each push clears and rewrites the arrangement so it's fully idempotent.

## Files touched

  - pull_song.py
  - setup_song.py
  - AbletonMCP_Remote_Script/__init__.py

## Tweet draft

Completed the round-trip: `pull_song.py` now reads the Ableton arrangement back to JSON. First version used session view scene names to reconstruct sections — too clever. Switched to reading `arrangement_clips` directly: positions and lengths, no heuristics. Lose section names on pull but gain simplicity. Now the loop is: edit JSON → push → tweak in Ableton → pull → edit → repeat [link]

---

_commit: 9ade269 · screenshot: no screenshot_
