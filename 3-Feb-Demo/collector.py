#!/usr/bin/env python3
"""
Collector Service Module for Project PEAK

Asynchronous RF signal collector (BLE, ADS-B, Wi-Fi, HackRF spectrum) that posts into the Controller API.
It geolocates the collector via IP lookup (http://ip-api.com/json/) and tags each signal with latitude/longitude.
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
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{CONTROLLER_URL}/api/collection-status", timeout=5)
            return r.json().get("active", False)
    except Exception:
        return False

# ─── Scanning Routines ──────────────────────────────────────────────────────────
async def scan_spectrum() -> list[dict]:
    """
    HackRF sweep 100 MHz–6 GHz via hackrf_sweep → /tmp/sweep.csv
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
    BLE scan via BleakScanner
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
    ADS-B capture via dump1090-mutability
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
    Wi-Fi probe‐request capture via tcpdump
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
