#!/usr/bin/env python3
"""
# Collector Service Module

The Collector Service is a core component of Project PEAK that performs asynchronous RF signal collection
across multiple protocols and frequencies. It acts as a data gathering agent that communicates with the
Controller service to store and visualize the collected signals.

## Features

- Multi-protocol signal collection (BLE, ADS-B, Wi-Fi, HackRF spectrum)
- Automatic geolocation via IP lookup
- Asynchronous operation for efficient scanning
- Automatic hardware detection and registration
- Configurable scan intervals and timeouts

## Configuration

The service can be configured through environment variables:

- `CONTROLLER_URL`: URL of the Controller service (default: "http://127.0.0.1:8000")
- `SCAN_INTERVAL`: Time between scan cycles in seconds (default: 10)
- `COLLECTION_TIMEOUT`: Maximum time to wait for each scan in seconds (default: 5)

## Hardware Requirements

The service automatically detects and uses available RF hardware:

- HackRF One for spectrum analysis
- RTL-SDR dongle for ADS-B reception
- Bluetooth adapter for BLE scanning
- Wi-Fi interface for probe request capture

## Signal Format

All collected signals follow this JSON structure:

```json
{
    "timestamp": "ISO-8601 datetime",
    "type": "Signal type (Bluetooth/ADS-B/Wi-Fi/Spectrum)",
    "name_address": "Device identifier",
    "signal_strength": "Signal strength in dBm or N/A",
    "frequency": "Operating frequency",
    "additional_info": "Protocol-specific details",
    "latitude": "Collector latitude",
    "longitude": "Collector longitude"
}
```
"""
import asyncio
import os
import time
from datetime import datetime
import httpx
import requests
from bleak import BleakScanner

# ─── Configuration ───────────────────────────────────────────────────────────────
CONTROLLER_URL    = os.environ.get("CONTROLLER_URL", "http://127.0.0.1:8000")
SCAN_INTERVAL     = int(os.environ.get("SCAN_INTERVAL", 10))
COLLECTION_TIMEOUT = int(os.environ.get("COLLECTION_TIMEOUT", 5))

# ─── Geolocate once via IP ──────────────────────────────────────────────────────
try:
    _r = requests.get("http://ip-api.com/json/", timeout=2).json()
    if _r.get("status") == "success":
        COL_LAT, COL_LON = _r["lat"], _r["lon"]
    else:
        COL_LAT, COL_LON = None, None
except Exception:
    COL_LAT, COL_LON = None, None

# ─── Controller Status Endpoint ─────────────────────────────────────────────────
async def get_collection_status() -> bool:
    """
    Check if signal collection is currently active.

    Returns:
        bool: True if collection is active, False otherwise.

    Note:
        This function queries the Controller service's collection status endpoint.
        If the Controller is unreachable, returns False to prevent unnecessary scanning.
    """
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CONTROLLER_URL}/api/collection-status", timeout=5)
            return r.json().get("active", False)
    except Exception:
        return False

# ─── Scanning Routines ──────────────────────────────────────────────────────────
async def scan_spectrum() -> list[dict]:
    """
    Perform a spectrum sweep using HackRF One.

    This function executes hackrf_sweep to scan frequencies from 100 MHz to 6 GHz,
    saving the results to a temporary CSV file and processing them into signal records.

    Returns:
        list[dict]: List of spectrum signal records, each containing frequency and amplitude data.

    Note:
        Requires hackrf_sweep to be installed and HackRF One to be connected.
        The sweep uses a 30 dB gain setting for optimal signal detection.
    """
    try:
        csvf = "/tmp/sweep.csv"
        p = await asyncio.create_subprocess_exec(
            "hackrf_sweep", "-f", "100M:6000M", "-l", "30", "-w", csvf,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await p.wait()
        out = []
        with open(csvf) as f:
            for line in f:
                if line.startswith("Frequency"):
                    continue
                freq, amp = line.strip().split(",")
                out.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "Spectrum",
                    "name_address": f"{freq} Hz",
                    "signal_strength": amp,
                    "frequency": f"{freq} Hz",
                    "additional_info": "",
                    "latitude": COL_LAT,
                    "longitude": COL_LON
                })
        return out
    except Exception as e:
        print("Spectrum scan error:", e)
        return []

async def scan_bluetooth() -> list[dict]:
    """
    Perform a Bluetooth Low Energy (BLE) scan using BleakScanner.

    This function discovers nearby BLE devices and records their presence.
    Each device is recorded with its name (if available) and MAC address.

    Returns:
        list[dict]: List of Bluetooth signal records, each containing device information.

    Note:
        Requires a Bluetooth adapter and the bleak library.
        Signal strength is estimated at -70 dBm as BLE devices typically operate in this range.
    """
    try:
        devices = await BleakScanner.discover(timeout=COLLECTION_TIMEOUT)
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Bluetooth",
            "name_address": f"{d.name or 'Unknown'} [{d.address}]",
            "signal_strength": -70,
            "frequency": "2.4 GHz",
            "additional_info": "",
            "latitude": COL_LAT,
            "longitude": COL_LON
        } for d in devices]
    except Exception as e:
        print("Bluetooth scan error:", e)
        return []

async def capture_adsb() -> list[dict]:
    """
    Capture ADS-B signals using dump1090-mutability.

    This function runs dump1090-mutability in interactive mode to capture
    aircraft position and identification data from ADS-B broadcasts.

    Returns:
        list[dict]: List of ADS-B signal records, each containing aircraft information.

    Note:
        Requires dump1090-mutability to be installed and an RTL-SDR dongle.
        ADS-B operates on 1090 MHz and is used by aircraft to broadcast their position.
    """
    try:
        p = await asyncio.create_subprocess_exec(
            "dump1090-mutability", "--interactive",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        results = []
        start = time.time()
        while time.time() - start < COLLECTION_TIMEOUT:
            ln = await p.stdout.readline()
            if ln.startswith(b"*"):
                txt = ln.decode(errors="ignore").strip()
                results.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "ADS-B",
                    "name_address": "Aircraft",
                    "signal_strength": "N/A",
                    "frequency": "1090 MHz",
                    "additional_info": txt,
                    "latitude": COL_LAT,
                    "longitude": COL_LON
                })
        p.terminate()
        return results
    except Exception as e:
        print("ADS-B error:", e)
        return []

async def capture_wifi() -> list[dict]:
    """
    Capture Wi-Fi probe requests using tcpdump.

    This function monitors the wireless interface for probe requests,
    which are broadcast by devices searching for known networks.

    Returns:
        list[dict]: List of Wi-Fi signal records, each containing probe request information.

    Note:
        Requires tcpdump to be installed and a wireless interface.
        Automatically detects the first available wireless interface if wlan0 is not present.
    """
    iface = "wlan0"
    if not os.path.exists(f"/sys/class/net/{iface}"):
        nets = os.listdir("/sys/class/net")
        iface = next((i for i in nets if os.path.exists(f"/sys/class/net/{i}/wireless")), "eth0")
    try:
        p = await asyncio.create_subprocess_exec(
            "tcpdump", "-i", iface, "-c", "10", "-nn",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        out, _ = await p.communicate()
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Wi-Fi",
            "name_address": "Probe Request",
            "signal_strength": "N/A",
            "frequency": "2.4/5 GHz",
            "additional_info": line,
            "latitude": COL_LAT,
            "longitude": COL_LON
        } for line in out.decode(errors="ignore").splitlines() if line.strip()]
    except Exception as e:
        print("Wi-Fi scan error:", e)
        return []

# ─── Main Collection Loop ───────────────────────────────────────────────────────
async def collect_and_send():
    """
    Main collection loop that coordinates all scanning activities.

    This function:
    1. Detects available RF hardware
    2. Registers detected hardware with the Controller
    3. Continuously performs scans when collection is active
    4. Sends collected signals to the Controller

    The function runs indefinitely, checking the collection status
    before each scan cycle and sleeping for SCAN_INTERVAL seconds between cycles.
    """
    # hardware detection
    hackrf = rtlsdr = False
    try:
        p = await asyncio.create_subprocess_exec("hackrf_info", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p.wait()
        hackrf = (p.returncode == 0)
    except: pass

    try:
        p = await asyncio.create_subprocess_exec("rtl_test", "-t", stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await p.wait()
        rtlsdr = (p.returncode == 0)
    except: pass

    bt = False
    try:
        p = await asyncio.create_subprocess_exec("hciconfig", stdout=asyncio.subprocess.PIPE)
        out, _ = await p.communicate()
        bt = b"hci0" in out
    except: pass

    wifi_ifaces = [i for i in os.listdir("/sys/class/net") if os.path.exists(f"/sys/class/net/{i}/wireless")]

    devs = []
    if hackrf:      devs.append("HackRF One")
    if rtlsdr:      devs.append("RTL-SDR dongle")
    if wifi_ifaces: devs.append(f"Wi-Fi ({','.join(wifi_ifaces)})")
    if bt:          devs.append("Bluetooth adapter")
    if not devs:    devs = ["No RF devices detected"]

    # register hardware once
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{CONTROLLER_URL}/api/devices", json={"devices": devs}, timeout=5)
            print("[Collector] devices →", devs)
    except Exception as e:
        print("Failed to register devices:", e)

    # continuous loop
    while True:
        if await get_collection_status():
            print("[Collector] starting scans…")
            tasks = []
            if hackrf:      tasks.append(asyncio.create_task(scan_spectrum()))
            if bt:          tasks.append(asyncio.create_task(scan_bluetooth()))
            if rtlsdr:      tasks.append(asyncio.create_task(capture_adsb()))
            if wifi_ifaces: tasks.append(asyncio.create_task(capture_wifi()))

            results = await asyncio.gather(*tasks) if tasks else []
            all_sigs = [sig for sub in results for sig in sub]
            if all_sigs:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(f"{CONTROLLER_URL}/api/collect", json=all_sigs, timeout=10)
                    print(f"[Collector] sent {len(all_sigs)} signals")
                except Exception as e:
                    print("Failed to send signals:", e)
            else:
                print("[Collector] no signals found")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(collect_and_send())
