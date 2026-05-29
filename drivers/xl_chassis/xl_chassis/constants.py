"""
Some constant values for chassis controller.
"""

from geometry_msgs.msg import Transform

# Rate at which the topic is published (in Hz)
TOPIC_PUBLISH_RATE_HZ = 10

# Frame IDs
BASE_LINK_FRAME_ID = "base_link"
BASE_SCAN_FRAME_ID = "base_scan"
BASE_FOOTPRINT_FRAME_ID = "base_footprint"
ODOM_FRAME_ID = "odom"
MAP_FRAME_ID = "map"

# Topic names
LASER_SCAN_TOPIC = "scan"
ODOM_TOPIC = "odom"

# Zero transformation values
ZERO_TRANSFORMATION = Transform()
ZERO_TRANSFORMATION.translation.x = 0.0
ZERO_TRANSFORMATION.translation.y = 0.0
ZERO_TRANSFORMATION.translation.z = 0.0
ZERO_TRANSFORMATION.rotation.x = 0.0
ZERO_TRANSFORMATION.rotation.y = 0.0
ZERO_TRANSFORMATION.rotation.z = 0.0
ZERO_TRANSFORMATION.rotation.w = 1.0
