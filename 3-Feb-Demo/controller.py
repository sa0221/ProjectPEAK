#!/usr/bin/env python3
"""
Controller Service Module for Project PEAK

FastAPI service that centralizes control, data ingestion, and storage (SQLite)
for live RF signal collections, and serves a Tailwind/Chart.js/Leaflet dashboard at "/".
"""

import requests, csv, io, re, uvicorn
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

app = FastAPI(title="Project PEAK Controller")

# ─── Database Setup ─────────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./data/signals.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Signal(Base):
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

# ensure our table exists
Base.metadata.create_all(bind=engine)

# ─── In-memory State ────────────────────────────────────────────────────────────
collection_active: bool    = True
devices_info:     list[str] = []

def get_controller_location() -> tuple[float, float]:
    """Try external IP geolocation, else Denver fallback."""
    try:
        r = requests.get("http://ip-api.com/json/", timeout=2).json()
        if r.get("status") == "success":
            return r["lat"], r["lon"]
    except:
        pass
    return 39.7392, -104.9903

CONTROLLER_LAT, CONTROLLER_LON = get_controller_location()

# ─── API Endpoints ─────────────────────────────────────────────────────────────
@app.get("/api/location")
async def api_location():
    return {"lat": CONTROLLER_LAT, "lon": CONTROLLER_LON}

@app.get("/api/collection-status")
async def api_collection_status():
    return {"active": collection_active}

@app.post("/api/start")
async def start_collection():
    global collection_active
    collection_active = True
    return {"status": "collection started"}

@app.post("/api/stop")
async def stop_collection():
    global collection_active
    collection_active = False
    return {"status": "collection stopped"}

@app.post("/api/devices")
async def update_devices(dev: dict = Body(...)):
    global devices_info
    devices_info = dev.get("devices", [])
    return {"status": "devices updated"}

@app.get("/api/devices")
async def get_devices():
    return {"devices": devices_info}

@app.post("/api/collect")
async def collect_signals(signals: list[dict] = Body(...)):
    db = SessionLocal()
    ctrl = re.compile(r'[\x00-\x1F\x7F]')
    for s in signals:
        info = s.get("additional_info", "")
        clean = ctrl.sub("", info)
        db.add(Signal(
            timestamp=s.get("timestamp",""),
            type=s.get("type",""),
            name_address=s.get("name_address",""),
            signal_strength=s.get("signal_strength",""),
            frequency=s.get("frequency",""),
            latitude=s.get("latitude"),
            longitude=s.get("longitude"),
            additional_info=clean
        ))
    db.commit()
    db.close()
    return {"status": "success", "received": len(signals)}

@app.get("/api/data")
async def get_data():
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
    db = SessionLocal()
    db.query(Signal).delete()
    db.commit()
    db.close()
    return {"status": "reset"}

@app.post("/api/save")
async def save_data():
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
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
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
      <button id="reset-btn" class="btn btn-accent mr-2">Reset DB</button>
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
    <div class="card"><h2 class="font-semibold">Total Signals</h2><p id="total-signals" class="text-2xl mt-2">0</p></div>
    <div class="card"><h2 class="font-semibold">Last Timestamp</h2><p id="last-time" class="text-2xl mt-2">N/A</p></div>
    <div class="card"><h2 class="font-semibold">Controller Loc</h2><p id="ctrl-loc" class="mt-2">…</p></div>
    <div class="card"><h2 class="font-semibold">Detected HW</h2><p id="hw-list" class="mt-2">…</p></div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
    <div class="card">
      <canvas id="chart" height="200"></canvas>
    </div>
    <div class="card">
      <div id="map" style="height:300px;"></div>
    </div>
  </div>

  <div class="card overflow-auto" style="max-height:300px;">
    <table class="table">
      <thead>
        <tr>
          <th>Time</th><th>Type</th><th>Name/Addr</th><th>RSSI</th><th>Freq</th><th>Info</th><th>Lat</th><th>Lon</th>
        </tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>

<script>
document.addEventListener('DOMContentLoaded', () => {
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
        chartCtx = document.getElementById('chart').getContext('2d'),
        mapDiv   = document.getElementById('map');

  let chart, map, heat;

  // init map
  fetch('/api/location').then(r=>r.json()).then(loc=>{
    locEl.textContent = `${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)}`;
    map = L.map(mapDiv).setView([loc.lat, loc.lon], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
      attribution:'© OpenStreetMap'
    }).addTo(map);
    heat = L.heatLayer([], {radius:25,blur:15}).addTo(map);
  });

  // load hardware
  fetch('/api/devices').then(r=>r.json()).then(d=>{
    hwEl.textContent = d.devices.join(', ');
  });

  startBtn.onclick = () => fetch('/api/start',{method:'POST'}).then(_=>load());
  stopBtn.onclick  = () => fetch('/api/stop',{ method:'POST' });
  resetBtn.onclick = () => fetch('/api/reset',{method:'POST'}).then(_=>load());
  saveBtn.onclick  = () => fetch('/api/save',{method:'POST'})
    .then(r=>r.blob()).then(b=>{
      const u=URL.createObjectURL(b),a=document.createElement('a');
      a.href=u;a.download='signals.csv';document.body.append(a);a.click();a.remove();
    });

  filter.onchange = load;
  function load(){
    fetch('/api/data').then(r=>r.json()).then(data=>{
      const f = filter.value;
      const filtered = data.filter(s=>f==='all'||s.type===f);
      totalEl.textContent = filtered.length;
      lastEl.textContent = filtered.length ? filtered[filtered.length-1].timestamp : 'N/A';

      // table
      tbody.innerHTML = '';
      filtered.forEach(s=>{
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${s.timestamp}</td>
          <td>${s.type}</td>
          <td>${s.name_address}</td>
          <td>${s.signal_strength}</td>
          <td>${s.frequency}</td>
          <td>${s.additional_info}</td>
          <td>${s.latitude||''}</td>
          <td>${s.longitude||''}</td>
        `;
        tbody.append(tr);
      });

      // chart
      const counts = {};
      filtered.forEach(s=>counts[s.type]=(counts[s.type]||0)+1);
      const labels = Object.keys(counts), vals = Object.values(counts);
      if (!chart) {
        chart = new Chart(chartCtx, {
          type:'bar',
          data:{labels, datasets:[{
            label:'Count', data:vals, backgroundColor:'rgba(59,130,246,0.7)'
          }]},
          options:{scales:{y:{beginAtZero:true}}}
        });
      } else {
        chart.data.labels=labels; chart.data.datasets[0].data=vals; chart.update();
      }

      // heatmap
      heat.setLatLngs(filtered
        .filter(s=>s.latitude&&s.longitude)
        .map(s=>[s.latitude,s.longitude,0.5]));
    });
  }

  load();
  setInterval(load, 5000);
});
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE

# ─── Server ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
