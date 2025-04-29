#!/usr/bin/env python3
"""
Collector Service Module for Project PEAK

Asynchronous RF signal collector (BLE, ADS-B, Wi-Fi, HackRF spectrum)
that posts into the Controller API.
"""
import asyncio, os, time
from datetime import datetime
import httpx
from bleak import BleakScanner

CONTROLLER_URL     = os.getenv("CONTROLLER_URL", "http://127.0.0.1:8000")
SCAN_INTERVAL      = int(os.getenv("SCAN_INTERVAL",      10))
COLLECTION_TIMEOUT = int(os.getenv("COLLECTION_TIMEOUT",  5))

async def get_collection_status():
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{CONTROLLER_URL}/api/collection-status", timeout=5)
            return r.json().get("active", False)
    except:
        return False

async def scan_spectrum():
    """Run hackrf_sweep, parse /tmp/sweep.csv."""
    try:
        csvf = "/tmp/sweep.csv"
        p = await asyncio.create_subprocess_exec(
            "hackrf_sweep","-f","100M:6000M","-l","30","-w",csvf,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await p.wait()
        out = []
        with open(csvf) as f:
            for line in f:
                if line.startswith("Frequency"): continue
                freq,amp = line.strip().split(",")
                out.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "Spectrum",
                    "name_address": freq+" Hz",
                    "signal_strength": amp,
                    "frequency": freq+" Hz",
                    "additional_info": "",
                    "latitude": None,
                    "longitude": None
                })
        return out
    except Exception as e:
        print("Spectrum scan error:",e)
        return []

async def scan_bluetooth():
    try:
        devs = await BleakScanner.discover(timeout=COLLECTION_TIMEOUT)
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Bluetooth",
            "name_address": f"{d.name or 'Unknown'} [{d.address}]",
            "signal_strength": -70,
            "frequency": "2.4 GHz",
            "additional_info": "",
            "latitude": None,
            "longitude": None
        } for d in devs]
    except Exception as e:
        print("Bluetooth scan error:",e)
        return []

async def capture_adsb():
    try:
        p = await asyncio.create_subprocess_exec(
            "dump1090-mutability","--interactive",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        out = []
        start = time.time()
        while time.time()-start < COLLECTION_TIMEOUT:
            ln = await p.stdout.readline()
            if ln.startswith(b"*"):
                txt = ln.decode(errors="ignore").strip()
                out.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "ADS-B",
                    "name_address": "Aircraft",
                    "signal_strength": "N/A",
                    "frequency": "1090 MHz",
                    "additional_info": txt,
                    "latitude": None,
                    "longitude": None
                })
        p.terminate()
        return out
    except Exception as e:
        print("ADS-B error:",e)
        return []

async def capture_wifi():
    iface="wlan0"
    if not os.path.exists(f"/sys/class/net/{iface}"):
        nets=os.listdir("/sys/class/net")
        iface=next((i for i in nets if os.path.isdir(f"/sys/class/net/{i}/wireless")),iface)
    try:
        p = await asyncio.create_subprocess_exec(
            "tcpdump","-i",iface,"-c","10","-nn",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )
        data,_ = await p.communicate()
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Wi-Fi",
            "name_address": "Probe Request",
            "signal_strength": "N/A",
            "frequency": "2.4/5 GHz",
            "additional_info": ln.strip(),
            "latitude": None,
            "longitude": None
        } for ln in data.decode(errors="ignore").splitlines() if ln.strip()]
    except Exception as e:
        print("Wi-Fi scan error:",e)
        return []

async def collect_and_send():
    # Detect hardware once
    hackrf=rtlsdr=False
    try:
        p=await asyncio.create_subprocess_exec("hackrf_info",stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
        await p.wait(); hackrf=(p.returncode==0)
    except: pass
    try:
        p=await asyncio.create_subprocess_exec("rtl_test","-t",stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL)
        await p.wait(); rtlsdr=(p.returncode==0)
    except: pass

    bt=False
    try:
        p=await asyncio.create_subprocess_exec("hciconfig",stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
        out,_=await p.communicate(); bt=(b"hci0" in out)
    except: pass

    wifi_ifaces=[i for i in os.listdir("/sys/class/net") if os.path.isdir(f"/sys/class/net/{i}/wireless")]

    devs=[]
    if hackrf:     devs.append("HackRF One")
    if rtlsdr:     devs.append("RTL-SDR dongle")
    if bt:         devs.append("Bluetooth adapter")
    if wifi_ifaces:devs.append(f"Wi-Fi({','.join(wifi_ifaces)})")
    if not devs:   devs=["No RF devices detected"]

    # Post device list once
    try:
        async with httpx.AsyncClient() as c:
            await c.post(f"{CONTROLLER_URL}/api/devices",json={"devices":devs},timeout=5)
            print("[Collector] devices→",devs)
    except Exception as e:
        print("Device registration failed:",e)

    # Loop
    while True:
        if await get_collection_status():
            print("[Collector] scanning…")
            tasks=[]
            if hackrf:     tasks.append(asyncio.create_task(scan_spectrum()))
            if bt:         tasks.append(asyncio.create_task(scan_bluetooth()))
            if rtlsdr:     tasks.append(asyncio.create_task(capture_adsb()))
            if wifi_ifaces:tasks.append(asyncio.create_task(capture_wifi()))

            results=await asyncio.gather(*tasks) if tasks else []
            signals=[s for sub in results for s in sub]
            if signals:
                try:
                    async with httpx.AsyncClient() as c:
                        await c.post(f"{CONTROLLER_URL}/api/collect",json=signals,timeout=10)
                    print(f"[Collector] sent {len(signals)} signals")
                except Exception as e:
                    print("Post-collect failed:",e)
            else:
                print("[Collector] no signals")
        await asyncio.sleep(SCAN_INTERVAL)

if __name__=="__main__":
    asyncio.run(collect_and_send())
