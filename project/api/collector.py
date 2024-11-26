import asyncio
import csv
import os
import re
import subprocess
import time
from datetime import datetime
from bleak import BleakScanner

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

# Collect ADS-B data
def collect_adsb():
    try:
        dump1090_path = "../dump1090/dump1090"
        if not os.path.isfile(dump1090_path):
            print(f"[!] dump1090 not found at {dump1090_path}")
            return

        process = subprocess.Popen(
            [dump1090_path, "--interactive"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Read for 5 seconds
        start_time = time.time()
        while time.time() - start_time < 5:
            line = process.stdout.readline()
            if line:
                match = re.search(r"ICAO Address\s*:\s*(\w+).*Altitude\s*:\s*(\d+).*EW velocity\s*:\s*(\d+).*NS velocity\s*:\s*(\d+)", line)
                if match:
                    icao_address = match.group(1)
                    altitude = match.group(2)
                    ew_velocity = int(match.group(3))
                    ns_velocity = int(match.group(4))
                    velocity = (ew_velocity**2 + ns_velocity**2)**0.5

                    log_data(
                        "ADS-B",
                        f"[{icao_address}]",
                        "N/A",
                        f"Altitude: {altitude}, Speed: {velocity:.2f} knots"
                    )
        
        process.terminate()
    except Exception as e:
        print(f"[!] Error collecting ADS-B data: {e}")

# Scan Bluetooth devices
async def scan_bluetooth():
    try:
        devices = await BleakScanner.discover()
        for device in devices:
            log_data(
                "Bluetooth",
                f"{device.name or 'Unknown'} [{device.address}]",
                str(device.rssi),  # Replace with AdvertisementData.rssi if needed
                ""
            )
    except Exception as e:
        print(f"[!] Bluetooth error: {e}")

# Capture Wi-Fi packets
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

# Main collection function
async def main():
    try:
        # Run all collection methods
        await scan_bluetooth()
        collect_adsb()
        capture_wifi()
    except Exception as e:
        print(f"[!] Error in main collection: {e}")

if __name__ == "__main__":
    asyncio.run(main())
