import csv
import os
import re
import subprocess
import time
from datetime import datetime
from tqdm import tqdm
from bleak import BleakScanner
import asyncio

# Output CSV file
OUTPUT_FILE = "project_peak_signals.csv"

# Initialize CSV file with headers if it doesn't exist
if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Additional Info"])

# Log data to CSV
def log_data(signal_type, name_or_address, strength, additional_info=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, signal_type, name_or_address, strength, additional_info])

# 1. Collect concise ADS-B data
def collect_adsb():
    try:
        adsb_process = subprocess.Popen(["rtl_adsb"], stdout=subprocess.PIPE, universal_newlines=True)
        time.sleep(5)  # Collect for 5 seconds
        adsb_process.terminate()
        
        for line in adsb_process.stdout:
            if line.strip():
                match = re.search(r"callsign:(\w+).*heading:(\d+).*signal:(\S+)", line)
                if match:
                    callsign = match.group(1)
                    heading = match.group(2)
                    signal_strength = match.group(3)
                    log_data("ADS-B", callsign, signal_strength, f"Heading: {heading}")
                else:
                    log_data("ADS-B", "Unknown", "N/A", line.strip())
    except FileNotFoundError:
        print("[!] rtl_adsb command not found. Ensure rtl-sdr is installed.")

# 2. Scan Bluetooth devices using Bleak (using default adapter)
async def scan_bluetooth():
    try:
        devices = await BleakScanner.discover()  # No specific adapter needed
        for device in devices:
            log_data("Bluetooth", f"{device.name} [{device.address}]", device.rssi)
    except Exception as e:
        print(f"[!] Bluetooth error: {e}")

# 3. Capture Wi-Fi packets in monitor mode on wlan0
def capture_packets():
    try:
        tcpdump_process = subprocess.Popen(["tcpdump", "-i", "wlan0", "-c", "10", "-n"], stdout=subprocess.PIPE, universal_newlines=True)
        for line in tcpdump_process.stdout:
            if line.strip():
                log_data("Wi-Fi Packet", "tcpdump", "N/A", line.strip())
        tcpdump_process.terminate()
    except FileNotFoundError:
        print("[!] tcpdump command not found. Please install tcpdump.")

# Main loop to run all tasks continuously
async def main():
    print("[*] Starting continuous signal collection. Press Ctrl+C to stop.")
    try:
        while True:
            with tqdm(total=5, desc="Scanning", bar_format="{l_bar}{bar} [ time left: {remaining} ]") as pbar:
                await scan_bluetooth()
                pbar.update(1)

                capture_packets()
                pbar.update(1)

                collect_adsb()
                pbar.update(1)

            time.sleep(1)  # Short pause before the next cycle
    except KeyboardInterrupt:
        print("\n[*] Signal collection stopped. Check 'project_peak_signals.csv' for results.")
    except asyncio.CancelledError:
        print("[!] Async tasks were canceled.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Exiting program...")
