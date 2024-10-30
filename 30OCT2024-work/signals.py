import subprocess
import os
import time
import re
import numpy as np
from datetime import datetime
from scapy.all import *
from bluetooth import discover_devices, BluetoothError

# Output file
OUTPUT_FILE = "collected_signals.txt"

def log_data(data):
    """Log data to a single output file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"{timestamp} - {data}\n")

# 1. Collect ADS-B data using rtl-sdr
def collect_adsb():
    print("[*] Collecting ADS-B signals...")
    try:
        adsb_process = subprocess.Popen(
            ["rtl_adsb"], stdout=subprocess.PIPE, universal_newlines=True
        )
        time.sleep(30)  # Collect for 30 seconds
        adsb_process.terminate()

        for line in adsb_process.stdout:
            if line.strip():
                log_data(f"ADS-B Data: {line.strip()}")
    except FileNotFoundError:
        print("[!] rtl_adsb not found. Ensure rtl-sdr is installed.")

# 2. Scan Bluetooth devices and record strength
def scan_bluetooth():
    print("[*] Scanning Bluetooth devices...")
    try:
        devices = discover_devices(duration=10, lookup_names=True, device_id=0)
        for addr, name in devices:
            rssi = get_bluetooth_rssi(addr)
            log_data(f"Bluetooth Device: {name} [{addr}], Strength: {rssi} dBm")
    except BluetoothError as e:
        print(f"[!] Bluetooth error: {e}")

def get_bluetooth_rssi(addr):
    """Get the RSSI (signal strength) of a Bluetooth device."""
    try:
        output = subprocess.check_output(
            ["sudo", "btmgmt", "find"], universal_newlines=True
        )
        match = re.search(rf"{addr} .* RSSI (-\d+)", output)
        if match:
            return match.group(1)
    except subprocess.CalledProcessError:
        pass
    return "Unknown"

# 3. Scan Wi-Fi networks and their signal strength
def scan_wifi():
    print("[*] Scanning Wi-Fi networks...")
    try:
        iwlist_output = subprocess.check_output(
            ["iwlist", "wlan0", "scan"], universal_newlines=True
        )
        networks = re.findall(r'ESSID:"(.*?)".*?Signal level=(-\d+) dBm', iwlist_output, re.DOTALL)
        for ssid, signal in networks:
            log_data(f"Wi-Fi Network: {ssid}, Signal Strength: {signal} dBm")
    except subprocess.CalledProcessError:
        print("[!] Error scanning Wi-Fi. Ensure wlan0 is active.")

# 4. Collect ambient signals using HackRF
def analyze_ambient_signals():
    print("[*] Collecting ambient signals with HackRF...")
    try:
        subprocess.run([
            "hackrf_transfer", "-r", "/tmp/ambient.iq", "-s", "2000000", "-f", "100000000"
        ], timeout=30)  # Capture 30 seconds of ambient signals

        strength = process_iq_file("/tmp/ambient.iq")
        log_data(f"Ambient Signal Strength: {strength} dB")
    except subprocess.TimeoutExpired:
        print("[!] HackRF capture timed out.")
    except FileNotFoundError:
        print("[!] HackRF not found. Ensure HackRF tools are installed.")

def process_iq_file(iq_file):
    """Process the IQ file to estimate signal strength."""
    try:
        iq_data = np.fromfile(iq_file, dtype=np.uint8)
        amplitude = np.abs(iq_data - 127)  # Normalize IQ values
        avg_strength = 20 * np.log10(np.mean(amplitude))
        return round(avg_strength, 2)
    except Exception as e:
        print(f"[!] Error processing IQ file: {e}")
        return "Unknown"

# Main function to run all tasks
def main():
    print("[*] Starting signal collection...")
    log_data("=== Signal Collection Start ===")
    
    scan_bluetooth()
    scan_wifi()
    collect_adsb()
    analyze_ambient_signals()
    
    log_data("=== Signal Collection End ===")
    print("[*] Signal collection complete. Check 'collected_signals.txt' for results.")

if __name__ == "__main__":
    main()
