from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import csv
import asyncio
import threading
from bleak import BleakScanner
import random
import time

app = Flask(__name__)
CORS(app)

# Database setup
DATABASE_URL = "sqlite:///signals.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

class Signal(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    signal_type = Column(String)
    name_address = Column(String)
    signal_strength = Column(String)
    frequency = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    additional_info = Column(String)

Base.metadata.create_all(engine)

# Global variables
is_collecting = False
collection_thread = None

def log_data(signal_type, name_or_address, strength, frequency, latitude, longitude, additional_info=""):
    new_signal = Signal(
        signal_type=signal_type,
        name_address=name_or_address,
        signal_strength=strength,
        frequency=frequency,
        latitude=latitude,
        longitude=longitude,
        additional_info=additional_info
    )
    session.add(new_signal)
    session.commit()

def simulate_gps_coordinates():
    latitude = 39.7392 + random.uniform(-0.01, 0.01)
    longitude = -104.9903 + random.uniform(-0.01, 0.01)
    return latitude, longitude

async def scan_bluetooth():
    try:
        devices = await BleakScanner.discover()
        for device in devices:
            latitude, longitude = simulate_gps_coordinates()
            log_data(
                "Bluetooth",
                f"{device.name or 'Unknown'} [{device.address}]",
                "-70",  # Replace with a default or mock RSSI
                "2.4 GHz",
                latitude,
                longitude,
                ""
            )
    except Exception as e:
        print(f"[!] Bluetooth error: {e}")

def collect_adsb():
    latitude, longitude = simulate_gps_coordinates()
    log_data("ADS-B", "Aircraft", "N/A", "1090 MHz", latitude, longitude, "Sample ADS-B data")

def capture_wifi():
    latitude, longitude = simulate_gps_coordinates()
    log_data("Wi-Fi", "Unknown Device", "N/A", "2.4/5 GHz", latitude, longitude, "Sample Wi-Fi data")

def collect_hackrf():
    latitude, longitude = simulate_gps_coordinates()
    log_data("HackRF", "Ambient Signal", "N/A", "915 MHz", latitude, longitude, "Sample HackRF data")

async def run_collections():
    await scan_bluetooth()
    collect_adsb()
    capture_wifi()
    collect_hackrf()

def collection_worker():
    global is_collecting
    while is_collecting:
        asyncio.run(run_collections())
        time.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_collection():
    global is_collecting, collection_thread
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
        session.query(Signal).delete()
        session.commit()
        return jsonify({"status": "Database cleared"})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    signals = session.query(Signal).all()
    data = [
        {
            "timestamp": signal.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "type": signal.signal_type,
            "name_address": signal.name_address,
            "signal_strength": signal.signal_strength,
            "frequency": signal.frequency,
            "latitude": signal.latitude,
            "longitude": signal.longitude,
            "additional_info": signal.additional_info,
        }
        for signal in signals
    ]
    return jsonify(data)

@app.route('/api/save', methods=['POST'])
def save_csv():
    try:
        # Ensure the directory exists
        output_dir = os.path.join(os.getcwd(), 'api')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "signals_export.csv")
        
        # Write database data to CSV
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Frequency", "Latitude", "Longitude", "Additional Info"])
            for signal in session.query(Signal).all():
                writer.writerow([
                    signal.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    signal.signal_type,
                    signal.name_address,
                    signal.signal_strength,
                    signal.frequency,
                    signal.latitude,
                    signal.longitude,
                    signal.additional_info,
                ])
        
        # Serve the file as a download
        return send_file(output_file, as_attachment=True)
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
