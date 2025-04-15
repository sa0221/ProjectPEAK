#!/usr/bin/env python3
"""
Controller Service Module for Project PEAK

This module provides a FastAPI-powered web service that centralizes control and data management for the Project PEAK system.
It exposes RESTful endpoints for starting/stopping signal collection, updating and retrieving detected hardware details,
persisting collected signal data to a SQLite database using SQLAlchemy, and offering a real-time HTML dashboard to monitor
and analyze the received signals.

Key Features:
    - API endpoints for controlling signal collection:
        * /api/start: Enable data collection.
        * /api/stop: Disable data collection.
        * /api/collection-status: Query the current status.
    - Device registration via /api/devices: Allows collectors to report detected hardware.
    - Data ingestion endpoint (/api/collect) for persisting RF signal data with detailed metadata.
    - Endpoints for data retrieval:
        * /api/data: Retrieve all stored signals.
        * /api/save: Export signals as a CSV file.
    - A built-in dashboard (HTML served at '/') that uses Chart.js and Leaflet.js for visualization.
    - Geolocation retrieval for dynamic UI mapping, falling back to default (Denver) if necessary.

Usage:
    Execute this module directly (or via Docker) to start the uvicorn ASGI server on port 8000.
    
Requirements:
    - Python 3.11+
    - FastAPI, uvicorn, SQLAlchemy, requests, csv, and other supporting libraries.

Author: [Your Name]
Date: 2025-04-14
"""

import requests
import uvicorn
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, StreamingResponse
import csv, io, re
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

app = FastAPI(title="Project PEAK Controller")

# --- Database Setup ---
DATABASE_URL: str = "sqlite:///signals.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Signal(Base):
    """
    SQLAlchemy ORM model for storing RF signal entries.

    Attributes:
        id (int): Unique primary key.
        timestamp (str): Timestamp of signal capture (ISO formatted).
        type (str): Signal type (e.g., Bluetooth, ADS-B, Wi-Fi).
        name_address (str): Concatenated device name and/or address.
        signal_strength (str): Signal strength (may be "N/A" if not available).
        frequency (str): Reception frequency (e.g., "1090 MHz" for ADS-B).
        latitude (float): Latitude from geolocation, if available.
        longitude (float): Longitude from geolocation, if available.
        additional_info (str): Raw or supplementary signal data.
    """
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)
    type = Column(String)
    name_address = Column(String)
    signal_strength = Column(String)
    frequency = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    additional_info = Column(String)

Base.metadata.create_all(bind=engine)

# --- Controller State ---
collection_active: bool = False  # Global flag indicating whether collection is ongoing.
devices_info: list[str] = []       # Stores the latest reported hardware devices from collectors.

def get_controller_location() -> tuple[float, float]:
    """
    Obtain the geolocation coordinates for the Controller using an external service.

    This function sends a GET request to "http://ip-api.com/json/" to retrieve latitude and longitude.
    If the API call is unsuccessful, it logs the error and falls back to default coordinates (Denver).

    Returns:
        tuple[float, float]: A tuple containing (latitude, longitude).

    Notes:
        The geolocation data is used for mapping purposes in the dashboard UI.
    """
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()
        if data.get("status") == "success":
            lat = data.get("lat")
            lon = data.get("lon")
            print(f"[Controller] Detected location: {lat}, {lon}")
            return lat, lon
        else:
            print("[Controller] Geolocation API error; using fallback coordinates.")
            return 39.7392, -104.9903
    except Exception as e:
        print(f"[Controller] Exception in geolocation: {e}")
        return 39.7392, -104.9903

CONTROLLER_LAT, CONTROLLER_LON = get_controller_location()

@app.get("/api/location")
async def api_location() -> dict:
    """
    Endpoint: GET /api/location

    Returns the current geographical coordinates of the Controller.

    Returns:
        dict: A dictionary with keys 'lat' and 'lon' representing the controller's latitude and longitude.
    """
    return {"lat": CONTROLLER_LAT, "lon": CONTROLLER_LON}

@app.get("/api/collection-status")
async def api_collection_status() -> dict:
    """
    Endpoint: GET /api/collection-status

    Provides the current state (active/inactive) of the RF signal collection process.

    Returns:
        dict: {"active": <bool>} indicating if signal collection is enabled.
    """
    return {"active": collection_active}

@app.post("/api/start")
async def start_collection() -> dict:
    """
    Endpoint: POST /api/start

    Activates the RF signal collection process.
    
    Side Effects:
        Sets the global variable 'collection_active' to True.

    Returns:
        dict: A confirmation message, e.g., {"status": "collection started"}.
    """
    global collection_active
    collection_active = True
    return {"status": "collection started"}

@app.post("/api/stop")
async def stop_collection() -> dict:
    """
    Endpoint: POST /api/stop

    Deactivates the RF signal collection process.
    
    Side Effects:
        Sets the global variable 'collection_active' to False.

    Returns:
        dict: A confirmation message, e.g., {"status": "collection stopped"}.
    """
    global collection_active
    collection_active = False
    return {"status": "collection stopped"}

@app.post("/api/devices")
async def update_devices(devices: dict = Body(...)) -> dict:
    """
    Endpoint: POST /api/devices

    Updates the Controller with the latest list of detected hardware devices provided by a collector.

    Args:
        devices (dict): Expected in the format {"devices": [<device1>, <device2>, ...]}.

    Side Effects:
        Updates the global 'devices_info' list with the provided devices.

    Returns:
        dict: A simple confirmation message, e.g., {"status": "devices updated"}.
    """
    global devices_info
    devices_info = devices.get("devices", [])
    return {"status": "devices updated"}

@app.get("/api/devices")
async def get_devices() -> dict:
    """
    Endpoint: GET /api/devices

    Returns the most recently recorded list of detected hardware devices.

    Returns:
        dict: A dictionary containing the key 'devices' with an array of device names.
    """
    return {"devices": devices_info}

@app.post("/api/collect")
async def collect_signals(signals: list = Body(...)) -> dict:
    """
    Endpoint: POST /api/collect

    Ingests a list of RF signal data dictionaries (sent by collectors), cleans the extra control characters,
    and persists each entry into the SQLite database using SQLAlchemy.

    Args:
        signals (list): A list of dictionaries containing signal information (e.g., timestamp, type, name_address, etc.).

    Process:
        - Iterates over each dictionary.
        - Removes control characters from the 'additional_info' field for a clean display.
        - Creates and adds a new Signal instance to the database.
        - Commits the changes.

    Returns:
        dict: A confirmation with the count of successfully received signals (e.g., {"status": "success", "received": <count>}).
    """
    db = SessionLocal()
    control_char_pattern = re.compile(r'[\x00-\x1F\x7F]')
    for sig in signals:
        info = sig.get("additional_info", "")
        cleaned_info = control_char_pattern.sub("", info)
        new_signal = Signal(
            timestamp=sig.get("timestamp", ""),
            type=sig.get("type", ""),
            name_address=sig.get("name_address", ""),
            signal_strength=sig.get("signal_strength", ""),
            frequency=sig.get("frequency", ""),
            latitude=sig.get("latitude"),
            longitude=sig.get("longitude"),
            additional_info=cleaned_info
        )
        db.add(new_signal)
    db.commit()
    db.close()
    return {"status": "success", "received": len(signals)}

@app.get("/api/data")
async def get_data() -> list[dict]:
    """
    Endpoint: GET /api/data

    Retrieves all stored RF signal entries from the database.

    Returns:
        list[dict]: A list of dictionaries, each representing a stored signal with keys such as
                    timestamp, type, name_address, signal_strength, frequency, latitude, longitude, and additional_info.
    """
    db = SessionLocal()
    signals = db.query(Signal).all()
    db.close()
    return [{
        "timestamp": s.timestamp,
        "type": s.type,
        "name_address": s.name_address,
        "signal_strength": s.signal_strength,
        "frequency": s.frequency,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "additional_info": s.additional_info
    } for s in signals]

@app.post("/api/reset")
async def reset_data() -> dict:
    """
    Endpoint: POST /api/reset

    Deletes all RF signal data stored in the database.

    Side Effects:
        Clears the 'signals' table in the SQLite database.

    Returns:
        dict: A confirmation message indicating that the reset was successful, e.g., {"status": "reset"}.
    """
    db = SessionLocal()
    db.query(Signal).delete()
    db.commit()
    db.close()
    return {"status": "reset"}

@app.post("/api/save")
async def save_data() -> StreamingResponse:
    """
    Endpoint: POST /api/save

    Exports the stored RF signal data as a CSV file by reading from the SQLite database and writing data to an in-memory CSV.

    Process:
        - Queries all Signal entries.
        - Writes the data with headers into a CSV format.
        - Wraps the in-memory CSV content into a StreamingResponse with appropriate headers
          to prompt a file download.

    Returns:
        StreamingResponse: A stream of CSV data with the header indicating 'filename=signals_export.csv'.
    """
    db = SessionLocal()
    signals = db.query(Signal).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Additional Info", "Frequency", "Latitude", "Longitude"])
    for s in signals:
        writer.writerow([
            s.timestamp,
            s.type,
            s.name_address,
            s.signal_strength,
            s.additional_info,
            s.frequency,
            s.latitude,
            s.longitude
        ])
    db.close()
    response = StreamingResponse(io.StringIO(output.getvalue()), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=signals_export.csv"
    return response

# --- HTML UI ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Project PEAK Controller Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat/dist/leaflet-heat.js"></script>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f4; }
    h1 { text-align: center; }
    #controls { text-align: center; margin-bottom: 20px; }
    button { padding: 10px 20px; margin: 5px; border: none; background-color: #007bff; color: white; border-radius: 5px; cursor: pointer; }
    button:hover { background-color: #0056b3; }
    select { padding: 10px; margin: 5px; border-radius: 5px; }
    #stats { text-align: center; margin-bottom: 20px; }
    #signal-list { list-style: none; padding: 10px; max-height: 300px; overflow-y: scroll; background: white; border-radius: 5px; }
    #signal-list li { border-bottom: 1px solid #ddd; padding: 5px; }
    #chart-canvas { margin: auto; display: block; max-width: 600px; }
    #map { height: 400px; margin: 20px auto; max-width: 600px; }
  </style>
</head>
<body>
  <h1>Project PEAK Controller Dashboard</h1>
  <div id="controls">
    <button id="start-btn">Start Collection</button>
    <button id="stop-btn">Stop Collection</button>
    <button id="reset-btn">Reset Data</button>
    <button id="save-btn">Save as CSV</button>
    <select id="signal-type-select">
      <option value="all">All</option>
      <option value="Bluetooth">Bluetooth</option>
      <option value="ADS-B">ADS-B</option>
      <option value="Wi-Fi">Wi-Fi</option>
      <option value="Spectrum">Spectrum</option>
    </select>
  </div>
  <div id="stats">
    <h3>Total Signals: <span id="total-signals">0</span></h3>
    <h3>Last Signal Time: <span id="last-signal-time">N/A</span></h3>
    <h3>Controller Location: <span id="controller-location">Loading...</span></h3>
    <h3>Detected Hardware: <span id="hardware-list">Loading...</span></h3>
  </div>
  <ul id="signal-list"></ul>
  <canvas id="chart-canvas" width="600" height="300"></canvas>
  <div id="map"></div>
  <script>
    // Frontend dashboard logic to fetch, display, and update signal data and statistics.
    document.addEventListener('DOMContentLoaded', () => {
      const startBtn = document.getElementById('start-btn');
      const stopBtn = document.getElementById('stop-btn');
      const resetBtn = document.getElementById('reset-btn');
      const saveBtn = document.getElementById('save-btn');
      const signalTypeSelect = document.getElementById('signal-type-select');
      const signalList = document.getElementById('signal-list');
      const chartCanvas = document.getElementById('chart-canvas');
      const mapDiv = document.getElementById('map');
      const totalSignalsEl = document.getElementById('total-signals');
      const lastSignalTimeEl = document.getElementById('last-signal-time');
      const controllerLocEl = document.getElementById('controller-location');
      const hardwareListEl = document.getElementById('hardware-list');

      let isCollecting = false;
      let selectedSignalType = 'all';
      let chart;
      let map;
      let markers = [];
      let heatLayer;
      let totalSignals = 0;

      // Update UI with controller geolocation.
      fetch('/api/location')
        .then(res => res.json())
        .then(loc => {
          controllerLocEl.textContent = loc.lat + ", " + loc.lon;
          if (!map) {
            map = L.map(mapDiv).setView([loc.lat, loc.lon], 12);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
              attribution: '© OpenStreetMap contributors'
            }).addTo(map);
            heatLayer = L.heatLayer([], { radius: 25, blur: 15, maxZoom: 17 }).addTo(map);
          }
        });

      // Populate detected hardware list.
      fetch('/api/devices')
        .then(res => res.json())
        .then(data => {
          hardwareListEl.textContent = data.devices ? data.devices.join(', ') : 'None';
        });

      fetchData();

      // Start collection button handler.
      startBtn.addEventListener('click', () => {
        fetch('/api/start', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            alert(data.status);
            isCollecting = true;
            fetchData();
          });
      });

      // Stop collection button handler.
      stopBtn.addEventListener('click', () => {
        fetch('/api/stop', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            alert(data.status);
            isCollecting = false;
          });
      });

      // Reset data button handler.
      resetBtn.addEventListener('click', () => {
        fetch('/api/reset', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            alert(data.status);
            resetUI();
            fetchData();
          });
      });

      // CSV export button handler.
      saveBtn.addEventListener('click', () => {
        fetch('/api/save', { method: 'POST' })
          .then(res => res.blob())
          .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'signals_export.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
          });
      });

      // Update selected signal type and refresh data.
      signalTypeSelect.addEventListener('change', () => {
        selectedSignalType = signalTypeSelect.value;
        fetchData();
      });

      // Fetch signal data repeatedly from the API.
      function fetchData() {
        fetch('/api/data')
          .then(res => res.json())
          .then(data => {
            updateSignalStats(data);
            updateSignalList(data);
            updateChart(data);
            updateMap(data);
            if (isCollecting) setTimeout(fetchData, 2000);
          });
      }

      // Update signal statistics: total count and last signal time.
      function updateSignalStats(data) {
        totalSignals = data.length;
        totalSignalsEl.textContent = totalSignals;
        if (totalSignals > 0) {
          lastSignalTimeEl.textContent = data[data.length - 1].timestamp;
        } else {
          lastSignalTimeEl.textContent = 'N/A';
        }
      }

      // Build a detailed list of signals.
      function updateSignalList(data) {
        signalList.innerHTML = '';
        const filteredData = data.filter(signal =>
          selectedSignalType === 'all' || signal.type === selectedSignalType
        );
        filteredData.forEach(signal => {
          const listItem = document.createElement('li');
          listItem.innerHTML = "<b>Timestamp:</b> " + signal.timestamp + "<br>" +
            "<b>Type:</b> " + signal.type + "<br>" +
            "<b>Name/Address:</b> " + signal.name_address + "<br>" +
            "<b>Signal Strength:</b> " + (signal.signal_strength || "N/A") + "<br>" +
            "<b>Frequency:</b> " + (signal.frequency || "N/A") + "<br>" +
            "<b>Latitude:</b> " + (signal.latitude || "N/A") + "<br>" +
            "<b>Longitude:</b> " + (signal.longitude || "N/A") + "<br>" +
            "<b>Additional Info:</b> " + (signal.additional_info || "N/A");
          listItem.className = 'signal-item';
          signalList.appendChild(listItem);
        });
      }

      // Update chart displaying signal counts per type.
      function updateChart(data) {
        const signalCounts = data.reduce((acc, signal) => {
          acc[signal.type] = (acc[signal.type] || 0) + 1;
          return acc;
        }, {});

        const labels = Object.keys(signalCounts);
        const counts = Object.values(signalCounts);

        if (!chart) {
          chart = new Chart(chartCanvas.getContext('2d'), {
            type: 'bar',
            data: {
              labels: labels,
              datasets: [{
                label: 'Signal Count',
                data: counts,
                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1,
              }],
            },
            options: {
              responsive: true,
              scales: { y: { beginAtZero: true } },
            },
          });
        } else {
          chart.data.labels = labels;
          chart.data.datasets[0].data = counts;
          chart.update();
        }
      }

      // Update map and heatmap with signal locations.
      function updateMap(data) {
        if (!map) {
          fetch('/api/location')
            .then(res => res.json())
            .then(loc => {
              map = L.map(mapDiv).setView([loc.lat, loc.lon], 12);
              L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
              }).addTo(map);
              heatLayer = L.heatLayer([], { radius: 25, blur: 15, maxZoom: 17 }).addTo(map);
            });
        }
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];
        const heatData = [];
        data.filter(signal =>
          selectedSignalType === 'all' || signal.type === selectedSignalType
        ).forEach(signal => {
          if (signal.latitude && signal.longitude) {
            heatData.push([parseFloat(signal.latitude), parseFloat(signal.longitude), 0.5]);
            const marker = L.marker([parseFloat(signal.latitude), parseFloat(signal.longitude)])
              .addTo(map)
              .bindPopup("<b>Type:</b> " + signal.type + "<br>" +
                         "<b>Name/Address:</b> " + signal.name_address + "<br>" +
                         "<b>Signal Strength:</b> " + (signal.signal_strength || "N/A") + "<br>" +
                         "<b>Frequency:</b> " + (signal.frequency || "N/A") + "<br>" +
                         "<b>Additional Info:</b> " + (signal.additional_info || "N/A"));
            markers.push(marker);
          }
        });
        if (heatLayer) {
          heatLayer.setLatLngs(heatData);
        }
      }

      // Clear UI elements when resetting data.
      function resetUI() {
        totalSignals = 0;
        totalSignalsEl.textContent = '0';
        lastSignalTimeEl.textContent = 'N/A';
        signalList.innerHTML = '';
        if (chart) {
          chart.data.labels = [];
          chart.data.datasets[0].data = [];
          chart.update();
        }
        if (map && heatLayer) {
          heatLayer.setLatLngs([]);
          markers.forEach(marker => map.removeLayer(marker));
          markers = [];
        }
      }
    });
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """
    Serves the dynamic HTML dashboard for monitoring the Project PEAK Controller.

    Returns:
        HTMLResponse: The static HTML content rendering the dashboard,
                      featuring control buttons, charts, maps, and data feeds.
    """
    return HTML_PAGE

if __name__ == "__main__":
    # Start the Controller service using uvicorn. The app listens on all network interfaces at port 8000.
    uvicorn.run("controller:app", host="0.0.0.0", port=8000)
