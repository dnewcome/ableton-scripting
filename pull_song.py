#!/usr/bin/env python3
"""
Read the current Ableton Live arrangement and generate a .song.json skeleton.

Section grouping rules:
  - Each unique start position in the arrangement is a section boundary.
  - Clips across all tracks that share the same start position belong to the
    same section.
  - Section length is derived from the arrangement clip end times.
  - Sections are named A, B, C, … in timeline order (arrangement clips carry
    no section names).

Usage:
    python3 pull_song.py [output.song.json]

Defaults to pulled_song.song.json if no argument is given.
Ableton must be open with the MCP Remote Script active.
"""

import socket
import json
import sys
import string

HOST = "localhost"
PORT = 9877

# Reverse map: MIDI pitch number → note name (e.g. 53 → "F3")
_PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_to_note(pitch):
    """Convert a MIDI pitch number to a note name like 'F3'."""
    pitch = int(pitch)
    octave = (pitch // 12) - 1
    name = _PITCH_CLASSES[pitch % 12]
    return f"{name}{octave}"


def send_command(sock, command_type, params=None):
    command = {"type": command_type, "params": params or {}}
    sock.sendall(json.dumps(command).encode("utf-8"))
    chunks = []
    sock.settimeout(10)
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError:
                continue
        except socket.timeout:
            break
    return json.loads(b"".join(chunks).decode("utf-8"))


def get_result(response):
    """Unwrap the result field, parsing JSON strings if needed."""
    result = response.get("result", {})
    if isinstance(result, str):
        result = json.loads(result)
    return result


def best_effort_instrument_uri(devices):
    """
    Given a list of device dicts from get_track_info, return the first
    plausible instrument URI or None.

    The MCP server exposes device class_name and name but not the browser URI
    directly.  When class_name is available we emit a best-guess query URI.
    """
    for dev in devices:
        dev_type = dev.get("type", "")
        if dev_type not in ("instrument", "drum_machine", "rack", "unknown"):
            continue
        class_name = dev.get("class_name", "")
        preset_name = dev.get("name", "")
        if class_name and preset_name:
            return f"query:{class_name}:{preset_name}"
        elif class_name:
            return f"query:{class_name}"
    return None


def _find_clip_at(clips, start_time, tol=0.001):
    """Return the clip dict whose start_time matches within tol, or None."""
    for c in clips:
        if abs(c["start_time"] - start_time) < tol:
            return c
    return None


def pull_song(sock):
    # --- Session metadata ---
    session = get_result(send_command(sock, "get_session_info"))
    bpm = session.get("tempo", 120)
    time_sig = [
        session.get("signature_numerator", 4),
        session.get("signature_denominator", 4),
    ]
    beats_per_bar = time_sig[0]
    track_count = session.get("track_count", 0)

    print(f"Tempo: {bpm} BPM  |  Time sig: {time_sig[0]}/{time_sig[1]}")
    print(f"Tracks: {track_count}")

    # --- Per-track info (names + instrument URIs) ---
    tracks_raw = []
    for ti in range(track_count):
        resp = send_command(sock, "get_track_info", {"track_index": ti})
        tracks_raw.append(get_result(resp))

    # --- Read arrangement clips per track ---
    track_defs = {}
    arr_clips_by_track = {}   # track_id → [clip_info dicts]

    for ti, info in enumerate(tracks_raw):
        track_id = f"track_{ti}"
        track_name = info.get("name", track_id)
        instr_uri = best_effort_instrument_uri(info.get("devices", []))

        track_def = {"id": track_id, "name": track_name}
        if instr_uri:
            track_def["instrument_uri"] = instr_uri
        track_defs[track_id] = track_def

        resp = send_command(sock, "get_arrangement_clips", {"track_index": ti})
        result = get_result(resp)
        clips = result.get("clips", []) if isinstance(result, dict) else []
        arr_clips_by_track[track_id] = clips

    # --- Collect unique section start positions across all tracks ---
    all_starts = set()
    for clips in arr_clips_by_track.values():
        for c in clips:
            all_starts.add(round(c["start_time"], 6))
    section_starts = sorted(all_starts)

    print(f"Arrangement sections found: {len(section_starts)}")

    if not section_starts:
        print("  (no arrangement clips — empty song)")
        return {
            "name": "Pulled Song",
            "bpm": bpm,
            "time_signature": time_sig,
            "clips": {},
            "tracks": list(track_defs.values()),
            "sections": [],
        }

    # --- Build clip library and sections ---
    clip_library = {}
    clip_counter = [0]

    def make_clip_id():
        clip_counter[0] += 1
        return f"clip_{clip_counter[0]:03d}"

    label_iter = iter(string.ascii_uppercase)
    song_sections = []

    for start_time in section_starts:
        # Section length = max end_time of any clip starting here
        section_end = start_time
        for clips in arr_clips_by_track.values():
            c = _find_clip_at(clips, start_time)
            if c:
                section_end = max(section_end, c["end_time"])
        section_beats = section_end - start_time
        section_bars = max(1, round(section_beats / beats_per_bar))

        section_clips = {}
        for track_id, clips in arr_clips_by_track.items():
            c = _find_clip_at(clips, start_time)
            if c is None:
                section_clips[track_id] = None
                continue

            # Fetch MIDI notes for this arrangement clip
            ti = int(track_id.split("_")[1])
            notes_resp = send_command(sock, "get_arrangement_clip_notes", {
                "track_index":      ti,
                "arrangement_time": c["start_time"],
            })
            if notes_resp.get("status") == "error":
                notes = []
                loop_end = c.get("loop_end", c["length"])
            else:
                notes_data = get_result(notes_resp)
                notes    = notes_data.get("notes", [])
                loop_end = notes_data.get("loop_end", c["length"])

            # Convert MIDI pitch numbers to note names
            notes_out = []
            for n in notes:
                note_entry = {
                    "pitch":    midi_to_note(n["pitch"]),
                    "start":    round(n["start"], 6),
                    "duration": round(n["duration"], 6),
                    "velocity": int(n["velocity"]),
                }
                if n.get("mute"):
                    note_entry["mute"] = True
                notes_out.append(note_entry)

            # De-duplicate: identical content → same clip_id
            content_key = json.dumps(
                {"loop_end": loop_end, "notes": notes_out}, sort_keys=True
            )
            if content_key not in clip_library:
                cid = make_clip_id()
                clip_library[content_key] = {
                    "id": cid,
                    "def": {
                        "name":   c.get("name", cid),
                        "length": loop_end,
                        "notes":  notes_out,
                    },
                }
            section_clips[track_id] = clip_library[content_key]["id"]

        section_name = next(label_iter, f"section_{len(song_sections) + 1}")
        song_sections.append({
            "name":  section_name,
            "bars":  section_bars,
            "clips": section_clips,
        })
        print(f"  {section_name}  beat {start_time:.4g}–{section_end:.4g}"
              f"  ({section_bars} bars)  tracks: "
              + ", ".join(tid for tid, cid in section_clips.items() if cid))

    # --- Assemble final song dict ---
    clips_out = {v["id"]: v["def"] for v in clip_library.values()}

    song = {
        "name": "Pulled Song",
        "bpm": bpm,
        "time_signature": time_sig,
        "clips": clips_out,
        "tracks": list(track_defs.values()),
        "sections": song_sections,
    }
    return song


def main():
    out_file = sys.argv[1] if len(sys.argv) > 1 else "pulled_song.song.json"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"Connected to Ableton at {HOST}:{PORT}\n")
        song = pull_song(sock)

    with open(out_file, "w") as f:
        json.dump(song, f, indent=2)

    print(f"\nWrote {out_file}")
    print(f"  {len(song['tracks'])} track(s)")
    print(f"  {len(song['clips'])} clip(s) in library")
    print(f"  {len(song['sections'])} section(s): "
          + ", ".join(s["name"] for s in song["sections"]))


if __name__ == "__main__":
    main()
