# src/utils/data_structures.py

from dataclasses import dataclass, field

@dataclass
class LoRaPacket:
    """
    Represents a LoRa packet with metadata and payload.
    """
    node_id: str
    rssi: float
    snr: float
    payload: dict

@dataclass
class NodePosition:
    """
    Represents the position of a node in 2D space.
    """
    node_id: str
    x: float
    y: float

@dataclass
class SignalInfo:
    """
    Represents the detected signal information.
    """
    source_node_id: int
    position: dict
    signal_type: str
    signal_strength: float
    protocol: str
    frequency: float
    channel: int
    strength_over_time: list
    speed: float
    direction: float