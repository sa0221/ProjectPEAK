from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import threading
import os
import csv
import time
from datetime import datetime
import asyncio
from bleak import BleakScanner
import subprocess
import random

app = Flask(__name__)
CORS(app)

# Global variables
is_collecting = False
collection_thread = None
OUTPUT_FILE = "project_peak_signals.csv"

# Ensure the CSV exists with headers
def initialize_csv():
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Type", "Name/Address", "Signal Strength",
                "Frequency", "Latitude", "Longitude", "Additional Info"
            ])

def log_data(signal_type, name_or_address, strength, frequency, latitude, longitude, additional_info=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, signal_type, name_or_address, strength, frequency, latitude, longitude, additional_info])

def collect_adsb():
    try:
        dump1090_path = "/usr/local/bin/dump1090"
        if not os.path.isfile(dump1090_path):
            print(f"[!] dump1090 not found at {dump1090_path}")
            return
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
                log_data("ADS-B", "Aircraft", "N/A", "1090 MHz", 0.0, 0.0, line.strip())
        process.terminate()
    except Exception as e:
        print(f"[!] Error collecting ADS-B data: {e}")

async def scan_bluetooth():
    try:
        devices = await BleakScanner.discover()
        for device in devices:
            latitude, longitude = simulate_gps_coordinates()
            log_data(
                "Bluetooth",
                f"{device.name or 'Unknown'} [{device.address}]",
                str(device.rssi),
                "2.4 GHz",
                latitude,
                longitude,
                ""
            )
    except Exception as e:
        print(f"[!] Bluetooth error: {e}")

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
                latitude, longitude = simulate_gps_coordinates()
                log_data("Wi-Fi", "Unknown Device", "N/A", "2.4/5 GHz", latitude, longitude, line.strip())
    except Exception as e:
        print(f"[!] Error collecting Wi-Fi packets: {e}")

def collect_hackrf():
    try:
        output_file = "/tmp/hackrf_output.bin"
        process = subprocess.Popen(
            [
                "hackrf_transfer", 
                "-r", output_file,
                "-f", "915000000",  # Center frequency in Hz
                "-s", "2000000"     # Sample rate in Hz
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        start_time = time.time()
        while time.time() - start_time < 5:
            line = process.stderr.readline()
            if line.strip():
                latitude, longitude = simulate_gps_coordinates()
                log_data("HackRF", "Ambient Signal", "N/A", "915 MHz", latitude, longitude, "Collected samples")
        process.terminate()
    except Exception as e:
        print(f"[!] Error collecting HackRF data: {e}")

def simulate_gps_coordinates():
    # Simulated GPS coordinates for testing
    latitude = 39.7392 + random.uniform(-0.01, 0.01)
    longitude = -104.9903 + random.uniform(-0.01, 0.01)
    return latitude, longitude

def triangulate_signals(signal_data):
    # Dummy triangulation logic for demonstration
    if len(signal_data) < 3:
        return {"status": "Insufficient data for triangulation"}
    latitude = sum([signal["latitude"] for signal in signal_data]) / len(signal_data)
    longitude = sum([signal["longitude"] for signal in signal_data]) / len(signal_data)
    return {"latitude": latitude, "longitude": longitude, "status": "Triangulation successful"}

async def run_collections():
    initialize_csv()
    await scan_bluetooth()
    collect_adsb()
    capture_wifi()
    collect_hackrf()

def collection_worker():
    global is_collecting
    while is_collecting:
        try:
            asyncio.run(run_collections())
        except Exception as e:
            print(f"[!] Error in collection: {e}")
        time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_collection():
    global is_collecting, collection_thread
    initialize_csv()
    if not is_collecting:
        is_collecting = True
        collection_thread = threading.Thread(target=collection_worker)
        collection_thread.start()
        return jsonify({"status": "Collection started"})
    return jsonify({"status": "Collection already running"})

@app.route('/api/stop', methods=['POST'])
def stop_collection():
    global is_collecting
    if is_collecting:
        is_collecting = False
        return jsonify({"status": "Collection stopped"})
    return jsonify({"status": "Collection not running"})

@app.route('/api/reset', methods=['POST'])
def reset_data():
    try:
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
        initialize_csv()
        return jsonify({"status": "Data reset successful"})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        with open(OUTPUT_FILE, 'r') as f:
            lines = f.readlines()
            lines = lines[-100:]
        data = []
        headers = [
            'timestamp', 'type', 'name_address', 'signal_strength',
            'frequency', 'latitude', 'longitude', 'additional_info'
        ]
        for line in lines[1:]:
            values = line.strip().split(',')
            data.append(dict(zip(headers, values)))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/triangulate', methods=['POST'])
def api_triangulate():
    try:
        signal_data = request.json.get("signals", [])
        result = triangulate_signals(signal_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    initialize_csv()
    app.run(host='0.0.0.0', port=8000)
