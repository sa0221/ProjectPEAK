import asyncio
import os
import subprocess
import time
from datetime import datetime
import httpx
from bleak import BleakScanner

# Environment variables
CONTROLLER_URL = os.environ.get("CONTROLLER_URL", "http://controller:8000")
SCAN_INTERVAL = 10  # Seconds between scans
COLLECTION_TIMEOUT = 5  # Seconds per scan type

async def get_collection_status():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{CONTROLLER_URL}/api/collection-status")
            return response.json().get("active", False)
    except Exception as e:
        print(f"Error getting collection status: {e}")
        return False

async def scan_bluetooth():
    """Improved BLE scanning with error handling"""
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

async def capture_adsb():
    """Improved ADS-B collection with device check (RTL-SDR required)"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "dump1090-mutability",
            "--interactive",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        signals = []
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

async def capture_wifi():
    """Wi-Fi scanning with interface detection"""
    interface = "wlan0"
    try:
        # Determine an active wireless interface
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
        output = await proc.communicate()
        return [{
            "timestamp": datetime.now().isoformat(),
            "type": "Wi-Fi",
            "name_address": "Probe Request",
            "signal_strength": "N/A",
            "frequency": "2.4/5 GHz",
            "additional_info": line.strip(),
            "latitude": None,
            "longitude": None
        } for line in output[0].decode().splitlines() if line.strip()]
    except Exception as e:
        print(f"Wi-Fi scan error: {str(e)}")
        return []

async def collect_and_send():
    """Main collection loop with dynamic hardware detection and status checking"""
    # Detect available hardware devices at startup
    devices_posted = False
    hackrf_present = False
    rtlsdr_present = False
    bt_present = False
    wifi_ifaces = []
    # Check for HackRF (SDR)
    try:
        proc = await asyncio.create_subprocess_exec("hackrf_info", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if proc.returncode == 0:
            hackrf_present = True
    except FileNotFoundError:
        pass
    # Check for RTL-SDR (ADS-B dongle)
    try:
        proc = await asyncio.create_subprocess_exec("rtl_test", "-t", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await proc.communicate()
        if proc.returncode == 0:
            rtlsdr_present = True
    except FileNotFoundError:
        pass
    # Check for Bluetooth adapter
    proc = await asyncio.create_subprocess_exec("hciconfig", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    if b"hci0" in stdout:
        bt_present = True
    # Check for Wi-Fi interfaces
    try:
        wifi_ifaces = [iface for iface in os.listdir("/sys/class/net") if os.path.exists(f"/sys/class/net/{iface}/wireless")]
    except Exception:
        wifi_ifaces = []
    # Prepare device list for UI display
    device_list = []
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
    # Send detected devices to controller API
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{CONTROLLER_URL}/api/devices", json={"devices": device_list})
            print(f"[Collector] Detected devices: {', '.join(device_list)}")
        devices_posted = True
    except Exception as e:
        print(f"[Collector] Device info post failed: {e}")
        devices_posted = False

    while True:
        # Retry posting device list until successful
        if not devices_posted:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"{CONTROLLER_URL}/api/devices", json={"devices": device_list})
                    print(f"[Collector] Detected devices: {', '.join(device_list)}")
                devices_posted = True
            except Exception as e:
                print(f"[Collector] Retry device post: {e}")
        # Only scan if collection is active
        if await get_collection_status():
            print("[Collector] Starting collection cycle...")
            tasks = []
            if bt_present:
                tasks.append(asyncio.create_task(scan_bluetooth()))
            if rtlsdr_present:
                tasks.append(asyncio.create_task(capture_adsb()))
            if wifi_ifaces:
                tasks.append(asyncio.create_task(capture_wifi()))
            results = await asyncio.gather(*tasks) if tasks else []
            all_signals = [sig for sublist in results for sig in sublist]
            if all_signals:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(f"{CONTROLLER_URL}/api/collect", json=all_signals, timeout=10)
                    print(f"[Collector] Sent {len(all_signals)} signals")
                except Exception as e:
                    print(f"Failed to send data: {str(e)}")
            else:
                print("[Collector] No signals collected")
        await asyncio.sleep(SCAN_INTERVAL)

def main():
    asyncio.run(collect_and_send())

if __name__ == "__main__":
    main()
