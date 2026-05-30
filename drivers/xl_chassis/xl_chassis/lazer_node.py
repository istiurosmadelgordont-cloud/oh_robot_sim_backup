"""
ROS2 Node to publish laser scanner data from chassis API as LaserScan messages.
"""

import math
from typing import List, Tuple

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import TransformStamped
from tf2_ros import StaticTransformBroadcaster

from .chassis import Chassis
from .constants import *


class LazerNode(Node):
    """
    ROS2 Node: Get laser data from chassis API, process and publish as LaserScan messages.
    """

    def __init__(self) -> None:
        """
        Initialize LazerNode, set up publisher and timer.
        """
        super().__init__("laser_node")
        self.publisher_ = self.create_publisher(LaserScan, LASER_SCAN_TOPIC, 10)
        self.tf_broadcaster = StaticTransformBroadcaster(self)
        self.chassis = Chassis()

        self.publish_static_transform()
        self.timer = self.create_timer(1.0 / TOPIC_PUBLISH_RATE_HZ, self._time_cb)
        self.get_logger().info("LazerNode initialized")

    def publish_static_transform(self):
        """
        Publish static transforms between base_link, base_scan, and base_footprint.
        """
        transform_bls = TransformStamped()
        transform_bls.header.stamp = self.get_clock().now().to_msg()
        transform_bls.header.frame_id = BASE_LINK_FRAME_ID
        transform_bls.child_frame_id = BASE_SCAN_FRAME_ID
        transform_bls.transform = ZERO_TRANSFORMATION

        transform_bfl = TransformStamped()
        transform_bfl.header.stamp = self.get_clock().now().to_msg()
        transform_bfl.header.frame_id = BASE_FOOTPRINT_FRAME_ID
        transform_bfl.child_frame_id = BASE_LINK_FRAME_ID
        transform_bfl.transform = ZERO_TRANSFORMATION

        self.tf_broadcaster.sendTransform([transform_bls, transform_bfl])

    def _time_cb(self) -> None:
        """
        Timer callback to get laser data, process it, and publish as LaserScan message.
        """
        # Get raw laser data and robot position from chassis
        try:
            lazer_list = self.chassis.get_laser()
            pos = self.chassis.get_pos()
        except Exception as e:
            self.get_logger().error(f"Failed to get laser data from chassis: {e}")
            return

        # Try to process raw data into LaserScan message
        try:
            msg = self.process_lazer_data(lazer_list, pos)
        except Exception as e:
            self.get_logger().error(f"Failed to process raw data into LaserScan: {e}")
            return

        # Publish the LaserScan message
        self.publisher_.publish(msg)

    def process_lazer_data(
        self,
        raw: List[List[float]],
        pos: Tuple[float, float, float],
    ) -> LaserScan:
        """
        Process raw data into a LaserScan message.

        Args:
            raw: List of (x, y) tuples representing laser points.
            pos: Tuple (x0, y0, theta0) representing robot position and orientation

        Returns:
            LaserScan message populated with processed data.
        """

        # Create LaserScan message
        msg = LaserScan()

        # Header
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = BASE_SCAN_FRAME_ID

        # Static parameters of laser scanner
        # Min & max angles for 270 degree scan
        msg.angle_min = -135.0 * (math.pi / 180.0)
        msg.angle_max = 135.0 * (math.pi / 180.0)
        # Min & max range
        msg.range_min = 0.02  # Precision ±2cm, min range 2cm
        msg.range_max = 30.0  # Max detection distance
        # Set scan time based on TOPIC_PUBLISH_RATE_HZ frequency for instance
        msg.scan_time = 1.0 / TOPIC_PUBLISH_RATE_HZ
        # Set angle increment to 0.1 degree (in radians)
        msg.angle_increment = math.radians(0.1)
        # Leave intensities empty
        msg.intensities = []

        # Dynamic parameters of laser scanner
        num_readings = (
            int(round((msg.angle_max - msg.angle_min) / msg.angle_increment)) + 1
        )
        # Calculate time increment
        msg.time_increment = (
            msg.scan_time / (num_readings - 1) if num_readings > 1 else 0.0
        )
        # Initialize all ranges to infinity
        msg.ranges = [float("inf")] * num_readings

        # Iterate over raw (x, y) points
        for x, y in raw:
            # Convert (x, y) to (distance, angle) relative to robot position
            x0, y0, theta0 = pos
            distance = math.sqrt((x - x0) ** 2 + (y - y0) ** 2)
            angle = math.atan2(y - y0, x - x0) - theta0

            # Update range if within valid angle range
            if msg.angle_min <= angle <= msg.angle_max:
                index = int(round((angle - msg.angle_min) / msg.angle_increment))
                if 0 <= index < num_readings:
                    msg.ranges[index] = min(msg.ranges[index], distance)

        return msg


def main(argv=None) -> None:
    """
    Main function to initialize the LazerNode and start spinning.
    """
    rclpy.init(args=argv)
    node = LazerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("KeyboardInterrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
