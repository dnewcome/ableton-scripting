#!/usr/bin/env python3
"""
Read the current Ableton Live session and generate a .song.json skeleton.

Section grouping rules:
  - A scene with a non-empty name starts a new section; that name becomes the
    section name.
  - A scene with an empty name is appended to the current section IF the
    previous clip has follow_action_a == 4 (Next).  Otherwise it starts a new
    unnamed section.
  - Sections that were never given a scene name are assigned A, B, C, … in
    order of appearance.

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

FOLLOW_NEXT = 4   # follow_action_a int value for "Next"


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
    directly.  We leave a comment-style placeholder so users know what to fill
    in.  When class_name is available we emit a best-guess query URI.
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

    # --- Scene names ---
    scene_resp = send_command(sock, "get_scene_names")
    scenes = get_result(scene_resp)
    if isinstance(scenes, dict):
        scenes = scenes.get("scenes", [])
    scene_count = len(scenes)
    print(f"Scenes: {scene_count}")

    # --- Per-track info ---
    tracks_raw = []
    for ti in range(track_count):
        resp = send_command(sock, "get_track_info", {"track_index": ti})
        info = get_result(resp)
        tracks_raw.append(info)

    # --- Build clip library and track→scene data ---
    # clip_key: (track_id, clip_content_hash) → clip_id
    clip_library = {}
    clip_counter = [0]

    def make_clip_id():
        clip_counter[0] += 1
        return f"clip_{clip_counter[0]:03d}"

    # track_id → track_def
    track_defs = {}
    # (track_id, scene_idx) → clip_id (or None)
    scene_clips = {}   # scene_idx → {track_id: clip_id_or_None}

    for ti, info in enumerate(tracks_raw):
        track_id = f"track_{ti}"
        track_name = info.get("name", track_id)
        devices = info.get("devices", [])
        instr_uri = best_effort_instrument_uri(devices)

        track_def = {"id": track_id, "name": track_name}
        if instr_uri:
            track_def["instrument_uri"] = instr_uri
        track_defs[track_id] = track_def

        clips_info = info.get("clip_slots", [])
        for slot_info in clips_info:
            si = slot_info.get("index", 0)
            if si not in scene_clips:
                scene_clips[si] = {}

            clip_info = slot_info.get("clip", None)
            if clip_info is None:
                scene_clips[si][track_id] = None
                continue

            # Fetch full notes
            notes_resp = send_command(sock, "get_clip_notes", {
                "track_index": ti,
                "clip_index": si,
            })
            notes_data = get_result(notes_resp)
            if notes_resp.get("status") == "error" or not isinstance(notes_data, dict):
                notes = []
                clip_length = clip_info.get("length", 4)
                loop_end = clip_info.get("loop_end", clip_length)
            else:
                notes = notes_data.get("notes", [])
                clip_length = notes_data.get("length", clip_info.get("length", 4))
                loop_end = notes_data.get("loop_end", clip_length)

            # Convert pitches to note names
            notes_out = []
            for n in notes:
                notes_out.append({
                    "pitch":    midi_to_note(n["pitch"]),
                    "start":    round(n["start"], 6),
                    "duration": round(n["duration"], 6),
                    "velocity": int(n["velocity"]),
                })
                if n.get("mute"):
                    notes_out[-1]["mute"] = True

            # De-duplicate clip content: identical notes+loop_end → same clip_id
            content_key = json.dumps({"loop_end": loop_end, "notes": notes_out},
                                     sort_keys=True)
            if content_key not in clip_library:
                cid = make_clip_id()
                clip_library[content_key] = {
                    "id": cid,
                    "def": {
                        "name": clip_info.get("name", cid),
                        "length": loop_end,
                        "notes": notes_out,
                    }
                }
            cid = clip_library[content_key]["id"]
            scene_clips[si][track_id] = cid

    # Fill any missing slots as None
    for si in range(scene_count):
        if si not in scene_clips:
            scene_clips[si] = {}
        for tid in track_defs:
            if tid not in scene_clips[si]:
                scene_clips[si][tid] = None

    # --- Group scenes into sections ---
    # Determine follow action for the last clip in each scene across all tracks
    def scene_follow_action(si):
        """Return the follow_action_a int for scene si (use highest-priority found)."""
        for ti, info in enumerate(tracks_raw):
            for slot_info in info.get("clip_slots", []):
                if slot_info.get("index") == si:
                    c = slot_info.get("clip")
                    if c:
                        return c.get("follow_action_a", FOLLOW_NEXT)
        return FOLLOW_NEXT  # assume next if no clip found

    # Assign labels to unnamed-section groups (A, B, C, …)
    label_iter = iter(string.ascii_uppercase)

    sections = []
    current_section = None   # {"name": str, "scenes": [int]}

    for si in range(scene_count):
        scene_name = scenes[si]["name"] if si < len(scenes) else ""

        if scene_name:
            # Named scene → flush current and start new named section
            if current_section is not None:
                sections.append(current_section)
            current_section = {"name": scene_name, "scenes": [si]}
        else:
            # Unnamed scene — continue current section if previous follow was Next
            prev_follow = None
            if current_section is not None and current_section["scenes"]:
                prev_si = current_section["scenes"][-1]
                prev_follow = scene_follow_action(prev_si)

            if current_section is not None and prev_follow == FOLLOW_NEXT:
                current_section["scenes"].append(si)
            else:
                # Start a new unnamed section
                if current_section is not None:
                    sections.append(current_section)
                label = next(label_iter, f"Section_{len(sections)}")
                current_section = {"name": label, "scenes": [si]}

    if current_section is not None:
        sections.append(current_section)

    # --- Convert sections to song-format dicts ---
    # Each multi-scene section: bars = sum of each scene's bars (derived from
    # clip length / beats_per_bar, defaulting to 1 bar if no clips)
    def scene_bars(si):
        """Estimate bar count for a scene from clip lengths."""
        for tid, cid in scene_clips.get(si, {}).items():
            if cid is not None:
                cdef = next((v["def"] for v in clip_library.values() if v["id"] == cid), None)
                if cdef:
                    beats = cdef["length"]
                    bars = max(1, round(beats / beats_per_bar))
                    return bars
        return 1  # default: 1 bar when scene is empty

    song_sections = []
    for sec in sections:
        total_bars = sum(scene_bars(si) for si in sec["scenes"])

        # Merge clip maps: first non-None value per track wins
        merged_clips = {}
        for tid in track_defs:
            merged_clips[tid] = None
            for si in sec["scenes"]:
                cid = scene_clips.get(si, {}).get(tid)
                if cid is not None:
                    merged_clips[tid] = cid
                    break

        # Follow action for the section: look at last scene's follow action
        last_si = sec["scenes"][-1]
        fa = scene_follow_action(last_si)
        # Only emit follow_action if it deviates from the default (next, or stop
        # on the last section)
        sec_entry = {
            "name": sec["name"],
            "bars": total_bars,
            "clips": merged_clips,
        }
        # We'll fix up follow_action on the last section after building the list
        sec_entry["_raw_follow"] = fa
        song_sections.append(sec_entry)

    # Emit follow_action only when it differs from the default that setup_song.py
    # would apply: "next" (4) for all sections except the last, "stop" (1) for last.
    FOLLOW_STOP = 1
    for i, sec_entry in enumerate(song_sections):
        raw = sec_entry.pop("_raw_follow", FOLLOW_NEXT)
        is_last = (i == len(song_sections) - 1)
        default = FOLLOW_STOP if is_last else FOLLOW_NEXT
        if raw != default:
            # Map int back to string for the JSON
            _FA_MAP = {1: "stop", 2: "loop", 3: "prev", 4: "next",
                       5: "first", 6: "last", 7: "any", 8: "other"}
            sec_entry["follow_action"] = _FA_MAP.get(raw, str(raw))

    # --- Assemble final song dict ---
    clips_out = {v["id"]: v["def"] for v in clip_library.values()}
    tracks_out = list(track_defs.values())

    song = {
        "name": "Pulled Song",
        "bpm": bpm,
        "time_signature": time_sig,
        "clips": clips_out,
        "tracks": tracks_out,
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
