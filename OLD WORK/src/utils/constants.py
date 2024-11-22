# src/utils/constants.py

PROTOCOL_VERSION = 1
SIGNAL_TYPE_MAP = {
    'Wi-Fi': 1,
    'Bluetooth': 2,
    '5G': 3,
    'LoRa': 4,
    'Zigbee': 5
}
PROTOCOL_TYPE_MAP = {
    '802.11n': 1,
    '802.11ac': 2,
    '802.11ax': 3,
    'BLE': 4,
    'Classic Bluetooth': 5,
    'NR': 6
}
MAX_PACKET_SIZE = 255  # Max size in bytes for LoRaWAN