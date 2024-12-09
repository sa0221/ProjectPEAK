import asyncio
import csv
import os
import time
from datetime import datetime
from bleak import BleakScanner
import subprocess

OUTPUT_FILE = "project_peak_signals.csv"

def initialize_csv():
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Additional Info"])

def log_data(signal_type, name_or_address, strength, additional_info=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, signal_type, name_or_address, strength, additional_info])

def collect_adsb():
    try:
        dump1090_path = "/usr/local/bin/dump1090"
        if not os.path.isfile(dump1090_path):
            print(f"[!] dump1090 not found at {dump1090_path}")
            return
        process = subprocess.Popen(
            [dump1090_path, "--interactive"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        start_time = time.time()
        while time.time() - start_time < 5:
            line = process.stdout.readline()
            if line:
                log_data("ADS-B", "dump1090", "N/A", line.strip())
        process.terminate()
    except Exception as e:
        print(f"[!] Error collecting ADS-B data: {e}")

async def scan_bluetooth():
    try:
        devices = await BleakScanner.discover()
        for device in devices:
            log_data(
                "Bluetooth",
                f"{device.name or 'Unknown'} [{device.address}]",
                "N/A",
                ""
            )
    except Exception as e:
        print(f"[!] Bluetooth error: {e}")

def capture_wifi():
    try:
        process = subprocess.Popen(
            ["tcpdump", "-i", "wlan0", "-c", "10", "-nn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            if line.strip():
                log_data("Wi-Fi", "tcpdump", "N/A", line.strip())
    except Exception as e:
        print(f"[!] Error collecting Wi-Fi packets: {e}")

def spectrum_sweep():
    try:
        process = subprocess.Popen(
            ["hackrf_sweep", "-f", "100:6000", "-w", "2000000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            if line.strip():
                log_data("Spectrum", "hackrf_sweep", "N/A", line.strip())
    except Exception as e:
        print(f"[!] Error in spectrum sweep: {e}")

def run_collections():
    asyncio.run(scan_bluetooth())
    collect_adsb()
    capture_wifi()
    spectrum_sweep()
