#!/usr/bin/env python3
"""
Load a .song.json file and build the song structure in Ableton Live.

Song sections map to scenes in the session view. Each section's clips
are placed in the corresponding scene row for each track. Clips shorter
than their section will loop naturally in Ableton to fill the section.

Usage:
    python3 setup_song.py [song_file.json]

Defaults to fminor_groove.song.json if no argument is given.
Ableton must be open with the MCP Remote Script active.
"""

import socket
import json
import sys
import time

HOST = "localhost"
PORT = 9877

NOTE_OFFSETS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_midi(note):
    """Convert a note name like 'F3', 'Ab4', 'C#5' to a MIDI pitch number."""
    if isinstance(note, int):
        return note
    note = str(note).strip()
    letter = note[0].upper()
    rest = note[1:]
    if rest and rest[0] in ("#", "b"):
        accidental, octave = rest[0], int(rest[1:])
    else:
        accidental, octave = "", int(rest)
    pitch = (octave + 1) * 12 + NOTE_OFFSETS[letter]
    if accidental == "#":
        pitch += 1
    elif accidental == "b":
        pitch -= 1
    return pitch


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


def setup_song(sock, song_def):
    bpm = song_def.get("bpm", 120)
    time_sig = song_def.get("time_signature", [4, 4])
    beats_per_bar = time_sig[0]
    clip_library = song_def.get("clips", {})
    track_defs = song_def.get("tracks", [])
    sections = song_def.get("sections", [])

    # --- Set tempo ---
    result = send_command(sock, "set_tempo", {"tempo": bpm})
    print(f"Tempo: {bpm} BPM  ({result.get('result', 'ok')})")

    # --- Create tracks ---
    session = send_command(sock, "get_session_info")
    session_result = session["result"]
    if isinstance(session_result, str):
        session_result = json.loads(session_result)
    base_index = session_result["track_count"]
    print(f"\nCreating {len(track_defs)} track(s) starting at index {base_index}:")

    track_indices = {}
    for i, track_def in enumerate(track_defs):
        idx = base_index + i
        send_command(sock, "create_midi_track", {"index": -1})
        time.sleep(0.2)
        send_command(sock, "set_track_name", {"track_index": idx, "name": track_def["name"]})
        if "instrument_uri" in track_def:
            result = send_command(sock, "load_browser_item", {
                "track_index": idx,
                "item_uri": track_def["instrument_uri"],
            })
            time.sleep(0.3)
        track_indices[track_def["id"]] = idx
        print(f"  [{idx}] {track_def['name']}")

    # --- Build scenes and clips ---
    print(f"\nBuilding {len(sections)} section(s):")

    for scene_idx, section in enumerate(sections):
        section_name = section["name"]
        section_bars = section["bars"]
        section_beats = section_bars * beats_per_bar
        section_clips = section.get("clips", {})

        # Name the scene (best-effort — not all MCP builds support this)
        send_command(sock, "set_scene_name", {
            "scene_index": scene_idx,
            "name": section_name,
        })

        active_tracks = [tid for tid, cid in section_clips.items() if cid is not None]
        print(f"\n  [{scene_idx}] {section_name}  ({section_bars} bars / {section_beats} beats)"
              f"  tracks: {active_tracks or '—'}")

        for track_id, clip_id in section_clips.items():
            if clip_id is None:
                continue

            if track_id not in track_indices:
                print(f"    WARNING: track id '{track_id}' not defined — skipping")
                continue

            clip_def = clip_library.get(clip_id)
            if clip_def is None:
                print(f"    WARNING: clip id '{clip_id}' not in clip library — skipping")
                continue

            track_idx = track_indices[track_id]
            clip_length = clip_def["length"]
            clip_name = clip_def.get("name", clip_id)

            # How many full loops fit in the section (informational only)
            loops = section_beats / clip_length
            loop_note = f"loops ×{loops:.4g}" if loops != 1 else "no loop"

            # Create the clip at its natural length; Ableton loops it automatically
            send_command(sock, "create_clip", {
                "track_index": track_idx,
                "clip_index": scene_idx,
                "length": clip_length,
            })
            time.sleep(0.1)

            send_command(sock, "set_clip_name", {
                "track_index": track_idx,
                "clip_index": scene_idx,
                "name": clip_name,
            })

            raw_notes = clip_def.get("notes", [])
            notes = [
                {
                    "pitch": note_to_midi(n["pitch"]),
                    "start_time": n["start"],
                    "duration": n["duration"],
                    "velocity": n.get("velocity", 100),
                    "mute": n.get("mute", False),
                }
                for n in raw_notes
            ]
            if notes:
                send_command(sock, "add_notes_to_clip", {
                    "track_index": track_idx,
                    "clip_index": scene_idx,
                    "notes": notes,
                })

            print(f"    {track_id}: '{clip_name}'  {clip_length} beats  ({loop_note} to fill {section_beats} beats)")


def main():
    song_file = sys.argv[1] if len(sys.argv) > 1 else "fminor_groove.song.json"
    with open(song_file) as f:
        song_def = json.load(f)

    print(f"Song: {song_def.get('name', song_file)}\n")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"Connected to Ableton at {HOST}:{PORT}\n")
        setup_song(sock, song_def)
        print("\nDone!")


if __name__ == "__main__":
    main()
