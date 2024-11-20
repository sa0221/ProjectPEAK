import subprocess
import numpy as np
import time
from datetime import datetime

OUTPUT_FILE = "project_peak_signals.txt"

def log_data(data):
    """Logs data with timestamps to an output file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"{timestamp} - {data}\n")

def collect_signals(center_freq, sample_rate, duration=5):
    """Collects signals using HackRF."""
    print(f"[*] Capturing {duration} seconds at {center_freq / 1e6} MHz...")
    iq_file = "/tmp/signal_capture.iq"

    # Run HackRF to capture raw IQ data
    try:
        subprocess.run([
            "hackrf_transfer", "-r", iq_file,
            "-f", str(int(center_freq)), "-s", str(int(sample_rate))
        ], timeout=duration)

        # Process the IQ data
        signal_strength = process_iq_file(iq_file)
        log_data(f"Captured Signal: {center_freq / 1e6} MHz, Strength: {signal_strength} dB")
    except subprocess.TimeoutExpired:
        print("[!] HackRF capture timed out.")
    except FileNotFoundError:
        print("[!] HackRF not found. Ensure HackRF tools are installed.")

def process_iq_file(iq_file):
    """Processes raw IQ data to estimate signal strength."""
    try:
        iq_data = np.fromfile(iq_file, dtype=np.uint8)
        amplitude = np.abs(iq_data - 127.5)  # Normalize to 0-centered data
        avg_strength = 20 * np.log10(np.mean(amplitude))
        return round(avg_strength, 2)
    except Exception as e:
        print(f"[!] Error processing IQ file: {e}")
        return "Unknown"

def scan_frequency_range(start_freq, end_freq, step_freq, sample_rate):
    """Scans a range of frequencies in steps."""
    print(f"[*] Scanning frequency range {start_freq / 1e6} MHz to {end_freq / 1e6} MHz...")
    current_freq = start_freq

    while current_freq <= end_freq:
        collect_signals(current_freq, sample_rate)
        current_freq += step_freq

def main():
    print("[*] Starting Project PEAK signal collection...")
    log_data("=== Signal Collection Start ===")

    # Example: Scan from 2.4 GHz to 2.5 GHz (Wi-Fi, Bluetooth range)
    start_freq = 2.4e9  # 2.4 GHz
    end_freq = 2.5e9    # 2.5 GHz
    step_freq = 10e6    # 10 MHz steps
    sample_rate = 2e6   # 2 MHz sample rate

    scan_frequency_range(start_freq, end_freq, step_freq, sample_rate)

    log_data("=== Signal Collection End ===")
    print("[*] Signal collection complete. Check 'project_peak_signals.txt' for results.")

if __name__ == "__main__":
    main()
