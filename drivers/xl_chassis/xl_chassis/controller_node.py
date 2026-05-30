"""
A ROS2 node that subscribes to 'cmd_vel'.
"""

import time
from math import pi
from typing import Optional

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from .chassis import Chassis


class ChassisControllerNode(Node):
    """
    Subscribe to 'cmd_vel' and controll the chassis.
    """

    def __init__(self) -> None:
        super().__init__("chassis_controller")

        # Create a controller instance
        self.controller = Chassis()
        self.cmd_interval = 0.1  # seconds

        # Subscriber to Nav2 /cmd_vel
        self.subscription = self.create_subscription(
            Twist,
            "cmd_vel",
            self._cmd_vel_cb,
            10,
        )

        self.get_logger().info('ChassisControllerNode started; subscribed to "cmd_vel"')

    def _cmd_vel_cb(self, msg: Twist) -> None:
        """
        Callback for incoming cmd_vel messages.
        """
        self.last_cmd = msg
        self.last_cmd_time = time.time()

        self.get_logger().debug(
            f"Received cmd_vel: linear=({msg.linear.x:.3f},{msg.linear.y:.3f},{msg.linear.z:.3f}) "
            f"angular=({msg.angular.x:.3f},{msg.angular.y:.3f},{msg.angular.z:.3f})"
        )

        # Controll the chassis here
        # self.controller.speed_ctrl(msg.linear.x, msg.angular.z)

        try:
            # Send move commands to chassis
            if msg.linear.x != 0.0:
                self.controller.move_x(
                    100 * self.cmd_interval * msg.linear.x, msg.linear.x
                )
            if msg.angular.z != 0.0:
                self.controller.move_theta(
                    self.cmd_interval * msg.angular.z / pi * 180, msg.angular.z
                )
        except Exception as e:
            self.get_logger().error(f"Failed to send command to chassis: {e}")


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = ChassisControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("KeyboardInterrupt, shutting down")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
