# examples/central_node.py

import sys
import time
sys.path.insert(0, '../src')

from lora_communication.lora_receiver import create_receiver
from protocol.packet_handler import receive_packet
from utils.data_structures import NodePosition
from data_fusion.fusion import fuse_data_from_nodes
from triangulation.triangulate import triangulate_position

def main():
    """
    Main function to run the central node.
    """
    receiver = create_receiver()
    node_positions = {
        1: NodePosition(1, 0, 0),
        2: NodePosition(2, 100, 0),
        3: NodePosition(3, 50, 86.6)
    }
    received_packets = []

    try:
        print("Central Node: Waiting for LoRa packets...")
        while True:
            if receiver.get_irq_flags()['rx_done']:
                packet_bytes = receiver.read_payload(nocheck=True)
                # Handle the packet
                packet = receive_packet(packet_bytes)
                if packet:
                    received_packets.append(packet)
                    print(f"Received packet from node {packet['source_node_id']}")
                    # Process when enough packets are collected
                    if len(received_packets) >= 3:
                        fused_data = fuse_data_from_nodes([p['signal_info'] for p in received_packets])
                        print(f"Fused data: {fused_data}")
                        distances = [100 - p['signal_strength'] for p in received_packets]  # Example distance estimation
                        positions = [node_positions[p['source_node_id']] for p in received_packets]
                        try:
                            position = triangulate_position(
                                [(pos.x, pos.y) for pos in positions],
                                distances
                            )
                            print(f"Estimated position: {position}")
                        except ValueError as e:
                            print(f"Triangulation error: {e}")
                        received_packets = []
                # Continue receiving
                receiver.set_mode(MODE.RXCONT)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        receiver.set_mode(MODE.SLEEP)
        BOARD.teardown()

if __name__ == "__main__":
    main()
