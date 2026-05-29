
import os
import launch
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from robot_sim_common import config

PKG_NAME="xl_chassis"


def launch_setup(context: launch.LaunchContext, *args, **kwargs):
    # get the actual string of substitutions
    slam2d_map = context.perform_substitution(LaunchConfiguration('map'))
    use_sim = context.perform_substitution(LaunchConfiguration('use_sim_time'))

    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': os.path.join(config.ASSET_SLAM2D_MAPS_DIR, slam2d_map)}]
    )
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[{'use_sim_time': use_sim == 'True'},
                    {'initial_pose.x': 0.0},
                    {'initial_pose.y': 0.0},
                    {'initial_pose.z': 0.0},
                    {'initial_pose.yaw': 0.0}]
    )
    
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map_server',
        output='screen',
        parameters=[{'use_sim_time': use_sim == 'True'},
                    {'autostart': True},
                    {'node_names': ['map_server', 'amcl']}]
    )
    return [
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
        ),
        map_server_node,
        amcl_node,
        lifecycle_manager_node
    ]


def generate_launch_description() -> launch.LaunchDescription:
    return launch.LaunchDescription([
        DeclareLaunchArgument(
            'map',
            default_value="sjtu20260109.yaml",
            description='Full path to map yaml file to load'
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            description='Use simulation time'
        ),
        OpaqueFunction(function=launch_setup)
    ])
