# src/data_fusion/fusion.py

def fuse_data_from_nodes(packets):
    """
    Fuse data from multiple nodes.

    Args:
        packets (list): List of data packets from different nodes.

    Returns:
        dict: Fused data from all nodes.
    """
    fused_data = {}
    for packet in packets:
        update_fused_data(fused_data, packet)
    return fused_data

def update_fused_data(fused_data, packet):
    """
    Update the fused data with a new packet.

    Args:
        fused_data (dict): The current fused data.
        packet (dict): New data packet to incorporate.
    """
    # This is a simple example that just averages the values
    # You may want to implement a more sophisticated fusion algorithm
    for key, value in packet.items():
        if key in fused_data:
            fused_data[key] = (fused_data[key] + value) / 2
        else:
            fused_data[key] = value