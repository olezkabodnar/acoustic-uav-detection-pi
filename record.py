# 
# record sound from the microphone and save it as a WAV file.
# 
#     How to run 
#     python record.py       
#     python record.py 10 -> records 10 seconds
#

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import sounddevice as sd
import soundfile as sf

# ---------- Settings ----------
MIC_NAME = "USB Audio"   # part of the microphone name (python -m sounddevice)
SAMPLE_RATE = 16000      # samples per second
SECONDS = 60             # default length of a recording
FOLDER = "recordings"    # where the files are saved

# The length can also be given on the command line: python record.py 10
if len(sys.argv) > 1:
    SECONDS = float(sys.argv[1])


# ---------- 1. Find the microphone ----------
mic = None
for number, device in enumerate(sd.query_devices()):
    if MIC_NAME in device["name"] and device["max_input_channels"] > 0:
        mic = number
        break

if mic is None:
    print(f"Error: no microphone with '{MIC_NAME}' in its name was found.")
    print("These are the devices I can see:")
    print(sd.query_devices())
    sys.exit(1)

print("Using microphone:", sd.query_devices(mic)["name"])


# ---------- 2. Check the clock ( for the UTC time) ----------
result = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"],
                        capture_output=True, text=True)
clock_ok = result.stdout.strip() == "yes"
if not clock_ok:
    print("Warning: the clock is not synchronised, so the UTC time may be wrong.")


# ---------- 3. Record ----------
start_time = datetime.now(timezone.utc)
print(f"Recording {SECONDS:g} seconds...")

try:
    # sd.rec() starts recording in the background and returns straight away
    audio = sd.rec(int(SECONDS * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype="int16", device=mic)

    # Wait for the recording, plus 2 seconds extra.
    # If it is still running after that, the microphone stopped sending sound

    time.sleep(SECONDS + 2)
    if sd.get_stream().active:
        sd.stop()
        raise RuntimeError("the microphone stopped sending sound (unplugged?)")

except Exception as error:
    # Nothing has been written to disk yet, so no empty file is left behind.
    print("Error: the recording failed:", error)
    print("No file was saved.")
    sys.exit(1)

# Check if there were any gaps in the audio.
gaps = sd.get_status().input_overflow  # "overflow" means a small gap in the audio


# ---------- 4. Save the WAV file and its details ----------
os.makedirs(FOLDER, exist_ok=True)
name = start_time.strftime("%Y-%m-%dT%H-%M-%SZ")
wav_path = f"{FOLDER}/{name}.wav"

sf.write(wav_path, audio, SAMPLE_RATE)

details = {
    "file": f"{name}.wav",
    "start_utc": start_time.isoformat(),
    "seconds": SECONDS,
    "sample_rate": SAMPLE_RATE,
    "microphone": sd.query_devices(mic)["name"],
    "clock_synchronised": clock_ok,
    "gaps_in_audio": gaps,
}
with open(f"{FOLDER}/{name}.json", "w") as file:
    json.dump(details, file, indent=2)

print("Saved", wav_path)
if gaps:
    print("Warning: some audio was missed, recording has small gaps.")
