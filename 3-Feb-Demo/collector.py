import asyncio
import os
import subprocess
import time
from datetime import datetime
import random
import httpx
from bleak import BleakScanner

# Environment variables
CONTROLLER_URL = os.environ.get("CONTROLLER_URL", "http://controller:8000")

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_random_location(base_lat, base_lon):
    """ Return a random latitude/longitude within ~1km of the given location. """
    offset_lat = random.uniform(-0.01, 0.01)
    offset_lon = random.uniform(-0.01, 0.01)
    return base_lat + offset_lat, base_lon + offset_lon

async def get_controller_location():
    """ Query the controller for its current location. """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CONTROLLER_URL}/api/location")
            data = response.json()
            return data.get("lat", 39.7392), data.get("lon", -104.9903)
    except Exception as e:
        print(f"[Collector] Error retrieving controller location: {e}")
        return 39.7392, -104.9903  # Default fallback

async def scan_bluetooth(controller_lat, controller_lon):
    """ Scan for Bluetooth devices and log signals. """
    signals = []
    try:
        devices = await BleakScanner.discover(timeout=5.0)
        for device in devices:
            lat, lon = get_random_location(controller_lat, controller_lon)
            signals.append({
                "timestamp": get_timestamp(),
                "type": "Bluetooth",
                "name_address": f"{device.name or 'Unknown'} [{device.address}]",
                "signal_strength": "-70 dBm",
                "additional_info": "",
                "frequency": "2.4 GHz",
                "latitude": lat,
                "longitude": lon
            })
    except Exception as e:
        print(f"[Bluetooth] Error: {e}")
    return signals

def collect_adsb(controller_lat, controller_lon):
    """ Capture ADS-B signals using dump1090. """
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
            if line.startswith("8D"):  # Simple filter for ADS-B messages
                lat, lon = get_random_location(controller_lat, controller_lon)
                signals.append({
                    "timestamp": get_timestamp(),
                    "type": "ADS-B",
                    "name_address": "dump1090",
                    "signal_strength": "N/A",
                    "additional_info": line.strip(),
                    "frequency": "1090 MHz",
                    "latitude": lat,
                    "longitude": lon
                })
        process.terminate()
    except Exception as e:
        print(f"[ADS-B] Error: {e}")
    return signals

def capture_wifi(controller_lat, controller_lon):
    """ Capture Wi-Fi probe requests. """
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
                lat, lon = get_random_location(controller_lat, controller_lon)
                signals.append({
                    "timestamp": get_timestamp(),
                    "type": "Wi-Fi",
                    "name_address": "tcpdump",
                    "signal_strength": "N/A",
                    "additional_info": line.strip(),
                    "frequency": "2.4/5 GHz",
                    "latitude": lat,
                    "longitude": lon
                })
    except Exception as e:
        print(f"[Wi-Fi] Error: {e}")
    return signals

def spectrum_sweep(controller_lat, controller_lon):
    """ Scan RF spectrum using HackRF. """
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
                lat, lon = get_random_location(controller_lat, controller_lon)
                signals.append({
                    "timestamp": get_timestamp(),
                    "type": "Spectrum",
                    "name_address": "hackrf_sweep",
                    "signal_strength": "N/A",
                    "additional_info": line.strip(),
                    "frequency": "various",
                    "latitude": lat,
                    "longitude": lon
                })
    except Exception as e:
        print(f"[Spectrum] Error: {e}")
    return signals

async def collect_and_send():
    """ Main collection loop that transmits data to the controller. """
    while True:
        print("[Collector] Starting collection cycle...")
        controller_lat, controller_lon = await get_controller_location()

        # Gather signals
        bt_signals = await scan_bluetooth(controller_lat, controller_lon)
        adsb_signals = await asyncio.to_thread(collect_adsb, controller_lat, controller_lon)
        wifi_signals = await asyncio.to_thread(capture_wifi, controller_lat, controller_lon)
        spectrum_signals = await asyncio.to_thread(spectrum_sweep, controller_lat, controller_lon)

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
