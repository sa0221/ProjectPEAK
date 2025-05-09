#!/usr/bin/env python3
"""
# Controller Service Module

The Controller Service is the central hub of Project PEAK, providing a FastAPI-based web interface
for managing RF signal collection, storage, and visualization. It coordinates multiple collectors
and provides a real-time dashboard for monitoring RF activity.

## Features

- RESTful API for signal collection and management
- SQLite database for signal storage
- Real-time dashboard with interactive visualizations
- Support for multiple collector instances
- Data export capabilities
- Automatic geolocation

## API Endpoints

### Collection Control
- `GET /api/collection-status` - Check if collection is active
- `POST /api/start` - Start signal collection
- `POST /api/stop` - Stop signal collection
- `POST /api/reset` - Clear all collected data

### Data Management
- `GET /api/data` - Retrieve all collected signals
- `POST /api/collect` - Submit new signals from collectors
- `POST /api/save` - Export data as CSV
- `GET /api/location` - Get controller's geolocation
- `GET /api/devices` - List detected hardware
- `POST /api/devices` - Update hardware information

## Dashboard

The dashboard (`/`) provides:
- Real-time signal visualization
- Interactive map with heatmap overlay
- Signal type filtering
- Data export controls
- Hardware status monitoring

## Database Schema

The SQLite database (`signals.db`) uses the following schema:

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    type TEXT,
    name_address TEXT,
    signal_strength TEXT,
    frequency TEXT,
    latitude FLOAT,
    longitude FLOAT,
    additional_info TEXT
);
```
"""
import requests, csv, io, re, uvicorn
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="Project PEAK Controller")

# ─── Database Setup ─────────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./data/signals.db"
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base         = declarative_base()

class Signal(Base):
    """
    SQLAlchemy model for storing RF signals.

    Attributes:
        id (int): Primary key
        timestamp (str): ISO-8601 timestamp of signal detection
        type (str): Signal type (Bluetooth/ADS-B/Wi-Fi/Spectrum)
        name_address (str): Device identifier or address
        signal_strength (str): Signal strength in dBm or N/A
        frequency (str): Operating frequency
        latitude (float): Detection latitude
        longitude (float): Detection longitude
        additional_info (str): Protocol-specific details
    """
    __tablename__ = "signals"
    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(String)
    type            = Column(String)
    name_address    = Column(String)
    signal_strength = Column(String)
    frequency       = Column(String)
    latitude        = Column(Float)
    longitude       = Column(Float)
    additional_info = Column(String)

# create table if missing
Base.metadata.create_all(bind=engine)

# ─── In-Memory State ────────────────────────────────────────────────────────────
collection_active: bool    = True
devices_info:     list[str] = []

def get_controller_location() -> tuple[float, float]:
    """
    Fetch the controller's geolocation via IP lookup.

    Returns:
        tuple[float, float]: (latitude, longitude) of the controller.
        Falls back to Denver coordinates (39.7392, -104.9903) if lookup fails.

    Note:
        Uses ip-api.com for geolocation. The free tier has rate limits.
    """
    try:
        resp = requests.get("http://ip-api.com/json/", timeout=2).json()
        if resp.get("status") == "success":
            return resp["lat"], resp["lon"]
    except:
        pass
    return 39.7392, -104.9903

CONTROLLER_LAT, CONTROLLER_LON = get_controller_location()

# ─── API ────────────────────────────────────────────────────────────────────────
@app.get("/api/location")
async def api_location():
    """
    Get the controller's current geolocation.

    Returns:
        dict: Contains latitude and longitude of the controller.
    """
    return {"lat": CONTROLLER_LAT, "lon": CONTROLLER_LON}

@app.get("/api/collection-status")
async def api_collection_status():
    """
    Check if signal collection is currently active.

    Returns:
        dict: Contains the current collection status.
    """
    return {"active": collection_active}

@app.post("/api/start")
async def start_collection():
    """
    Start the signal collection process.

    Returns:
        dict: Confirmation of collection start.
    """
    global collection_active
    collection_active = True
    return {"status": "collection started"}

@app.post("/api/stop")
async def stop_collection():
    """
    Stop the signal collection process.

    Returns:
        dict: Confirmation of collection stop.
    """
    global collection_active
    collection_active = False
    return {"status": "collection stopped"}

@app.post("/api/devices")
async def update_devices(dev: dict = Body(...)):
    """
    Update the list of detected RF hardware.

    Args:
        dev (dict): Contains a list of detected devices.

    Returns:
        dict: Confirmation of device list update.
    """
    global devices_info
    devices_info = dev.get("devices", [])
    return {"status": "devices updated"}

@app.get("/api/devices")
async def get_devices():
    """
    Get the current list of detected RF hardware.

    Returns:
        dict: Contains the list of detected devices.
    """
    return {"devices": devices_info}

@app.post("/api/collect")
async def collect_signals(signals: list[dict] = Body(...)):
    """
    Store new signals from collectors in the database.

    Args:
        signals (list[dict]): List of signal records to store.

    Returns:
        dict: Contains status and number of signals received.

    Note:
        Cleans control characters from additional_info field before storage.
    """
    db = SessionLocal()
    ctrl = re.compile(r'[\x00-\x1F\x7F]')
    for s in signals:
        info_clean = ctrl.sub("", s.get("additional_info", ""))
        db.add(Signal(
            timestamp       = s.get("timestamp",""),
            type            = s.get("type",""),
            name_address    = s.get("name_address",""),
            signal_strength = s.get("signal_strength",""),
            frequency       = s.get("frequency",""),
            latitude        = s.get("latitude"),
            longitude       = s.get("longitude"),
            additional_info = info_clean
        ))
    db.commit()
    db.close()
    return {"status": "success", "received": len(signals)}

@app.get("/api/data")
async def get_data():
    """
    Retrieve all stored signals from the database.

    Returns:
        list[dict]: List of all signal records.
    """
    db = SessionLocal()
    rows = db.query(Signal).all()
    db.close()
    return [{
        "timestamp": r.timestamp,
        "type": r.type,
        "name_address": r.name_address,
        "signal_strength": r.signal_strength,
        "frequency": r.frequency,
        "latitude": r.latitude,
        "longitude": r.longitude,
        "additional_info": r.additional_info
    } for r in rows]

@app.post("/api/reset")
async def reset_data():
    """
    Clear all stored signals from the database.

    Returns:
        dict: Confirmation of data reset.
    """
    db = SessionLocal()
    db.query(Signal).delete()
    db.commit()
    db.close()
    return {"status": "reset"}

@app.post("/api/save")
async def save_data():
    """
    Export all stored signals as a CSV file.

    Returns:
        StreamingResponse: CSV file download containing all signals.

    Note:
        The CSV includes all signal fields in a human-readable format.
    """
    db = SessionLocal()
    rows = db.query(Signal).all()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp","Type","Name/Address","Signal Strength",
        "Additional Info","Frequency","Latitude","Longitude"
    ])
    for r in rows:
        writer.writerow([
            r.timestamp, r.type, r.name_address, r.signal_strength,
            r.additional_info, r.frequency, r.latitude, r.longitude
        ])

    resp = StreamingResponse(io.StringIO(output.getvalue()), media_type="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=signals_export.csv"
    return resp

# ─── Dashboard UI ──────────────────────────────────────────────────────────────
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Project PEAK Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.heat/dist/leaflet-heat.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { background: #1e293b; color: #f1f5f9; }
    .card { @apply bg-gray-800 rounded-lg shadow-lg p-6 mb-6; }
    .btn { @apply px-4 py-2 rounded-lg font-semibold focus:outline-none; }
    .btn-primary { @apply bg-blue-500 hover:bg-blue-600; }
    .btn-accent  { @apply bg-green-500 hover:bg-green-600; }
    .btn-danger  { @apply bg-red-500 hover:bg-red-600; }
    .table { @apply w-full text-sm text-left text-gray-300; }
    .table th { @apply border-b border-gray-700 py-2; }
    .table td { @apply border-b border-gray-700 py-2; }
  </style>
</head>
<body class="p-8">
  <h1 class="text-3xl font-bold mb-6 text-center">🚀 Project PEAK Controller Dashboard</h1>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
    <div class="card text-center">
      <button id="start-btn" class="btn btn-primary mr-2">Start</button>
      <button id="stop-btn"  class="btn btn-danger">Stop</button>
    </div>
    <div class="card text-center">
      <button id="reset-btn" class="btn btn-accent mr-2">Clear Data</button>
      <button id="save-btn"  class="btn btn-primary">Export CSV</button>
    </div>
    <div class="card text-center">
      <label>Filter:</label>
      <select id="type-filter" class="mt-2 p-2 rounded-lg bg-gray-700 text-gray-200">
        <option value="all">All</option>
        <option>Bluetooth</option>
        <option>ADS-B</option>
        <option>Wi-Fi</option>
        <option>Spectrum</option>
      </select>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
    <div class="card text-center">
      <h2 class="font-semibold">Total Signals</h2>
      <p id="total-signals" class="text-2xl mt-2">0</p>
    </div>
    <div class="card text-center">
      <h2 class="font-semibold">Last Timestamp</h2>
      <p id="last-time" class="text-2xl mt-2">N/A</p>
    </div>
    <div class="card text-center">
      <h2 class="font-semibold">Controller Loc</h2>
      <p id="ctrl-loc" class="mt-2">…</p>
    </div>
    <div class="card text-center">
      <h2 class="font-semibold">Detected HW</h2>
      <p id="hw-list" class="mt-2">…</p>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
    <div class="card"><canvas id="chart" height="200"></canvas></div>
    <div class="card"><div id="map" style="height:300px;"></div></div>
  </div>

  <div class="card overflow-auto" style="max-height:300px;">
    <table class="table">
      <thead>
        <tr>
          <th>Time</th><th>Type</th><th>Name/Addr</th><th>RSSI</th>
          <th>Freq</th><th>Info</th><th>Lat</th><th>Lon</th>
        </tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>

<script>
document.addEventListener('DOMContentLoaded', ()=>{
  const startBtn = document.getElementById('start-btn'),
        stopBtn  = document.getElementById('stop-btn'),
        resetBtn = document.getElementById('reset-btn'),
        saveBtn  = document.getElementById('save-btn'),
        filter   = document.getElementById('type-filter'),
        totalEl  = document.getElementById('total-signals'),
        lastEl   = document.getElementById('last-time'),
        locEl    = document.getElementById('ctrl-loc'),
        hwEl     = document.getElementById('hw-list'),
        tbody    = document.getElementById('table-body'),
        ctx      = document.getElementById('chart').getContext('2d'),
        mapDiv   = document.getElementById('map');
  let chart, map, heat;

  fetch('/api/location').then(r=>r.json()).then(loc=>{
    locEl.textContent = `${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)}`;
    map = L.map(mapDiv).setView([loc.lat, loc.lon], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    heat = L.heatLayer([], {radius: 25}).addTo(map);
  });

  fetch('/api/devices').then(r=>r.json()).then(d=>{
    hwEl.textContent = d.devices.join(", ");
  });

  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Signals',
        data: [],
        borderColor: '#3b82f6',
        tension: 0.1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#334155' },
          ticks: { color: '#94a3b8' }
        },
        x: {
          grid: { color: '#334155' },
          ticks: { color: '#94a3b8' }
        }
      },
      plugins: {
        legend: {
          labels: { color: '#94a3b8' }
        }
      }
    }
  });

  function updateUI(data) {
    const filtered = filter.value === "all" ? data : data.filter(d => d.type === filter.value);
    totalEl.textContent = filtered.length;
    if (filtered.length > 0) {
      lastEl.textContent = new Date(filtered[0].timestamp).toLocaleString();
    }

    // update chart
    const times = filtered.map(d => new Date(d.timestamp).toLocaleTimeString());
    const counts = filtered.map(d => 1);
    chart.data.labels = times;
    chart.data.datasets[0].data = counts;
    chart.update();

    // update map
    const points = filtered
      .filter(d => d.latitude && d.longitude)
      .map(d => [d.latitude, d.longitude, 1]);
    heat.setLatLngs(points);

    // update table
    tbody.innerHTML = filtered.map(d => `
      <tr>
        <td>${new Date(d.timestamp).toLocaleString()}</td>
        <td>${d.type}</td>
        <td>${d.name_address}</td>
        <td>${d.signal_strength}</td>
        <td>${d.frequency}</td>
        <td>${d.additional_info}</td>
        <td>${d.latitude?.toFixed(4) || 'N/A'}</td>
        <td>${d.longitude?.toFixed(4) || 'N/A'}</td>
      </tr>
    `).join('');
  }

  function refresh() {
    fetch('/api/data').then(r=>r.json()).then(updateUI);
  }

  startBtn.onclick = () => fetch('/api/start').then(refresh);
  stopBtn.onclick = () => fetch('/api/stop');
  resetBtn.onclick = () => fetch('/api/reset').then(refresh);
  saveBtn.onclick = () => window.location.href = '/api/save';
  filter.onchange = refresh;

  refresh();
  setInterval(refresh, 5000);
});
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    """
    Serve the main dashboard interface.

    Returns:
        HTMLResponse: The dashboard HTML page.

    Note:
        The dashboard provides real-time visualization of collected signals
        using Chart.js for graphs and Leaflet for maps.
    """
    return HTML_PAGE

# ─── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
