# src/protocol/packet_handler.py

import struct
from utils.data_structures import LoRaPacket
from .packet_builder import compute_checksum
from utils.constants import MAX_PACKET_SIZE
from protocol.packet_builder import (
    compress_position,
    compress_rssi,
    build_packet
)

def receive_packet(packet_bytes):
    """
    Handle a received packet.

    Args:
        packet_bytes (bytes): The received packet data.

    Returns:
        dict: Parsed packet fields or None if invalid.
    """
    try:
        packet = parse_packet(packet_bytes)
        packet['packet_life_counter'] -= 1
        if packet['packet_life_counter'] > 0:
            update_and_forward_packet(packet)
        else:
            send_to_controller(packet)
        return packet
    except ValueError as e:
        print(f"Error parsing packet: {e}")
        return None

def parse_packet(packet_bytes):
    """
    Parse a packet according to the custom protocol.

    Args:
        packet_bytes (bytes): The packet data.

    Returns:
        dict: Parsed packet fields.
    """
    # Extract initial fields
    header_format = '>B I H H Q 12s B B B'
    header_size = struct.calcsize(header_format)
    header_fields = struct.unpack(header_format, packet_bytes[:header_size])

    protocol_version = header_fields[0]
    packet_id = header_fields[1]
    source_node_id = header_fields[2]
    dest_node_id = header_fields[3]
    timestamp = header_fields[4]
    position_data = header_fields[5]
    signal_type = header_fields[6]
    signal_strength = header_fields[7]
    protocol = header_fields[8]

    # Get lengths
    idx = header_size
    signal_info_length = packet_bytes[idx]
    idx += 1
    signal_info = packet_bytes[idx:idx + signal_info_length]
    idx += signal_info_length
    strength_over_time_length = packet_bytes[idx]
    idx += 1
    strength_over_time = packet_bytes[idx:idx + strength_over_time_length]
    idx += strength_over_time_length
    speed_direction = struct.unpack('>H', packet_bytes[idx:idx + 2])[0]
    idx += 2
    packet_life_counter = packet_bytes[idx]
    idx += 1
    checksum = struct.unpack('>H', packet_bytes[idx:idx + 2])[0]

    # Recompute checksum and verify
    if compute_checksum(packet_bytes[:-2]) != checksum:
        raise ValueError("Checksum does not match.")

    # Return packet as dictionary
    packet = {
        'protocol_version': protocol_version,
        'packet_id': packet_id,
        'source_node_id': source_node_id,
        'dest_node_id': dest_node_id,
        'timestamp': timestamp,
        'position_data': position_data,  # Should be decompressed
        'signal_type': signal_type,
        'signal_strength': signal_strength,
        'protocol': protocol,
        'signal_info': signal_info,  # Should be decompressed
        'strength_over_time': strength_over_time,  # Should be decompressed
        'speed_direction': speed_direction,
        'packet_life_counter': packet_life_counter,
        'checksum': checksum
    }

    return packet

def update_and_forward_packet(packet):
    """
    Update packet with local observations and forward it.

    Args:
        packet (dict): The packet to update and forward.
    """
    # Implement signal matching and update logic if needed
    # For simplicity, we'll forward the packet as is
    # Recompute checksum
    packet['checksum'] = 0  # Reset before recomputing
    packet_bytes = rebuild_packet(packet)
    packet['checksum'] = compute_checksum(packet_bytes[:-2])
    packet_bytes = rebuild_packet(packet)
    # Send the packet
    broadcast_packet(packet_bytes)

def send_to_controller(packet):
    """
    Send the packet to the central controller.

    Args:
        packet (dict): The packet to send.
    """
    # Implement the logic to send the packet to the controller
    print("Sending packet to controller:", packet)

def rebuild_packet(packet):
    """
    Rebuild the packet after updating fields.

    Args:
        packet (dict): The packet data.

    Returns:
        bytes: The rebuilt packet bytes.
    """
    # Use the build_packet function to rebuild the packet
    signal_info = {
        'source_node_id': packet['source_node_id'],
        'position': decompress_position(packet['position_data']),
        'signal_type': packet['signal_type'],
        'signal_strength': packet['signal_strength'],
        'protocol': packet['protocol'],
        'frequency': 0,  # Placeholder
        'channel': 0,    # Placeholder
        'strength_over_time': packet['strength_over_time'],
        'speed': packet['speed_direction'] >> 8,
        'direction': (packet['speed_direction'] & 0xFF) * 360 / 255
    }
    return build_packet(signal_info)

def broadcast_packet(packet_bytes):
    """
    Broadcast the packet to other nodes.

    Args:
        packet_bytes (bytes): The packet data.
    """
    # Implement the broadcasting logic using LoRa
    pass

def decompress_position(position_data):
    """
    Decompress position data from bytes.

    Args:
        position_data (bytes): Compressed position data.

    Returns:
        dict: Decompressed position with 'lat', 'lon', 'alt'.
    """
    lat, lon, alt = struct.unpack('>iii', position_data)
    return {'lat': lat / 1e7, 'lon': lon / 1e7, 'alt': alt / 1e2}
