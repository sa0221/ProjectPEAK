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
    let markers = [];

    // Start collection
    startBtn.addEventListener('click', () => {
        fetch('/api/start', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.status);
                isCollecting = true;
                fetchData();
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

    // Reset data
    resetBtn.addEventListener('click', () => {
        fetch('/api/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.status);
                signalData = [];
                updateUI();
            });
    });

    // Save data
    saveBtn.addEventListener('click', () => {
        fetch('/api/save', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert(data.message);
            });
    });

    // Signal type selector
    signalTypeSelect.addEventListener('change', () => {
        selectedSignalType = signalTypeSelect.value;
        updateUI();
    });

    // Fetch data
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

    // Update UI
    function updateUI() {
        updateSignalStats();
        updateSignalList();
        updateSignalChart();
        updateSignalMap();
    }

    // Update stats
    function updateSignalStats() {
        totalSignalsEl.textContent = signalData.length;
        if (signalData.length > 0) {
            lastSignalTimeEl.textContent = signalData[signalData.length - 1].timestamp;
        } else {
            lastSignalTimeEl.textContent = 'N/A';
        }
    }

    // Update signal list
    function updateSignalList() {
        signalList.innerHTML = '';
        const filteredData = signalData.filter(signal =>
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

    // Update map
    function updateSignalMap() {
        if (!map) {
            map = L.map(mapDiv).setView([39.7392, -104.9903], 12); // Default view
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);
        }

        // Clear existing markers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];

        const filteredData = signalData.filter(signal =>
            selectedSignalType === 'all' || signal.type === selectedSignalType
        );

        filteredData.forEach(signal => {
            if (signal.latitude && signal.longitude) {
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
    }
});
