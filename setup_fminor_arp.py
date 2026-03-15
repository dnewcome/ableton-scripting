#!/usr/bin/env python3
"""
Creates a MIDI track with an F minor arpeggio clip using the Night Crystal synth (Drift).
Run this script while Ableton Live is open with the MCP Remote Script active.
"""

import socket
import json
import time

HOST = "localhost"
PORT = 9877


def send_command(sock, command_type, params=None):
    command = {"type": command_type, "params": params or {}}
    sock.sendall(json.dumps(command).encode("utf-8"))

    # Read response
    chunks = []
    sock.settimeout(10)
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            # Try to parse — if it succeeds we have a full response
            try:
                data = json.loads(b"".join(chunks).decode("utf-8"))
                return data
            except json.JSONDecodeError:
                continue
        except socket.timeout:
            break

    return json.loads(b"".join(chunks).decode("utf-8"))


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        print(f"Connected to Ableton at {HOST}:{PORT}")

        # 1. Get session info to find where to insert the new track
        session = send_command(sock, "get_session_info")
        track_count = json.loads(session["result"])["track_count"]
        print(f"Current track count: {track_count}")

        # 2. Create a new MIDI track at the end
        result = send_command(sock, "create_midi_track", {"index": -1})
        track_index = track_count  # new track is appended at track_count index
        print(f"Created MIDI track at index {track_index}: {result.get('result')}")
        time.sleep(0.2)

        # 3. Name the track
        result = send_command(sock, "set_track_name", {
            "track_index": track_index,
            "name": "Fm Arpeggio"
        })
        print(f"Named track: {result.get('result')}")
        time.sleep(0.1)

        # 4. Load Night Crystal (Drift > Synth Keys)
        result = send_command(sock, "load_browser_item", {
            "track_index": track_index,
            "item_uri": "query:Synths#Drift:Synth%20Keys:FileId_3806"
        })
        print(f"Loaded Night Crystal: {result.get('result')}")
        time.sleep(0.3)

        # 5. Create a 2-bar (8 beat) MIDI clip in slot 0
        result = send_command(sock, "create_clip", {
            "track_index": track_index,
            "clip_index": 0,
            "length": 8.0
        })
        print(f"Created clip: {result.get('result')}")
        time.sleep(0.1)

        # 6. Name the clip
        result = send_command(sock, "set_clip_name", {
            "track_index": track_index,
            "clip_index": 0,
            "name": "Fm Arp"
        })
        print(f"Named clip: {result.get('result')}")

        # 7. Add F minor arpeggio notes (F, Ab, C across 2 octaves, 16th notes)
        # F minor triad: F=53, Ab=56, C=60, F=65, Ab=68, C=72, F=77
        notes = [
            # Bar 1: ascend F3 -> C5, then descend
            {"pitch": 53, "start_time": 0.00, "duration": 0.25, "velocity": 90, "mute": False},
            {"pitch": 56, "start_time": 0.25, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 60, "start_time": 0.50, "duration": 0.25, "velocity": 88, "mute": False},
            {"pitch": 65, "start_time": 0.75, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 68, "start_time": 1.00, "duration": 0.25, "velocity": 90, "mute": False},
            {"pitch": 72, "start_time": 1.25, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 68, "start_time": 1.50, "duration": 0.25, "velocity": 82, "mute": False},
            {"pitch": 65, "start_time": 1.75, "duration": 0.25, "velocity": 80, "mute": False},
            {"pitch": 60, "start_time": 2.00, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 56, "start_time": 2.25, "duration": 0.25, "velocity": 82, "mute": False},
            {"pitch": 53, "start_time": 2.50, "duration": 0.25, "velocity": 88, "mute": False},
            {"pitch": 56, "start_time": 2.75, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 60, "start_time": 3.00, "duration": 0.25, "velocity": 90, "mute": False},
            {"pitch": 65, "start_time": 3.25, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 68, "start_time": 3.50, "duration": 0.25, "velocity": 88, "mute": False},
            {"pitch": 72, "start_time": 3.75, "duration": 0.25, "velocity": 92, "mute": False},
            # Bar 2: peak at F5, descend and resolve
            {"pitch": 77, "start_time": 4.00, "duration": 0.25, "velocity": 95, "mute": False},
            {"pitch": 72, "start_time": 4.25, "duration": 0.25, "velocity": 88, "mute": False},
            {"pitch": 68, "start_time": 4.50, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 65, "start_time": 4.75, "duration": 0.25, "velocity": 82, "mute": False},
            {"pitch": 60, "start_time": 5.00, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 56, "start_time": 5.25, "duration": 0.25, "velocity": 80, "mute": False},
            {"pitch": 53, "start_time": 5.50, "duration": 0.25, "velocity": 88, "mute": False},
            {"pitch": 56, "start_time": 5.75, "duration": 0.25, "velocity": 82, "mute": False},
            {"pitch": 60, "start_time": 6.00, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 65, "start_time": 6.25, "duration": 0.25, "velocity": 88, "mute": False},
            {"pitch": 60, "start_time": 6.50, "duration": 0.25, "velocity": 82, "mute": False},
            {"pitch": 56, "start_time": 6.75, "duration": 0.25, "velocity": 80, "mute": False},
            {"pitch": 53, "start_time": 7.00, "duration": 0.50, "velocity": 95, "mute": False},  # held F
            {"pitch": 60, "start_time": 7.50, "duration": 0.25, "velocity": 85, "mute": False},
            {"pitch": 65, "start_time": 7.75, "duration": 0.25, "velocity": 85, "mute": False},
        ]
        result = send_command(sock, "add_notes_to_clip", {
            "track_index": track_index,
            "clip_index": 0,
            "notes": notes
        })
        print(f"Added notes: {result.get('result')}")
        time.sleep(0.1)

        # 8. Fire the clip
        result = send_command(sock, "fire_clip", {
            "track_index": track_index,
            "clip_index": 0
        })
        print(f"Fired clip: {result.get('result')}")

        print("\nDone! F minor arpeggio track is set up and playing.")


if __name__ == "__main__":
    main()
