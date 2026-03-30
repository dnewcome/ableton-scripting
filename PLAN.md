# Ableton Scripting — Project Plan

## Goal

Build a round-trip workflow between a human/LLM-editable JSON format (`.song.json`) and Ableton Live's arrangement view. The intent is to compose and edit song arrangements offline (in code or with an LLM), then push the result into Ableton — not to manipulate the live session interactively.

---

## Architecture

### Components

| Component | Location | Role |
|---|---|---|
| `setup_song.py` | `ableton-scripting/` | Push `.song.json` → Ableton (create tracks, session clips, render to arrangement) |
| `pull_song.py` | `ableton-scripting/` | Pull Ableton arrangement → `.song.json` skeleton |
| `AbletonMCP_Remote_Script/__init__.py` | `../ableton-mcp/` | Extended fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) — exposes Live API over a local socket on port 9877 |

### The JSON format

`.song.json` has three top-level sections:
- **`clips`** — a named clip library (MIDI notes, loop length). Clips are defined once and reused across tracks/sections.
- **`tracks`** — track definitions (name, instrument URI)
- **`sections`** — ordered list of sections, each with a name, bar count, and a `track_id → clip_id` map

See `fminor_groove.song.json` for a working example (5-section F minor groove).

### Push workflow (`setup_song.py`)

1. Set tempo
2. Create tracks, load instruments
3. Create session view clips with notes (session view is used as a staging area — the Live API requires a session clip source for arrangement placement)
4. **Clear the arrangement** (added 2026-03-29 — makes push idempotent)
5. Copy session clips to arrangement timeline via `duplicate_clip_to_arrangement`, accumulating beat positions per section
6. Set session clip loop points after arrangement pass (loop_end must be set after placement or it affects arrangement clip length)

### Pull workflow (`pull_song.py`)

Reads the arrangement view and reconstructes a `.song.json`:

1. Read session metadata (tempo, time sig, track count)
2. Read track info (names, instrument URIs)
3. Call `get_arrangement_clips` per track to get timeline positions
4. Collect unique `start_time` values across all tracks → section boundaries
5. For each section: call `get_arrangement_clip_notes` per clip, convert pitches to note names, de-duplicate content into the clip library
6. Label sections A, B, C, … (arrangement clips carry no section names)

---

## Key Decisions

### Pull from arrangement view, not session view (2026-03-29)

**Decision:** `pull_song.py` now reads `track.arrangement_clips` instead of `track.clip_slots`.

**Rationale:** The arrangement view is the actual song. The session view is a scratch pad used during push. Reading the session view back gave us clip content but required complex scene-grouping heuristics (follow actions, named scenes) to reconstruct section order. The arrangement gives us positions directly.

**Trade-off:** Section names are lost on pull — arrangement clips carry clip names (e.g. "Fm Arp"), not section names. Sections are re-labelled A/B/C/… on every pull. This is acceptable because the JSON is meant to be edited by a human or LLM before pushing back.

**Session view pull (old version):** The session-based `pull_song` is preserved in git history at commit `9ade269` (2026-03-15). It grouped scenes into sections using scene names and follow actions (follow_action_a == 4 = Next meant "continue current section"). Recover it with:
```
git show 9ade269:pull_song.py
```

### Session view as staging area (not bypassed)

`duplicate_clip_to_arrangement()` in the Live API requires a session clip source — there is no direct "create arrangement clip" API. The two-pass approach in `setup_song.py` (session first, then arrangement) is the right design given this constraint.

### Follow actions — deprioritized (2026-03-29)

Significant effort was spent getting follow actions to work for session-view playback. The core bug: setting `loop_end` resets `follow_action_time` to match it, so the two operations must happen in the same scheduler task. The fix (combining them in `set_clip_loop`) is in the remote script but `setup_song.py` still uses two separate calls.

**Decision:** Don't invest more time in follow actions right now. The arrangement view is the primary target. Follow action support in the session view can be revisited later if needed. The fix is already in place in the remote script if needed.

---

## Remote Script Extensions

The fork at `../ableton-mcp` ([dnewcome/ableton-mcp](https://github.com/dnewcome/ableton-mcp)) adds the following commands on top of upstream:

| Command | Type | Added | Description |
|---|---|---|---|
| `set_clip_follow_action` | write | `f0469c9` | Set follow action on a session clip |
| `copy_clip_to_arrangement` | write | `fba59bd` | Place a session clip on the arrangement timeline |
| `set_clip_loop` | write | `fba59bd` | Set loop region on a session clip (also accepts follow action params) |
| `set_arrangement_clip_end` | write | `fba59bd` | Stretch an arrangement clip to a target end time |
| `get_arrangement_clips` | read | `fba59bd` | Return all arrangement clips for a track with positions |
| `set_scene_name` | write | `fba59bd` | Name a session view scene |
| `get_scene_names` | read | `0718598` | Return all scene names |
| `get_clip_notes` | read | `0718598` | Return MIDI notes for a session clip |
| `get_track_info` | read | `0718598` | Extended: includes clip loop/follow-action properties |
| `get_clip_attributes` | read | `6f04e25` | Debug probe for clip and song follow-action attributes |
| `get_arrangement_clip_notes` | read | `2026-03-29` | Return MIDI notes for an arrangement clip (by track + start position) |
| `clear_arrangement` | write | `2026-03-29` | Delete all arrangement clips on a track (or all MIDI tracks) |

---

## Known Limitations / Open Issues

- **`clip.delete()` on arrangement clips** — not yet tested in Live. If it fails, `clear_arrangement` will log warnings and the push will layer on top of existing clips. Check Ableton's log on first test run.
- **Instrument URIs are approximate** — `get_track_info` returns device class names, not browser URIs. The `instrument_uri` values in pulled JSON are best-guess queries that may need manual correction.
- **Section names lost on pull** — arrangement clips don't store section names. Pulled JSON always uses A/B/C/… labels.
- **Audio tracks skipped** — only MIDI tracks are included in pull/push.

---

## Next Steps

- Test the full round-trip: `setup_song.py` → Ableton → `pull_song.py` → edit JSON → `setup_song.py`
- Verify `clip.delete()` works for arrangement clips in Live
- Consider storing section names as arrangement clip names on push (so pull can recover them)
