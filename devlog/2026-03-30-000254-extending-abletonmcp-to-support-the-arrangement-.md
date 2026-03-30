# Extending AbletonMCP to support the arrangement view

_2026-03-30_

## What happened

The [AbletonMCP](https://github.com/ahujasid/ableton-mcp) remote script is great for session view work but had no arrangement support at all. I forked it and added the commands I needed: `copy_clip_to_arrangement`, `get_arrangement_clips`, `set_clip_loop`, and a few others. The tricky part wasn't the commands themselves — it was a sequencing constraint in the Live API: `duplicate_clip_to_arrangement()` uses the session clip's `loop_end` as the arrangement clip length, so you can't set the loop region until after placement or you get clips that are the wrong size. There's no direct "create arrangement clip" API, so session clips act as a staging area — you build them first, copy them to the timeline, then set their loop points. Once I had that order right the arrangement rendering started working reliably.

## Files touched

  - AbletonMCP_Remote_Script/__init__.py (dnewcome/ableton-mcp fork)
  - setup_song.py

## Tweet draft

Forked AbletonMCP to add arrangement view support. The Live API has no direct "create arrangement clip" call — you have to stage clips in the session view first, then duplicate them to the timeline. Also hit a fun sequencing bug: setting loop_end before placement made every arrangement clip the wrong length. Once I got the order right everything snapped into place [link]

---

_commit: 5bbc98c · screenshot: no screenshot_
