import math
from typing import Tuple


def yaw_to_quaternion(yaw: float) -> Tuple[float, float, float, float]:
    """
    Return quaternion (x,y,z,w) for a yaw angle (radians).

    Args:
        yaw (float): The yaw angle in radians.

    Returns:
        Tuple[float, float, float, float]: The corresponding quaternion (x, y, z, w).
    """
    half = yaw * 0.5
    return (0.0, 0.0, math.sin(half), math.cos(half))
