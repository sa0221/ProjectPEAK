
# Project PEAK

## Codebase Information

### Project PEAK (Positioning and Emanation Analysis for Key Targets)

Project PEAK (Positioning and Emanation Analysis for Key Targets) aims to design a distributed IoT system capable of intercepting, analyzing, and triangulating electromagnetic signals across a range of communication protocols (e.g., Wi-Fi, Bluetooth, 5G). The system tracks and identifies devices such as UAVs, vehicles, and other electronic systems within a defined space.

### Code Breakdown
```
project_peak/
│
├── src/
│   ├── __init__.py
│   ├── lora_communication/
│   │   ├── __init__.py
│   │   ├── lora_config.py
│   │   ├── lora_sender.py
│   │   └── lora_receiver.py
│   ├── data_fusion/
│   │   ├── __init__.py
│   │   └── fusion.py
│   ├── triangulation/
│   │   ├── __init__.py
│   │   └── triangulate.py
│   ├── signal_processing/
│   │   ├── __init__.py
│   │   └── signal_detector.py
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── packet_builder.py
│   │   └── packet_handler.py
│   └── utils/
│       ├── __init__.py
│       ├── data_structures.py
│       └── constants.py
│
├── examples/
│   ├── __init__.py
│   ├── lora_node.py
│   └── central_node.py
│
├── tests/
│   ├── __init__.py
│   ├── test_lora.py
│   ├── test_fusion.py
│   ├── test_triangulation.py
│   └── test_signal_processing.py
│
├── requirements.txt
└── README.md
```

## 1. Objective

To design a distributed IoT system capable of intercepting, analyzing, and triangulating electromagnetic signals (emanations) across a range of communication protocols (e.g., Wi-Fi, Bluetooth, 5G) for tracking and identifying devices such as UAVs, vehicles, and other electronic systems in a defined space.

## 2. Components Required

### A. Signal Collection

- **HackRF One SDR**
    - Wideband signal receiver capable of capturing signals across the 1 MHz to 6 GHz range.
- **KrakenSDR**
    - 5-channel coherent RTL-SDR with Direction of Arrival (DoA) capabilities. Can be used in phased array mode for DoA or broken out into individual channels for multiple signal collection tasks.
- **Omni-Directional Antennas**
    - Antennas for the HackRF and KrakenSDR, covering various frequency bands without the complexity of directional antennas.

### B. Control and Processing

- **Raspberry Pi 4 Model B**
    - Acts as the primary controller and processing unit.
    - Handles signal processing, data storage, and communication.
- **Battery Pack**
    - High-capacity battery to power the Raspberry Pi and connected peripherals.
- **GPS Module**
    - Provides precise location data for each node. Essential for accurate geolocation of detected signals.
- **LoRaWAN Modules**
    - Enables long-range, low-power communication between distributed nodes.

### C. Communication

- **LoRaWAN Gateway**
    - Central hub for collecting data from nodes.
    - Manages communication and data relay between nodes.
- **Wi-Fi/Bluetooth Adapters**
    - For detecting and analyzing Wi-Fi and Bluetooth signals within the environment.

### D. Optional Components

- **Additional Sensors**
    - IMU (Inertial Measurement Unit) for capturing motion data.

---

## 3. Protocols for Signal Interception

### A. Wi-Fi (IEEE 802.11)

- **Frequency Range:** 2.4 GHz and 5 GHz bands.
- **Data Types:** Beacon frames, probe requests, data frames.
- **Protocols to Intercept:**
    - **802.11n/ac/ax:** Modern Wi-Fi standards with varying bandwidth and MIMO capabilities.

### B. Bluetooth (IEEE 802.15.1)

- **Frequency Range:** 2.4 GHz ISM band.
- **Data Types:** Device discovery packets, connection requests.
- **Protocols to Intercept:**
    - **BLE (Bluetooth Low Energy):** For low-power devices like fitness trackers.
    - **Classic Bluetooth:** For standard devices such as headsets and vehicle systems.

### C. 5G NR (New Radio)

- **Frequency Range:** Sub-6 GHz and mmWave (24 GHz and above).
- **Data Types:** Control signals, data channels.
- **Protocols to Intercept:**
    - **NR (New Radio):** For high-speed mobile communication and IoT.
    - **Considerations:** Use tools like the [5G MAG RT-MBMS Modem](https://github.com/5G-MAG/rt-mbms-modem) for simplified monitoring and analysis of 5G signals.

### D. Other Signals

- **LoRa:**
    - To detect LoRa-based IoT devices.
- **Zigbee (IEEE 802.15.4):**
    - For low-power, short-range communication in smart home devices.
- **RFID/NFC:**
    - For close-range identification systems.
- **Vehicle Tire Pressure Monitoring System (TPMS):**
    - Each tire has a unique ID, allowing for vehicle tracking based on TPMS signals.

---

## 4. Network Communication and Data Fusion

### A. Node Communication

- **LoRaWAN:**
    - Provides long-range communication with low power consumption.
    - Enables nodes to relay intercepted data to a central server.

### B. Data Synchronization

- **NTP (Network Time Protocol):**
    - Ensures all nodes have synchronized timestamps for accurate triangulation.

### C. Data Fusion and Triangulation

- **Relative Signal Strength Triangulation:**
    - Utilizes Received Signal Strength Indicator (RSSI) for triangulating the source of detected signals, avoiding the need for highly accurate timing devices like GPS-disciplined oscillators.
- **Direction of Arrival (DoA):**
    - Using KrakenSDR for enhanced DoA estimation via phased array setup, improving accuracy in signal direction detection.

### D. Identification Logic

- **Machine Learning Models:**
    - For classifying detected signals based on known patterns (e.g., Wi-Fi fingerprints, Bluetooth signatures).
- **Database Lookup:**
    - To match intercepted signals with known devices or UAS/vehicle systems, including the unique IDs from TPMS for vehicle tracking.

---

## 5. Visualization and Tracking

### A. Mapping and Plotting
- **GIS Software (e.g., QGIS):**  
  - For visualizing the location and movement of identified devices on a map.
- **Custom Software:**  
  - For real-time plotting of detected signals and triangulated positions.

### B. Space-Time Analysis
- **Time-series Plots:**  
  - To track the movement of devices over time.
- **Heatmaps:**  
  - To visualize areas of high signal activity or device concentration.

---

## 6. Deployment Considerations

### A. Node Placement
- **Optimal Coverage:**  
  - Nodes should be placed to maximize coverage and minimize blind spots.
- **Elevation and Line-of-Sight:**  
  - Elevated deployment can improve range and triangulation accuracy.

### B. Power Management
- **Battery Life:**  
  - Power-efficient operation is crucial for prolonged deployments.
- **Solar Panels:**  
  - Consider using solar panels for extended field deployments.

### C. Environmental Considerations
- **Ruggedized Enclosures:**  
  - Protects the equipment from environmental factors like dust, moisture, and temperature variations.

---

# SIGINT Collection IoT System - Tech Sheet

| **Component**          | **Specification**                                                                 | **Purpose**                                 |
|------------------------|-----------------------------------------------------------------------------------|---------------------------------------------|
| **HackRF One**         | 1 MHz to 6 GHz SDR                                                                | Signal collection across multiple bands     |
| **KrakenSDR**          | 5-channel coherent RTL-SDR                                                        | DoA estimation or multi-channel signal collection  |
| **Raspberry Pi 4**     | Quad-core Cortex-A72, 4GB RAM, USB 3.0, Gigabit Ethernet                          | Control, processing, and data relay         |
| **LoRaWAN Module**     | SX1276 LoRa module                                                                | Long-range communication between nodes      |
| **GPS Module**         | Ublox NEO-6M or similar                                                           | Location data for triangulation             |
| **Battery Pack**       | 10,000mAh or higher                                                               | Power supply for Raspberry Pi and peripherals|
| **Antenna**            | Omni-directional antennas                                                         | Enhanced signal capture and triangulation   |
| **LoRaWAN Gateway**    | 8-channel gateway, 915 MHz                                                        | Central node for LoRaWAN communication      |
| **Wi-Fi Adapter**      | 2.4/5 GHz USB Wi-Fi adapter                                                       | Wi-Fi signal detection and analysis         |
| **Bluetooth Adapter**  | USB Bluetooth 5.0 dongle                                                          | Bluetooth signal detection and analysis     |
| **GIS Software**       | QGIS or custom software                                                           | Visualization and plotting                  |
| **Machine Learning**   | TensorFlow, Scikit-learn                                                          | Signal classification and identification    |
| **Time Synchronization**| NTP Protocol, GPS Time Sync                                                      | Accurate timestamping for triangulation     |
| **Solar Panel (Optional)** | 20W portable solar panel                                                      | Extended field deployment                   |

---

## 7. Custom Data Transmission Protocol Design

### A. Overview

The custom protocol is designed to efficiently transmit data collected by each node in the SIGINT collection network. The protocol ensures that data is shared among all nodes in the network, with each node forwarding the data to other nodes before it is sent to the central controller for analysis. This decentralized approach allows for redundancy and improved accuracy in determining the position, strength, speed, and origin of detected signals.

### B. Data Packet Structure

Each data packet transmitted by a node will include the following fields:

| **Field**               | **Size (bits)** | **Description**                                                                         |
|-------------------------|-----------------|-----------------------------------------------------------------------------------------|
| **Protocol Version**    | 8               | Version of the custom protocol                                                          |
| **Packet ID**           | 32              | Unique identifier for each packet                                                       |
| **Source Node ID**      | 16              | Identifier for the node that initially detected the signal                              |
| **Destination Node ID** | 16              | Identifier for the intended recipient node (broadcast if 0xFFFF)                        |
| **Timestamp**           | 64              | GPS-based timestamp of when the signal was detected                                     |
| **Position Data**       | 128             | Latitude, longitude, and altitude of the source node                                    |
| **Signal Type**         | 8               | Encoded value representing the type of signal detected (Wi-Fi, Bluetooth, 5G, etc.)     |
| **Signal Strength**     | 8               | Received Signal Strength Indicator (RSSI) or other strength metric                      |
| **Protocol**            | 8               | Encoded value representing the communication protocol of the detected signal            |
| **Signal Info Length**  | 8               | Length of the Signal Information field

                                                  |
| **Signal Information**  | Variable        | Specific data related to the signal, such as frequency, modulation, etc.                |
| **Strength Over Time Length** | 8         | Length of the Strength Over Time field                                                  |
| **Strength Over Time**  | Variable        | Time-series data showing how signal strength has changed over time (optional field)     |
| **Speed and Direction** | 32              | Calculated speed and direction of the detected signal source (optional field)           |
| **Packet Life Counter** | 8               | Decrementing counter that determines how many hops the packet can make before expiring  |
| **Checksum**            | 16              | Error-checking value to ensure data integrity                                           |

### C. Packet Transmission Logic

1. **Initial Detection and Packet Creation:**
   - When a node detects a signal, it creates a data packet with all the relevant information, including a unique Packet ID, the Source Node ID, the Timestamp, Position Data, and other signal-related information.
   - The Packet Life Counter is initialized to a pre-defined value (e.g., 5).

2. **Broadcast to Nearby Nodes:**
   - The packet is broadcast to all nearby nodes within range using LoRaWAN or another suitable communication protocol.
   - The Destination Node ID is set to 0xFFFF for broadcast.

3. **Decrementing Packet Life Counter:**
   - Each node that receives the packet decrements the Packet Life Counter by 1.
   - If the Packet Life Counter reaches 0, the packet is not forwarded further.

4. **Data Fusion and Forwarding:**
   - Nodes that receive a packet compare it with their own data. If a similar signal has been detected, the node updates the packet with additional information (e.g., its own Position Data, updated Signal Strength, etc.) before forwarding the packet.
   - If no similar signal is detected, the packet is forwarded unchanged.

5. **Final Transmission to Central Controller:**
   - When the Packet Life Counter is decremented to 1, the node sends the packet directly to the central controller.
   - The central controller aggregates all received packets, performs data analysis, and uses the collected data to determine the signal's position, strength, speed, and origin.

### D. Central Controller Data Analysis

Once the central controller receives data packets from multiple nodes, it performs the following analysis:

1. **Triangulation:**  
   - Using the Position Data from different nodes, the central controller calculates the exact location of the signal source through triangulation.

2. **Signal Strength Mapping:**  
   - The central controller plots the Signal Strength data over time and space, creating a map of signal intensity across the monitored area.

3. **Speed and Direction Calculation:**  
   - By analyzing the Timestamp and Position Data from sequential packets, the central controller estimates the speed and direction of the signal source.

4. **Device Identification:**  
   - The system cross-references the Signal Type, Protocol, and Signal Information with a database to identify the likely device (e.g., phone, UAS, remote) generating the signal.

5. **Threat Assessment:**  
   - The central controller flags any signals or devices that meet predefined criteria for further investigation or action.

---

## 8. Custom Data Transmission Protocol (LoRaWAN Compatible)

### A. Protocol Overview
A decentralized protocol designed to transmit collected signal data between nodes using LoRaWAN, with considerations for LoRaWAN's data rate and latency. The protocol ensures efficient data sharing across nodes, decrementing a packet life counter, and forwarding critical data to the central controller for analysis.

### B. Data Packet Structure

Given LoRaWAN's data rate constraints (250 bps to 22 Kbps), the packet structure is optimized for minimal size and efficient transmission:

| **Field**               | **Size (bits)** | **Description**                                    |
|-------------------------|-----------------|----------------------------------------------------|
| **Protocol Version**    | 8               | Version of the custom protocol                     |
| **Packet ID**           | 32              | Unique packet identifier                           |
| **Source Node ID**      | 16              | ID of the detecting node                           |
| **Dest. Node ID**       | 16              | Target node ID (0xFFFF for broadcast)              |
| **Timestamp**           | 64              | GPS timestamp of detection                         |
| **Position Data**       | 128             | Latitude, longitude, altitude                      |
| **Signal Type**         | 8               | Encoded signal type (e.g., Wi-Fi, Bluetooth)       |
| **Signal Strength**     | 8               | RSSI or equivalent (compressed)                    |
| **Protocol**            | 8               | Encoded protocol type (e.g., 802.11n)              |
| **Signal Info Length**  | 8               | Length of the Signal Information field             |
| **Signal Info**         | Variable        | Frequency, channel (compressed)                    |
| **Strength Over Time Length** | 8         | Length of the Strength Over Time field             |
| **Strength Over Time**  | Variable        | Compressed time-series RSSI data                   |
| **Speed/Direction**     | 16              | Encoded speed and direction                        |
| **Packet Life Counter** | 8               | TTL for packet hops                                |
| **Checksum**            | 16              | Error-checking value                               |

### C. Pseudocode Implementation

#### 1. **Packet Creation**

```python
packet = {
    "protocol_version": 1,
    "packet_id": generate_id(),
    "source_node_id": NODE_ID,
    "dest_node_id": 0xFFFF,
    "timestamp": get_gps_time(),
    "position_data": get_compressed_position(),
    "signal_type": encode_signal_type(SIGNAL_TYPE_WIFI),
    "signal_strength": compress_rssi(measure_rssi()),
    "protocol": encode_protocol(PROTOCOL_80211N),
    "signal_info_length": len(compress_signal_info(2412, 1)),
    "signal_info": compress_signal_info(2412, 1),
    "strength_over_time_length": len(compress_rssi_timeseries(get_rssi_timeseries())),
    "strength_over_time": compress_rssi_timeseries(get_rssi_timeseries()),
    "speed_direction": encode_speed_direction(calculate_speed_direction()),
    "packet_life_counter": 5,
    "checksum": compute_checksum()
}
broadcast_packet(packet)
```

#### 2. **Packet Handling**

```python
def receive_packet(packet):
    packet["packet_life_counter"] -= 1
    if packet["packet_life_counter"] > 0:
        update_and_forward_packet(packet)
    else:
        send_to_controller(packet)

def update_and_forward_packet(packet):
    if signal_matches(packet["signal_info"]):
        packet["position_data"] = update_compressed_position()
        packet["signal_strength"] = max(packet["signal_strength"], compress_rssi(measure_rssi()))
    broadcast_packet(packet)
```

### D. Protocol Workflow
1. **Detection:** Node creates a data packet upon signal detection, optimized for LoRaWAN's low data rates.
2. **Broadcast:** Packet is broadcast to nearby nodes; each node decrements the Packet Life Counter.
3. **Data Fusion:** Nodes compare packet data with local observations, updating the packet if matching signals are found.
4. **Final Transmission:** When the Packet Life Counter reaches 1, the packet is sent to the central controller.
5. **Analysis:** Central controller performs triangulation, signal mapping, and device identification.

### E. LoRaWAN Considerations
- **Data Rate:** The protocol accounts for LoRaWAN's varying data rates, ensuring packets remain small enough for efficient transmission even at lower data rates (250 bps).
- **Latency:** With LoRaWAN's longest-range configuration, it may take several seconds to transmit a 1 KB message. The packet structure is designed to minimize size, ensuring timely data transmission.
