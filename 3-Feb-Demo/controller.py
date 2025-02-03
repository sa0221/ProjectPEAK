# controller.py
import requests
import uvicorn
from fastapi import FastAPI, Response, Body
from fastapi.responses import HTMLResponse, StreamingResponse
import csv
import io

app = FastAPI(title="Project PEAK Controller")

# Get the controller's real location from an external API.
def get_controller_location():
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
            return 39.7392, -104.9903  # fallback to Denver
    except Exception as e:
        print(f"[Controller] Exception in geolocation: {e}")
        return 39.7392, -104.9903  # fallback

# Set the controller's coordinates at startup.
CONTROLLER_LAT, CONTROLLER_LON = get_controller_location()

# In-memory database for collected signals
signals_db = []

@app.get("/api/location")
async def api_location():
    """Return the controller's current coordinates."""
    return {"lat": CONTROLLER_LAT, "lon": CONTROLLER_LON}

# Notice the use of Body(...) to explicitly parse the incoming JSON.
@app.post("/api/collect")
async def collect_signals(signals: list = Body(...)):
    global signals_db
    for sig in signals:
        signals_db.append(sig)
    return {"status": "success", "received": len(signals)}

@app.get("/api/data")
async def get_data():
    return signals_db

@app.post("/api/reset")
async def reset_data():
    global signals_db
    signals_db = []
    return {"status": "reset"}

@app.post("/api/start")
async def start_collection():
    return {"status": "collection started"}

@app.post("/api/stop")
async def stop_collection():
    return {"status": "collection stopped"}

@app.post("/api/save")
async def save_data():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "Type", "Name/Address", "Signal Strength", "Additional Info", "Frequency", "Latitude", "Longitude"])
    for sig in signals_db:
        writer.writerow([
            sig.get("timestamp", ""),
            sig.get("type", ""),
            sig.get("name_address", ""),
            sig.get("signal_strength", ""),
            sig.get("additional_info", ""),
            sig.get("frequency", ""),
            sig.get("latitude", ""),
            sig.get("longitude", "")
        ])
    response = StreamingResponse(io.StringIO(output.getvalue()), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=signals_export.csv"
    return response

# HTML UI with embedded JavaScript (Chart.js and Leaflet loaded via CDN)
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
    body { font-family: Arial, sans-serif; margin: 20px; }
    #controls { margin-bottom: 20px; }
    #signal-list li { margin-bottom: 10px; }
    #map { height: 400px; margin-top: 20px; }
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
  <div>
    <h3>Total Signals: <span id="total-signals">0</span></h3>
    <h3>Last Signal Time: <span id="last-signal-time">N/A</span></h3>
    <h3>Controller Location: <span id="controller-location">Loading...</span></h3>
  </div>
  <ul id="signal-list"></ul>
  <canvas id="chart-canvas" width="400" height="200"></canvas>
  <div id="map"></div>
  <script>
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

      let isCollecting = false;
      let selectedSignalType = 'all';
      let chart;
      let map;
      let markers = [];
      let heatLayer;
      let totalSignals = 0;

      // Fetch controller location and update UI
      fetch('/api/location')
        .then(res => res.json())
        .then(loc => {
          controllerLocEl.textContent = loc.lat + ", " + loc.lon;
          // Center the map on the controller's location
          if (map) {
            map.setView([loc.lat, loc.lon], 12);
          }
        });

      fetchData();

      startBtn.addEventListener('click', () => {
        fetch('/api/start', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            alert(data.status);
            isCollecting = true;
            fetchData();
          });
      });

      stopBtn.addEventListener('click', () => {
        fetch('/api/stop', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            alert(data.status);
            isCollecting = false;
          });
      });

      resetBtn.addEventListener('click', () => {
        fetch('/api/reset', { method: 'POST' })
          .then(res => res.json())
          .then(data => {
            alert(data.status);
            resetUI();
            fetchData();
          });
      });

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

      signalTypeSelect.addEventListener('change', () => {
        selectedSignalType = signalTypeSelect.value;
        fetchData();
      });

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

      function updateSignalStats(data) {
        totalSignals = data.length;
        totalSignalsEl.textContent = totalSignals;
        if (totalSignals > 0) {
          lastSignalTimeEl.textContent = data[data.length - 1].timestamp;
        } else {
          lastSignalTimeEl.textContent = 'N/A';
        }
      }

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

      function updateMap(data) {
        if (!map) {
          // Default to controller's location if available
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
async def index():
    return HTML_PAGE

if __name__ == "__main__":
    uvicorn.run("controller:app", host="0.0.0.0", port=8000)
