import sys
import time
import json
import serial  # Added to interface with GPS module
sys.path.insert(0, '../src')

from lora_communication.lora_sender import create_sender
from signal_processing.signal_detector import SignalDetector
from protocol.packet_builder import build_packet
from utils.data_structures import SignalInfo

# Set up GPS connection
gps_port = '/dev/ttyAMA0'  # Adjust for your setup
gps_baud = 9600
gps_serial = serial.Serial(gps_port, gps_baud, timeout=1)

def get_current_position():
    """
    Get the current GPS position from the GPS module.

    Returns:
        dict: Dictionary with 'lat', 'lon', 'alt'.
    """
    while True:
        data = gps_serial.readline().decode('ascii', errors='replace')
        if data.startswith('$GPGGA'):
            parts = data.split(',')
            lat = float(parts[2]) / 100.0  # Simplified parsing
            lon = float(parts[4]) / 100.0
            alt = float(parts[9])
            return {'lat': lat, 'lon': lon, 'alt': alt}
        time.sleep(0.1)

def main():
    """
    Main function to run the LoRa node.
    """
    sender = create_sender()
    node_id = 1  # Unique node ID
    detector = SignalDetector(freq=2.437e9)  # Example frequency for Wi-Fi channel 6

    try:
        while True:
            # Detect signal
            if detector.detect_signal():
                print("Signal detected!")
                # Gather signal information
                signal_info = SignalInfo(
                    source_node_id=node_id,
                    position=get_current_position(),
                    signal_type='Wi-Fi',
                    signal_strength=measure_rssi(),
                    protocol='802.11n',
                    frequency=2.437e9,
                    channel=6,
                    strength_over_time=get_rssi_timeseries(),
                    speed=calculate_speed(),
                    direction=calculate_direction()
                )
                # Build packet
                packet = build_packet(signal_info.__dict__)
                # Send packet
                sender.send_message(packet)
                print("Packet sent.")
            else:
                print("No signal detected.")
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        sender.set_mode(MODE.SLEEP)
        detector.close()
        gps_serial.close()  # Close GPS connection

if __name__ == "__main__":
    main()
