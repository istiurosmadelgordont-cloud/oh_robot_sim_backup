
import launch

from launch_ros.actions import Node

PKG_NAME="xl_chassis"


def generate_launch_description() -> launch.LaunchDescription:
    return launch.LaunchDescription([
        Node(
            package=PKG_NAME,
            executable='controller_node',
            name='xl_cmd_vel_controller',
            output='screen'
        ),
        Node(
            package=PKG_NAME,
            executable='pose_node',
            name='xl_odom_provider',
            output='screen'
        ),
        Node(
            package=PKG_NAME,
            executable='lazer_node',
            name='xl_laser_provider',
            output='screen'
        )
    ])
