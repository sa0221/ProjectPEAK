# examples/lora_node.py

import sys
import time
import json
import threading
sys.path.insert(0, '../src')

from lora_communication.lora_sender import create_sender
from signal_processing.signal_detector import SignalDetector
from protocol.packet_builder import build_packet
from utils.data_structures import SignalInfo
from utils.gps_module import GPSModule  # New module for GPS handling

def main():
    """
    Main function to run the LoRa node.
    """
    sender = create_sender()
    node_id = 1  # Unique node ID

    # Initialize GPS module
    gps_module = GPSModule('/dev/ttyS0')  # Update with the correct serial port

    # Initialize Signal Detector with HackRF One
    detector = SignalDetector(freq=2.437e9)  # Wi-Fi channel 6 frequency

    try:
        while True:
            # Update GPS position
            position = gps_module.get_position()
            # Detect signal
            if detector.detect_signal():
                print("Signal detected!")
                # Gather signal information
                signal_info = SignalInfo(
                    source_node_id=node_id,
                    position=position,
                    signal_type='Wi-Fi',
                    signal_strength=detector.measure_signal_strength(),
                    protocol='802.11n',
                    frequency=2.437e9,
                    channel=6,
                    strength_over_time=detector.get_rssi_timeseries(),
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
        gps_module.close()
        BOARD.teardown()

def calculate_speed():
    """
    Calculate the speed of the signal source.

    Returns:
        float: Speed in m/s.
    """
    # Implement speed calculation logic (placeholder)
    return 0.0

def calculate_direction():
    """
    Calculate the direction of the signal source.

    Returns:
        float: Direction in degrees.
    """
    # Implement direction calculation logic (placeholder)
    return 0.0

if __name__ == "__main__":
    main()
