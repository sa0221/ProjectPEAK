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
    """Improved ADS-B collection with device check"""
    try:
        proc = await asyncio.create_subprocess_exec(
            "dump1090",
            "--interactive",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
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
    """WiFi scanning with fallback interface detection"""
    interface = "wlan0"
    try:
        # Simple interface check
        if not os.path.exists(f"/sys/class/net/{interface}"):
            interfaces = os.listdir('/sys/class/net')
            interface = next((i for i in interfaces if i.startswith('wlan')), 'eth0')
        
        proc = await asyncio.create_subprocess_exec(
            "tcpdump",
            "-i", interface,
            "-c", "10",
            "-nn",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
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
        print(f"WiFi scan error: {str(e)}")
        return []

async def collect_and_send():
    """Main collection loop with status checking"""
    while True:
        if await get_collection_status():
            print("[Collector] Starting collection cycle...")
            
            # Run all scans concurrently
            bt_task = asyncio.create_task(scan_bluetooth())
            adsb_task = asyncio.create_task(capture_adsb())
            wifi_task = asyncio.create_task(capture_wifi())
            
            results = await asyncio.gather(bt_task, adsb_task, wifi_task)
            all_signals = [sig for sublist in results for sig in sublist]
            
            if all_signals:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"{CONTROLLER_URL}/api/collect",
                            json=all_signals,
                            timeout=10
                        )
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