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


    """Enrique's Original Code
    if len(node_positions) != 3 or len(distances) != 3:
        raise ValueError("Triangulation requires exactly 3 nodes and distances")

    A, B, C = node_positions
    r1, r2, r3 = distances

    # Calculate the position using trilateration
    # This is a simplified calculation and may not be accurate for all cases
    x = (r1**2 - r2**2 + B[0]**2) / (2 * B[0])
    y = (r1**2 - r3**2 + C[0]**2 + C[1]**2 - 2 * C[0] * x) / (2 * C[1])

    return (x, y)
    """

    # Validate inputs using helper function
    validate_inputs(node_positions, distances)

    A, B, C = node_positions
    r1, r2, r3 = distances

    # Coordinates for nodes A, B, and C
    x1, y1 = A
    x2, y2 = B
    x3, y3 = C

    # Using the system of equations derived from the distances to each node
    A2 = 2 * (x2 - x1)
    B2 = 2 * (y2 - y1)
    D2 = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2

    A3 = 2 * (x3 - x1)
    B3 = 2 * (y3 - y1)
    D3 = r1**2 - r3**2 - x1**2 + x3**2 - y1**2 + y3**2

    # Solving the system of linear equations for x and y
    denominator = (A2 * B3 - A3 * B2)
    if denominator == 0:
        raise ValueError("The nodes are collinear or too close together, which makes triangulation impossible.")

    x = (D2 * B3 - D3 * B2) / denominator
    y = (A2 * D3 - A3 * D2) / denominator

    return (x, y)


def calculate_distance(point1, point2):
    """Calculate the Euclidean distance between two 2D points."""
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def validate_inputs(node_positions, distances):
    """Validate the inputs for triangulation."""
    if len(node_positions) != 3:
        raise ValueError("Exactly 3 node positions are required.")
    if len(distances) != 3:
        raise ValueError("Exactly 3 distances are required.")
    for node in node_positions:
        if len(node) != 2:
            raise ValueError(f"Invalid node position: {node}. Must be a tuple of (x, y).")
    for dist in distances:
        if dist <= 0:
            raise ValueError(f"Invalid distance: {dist}. Distances must be positive numbers.")

def format_position(x, y):
    """Format the position as a dictionary."""
    return {"x": x, "y": y}
    