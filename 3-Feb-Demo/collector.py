#!/usr/bin/env python3
"""
Collector Service Module for Project PEAK

This module implements an asynchronous signal collection service designed for distributed RF data gathering. 
It supports multiple hardware interfaces (Bluetooth, ADS-B via RTL-SDR, and Wi-Fi) to scan, capture, and process
electromagnetic signals from various sources, then forward the collected data to a centralized Controller API for 
further analysis and storage.

Key Features:
    - Asynchronous scanning for high-performance, non-blocking operation.
    - Dynamic hardware detection: verifies presence of HackRF, RTL-SDR dongle, Bluetooth adapter, and Wi-Fi interfaces.
    - Concurrent execution of multiple scanning routines with robust error handling.
    - Automatic packaging of captured signals with metadata (timestamp, type, signal strength, etc.).
    - Reliable communication with the Controller API for device registration and signal data posting.

Environment Variables:
    - CONTROLLER_URL (str): The base URL for the Controller API (default: "http://controller:8000").
    - SCAN_INTERVAL (int): Interval in seconds between successive scanning cycles.
    - COLLECTION_TIMEOUT (int): Timeout in seconds for each scanning operation.

Usage:
    This module should be executed directly. It enters an infinite asynchronous loop, constantly checking
    if collection is active and then performing available hardware scans accordingly.

Author: [Your Name]
Date: 2025-04-14
"""

import asyncio
import os
import subprocess
import time
from datetime import datetime
import httpx
from bleak import BleakScanner

# Global environment configurations.
CONTROLLER_URL: str = os.environ.get("CONTROLLER_URL", "http://controller:8000")
SCAN_INTERVAL: int = 10          # Frequency between scanning cycles (seconds)
COLLECTION_TIMEOUT: int = 5        # Maximum duration for each scan (seconds)

async def get_collection_status() -> bool:
    """
    Retrieve and report whether the centralized Controller has activated data collection.

    The function makes an asynchronous GET request to the '/api/collection-status' endpoint on the Controller.
    In the case of errors (e.g., network issues or unexpected responses), it logs the error and returns False,
    thereby ensuring the collector does not scan unless the controller explicitly indicates active collection.

    Returns:
        bool: True if the Controller API signals that signal collection is active, else False.
    
    Raises:
        Exception details are printed to standard output for debugging purposes.
    
    Design Note:
        This check is performed periodically before each scan cycle to conserve resources.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CONTROLLER_URL}/api/collection-status")
            return response.json().get("active", False)
    except Exception as e:
        print(f"Error getting collection status: {e}")
        return False

async def scan_bluetooth() -> list[dict]:
    """
    Conduct a Bluetooth Low Energy (BLE) scan for nearby devices using the Bleak library.

    This function leverages BleakScanner.discover to detect BLE devices for up to COLLECTION_TIMEOUT seconds.
    For every device found, it returns a dictionary with:
      - Timestamp: When the device was detected (ISO format).
      - Type: "Bluetooth" (identifies the scan type).
      - Name/Address: Combines the device name (if available) with its hardware address.
      - Signal Strength: Hardcoded placeholder (-70 dBm) pending future enhancement.
      - Frequency: "2.4 GHz" to denote typical BLE operation frequency.
      - Latitude/Longitude: Set as None (reserved for future geo-tagging).

    Returns:
        list[dict]: A list of dictionaries, each representing an individual BLE device detection.

    Exception Handling:
        Any scanning error is caught, logged, and the function returns an empty list.

    Future Enhancement:
        Signal strength measurement may be refined to capture actual RSSI values dynamically.
    """
    try:
        devices = await BleakScanner.discover(timeout=COLLECTION_TIMEOUT)
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Bluetooth",
            "name_address": f"{d.name or 'Unknown'} [{d.address}]",
            "signal_strength": -70,
            "frequency": "2.4 GHz",
            "latitude": None,
            "longitude": None
        } for d in devices]
    except Exception as e:
        print(f"Bluetooth scan error: {str(e)}")
        return []

async def capture_adsb() -> list[dict]:
    """
    Capture ADS-B signals using the dump1090-mutability tool.

    This method spawns a subprocess to execute dump1090-mutability in interactive mode,
    capturing real-time output from an RTL-SDR dongle. The scan runs for up to COLLECTION_TIMEOUT seconds.
    For each line that begins with an asterisk ("*"), indicating an ADS-B message,
    a dictionary with the following keys is created:
      - Timestamp: Capture time in ISO format.
      - Type: "ADS-B" to denote the kind of signal.
      - Name/Address: Uses a hardcoded "Aircraft" identifier.
      - Signal Strength: "N/A" as a placeholder because actual RSSI measurement is not performed.
      - Frequency: "1090 MHz" representing ADS-B frequency.
      - Additional Info: Raw data (decoded message line).
      - Latitude/Longitude: Remain as None pending integration of geolocation.

    Returns:
        list[dict]: List of dictionaries with ADS-B signal data.

    Error Handling:
        All subprocess exceptions are captured, and an empty list is returned in case of failure.
    
    Note:
        An operational RTL-SDR dongle is a prerequisite for this function to yield useful data.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "dump1090-mutability",
            "--interactive",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        signals: list[dict] = []
        start_time = time.time()
        while time.time() - start_time < COLLECTION_TIMEOUT:
            line = await proc.stdout.readline()
            if line:
                decoded = line.decode().strip()
                if decoded.startswith("*"):
                    signals.append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "ADS-B",
                        "name_address": "Aircraft",
                        "signal_strength": "N/A",
                        "frequency": "1090 MHz",
                        "additional_info": decoded,
                        "latitude": None,
                        "longitude": None
                    })
        proc.terminate()
        return signals
    except Exception as e:
        print(f"ADS-B error: {str(e)}")
        return []

async def capture_wifi() -> list[dict]:
    """
    Perform a Wi-Fi scan by capturing probe requests through tcpdump.

    The function first determines an active wireless interface: it defaults to "wlan0"
    but will dynamically select another interface that exposes wireless capabilities if needed.
    It then spawns a subprocess to execute tcpdump with parameters to capture 10 packets (-c 10) in non-parsed format.
    The scanned output is parsed line-by-line to create a list of dictionaries with:
      - Timestamp: ISO-formatted time of capture.
      - Type: "Wi-Fi" indicating this scan type.
      - Name/Address: Descriptive label "Probe Request".
      - Signal Strength: Set as "N/A" (placeholder).
      - Frequency: "2.4/5 GHz" indicating the common operating bands.
      - Additional Info: The raw tcpdump output line.
      - Latitude/Longitude: Remain None for future enhancement.

    Returns:
        list[dict]: List of detected Wi-Fi signals as dictionaries.

    Exception Handling:
        If the subprocess fails or no wireless interface is found, logs the error and returns an empty list.
    """
    interface: str = "wlan0"
    try:
        if not os.path.exists(f"/sys/class/net/{interface}"):
            interfaces = os.listdir("/sys/class/net")
            interface = next((i for i in interfaces if os.path.exists(f"/sys/class/net/{i}/wireless")), "eth0")
        proc = await asyncio.create_subprocess_exec(
            "tcpdump",
            "-i", interface,
            "-c", "10",
            "-nn",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        output, _ = await proc.communicate()
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Wi-Fi",
            "name_address": "Probe Request",
            "signal_strength": "N/A",
            "frequency": "2.4/5 GHz",
            "additional_info": line.strip(),
            "latitude": None,
            "longitude": None
        } for line in output.decode().splitlines() if line.strip()]
    except Exception as e:
        print(f"Wi-Fi scan error: {str(e)}")
        return []

async def collect_and_send() -> None:
    """
    Main orchestration routine for dynamic hardware detection, signal collection, and communication with the Controller API.

    Operational Steps:
      1. **Hardware Detection**:
         - Checks for the presence of HackRF (for SDR), RTL-SDR dongles (for ADS-B),
           Bluetooth adapters (via 'hciconfig') and wireless interfaces.
         - The results are compiled into a human-readable device list.
      2. **Device Registration**:
         - Posts the detected devices list to the Controller at the '/api/devices' endpoint.
         - If posting fails, it retries until successful.
      3. **Signal Collection Loop**:
         - Periodically checks the Controller's collection status (via '/api/collection-status').
         - If active, concurrently dispatches available scan routines (Bluetooth, ADS-B, Wi-Fi).
         - Aggregates all scan results, then sends the collection to the Controller's '/api/collect' endpoint.
         - Waits for SCAN_INTERVAL seconds before starting the next cycle.
    
    Exception Handling:
      - Individual scan methods handle errors and return empty results on failure.
      - The overall loop logs failures without breaking, ensuring continuous operation.
    
    Returns:
        None: The function perpetually runs in an asynchronous event loop.
    
    Design Consideration:
      - Uses asyncio.gather to perform scanning concurrently. This design optimizes resource usage while
        ensuring that hardware detection is adaptive and robust.
    """
    devices_posted: bool = False
    hackrf_present: bool = False
    rtlsdr_present: bool = False
    bt_present: bool = False
    wifi_ifaces: list[str] = []

    # Check for HackRF One device (SDR)
    try:
        proc = await asyncio.create_subprocess_exec("hackrf_info", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if proc.returncode == 0:
            hackrf_present = True
    except FileNotFoundError:
        pass

    # Check for RTL-SDR dongle (required for ADS-B)
    try:
        proc = await asyncio.create_subprocess_exec("rtl_test", "-t", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if proc.returncode == 0:
            rtlsdr_present = True
    except FileNotFoundError:
        pass

    # Check for Bluetooth adapter via hciconfig output.
    proc = await asyncio.create_subprocess_exec("hciconfig", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    if b"hci0" in stdout:
        bt_present = True

    # Detect available Wi-Fi interfaces based on the presence of 'wireless' directories.
    try:
        wifi_ifaces = [iface for iface in os.listdir("/sys/class/net") if os.path.exists(f"/sys/class/net/{iface}/wireless")]
    except Exception:
        wifi_ifaces = []

    # Create a descriptive device list.
    device_list: list[str] = []
    if hackrf_present:
        device_list.append("HackRF One")
    if rtlsdr_present:
        device_list.append("RTL-SDR dongle")
    if wifi_ifaces:
        device_list.append(f"Wi-Fi ({', '.join(wifi_ifaces)})")
    if bt_present:
        device_list.append("Bluetooth adapter")
    if not device_list:
        device_list.append("No RF devices detected")

    # Register detected devices with the Controller API.
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{CONTROLLER_URL}/api/devices", json={"devices": device_list})
            print(f"[Collector] Detected devices: {', '.join(device_list)}")
        devices_posted = True
    except Exception as e:
        print(f"[Collector] Device info post failed: {e}")
        devices_posted = False

    # Main asynchronous loop for repetitive scanning and signal reporting.
    while True:
        # Retry device registration if necessary.
        if not devices_posted:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"{CONTROLLER_URL}/api/devices", json={"devices": device_list})
                    print(f"[Collector] Detected devices: {', '.join(device_list)}")
                devices_posted = True
            except Exception as e:
                print(f"[Collector] Retry device post: {e}")
        # Proceed with scanning only if collection is enabled by the Controller.
        if await get_collection_status():
            print("[Collector] Starting collection cycle...")
            tasks: list[asyncio.Task] = []
            if bt_present:
                tasks.append(asyncio.create_task(scan_bluetooth()))
            if rtlsdr_present:
                tasks.append(asyncio.create_task(capture_adsb()))
            if wifi_ifaces:
                tasks.append(asyncio.create_task(capture_wifi()))
            results = await asyncio.gather(*tasks) if tasks else []
            all_signals = [signal for sublist in results for signal in sublist]
            # Send aggregated signals to Controller API if any have been collected.
            if all_signals:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(f"{CONTROLLER_URL}/api/collect", json=all_signals, timeout=10)
                    print(f"[Collector] Sent {len(all_signals)} signals")
                except Exception as e:
                    print(f"Failed to send data: {str(e)}")
            else:
                print("[Collector] No signals collected")
        # Wait before beginning the next cycle.
        await asyncio.sleep(SCAN_INTERVAL)

def main() -> None:
    """
    Entry point for the Collector service module.

    Invokes the asynchronous collect_and_send() routine using asyncio.run(), initiating the perpetual scanning loop.
    
    Returns:
        None
    """
    asyncio.run(collect_and_send())

if __name__ == "__main__":
    main()
