# src/protocol/packet_builder.py

import struct
import time
from utils.data_structures import LoRaPacket
from utils.constants import (
    PROTOCOL_VERSION,
    SIGNAL_TYPE_MAP,
    PROTOCOL_TYPE_MAP,
    MAX_PACKET_SIZE
)

def build_packet(signal_info):
    """
    Build a packet according to the custom protocol.

    Args:
        signal_info (dict): Information about the detected signal.

    Returns:
        bytes: The packet ready to be sent over LoRaWAN.
    """
    packet_id = generate_packet_id()
    source_node_id = signal_info['source_node_id']
    dest_node_id = 0xFFFF  # Broadcast
    timestamp = int(time.time() * 1e3)  # GPS timestamp in milliseconds
    position_data = compress_position(signal_info['position'])
    signal_type = SIGNAL_TYPE_MAP.get(signal_info['signal_type'], 0)
    signal_strength = compress_rssi(signal_info['signal_strength'])
    protocol = PROTOCOL_TYPE_MAP.get(signal_info['protocol'], 0)
    signal_info_compressed = compress_signal_info(signal_info['frequency'], signal_info['channel'])
    signal_info_length = len(signal_info_compressed)
    strength_over_time_compressed = compress_rssi_timeseries(signal_info['strength_over_time'])
    strength_over_time_length = len(strength_over_time_compressed)
    speed_direction = encode_speed_direction(signal_info['speed'], signal_info['direction'])
    packet_life_counter = 5
    checksum = 0  # Placeholder for checksum

    # Pack the data into bytes
    packet_format = '>B I H H Q 16s B B B {}s B {}s H B H'.format(
        signal_info_length, strength_over_time_length
    )

    packet = struct.pack(
        packet_format,
        PROTOCOL_VERSION,
        packet_id,
        source_node_id,
        dest_node_id,
        timestamp,
        position_data,
        signal_type,
        signal_strength,
        protocol,
        signal_info_length,
        signal_info_compressed,
        strength_over_time_length,
        strength_over_time_compressed,
        speed_direction,
        packet_life_counter,
        checksum
    )

    # Compute checksum
    checksum = compute_checksum(packet)
    # Repack with correct checksum
    packet = packet[:-2] + struct.pack('>H', checksum)

    # Ensure packet does not exceed max size
    if len(packet) > MAX_PACKET_SIZE:
        raise ValueError("Packet size exceeds maximum allowed size.")

    return packet

def generate_packet_id():
    """
    Generate a unique packet ID.

    Returns:
        int: A unique packet ID.
    """
    return int(time.time() * 1e6) % (2**32)

def compress_position(position):
    """
    Compress latitude, longitude, altitude into 16 bytes.

    Args:
        position (dict): Dictionary with 'lat', 'lon', 'alt'.

    Returns:
        bytes: Compressed position data.
    """
    lat = int(position['lat'] * 1e7)
    lon = int(position['lon'] * 1e7)
    alt = int(position['alt'] * 1e2)
    return struct.pack('>iii', lat, lon, alt)

def compress_rssi(rssi):
    """
    Compress RSSI value into an 8-bit unsigned integer.

    Args:
        rssi (float): The RSSI value.

    Returns:
        int: Compressed RSSI.
    """
    return int(max(min(rssi + 120, 255), 0))

def compress_signal_info(frequency, channel):
    """
    Compress frequency and channel information.

    Args:
        frequency (float): Frequency in Hz.
        channel (int): Channel number.

    Returns:
        bytes: Compressed signal info.
    """
    freq = int(frequency / 1e3)  # Convert to kHz
    return struct.pack('>IH', freq, channel)

def compress_rssi_timeseries(rssi_timeseries):
    """
    Compress a time series of RSSI measurements.

    Args:
        rssi_timeseries (list): List of RSSI values.

    Returns:
        bytes: Compressed RSSI time series.
    """
    compressed = bytes([compress_rssi(rssi) for rssi in rssi_timeseries])
    return compressed

def encode_speed_direction(speed, direction):
    """
    Encode speed and direction into a 16-bit value.

    Args:
        speed (float): Speed in m/s.
        direction (float): Direction in degrees.

    Returns:
        int: Encoded speed and direction.
    """
    speed_enc = int(min(speed, 255))
    direction_enc = int(direction % 360 / 360 * 255)
    return (speed_enc << 8) | direction_enc

def compute_checksum(data):
    """
    Compute a simple checksum for error checking.

    Args:
        data (bytes): The data to compute the checksum on.

    Returns:
        int: The checksum value.
    """
    checksum = sum(data) % 65536
    return checksum