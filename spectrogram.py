# 
# spectrogram.py - draw a spectrogram (frequencies over time) of WAV recordings.
# 
#     How to run 
#     python analysis/spectrogram.py data/raw/pi/2026-11-10T23-31-38Z.wav
#     python analysis/spectrogram.py data/raw/pi/*.wav        (many files at once)
# 


import os
import sys

import matplotlib
matplotlib.use("Agg")            # save pictures to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import soundfile as sf
from scipy import signal

# ---------- Settings ----------
WINDOW = 1024          # samples in one FFT window (1024 / 16000 Hz = 64 ms)
OVERLAP = 512          # windows overlap by half, so the picture is smoother
MAX_FREQ = 4000        # highest frequency to show in the picture (Hz)
TOP_PEAKS = 5          # how many strongest frequencies to print
OUT_FOLDER = "outputs/spectrograms"


def make_spectrogram(path):
    # ---------- 1. Load the sound ----------
    sound, rate = sf.read(path)
    if sound.ndim == 2:                   # stereo -> mono (average the two channels)
        sound = sound.mean(axis=1)

    # A file shorter than one window cannot be analysed: report it, don't crash.
    if len(sound) < WINDOW:
        print(f"Skipped {path}: too short ({len(sound)} samples, need at least {WINDOW}).")
        return

    # ---------- 2. Calculate the spectrogram ----------
    # freqs = list of frequencies (Hz), times = list of times (s),
    # power[f, t] = how strong frequency f is at time t
    # "hann" window: smooths the edges of each window so a pure tone stays one clean line

    
    freqs, times, power = signal.spectrogram(sound, fs=rate, window="hann",
                                             nperseg=WINDOW, noverlap=OVERLAP)
    power_db = 10 * np.log10(power + 1e-12)     # decibels (+ tiny number to avoid log(0))

    # ---------- 3. Strongest frequencies in the whole file ----------
    average = power.mean(axis=1)                # average power of each frequency over time
    peaks, _ = signal.find_peaks(average)       # local maxima only, so neighbours don't repeat
    strongest = peaks[np.argsort(average[peaks])[::-1][:TOP_PEAKS]]
    peak_list = ", ".join(f"{freqs[i]:.0f} Hz" for i in sorted(strongest))
    print(f"{path}: {len(sound) / rate:.1f} s at {rate} Hz, strongest frequencies: {peak_list}")

    # ---------- 4. Draw and save the picture ----------
    plt.figure(figsize=(10, 5))
    plt.pcolormesh(times, freqs, power_db, shading="auto", cmap="magma")
    plt.colorbar(label="Power (dB)")
    plt.ylim(0, min(MAX_FREQ, rate / 2))
    plt.xlabel("Time (s)")
    plt.ylabel("Frequency (Hz)")
    plt.title(os.path.basename(path))
    plt.tight_layout()

    os.makedirs(OUT_FOLDER, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    picture = f"{OUT_FOLDER}/{name}.png"
    plt.savefig(picture, dpi=120)
    plt.close()
    print(f"  saved {picture}")


if len(sys.argv) < 2:
    print("Usage: python analysis/spectrogram.py file.wav [more files...]")
    sys.exit(1)

for path in sys.argv[1:]:
    try:
        make_spectrogram(path)
    except Exception as error:
        # one bad file should not stop the others
        print(f"Skipped {path}: could not read it ({error}).")
        
