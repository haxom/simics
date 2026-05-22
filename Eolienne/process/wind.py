#!/usr/bin/env python
# coding=utf8
"""
Realistic wind speed simulator with gust management.
Speed is recalculated every second and written to WIND_SPEED_FILE.
"""
__author__ = "haxom"
__email__ = "haxom@haxom.net"
__file__ = "wind.py"
__version__ = "1.1"


import time
import random
import math
import signal
import sys
from pathlib import Path

# --- Configuration ---
WIND_SPEED_FILE = "/tmp/wind.txt"   # Output file path (editable)
UPDATE_INTERVAL = 1.0                 # Recalculation interval in seconds

# Base wind speed
BASE_WIND_SPEED = 15.0     # m/s — central speed around which the wind oscillates
WIND_VARIABILITY = 2.5     # m/s — amplitude of slow background variations

# Gusts
GUST_PROBABILITY = 0.04    # Probability that a gust starts each second (4%)
GUST_MIN_STRENGTH = 5.0    # Minimum speed boost of a gust (m/s)
GUST_MAX_STRENGTH = 20.0   # Maximum speed boost of a gust (m/s)
GUST_MIN_DURATION = 3      # Minimum gust duration (seconds)
GUST_MAX_DURATION = 12     # Maximum gust duration (seconds)

# Physical limits
WIND_MIN = 0.0             # m/s (dead calm)
WIND_MAX = 65.0            # m/s — raise to 70.0 for extreme storm scenarios


class WindSimulator:
    def __init__(self):
        self.current_speed = BASE_WIND_SPEED
        self.smooth_speed = BASE_WIND_SPEED  # Smoothed speed (inertia)

        # Active gust state
        self.gust_active = False
        self.gust_strength = 0.0
        self.gust_remaining = 0        # remaining seconds
        self.gust_phase = 0.0          # envelope curve phase (0 -> 1 -> 0)

        # Slow background noise state
        self._noise_phase = random.uniform(0, 2 * math.pi)
        self._noise_speed = random.uniform(0.005, 0.015)  # rad/s — very slow drift

        self._tick = 0

    def _background_noise(self):
        """Slow, continuous background wind variation using layered sine waves."""
        self._noise_phase += self._noise_speed
        # Superposition of multiple sines at different frequencies -> more natural feel
        noise = (
            math.sin(self._noise_phase) * 0.6
            + math.sin(self._noise_phase * 2.3 + 1.1) * 0.3
            + math.sin(self._noise_phase * 5.7 + 2.4) * 0.1
        )
        return noise * WIND_VARIABILITY

    def _maybe_start_gust(self):
        """Randomly trigger a new gust if none is currently active."""
        if not self.gust_active and random.random() < GUST_PROBABILITY:
            self.gust_active = True
            self.gust_strength = random.uniform(GUST_MIN_STRENGTH, GUST_MAX_STRENGTH)
            self.gust_remaining = random.randint(GUST_MIN_DURATION, GUST_MAX_DURATION)
            self.gust_phase = 0.0
            print(f"  ⚡ Gust! +{self.gust_strength:.1f} m/s for ~{self.gust_remaining}s")

    def _gust_contribution(self):
        """Return the gust speed contribution using a smooth bell-curve envelope."""
        if not self.gust_active:
            return 0.0

        # Advance phase so it travels from 0 to pi over the gust duration
        self.gust_phase += math.pi / self.gust_remaining if self.gust_remaining > 0 else math.pi
        envelope = math.sin(self.gust_phase)  # smooth bell: rises then falls

        self.gust_remaining -= 1
        if self.gust_remaining <= 0:
            self.gust_active = False

        return self.gust_strength * max(0.0, envelope)

    def tick(self):
        """Compute the new wind speed for the current second."""
        self._tick += 1
        self._maybe_start_gust()

        # Background component + gust
        target = BASE_WIND_SPEED + self._background_noise() + self._gust_contribution()

        # Instantaneous turbulence (small random micro-variations)
        turbulence = random.gauss(0, 0.35)
        target += turbulence

        # Inertia: wind speed does not change instantaneously
        alpha = 0.3  # smoothing factor (0 = full inertia, 1 = instant response)
        self.smooth_speed += alpha * (target - self.smooth_speed)

        # Clamp to physical limits
        self.current_speed = max(WIND_MIN, min(WIND_MAX, self.smooth_speed))
        return self.current_speed

    @staticmethod
    def beaufort(speed_ms):
        """Return the Beaufort scale number and description for a given speed in m/s."""
        scale = [
            (0.3,  0,  "Calm"),
            (1.6,  1,  "Light air"),
            (3.4,  2,  "Light breeze"),
            (5.5,  3,  "Gentle breeze"),
            (8.0,  4,  "Moderate breeze"),
            (10.8, 5,  "Fresh breeze"),
            (13.9, 6,  "Strong breeze"),
            (17.2, 7,  "Near gale"),
            (20.8, 8,  "Gale"),
            (24.5, 9,  "Strong gale"),
            (28.5, 10, "Storm"),
            (32.7, 11, "Violent storm"),
            (float("inf"), 12, "Hurricane"),
        ]
        for threshold, bft, label in scale:
            if speed_ms < threshold:
                return bft, label
        return 12, "Hurricane"


def write_speed(filepath, speed):
    """Write the current wind speed as an integer in cm/s to the output file."""
    speed_cms = int(round(speed * 100))
    Path(filepath).write_text(f"{speed_cms}\n")


def signal_handler(sig, frame):
    print("\n\nSimulator stopped.")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)

    sim = WindSimulator()
    output_path = Path(WIND_SPEED_FILE)

    print("=" * 52)
    print("         WIND SPEED SIMULATOR")
    print("=" * 52)
    print(f"  Output file   : {output_path.resolve()}")
    print(f"  Base speed    : {BASE_WIND_SPEED} m/s")
    print(f"  Max speed     : {WIND_MAX} m/s")
    print(f"  Update rate   : every {UPDATE_INTERVAL}s")
    print(f"  Press Ctrl+C to stop")
    print("=" * 52)

    while True:
        speed = sim.tick()
        write_speed(WIND_SPEED_FILE, speed)

        bft, label = WindSimulator.beaufort(speed)
        gust_marker = " ⚡" if sim.gust_active else "  "
        print(
            f"[t={sim._tick:5d}s]{gust_marker} "
            f"{speed:5.2f} m/s  |  Beaufort {bft:2d} – {label}"
        )

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()