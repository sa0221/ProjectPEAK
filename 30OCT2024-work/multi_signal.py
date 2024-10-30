import subprocess
import numpy as np
import time
import threading
from datetime import datetime
from bluetooth import discover_devices, BluetoothError
from scapy.all import *

# Unified output file
OUTPUT_FILE = "multi_device_signals.txt"

def log_data(data):
    """Logs data to a single output file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"{timestamp} - {data}\n")

def collect_adsb():
    """Collect ADS-B data using RTL-SDR."""
    print("[*] Collecting ADS-B signals...")
    try:
        adsb_process = subprocess.Popen(["rtl_adsb"], stdout=subprocess.PIPE, universal_newlines=True)
        time.sleep(10)  # Collect for 10 seconds
        adsb_process.terminate()

        for line in adsb_process.stdout:
            log_data(f"ADS-B: {line.strip()}")
    except FileNotFoundError:
        print("[!] RTL-SDR not found or configured.")

def scan_bluetooth():
    """Scan for Bluetooth devices."""
    print("[*] Scanning Bluetooth devices...")
    try:
        devices = discover_devices(duration=8, lookup_names=True)
        for addr, name in devices:
            log_data(f"Bluetooth: {name} [{addr}]")
    except BluetoothError as e:
        print(f"[!] Bluetooth error: {e}")

def scan_wifi():
    """Scan Wi-Fi networks and their signal strengths."""
    print("[*] Scanning Wi-Fi networks...")
    try:
        iwlist_output = subprocess.check_output(["iwlist", "wlan0", "scan"], universal_newlines=True)
        networks = re.findall(r'ESSID:"(.*?)".*?Signal level=(-\d+) dBm', iwlist_output, re.DOTALL)
        for ssid, signal in networks:
            log_data(f"Wi-Fi: {ssid}, Signal: {signal} dBm")
    except subprocess.CalledProcessError:
        print("[!] Error scanning Wi-Fi. Ensure wlan0 is active.")

def collect_hackrf_signal(freq, sample_rate=2e6, duration=5):
    """Capture signals with HackRF."""
    print(f"[*] Capturing {duration} seconds at {freq / 1e6} MHz...")
    iq_file = f"/tmp/hackrf_capture_{int(freq)}.iq"

    try:
        subprocess.run(
            ["hackrf_transfer", "-r", iq_file, "-f", str(int(freq)), "-s", str(int(sample_rate))],
            timeout=duration
        )
        strength = process_iq_file(iq_file)
        log_data(f"HackRF: {freq / 1e6} MHz, Strength: {strength} dB")
    except subprocess.TimeoutExpired:
        print("[!] HackRF capture timed out.")
    except FileNotFoundError:
        print("[!] HackRF not found. Ensure HackRF tools are installed.")

def process_iq_file(iq_file):
    """Process HackRF IQ data to estimate signal strength."""
    try:
        iq_data = np.fromfile(iq_file, dtype=np.uint8)
        amplitude = np.abs(iq_data - 127.5)
        avg_strength = 20 * np.log10(np.mean(amplitude))
        return round(avg_strength, 2)
    except Exception as e:
        print(f"[!] Error processing IQ file: {e}")
        return "Unknown"

def scan_frequency_range(start_freq, end_freq, step_freq):
    """Scan a range of frequencies using HackRF."""
    current_freq = start_freq
    while current_freq <= end_freq:
        collect_hackrf_signal(current_freq)
        current_freq += step_freq

def main():
    print("[*] Starting multi-device signal collection...")
    log_data("=== Signal Collection Start ===")

    # Run all tasks in parallel threads
    threads = [
        threading.Thread(target=collect_adsb),
        threading.Thread(target=scan_bluetooth),
        threading.Thread(target=scan_wifi),
        threading.Thread(target=scan_frequency_range, args=(2.4e9, 2.5e9, 10e6)),
    ]

    # Start and join threads
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    log_data("=== Signal Collection End ===")
    print("[*] Signal collection complete. Check 'multi_device_signals.txt' for results.")

if __name__ == "__main__":
    main()
