#!/usr/bin/env python3
"""
Load a .track.json file and create the track in Ableton Live.

Usage:
    python3 setup_fminor_arp.py [track_file.json]

Defaults to fminor_arp.track.json if no argument is given.
Ableton must be open with the MCP Remote Script active.
"""

import socket
import json
import sys
import time

HOST = "localhost"
PORT = 9877

# --- Note name -> MIDI pitch ---

NOTE_OFFSETS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

def note_to_midi(note):
    """Convert a note name like 'F3', 'Ab4', 'C#5' to a MIDI pitch number."""
    if isinstance(note, int):
        return note
    note = str(note).strip()
    # Parse letter, optional accidental, octave
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


# --- Ableton socket communication ---

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


# --- Track setup ---

def setup_track(sock, track_def):
    # Determine insert index
    session = send_command(sock, "get_session_info")
    session_result = session["result"]
    if isinstance(session_result, str):
        session_result = json.loads(session_result)
    track_index = session_result["track_count"]
    print(f"Inserting track at index {track_index}")

    # Create MIDI track
    result = send_command(sock, "create_midi_track", {"index": -1})
    print(f"  Created track: {result.get('result')}")
    time.sleep(0.2)

    # Name the track
    if "name" in track_def:
        send_command(sock, "set_track_name", {"track_index": track_index, "name": track_def["name"]})
        print(f"  Named: {track_def['name']}")

    # Load instrument
    if "instrument_uri" in track_def:
        result = send_command(sock, "load_browser_item", {
            "track_index": track_index,
            "item_uri": track_def["instrument_uri"]
        })
        print(f"  Loaded instrument: {result.get('result')}")
        time.sleep(0.3)

    # Create clips
    for clip_def in track_def.get("clips", []):
        slot = clip_def.get("slot", 0)
        length = clip_def.get("length", 4)

        result = send_command(sock, "create_clip", {
            "track_index": track_index,
            "clip_index": slot,
            "length": length
        })
        print(f"  Created clip in slot {slot}: {result.get('result')}")
        time.sleep(0.1)

        if "name" in clip_def:
            send_command(sock, "set_clip_name", {
                "track_index": track_index,
                "clip_index": slot,
                "name": clip_def["name"]
            })

        # Add notes, resolving any note names to MIDI numbers
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
            result = send_command(sock, "add_notes_to_clip", {
                "track_index": track_index,
                "clip_index": slot,
                "notes": notes
            })
            print(f"  Added {len(notes)} notes: {result.get('result')}")

        if clip_def.get("fire"):
            result = send_command(sock, "fire_clip", {
                "track_index": track_index,
                "clip_index": slot
            })
            print(f"  Fired clip: {result.get('result')}")


def main():
    track_file = sys.argv[1] if len(sys.argv) > 1 else "fminor_arp.track.json"
    with open(track_file) as f:
        track_def = json.load(f)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"Connected to Ableton at {HOST}:{PORT}\n")
        setup_track(sock, track_def)
        print("\nDone!")


if __name__ == "__main__":
    main()
