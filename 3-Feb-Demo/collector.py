# collector.py

import asyncio
import subprocess
import time
from datetime import datetime
import random
import os
import httpx
from bleak import BleakScanner

# Configuration: the controller URL and base location
CONTROLLER_URL = os.environ.get("CONTROLLER_URL", "http://controller:8000")
CONTROLLER_LAT = 39.7392
CONTROLLER_LON = -104.9903

# Return a random latitude/longitude within ~1km of the controller.
def get_random_location():
    offset_lat = random.uniform(-0.01, 0.01)
    offset_lon = random.uniform(-0.01, 0.01)
    return CONTROLLER_LAT + offset_lat, CONTROLLER_LON + offset_lon

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Collect ADS-B signals using dump1090.
def collect_adsb():
    signals = []
    dump1090_path = "/usr/local/bin/dump1090"
    if not os.path.isfile(dump1090_path):
        print(f"[ADS-B] dump1090 not found at {dump1090_path}")
        return signals
    try:
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
                lat, lon = get_random_location()
                signals.append({
                    "timestamp": get_timestamp(),
                    "type": "ADS-B",
                    "name_address": "dump1090",
                    "signal_strength": "N/A",
                    "additional_info": line.strip(),
                    "frequency": "",
                    "latitude": lat,
                    "longitude": lon
                })
        process.terminate()
    except Exception as e:
        print(f"[ADS-B] Error: {e}")
    return signals

# Scan for Bluetooth devices.
async def scan_bluetooth():
    signals = []
    try:
        devices = await BleakScanner.discover(timeout=5.0)
        for device in devices:
            lat, lon = get_random_location()
            signals.append({
                "timestamp": get_timestamp(),
                "type": "Bluetooth",
                "name_address": f"{device.name or 'Unknown'} [{device.address}]",
                "signal_strength": "N/A",
                "additional_info": "",
                "frequency": "",
                "latitude": lat,
                "longitude": lon
            })
    except Exception as e:
        print(f"[Bluetooth] Error: {e}")
    return signals

# Capture Wi‑Fi packets using tcpdump.
def capture_wifi():
    signals = []
    try:
        process = subprocess.Popen(
            ["tcpdump", "-i", "wlan0", "-c", "10", "-nn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            if line.strip():
                lat, lon = get_random_location()
                signals.append({
                    "timestamp": get_timestamp(),
                    "type": "Wi-Fi",
                    "name_address": "tcpdump",
                    "signal_strength": "N/A",
                    "additional_info": line.strip(),
                    "frequency": "",
                    "latitude": lat,
                    "longitude": lon
                })
    except Exception as e:
        print(f"[Wi-Fi] Error: {e}")
    return signals

# Perform a spectrum sweep using hackrf_sweep.
def spectrum_sweep():
    signals = []
    try:
        process = subprocess.Popen(
            ["hackrf_sweep", "-f", "100:6000", "-w", "2000000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            if line.strip():
                lat, lon = get_random_location()
                signals.append({
                    "timestamp": get_timestamp(),
                    "type": "Spectrum",
                    "name_address": "hackrf_sweep",
                    "signal_strength": "N/A",
                    "additional_info": line.strip(),
                    "frequency": "",
                    "latitude": lat,
                    "longitude": lon
                })
    except Exception as e:
        print(f"[Spectrum] Error: {e}")
    return signals

# Main collection loop: gather data and send to controller.
async def collect_and_send():
    while True:
        print("[Collector] Starting collection cycle...")
        bt_signals = await scan_bluetooth()
        adsb_signals = await asyncio.to_thread(collect_adsb)
        wifi_signals = await asyncio.to_thread(capture_wifi)
        spectrum_signals = await asyncio.to_thread(spectrum_sweep)
        all_signals = bt_signals + adsb_signals + wifi_signals + spectrum_signals
        if all_signals:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(f"{CONTROLLER_URL}/api/collect", json=all_signals)
                    if response.status_code == 200:
                        print(f"[Collector] Sent {len(all_signals)} signals successfully.")
                    else:
                        print(f"[Collector] Failed to send signals: {response.text}")
            except Exception as e:
                print(f"[Collector] Error sending signals: {e}")
        else:
            print("[Collector] No signals collected this cycle.")
        await asyncio.sleep(10)

def main():
    asyncio.run(collect_and_send())

if __name__ == "__main__":
    main()
