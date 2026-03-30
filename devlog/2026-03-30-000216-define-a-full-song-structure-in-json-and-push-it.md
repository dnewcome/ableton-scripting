# Defining a full song structure in JSON and pushing it into Ableton Live

_2026-03-30_

## What happened

I got tired of clicking around in Ableton to build up song arrangements, so I built a way to describe a full multi-track song in a plain JSON file and push it into Live with a Python script. The format has a clip library (define a MIDI loop once, reuse it anywhere), tracks with instrument URIs, and ordered sections that map to positions on the arrangement timeline. The thing that surprised me was how naturally the "clip library + sections" model maps to how you actually think about a song — you have a handful of loops and you're really just deciding when each one plays. The first working example was `fminor_groove.song.json`: 5 sections, 3 tracks, a sparse intro building into a drop and back out. Running `python3 setup_song.py` and watching Ableton fill up with tracks and clips is still satisfying every time.

## Files touched

  - fminor_groove.song.json
  - setup_song.py
  - README.md

## Tweet draft

Been building a way to write Ableton songs in JSON and push them into Live with a Python script. Define your MIDI loops once in a clip library, then arrange sections by referencing clip IDs. `python3 setup_song.py` and the arrangement appears. Turns out "a handful of loops + a list of when they play" is basically how I think about writing music anyway [link]

---

_commit: 5bdc34e · screenshot: no screenshot_
