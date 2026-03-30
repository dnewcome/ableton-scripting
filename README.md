# Ableton Scripting

Python scripts for composing and editing full song arrangements in Ableton Live using a plain JSON format. The core idea is a round-trip workflow: write or generate a `.song.json` file, push it into Ableton, make changes in Ableton or in the JSON, and pull it back out again.

## How it works

This project uses the [AbletonMCP](https://github.com/ahujasid/ableton-mcp) Remote Script (forked at [dnewcome/ableton-mcp](https://github.com/dnewcome/ableton-mcp)), which exposes Ableton's Live API over a local socket on port 9877. The Python scripts connect to that socket and issue commands to create tracks, load instruments, write MIDI notes, and place clips on the arrangement timeline.

### The round-trip concept

```
.song.json  ──setup_song.py──▶  Ableton arrangement
                                        │
                               edit in Ableton or JSON
                                        │
.song.json  ◀──pull_song.py──  Ableton arrangement
```

The JSON file is the source of truth. You can:
- Write a song from scratch in JSON and push it to Ableton
- Have an LLM generate or edit a `.song.json` and push it
- Pull what's in the arrangement back to JSON, edit it, and push changes back
- Iterate freely — each push clears and rewrites the arrangement

### Session view as staging area

The Live API has no direct "create arrangement clip" call. Instead, `setup_song.py` uses a two-pass approach: clips are first created in the session view (which supports direct clip creation), then duplicated onto the arrangement timeline via `duplicate_clip_to_arrangement`. The session view is just a scratch pad — the arrangement is the actual song output.

---

## Requirements

- Ableton Live with the [dnewcome/ableton-mcp](https://github.com/dnewcome/ableton-mcp) Remote Script installed and active
- Python 3.6+
- No external dependencies — uses only the standard library

---

## Scripts

### `setup_song.py` — push JSON to Ableton

```bash
python3 setup_song.py                        # uses fminor_groove.song.json
python3 setup_song.py my_song.song.json
```

Reads a `.song.json` file and builds the song in Ableton:

1. Sets tempo and time signature
2. Creates MIDI tracks and loads instruments
3. Creates session view clips with MIDI notes (staging pass)
4. Clears the existing arrangement timeline
5. Places clips on the arrangement at the correct beat positions, section by section
6. Sets clip loop regions

Push is idempotent — running it twice on the same file clears and rewrites the arrangement rather than layering on top.

### `pull_song.py` — pull arrangement to JSON

```bash
python3 pull_song.py                         # writes pulled_song.song.json
python3 pull_song.py my_session.song.json
```

Reads the current Ableton arrangement and reconstructs a `.song.json`:

1. Reads session metadata (tempo, time signature)
2. Reads track names and instrument info
3. Reads `arrangement_clips` per track — positions on the timeline
4. Groups clips by `start_time` into sections (clips sharing a start position = one section)
5. Fetches MIDI notes for each arrangement clip
6. De-duplicates identical clip content into a shared clip library
7. Converts MIDI pitch numbers to note names (`53` → `"F3"`)

Sections are labelled A, B, C, … in timeline order. Arrangement clips don't store section names, so original names (e.g. "intro", "verse_A") are not recovered on pull.

---

## Song JSON format

```json
{
  "name": "My Song",
  "bpm": 128,
  "time_signature": [4, 4],

  "clips": {
    "bass_A": {
      "name": "Bass Loop A",
      "length": 4,
      "notes": [
        {"pitch": "F2", "start": 0.0, "duration": 0.45, "velocity": 95}
      ]
    }
  },

  "tracks": [
    { "id": "bass", "name": "Bass", "instrument_uri": "query:..." }
  ],

  "sections": [
    { "name": "intro",   "bars": 8,  "clips": { "bass": null   } },
    { "name": "verse_A", "bars": 16, "clips": { "bass": "bass_A" } },
    { "name": "outro",   "bars": 8,  "clips": { "bass": "bass_A" } }
  ]
}
```

### Top-level fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | No | — | Song name (informational) |
| `bpm` | number | No | `120` | Tempo in beats per minute |
| `time_signature` | `[beats, division]` | No | `[4, 4]` | e.g. `[4, 4]` for common time |
| `clips` | object | Yes | — | Named clip library (keyed by clip ID) |
| `tracks` | array | Yes | — | Track definitions |
| `sections` | array | Yes | — | Ordered sections that map to positions on the arrangement timeline |

### Clip library

Clips are defined once and referenced by ID from any number of tracks and sections. When `setup_song.py` runs it creates a separate clip instance for each track × section combination, but all instances share the same MIDI content.

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | No | Display name shown in Ableton (defaults to clip ID) |
| `length` | number | Yes | Clip length in beats |
| `notes` | array | No | MIDI notes (see note format below) |

### Track fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Internal ID used to reference this track from sections |
| `name` | string | Yes | Track name shown in Ableton |
| `instrument_uri` | string | No | Browser URI of the instrument preset to load |

### Section fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Section name — used to label scenes in Ableton |
| `bars` | integer | Yes | Section length in bars — determines how much timeline space the section occupies |
| `clips` | object | No | Map of `track_id → clip_id`. Omit a track or use `null` to leave it silent in this section |

Clips shorter than `bars × beats_per_bar` loop to fill the section. Clips longer are truncated.

### Note format

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `pitch` | string or integer | Yes | — | Note name (`"F3"`, `"Ab4"`, `"C#5"`) or MIDI number (`53`) |
| `start` | number | Yes | — | Start position in beats from the beginning of the clip |
| `duration` | number | Yes | — | Note length in beats |
| `velocity` | integer | No | `100` | MIDI velocity (1–127) |
| `mute` | boolean | No | `false` | Whether the note is muted |

#### Note names

Pitches follow the convention where middle C is `C4` (MIDI pitch 60).

| Format | Example | MIDI |
|---|---|---|
| Natural | `"F3"` | 53 |
| Flat | `"Ab4"` | 68 |
| Sharp | `"C#5"` | 73 |
| MIDI number | `60` | 60 (= C4) |

#### Common beat durations

| Value | Note |
|---|---|
| `4.0` | Whole note |
| `2.0` | Half note |
| `1.0` | Quarter note |
| `0.5` | Eighth note |
| `0.25` | Sixteenth note |
| `0.125` | Thirty-second note |

---

## Finding instrument URIs

The easiest method is to browse Ableton's instrument library via the MCP server (e.g. using Claude with the AbletonMCP MCP tool) and copy the `uri` field from the result. URIs look like:

```
query:Synths#Drift:Synth%20Keys:FileId_3806
```

When `pull_song.py` pulls a session, it generates best-guess `instrument_uri` values from the device class name and preset name. These are approximate and may need manual correction before a clean round-trip push.

---

## Example

`fminor_groove.song.json` is a complete working example: a 5-section F minor groove at 128 BPM across three tracks (arpeggio, pad, bass). It demonstrates:

- A **clip library** with 6 named clips (arp full, arp sparse, pad full, pad soft, bass main, bass root)
- **Section-level track silencing** — the intro has only the pad; the breakdown drops the bass
- **Clip reuse** — `arp_main` and `pad_full` are shared between `verse_A` and `drop` without duplication

```
intro       8 bars   pad_soft
verse_A    16 bars   arp_main + pad_full + bass_main
breakdown   8 bars   arp_sparse + pad_soft
drop       16 bars   arp_main + pad_full + bass_main
outro       8 bars   arp_sparse + pad_soft + bass_root
```

---

## Limitations

- **Section names are not preserved on pull.** Arrangement clips don't store section names. Pulled JSON always labels sections A, B, C, … Manually rename them after pulling if you want meaningful names.
- **Instrument URIs are approximate on pull.** The Live API exposes device class names but not browser URIs. Pulled `instrument_uri` values are best-guess queries.
- **Audio tracks are skipped.** Only MIDI tracks are included in pull and push.
- **`clip.delete()` on arrangement clips** — used by the clear pass in `setup_song.py`. Verify it works in your Live version if you see "Warning: could not delete clip" in Ableton's log.

---

## See also

- `PLAN.md` — architecture decisions, the full list of remote script extensions, and development history including the decision to pull from the arrangement view rather than the session view.
