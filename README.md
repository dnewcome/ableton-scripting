# Ableton Scripting

Python scripts for programmatically creating MIDI tracks and full song structures in Ableton Live using a simple JSON format.

## Scripts

| Script | Input | Description |
|---|---|---|
| `setup_song.py` | `.song.json` | Build a full multi-track song with named sections mapped to session view scenes |
| `setup_fminor_arp.py` | `.track.json` | Create a single MIDI track with clips (original single-track script) |

## Requirements

- Ableton Live with the [AbletonMCP](https://github.com/ahujasid/ableton-mcp) Remote Script installed and active
- Python 3.6+
- No external dependencies — uses only the standard library

---

## Song structure (`setup_song.py`)

```bash
python3 setup_song.py                        # uses fminor_groove.song.json
python3 setup_song.py my_song.song.json      # uses a custom song file
```

Creates all tracks, then maps each section to a scene in Ableton's session view. Clips shorter than their section loop automatically. Scene names are set to the section name.

### Song JSON format

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
    { "name": "intro",  "bars": 8,  "clips": { "bass": null } },
    { "name": "verse_A","bars": 16, "clips": { "bass": "bass_A" } },
    { "name": "outro",  "bars": 8,  "clips": { "bass": "bass_A" } }
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
| `sections` | array | Yes | — | Ordered song sections → scenes |

### Clip library

Clips are defined once and referenced by ID from multiple tracks and sections. The script creates a new clip instance per track×section combination.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | No | clip ID | Display name in Ableton |
| `length` | number | Yes | — | Clip length in beats |
| `notes` | array | No | `[]` | MIDI notes (same format as track JSON) |

### Track fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Internal ID used to reference this track from sections |
| `name` | string | Yes | Track name shown in Ableton |
| `instrument_uri` | string | No | Browser URI of the instrument to load |

### Section fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Section name, used to label the scene in Ableton |
| `bars` | integer | Yes | Section length in bars (informational; drives arrangement placement later) |
| `clips` | object | No | Map of `track_id → clip_id`. Use `null` to leave a track silent in this section. |

### Example

`fminor_groove.song.json` builds a 5-section F minor song (intro → verse A → breakdown → drop → outro) across three tracks: arpeggio, pad, and bass. The arp and pad clips are shared between sections.

---

## Single-track script (`setup_fminor_arp.py`)

```bash
python3 setup_fminor_arp.py                      # uses fminor_arp.track.json
python3 setup_fminor_arp.py my_track.json        # uses a custom track file
```

The script connects to Ableton over a local socket, appends a new MIDI track, loads the instrument, creates clips, and optionally fires them — all in one shot.

## Track JSON Format

A track file is a `.json` file with the following structure:

```json
{
  "name": "My Track",
  "instrument_uri": "query:Synths#Drift:Synth%20Keys:FileId_3806",
  "clips": [
    {
      "slot": 0,
      "name": "My Clip",
      "length": 8,
      "fire": true,
      "notes": [
        {"pitch": "F3",  "start": 0.00, "duration": 0.25, "velocity": 90},
        {"pitch": "Ab3", "start": 0.25, "duration": 0.25, "velocity": 85}
      ]
    }
  ]
}
```

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | No | Track name shown in Ableton |
| `instrument_uri` | string | No | Browser URI of the instrument to load |
| `clips` | array | No | List of clips to create on the track |

### Clip fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `slot` | integer | No | `0` | Clip slot index (row in session view) |
| `name` | string | No | — | Clip name shown in Ableton |
| `length` | number | No | `4` | Clip length in beats |
| `fire` | boolean | No | `false` | Start playing the clip after creation |
| `notes` | array | No | `[]` | List of MIDI notes |

### Note fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `pitch` | string or integer | Yes | — | Note name (`"F3"`, `"Ab4"`, `"C#5"`) or raw MIDI number (`53`) |
| `start` | number | Yes | — | Start position in beats from the beginning of the clip |
| `duration` | number | Yes | — | Note length in beats |
| `velocity` | integer | No | `100` | MIDI velocity (1–127) |
| `mute` | boolean | No | `false` | Whether the note is muted |

### Note names

Pitches can be written as a note letter, optional accidental, and octave number:

| Format | Example | Description |
|---|---|---|
| Natural | `"F3"` | F in octave 3 |
| Flat | `"Ab4"` | A-flat in octave 4 |
| Sharp | `"C#5"` | C-sharp in octave 5 |
| MIDI number | `53` | Raw MIDI pitch (middle C = 60) |

Octave numbers follow the convention where middle C is `C4` (MIDI 60).

### Beat values (common durations)

| Value | Note |
|---|---|
| `4.0` | Whole note |
| `2.0` | Half note |
| `1.0` | Quarter note |
| `0.5` | Eighth note |
| `0.25` | Sixteenth note |
| `0.125` | Thirty-second note |

### Finding instrument URIs

The easiest way to find a URI for any instrument or preset is to browse via the MCP tools (e.g. using Claude with the AbletonMCP server) and copy the `uri` field from the result. URIs look like:

```
query:Synths#Drift:Synth%20Keys:FileId_3806
```

## Example

`fminor_arp.track.json` included in this repo creates a MIDI track with the **Night Crystal** Drift preset playing a two-bar ascending/descending F minor arpeggio in 16th notes.
