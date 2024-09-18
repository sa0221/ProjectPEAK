# src/triangulation/triangulate.py

import math

def triangulate_position(node_positions, distances):
    """
    Triangulate a position based on known node positions and distances.

    Args:
        node_positions (list): List of (x, y) tuples representing node positions.
        distances (list): List of distances from each node to the target.

    Returns:
        tuple: (x, y) coordinates of the triangulated position.

    Raises:
        ValueError: If not exactly 3 nodes and distances are provided.
    """
    if len(node_positions) != 3 or len(distances) != 3:
        raise ValueError("Triangulation requires exactly 3 nodes and distances")

    A, B, C = node_positions
    r1, r2, r3 = distances

    # Calculate the position using trilateration
    # This is a simplified calculation and may not be accurate for all cases
    x = (r1**2 - r2**2 + B[0]**2) / (2 * B[0])
    y = (r1**2 - r3**2 + C[0]**2 + C[1]**2 - 2 * C[0] * x) / (2 * C[1])

    return (x, y)