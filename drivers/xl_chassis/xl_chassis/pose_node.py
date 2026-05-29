from typing import Tuple, List

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import (
    PoseWithCovariance,
    Pose,
    Point,
    Quaternion,
    TwistWithCovariance,
    Twist,
    Vector3,
    TransformStamped,
)
from tf2_ros import TransformBroadcaster

from .chassis import Chassis
from .constants import *
from .utils import yaw_to_quaternion


class PoseNode(Node):
    """
    ROS2 Node: Get position and speed from chassis API,
    process and publish as Odometry messages.
    """

    def __init__(self) -> None:
        """
        Initialize the PoseNode.
        """
        super().__init__("pose_node")
        self.publisher_ = self.create_publisher(Odometry, ODOM_TOPIC, 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        self.chassis = Chassis()

        self.timer = self.create_timer(1.0 / TOPIC_PUBLISH_RATE_HZ, self._time_cb)
        self.get_logger().info("PoseNode initialized")

    def _time_cb(self) -> None:
        """
        Timer callback to get data from chassis and publish Odometry.
        """
        try:
            position = self.chassis.get_pos()
            speed = self.chassis.get_speed()
        except Exception as e:
            self.get_logger().error(f"Failed to get data from chassis: {e}")
            return

        # Convert to Odometry message
        try:
            msg, tf_msg = self.process_data(position, speed)
        except Exception as e:
            self.get_logger().error(f"Failed to process data into Odometry: {e}")
            return

        # Publish Odometry and TF
        self.tf_broadcaster.sendTransform(tf_msg)
        self.publisher_.publish(msg)

        self.get_logger().debug(
            "Published Odometry with position: "
            f"x={msg.pose.pose.position.x}, y={msg.pose.pose.position.y}"
        )

    def process_data(
        self, position: tuple, speed: tuple
    ) -> Tuple[Odometry, List[TransformStamped]]:
        """
        Process position and speed data into an Odometry message.

        Args:
            position (tuple): (x, y, theta) position data.
            speed (tuple): (vx, vth) speed data.

        Returns:
            Tuple[Odometry, List[TransformStamped]]: The Odometry message and TF transforms
        """
        # Create Odometry message
        odom_msg = Odometry()

        # Header information
        odom_msg.header.stamp = self.get_clock().now().to_msg()
        odom_msg.header.frame_id = ODOM_FRAME_ID
        odom_msg.child_frame_id = BASE_LINK_FRAME_ID

        # Fill position data
        x, y, theta = position
        odom_msg.pose = PoseWithCovariance()
        odom_msg.pose.pose = Pose()
        odom_msg.pose.pose.position = Point(x=float(x), y=float(y), z=0.0)

        # Convert yaw to quaternion
        q = yaw_to_quaternion(theta)
        odom_msg.pose.pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

        # Fill speed data
        vx, vth = speed
        odom_msg.twist = TwistWithCovariance()
        odom_msg.twist.twist = Twist()
        odom_msg.twist.twist.linear = Vector3(x=float(vx), y=0.0, z=0.0)
        odom_msg.twist.twist.angular = Vector3(x=0.0, y=0.0, z=float(vth))

        # Create TF transform
        transform = TransformStamped()
        transform.header.stamp = odom_msg.header.stamp
        transform.header.frame_id = ODOM_FRAME_ID
        transform.child_frame_id = BASE_FOOTPRINT_FRAME_ID

        transform.transform.translation.x = float(x)
        transform.transform.translation.y = float(y)
        transform.transform.translation.z = 0.0
        transform.transform.rotation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

        return odom_msg, [transform]


def main(argv=None) -> None:
    """
    Main function to run the PoseNode.
    """
    rclpy.init(args=argv)
    node = PoseNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("KeyboardInterrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
