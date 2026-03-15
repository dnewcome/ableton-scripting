# Ableton Track Setup Script

A Python script for programmatically creating MIDI tracks in Ableton Live using a simple JSON format.

## Requirements

- Ableton Live with the [AbletonMCP](https://github.com/ahujasid/ableton-mcp) Remote Script installed and active
- Python 3.6+
- No external dependencies — uses only the standard library

## Usage

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
