# api/server.py

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import subprocess
import threading
import json
import os
import time
from datetime import datetime
from geopy.geocoders import Nominatim
import csv

app = Flask(__name__)
CORS(app)

# Global variables
is_collecting = False
collection_thread = None

# Ensure the CSV exists with headers
def initialize_csv():
    if not os.path.exists('project_peak_signals.csv'):
        with open('project_peak_signals.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Additional Info"])

def run_collection_script():
    global is_collecting
    while is_collecting:
        try:
            # Run the collection script and capture output
            result = subprocess.run(
                ['python3', 'api/collector.py'],  # Updated path
                capture_output=True,
                text=True,
                timeout=30
            )
            print("Collector Output:", result.stdout)
            print("Collector Error:", result.stderr)
        except subprocess.TimeoutExpired:
            print("Collection cycle completed")
        except Exception as e:
            print(f"Error in collection: {e}")
        time.sleep(1)

# Serve the frontend
@app.route('/')
def index():
    return render_template('index.html')

# API endpoints
@app.route('/api/start', methods=['POST'])
def start_collection():
    global is_collecting, collection_thread
    initialize_csv()
    if not is_collecting:
        is_collecting = True
        collection_thread = threading.Thread(target=run_collection_script)
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
        if os.path.exists('project_peak_signals.csv'):
            os.remove('project_peak_signals.csv')
        initialize_csv()
        return jsonify({"status": "Data reset successful"})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route('/api/save', methods=['POST'])
def save_data():
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f'project_peak_signals_{timestamp}.csv'
        os.system(f'cp project_peak_signals.csv {backup_file}')
        return jsonify({"status": "success", "message": f"Data saved to {backup_file}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        with open('project_peak_signals.csv', 'r') as f:
            lines = f.readlines()
            lines = lines[-100:]
        data = []
        headers = ['timestamp', 'type', 'name_address', 'signal_strength', 'additional_info']
        for line in lines[1:]:
            values = line.strip().split(',')
            data.append(dict(zip(headers, values)))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/location', methods=['GET'])
def get_location():
    try:
        geolocator = Nominatim(user_agent="ProjectPEAK")
        # Use actual coordinates or logic here
        location = geolocator.geocode("1600 Amphitheatre Parkway, Mountain View, CA")
        if location:
            return jsonify({"latitude": location.latitude, "longitude": location.longitude})
        else:
            return jsonify({"error": "Unable to fetch geo-coordinates"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    initialize_csv()
    app.run(host='0.0.0.0', port=8000)
