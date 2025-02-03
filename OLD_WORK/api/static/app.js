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

    let isCollecting = false;
    let selectedSignalType = 'all';
    let chart;
    let map;
    let markers = [];
    let heatLayer;
    let totalSignals = 0;

    // Fetch initial data
    fetchData();

    // Start collection
    startBtn.addEventListener('click', () => {
        fetch('/api/start', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.status);
                isCollecting = true;
                fetchData(); // Start fetching data
            });
    });

    // Stop collection
    stopBtn.addEventListener('click', () => {
        fetch('/api/stop', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.status);
                isCollecting = false;
            });
    });

    // Reset database
    resetBtn.addEventListener('click', () => {
        fetch('/api/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.status);
                resetUI();
                fetchData(); // Refresh the UI
            });
    });

    // Save data as CSV
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

    // Signal type filter
    signalTypeSelect.addEventListener('change', () => {
        selectedSignalType = signalTypeSelect.value;
        fetchData(); // Re-fetch and re-filter data
    });

    // Fetch data and update UI
    function fetchData() {
        fetch('/api/data')
            .then(res => res.json())
            .then(data => {
                updateSignalStats(data);
                updateSignalList(data);
                updateChart(data);
                updateMap(data);
                if (isCollecting) setTimeout(fetchData, 2000); // Real-time updates
            });
    }

    // Update signal stats
    function updateSignalStats(data) {
        totalSignals = data.length;
        totalSignalsEl.textContent = totalSignals;
        if (totalSignals > 0) {
            lastSignalTimeEl.textContent = data[data.length - 1].timestamp;
        } else {
            lastSignalTimeEl.textContent = 'N/A';
        }
    }

    // Update signal list
    function updateSignalList(data) {
        signalList.innerHTML = '';
        const filteredData = data.filter(signal =>
            selectedSignalType === 'all' || signal.type === selectedSignalType
        );
        filteredData.forEach(signal => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `
                <b>Timestamp:</b> ${signal.timestamp}<br>
                <b>Type:</b> ${signal.type}<br>
                <b>Name/Address:</b> ${signal.name_address}<br>
                <b>Signal Strength:</b> ${signal.signal_strength || 'N/A'}<br>
                <b>Frequency:</b> ${signal.frequency || 'N/A'}<br>
                <b>Latitude:</b> ${signal.latitude || 'N/A'}<br>
                <b>Longitude:</b> ${signal.longitude || 'N/A'}<br>
                <b>Additional Info:</b> ${signal.additional_info || 'N/A'}
            `;
            listItem.className = 'signal-item';
            signalList.appendChild(listItem);
        });
    }

    // Update chart
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
                    scales: {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            });
        } else {
            chart.data.labels = labels;
            chart.data.datasets[0].data = counts;
            chart.update();
        }
    }

    // Update map
    function updateMap(data) {
        if (!map) {
            map = L.map(mapDiv).setView([39.7392, -104.9903], 12); // Default to Denver
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            heatLayer = L.heatLayer([], { radius: 25, blur: 15, maxZoom: 17 }).addTo(map);
        }

        // Clear existing markers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];

        const heatData = [];
        data.filter(signal =>
            selectedSignalType === 'all' || signal.type === selectedSignalType
        ).forEach(signal => {
            if (signal.latitude && signal.longitude) {
                heatData.push([signal.latitude, signal.longitude, 0.5]); // Adjust intensity as needed
                const marker = L.marker([parseFloat(signal.latitude), parseFloat(signal.longitude)])
                    .addTo(map)
                    .bindPopup(`
                        <b>Type:</b> ${signal.type}<br>
                        <b>Name/Address:</b> ${signal.name_address}<br>
                        <b>Signal Strength:</b> ${signal.signal_strength || 'N/A'}<br>
                        <b>Frequency:</b> ${signal.frequency || 'N/A'}<br>
                        <b>Additional Info:</b> ${signal.additional_info || 'N/A'}
                    `);
                markers.push(marker);
            }
        });

        heatLayer.setLatLngs(heatData);
    }

    // Reset all UI components
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
