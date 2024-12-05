// api/static/app.js

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const resetBtn = document.getElementById('reset-btn');
    const saveBtn = document.getElementById('save-btn');
    const signalTypeSelect = document.getElementById('signal-type-select');
    const totalSignalsEl = document.getElementById('total-signals');
    const lastSignalTimeEl = document.getElementById('last-signal-time');
    const signalList = document.getElementById('signal-list');
    const chartCanvas = document.getElementById('chart-canvas');
    const mapDiv = document.getElementById('map');

    let isCollecting = false;
    let signalData = [];
    let selectedSignalType = 'all';
    let chart;
    let map;

    startBtn.addEventListener('click', () => {
        fetch('/api/start', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                isCollecting = true;
                fetchData();
            });
    });

    stopBtn.addEventListener('click', () => {
        fetch('/api/stop', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                isCollecting = false;
            });
    });

    resetBtn.addEventListener('click', () => {
        fetch('/api/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                signalData = [];
                updateUI();
            });
    });

    saveBtn.addEventListener('click', () => {
        fetch('/api/save', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
            });
    });

    signalTypeSelect.addEventListener('change', () => {
        selectedSignalType = signalTypeSelect.value;
        updateUI();
    });

    function fetchData() {
        if (!isCollecting) return;
        fetch('/api/data')
            .then(res => res.json())
            .then(data => {
                signalData = data;
                updateUI();
                setTimeout(fetchData, 2000);
            });
    }

    function updateUI() {
        updateSignalStats();
        updateSignalList();
        updateSignalChart();
        updateSignalMap();
    }

    function updateSignalStats() {
        totalSignalsEl.textContent = signalData.length;
        if (signalData.length > 0) {
            lastSignalTimeEl.textContent = signalData[signalData.length - 1].timestamp;
        } else {
            lastSignalTimeEl.textContent = 'N/A';
        }
    }

    function updateSignalList() {
        signalList.innerHTML = '';
        const filteredData = signalData.filter(signal => 
            selectedSignalType === 'all' || signal.type === selectedSignalType
        );
        filteredData.forEach(signal => {
            const listItem = document.createElement('li');
            listItem.textContent = `${signal.timestamp} - ${signal.type} - ${signal.name_address}`;
            signalList.appendChild(listItem);
        });
    }

    function updateSignalChart() {
        // Example chart using Chart.js
        if (!chart) {
            chart = new Chart(chartCanvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Signal Strength',
                        data: [],
                        borderColor: 'rgba(75, 192, 192, 1)',
                        fill: false,
                    }],
                },
                options: {
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'minute',
                            },
                        },
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            });
        }
        const filteredData = signalData.filter(signal => 
            selectedSignalType === 'all' || signal.type === selectedSignalType
        );
        chart.data.labels = filteredData.map(signal => signal.timestamp);
        chart.data.datasets[0].data = filteredData.map(signal => parseInt(signal.signal_strength) || 0);
        chart.update();
    }

    function updateSignalMap() {
        // Example map using Leaflet.js
        if (!map) {
            map = L.map(mapDiv).setView([0, 0], 2); // Default view
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
        }
        // Clear existing markers
        map.eachLayer((layer) => {
            if (layer instanceof L.Marker) {
                map.removeLayer(layer);
            }
        });
        // Add markers for signals (if location data is available)
        signalData.forEach(signal => {
            if (signal.latitude && signal.longitude) {
                L.marker([signal.latitude, signal.longitude])
                    .addTo(map)
                    .bindPopup(`${signal.type} - ${signal.name_address}`);
            }
        });
    }
});
