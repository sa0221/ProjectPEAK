from flask import Flask, render_template, request, jsonify
import os
import csv
import threading
import asyncio
from bleak import BleakScanner
from datetime import datetime
import subprocess
import re
import time

# Flask app
app = Flask(__name__)

# File to log signals
log_file = "project_peak_signals.csv"

# Initialize variables
is_collecting = False
data = {
    "Bluetooth": [],
    "ADS-B": [],
    "Wi-Fi": []
}
collect_thread = None

# Initialize CSV file
if not os.path.exists(log_file):
    with open(log_file, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Additional Info"])

# Function to log data
def log_data(signal_type, name_address, signal_strength, additional_info=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "type": signal_type,
        "name_address": name_address,
        "signal_strength": signal_strength,
        "additional_info": additional_info
    }
    data[signal_type].append(entry)
    with open(log_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, signal_type, name_address, signal_strength, additional_info])

# Function to collect Bluetooth signals
async def collect_bluetooth():
    devices = await BleakScanner.discover()
    for device in devices:
        log_data("Bluetooth", f"{device.name} [{device.address}]", device.rssi)

# Function to collect ADS-B data
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
        for line in process.stdout:
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
    except Exception as e:
        print(f"[!] Error collecting ADS-B data: {e}")

# Function to collect Wi-Fi packets using tcpdump
def collect_wifi():
    try:
        process = subprocess.Popen(
            ["tcpdump", "-i", "wlan0", "-c", "10", "-nn"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            log_data("Wi-Fi", "tcpdump", "N/A", line.strip())
    except Exception as e:
        print(f"[!] Error collecting Wi-Fi packets: {e}")

# Background collection function
def start_collection():
    global is_collecting
    is_collecting = True
    while is_collecting:
        asyncio.run(collect_bluetooth())
        collect_adsb()
        collect_wifi()
        time.sleep(10)  # Pause between cycles

# Flask routes
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Project PEAK Data Viewer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            .button.start { background-color: green; color: white; }
            .button.stop { background-color: red; color: white; }
            .button.reset { background-color: orange; color: white; }
            .button.save { background-color: blue; color: white; }
        </style>
    </head>
    <body>
        <h1>Project PEAK Data Viewer</h1>
        <div>
            <button class="button start" onclick="startCollection()">Start</button>
            <button class="button stop" onclick="stopCollection()">Stop</button>
            <button class="button reset" onclick="resetData()">Reset</button>
            <button class="button save" onclick="saveData()">Save</button>
        </div>
        <h2>Data</h2>
        <pre id="data-display"></pre>
        <script>
            function fetchData() {
                fetch("/data")
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById("data-display").textContent = JSON.stringify(data, null, 2);
                    });
            }
            function startCollection() {
                fetch("/start", { method: "POST" });
            }
            function stopCollection() {
                fetch("/stop", { method: "POST" });
            }
            function resetData() {
                fetch("/reset", { method: "POST" });
            }
            function saveData() {
                fetch("/save", { method: "POST" });
            }
            setInterval(fetchData, 2000);  // Fetch data every 2 seconds
        </script>
    </body>
    </html>
    """

@app.route("/start", methods=["POST"])
def start():
    global collect_thread
    if not is_collecting:
        collect_thread = threading.Thread(target=start_collection)
        collect_thread.start()
    return jsonify({"status": "Collection started"})

@app.route("/stop", methods=["POST"])
def stop():
    global is_collecting
    is_collecting = False
    if collect_thread and collect_thread.is_alive():
        collect_thread.join()
    return jsonify({"status": "Collection stopped"})

@app.route("/reset", methods=["POST"])
def reset():
    global data
    data = { "Bluetooth": [], "ADS-B": [], "Wi-Fi": [] }
    return jsonify({"status": "Data reset"})

@app.route("/save", methods=["POST"])
def save():
    return jsonify({"status": "Data saved to CSV", "file": log_file})

@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(data)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
