#!/usr/bin/env python3

import launch
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from ament_index_python.packages import get_package_share_directory

import os

from robot_sim_common import config

# current package
PKG_NAME = "demos"

DEFAULT_ROBOT_NAME = "xl_ipads_fixed"
DEFAULT_ROBOT_SIM_LAUNCH_SCRIPT = "gzsim.classic.launch.py"
DEFAULT_ROBOT_NAV2_CONFIG = "nav2_params.classic.yaml"

DEFAULT_ASSET_GZ_WORLD = "huawei_room.world"
DEFAULT_ASSET_SLAM2D_MAP = "huawei_room.yaml"


def launch_setup(context: launch.LaunchContext, *args, **kwargs):
    # get the actual string of substitutions
    robot_name = context.perform_substitution(LaunchConfiguration('robot_name'))
    nav2_params = context.perform_substitution(LaunchConfiguration('nav2_params'))
    slam2d_map = context.perform_substitution(LaunchConfiguration('map'))

    bringup_official_dir = get_package_share_directory('nav2_bringup')
    
    if not config.is_robot_navigable(robot_name):
        raise RuntimeError(
            f"robot '{robot_name}' is not navigable:"
            f" please create package '{config.get_robot_nav2_pkgname(robot_name)}'"
            f" and configure your robot with '{config.get_robot_nav2_params_file_pattern()}'")

    robot_nav2_share_dir = config.get_robot_nav2_share_dir(robot_name)

    pkg_share_dir = get_package_share_directory(PKG_NAME)
    action_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share_dir, 'launch', 'com_nomap.launch.py')
        ),
        launch_arguments={
            'robot_name': robot_name,
            'robot_sim_launch_script': DEFAULT_ROBOT_SIM_LAUNCH_SCRIPT,
            'world': DEFAULT_ASSET_GZ_WORLD
        }.items()
    )

    action_nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_official_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': os.path.join(config.ASSET_SLAM2D_MAPS_DIR, slam2d_map),
            'use_sim_time': 'True',
            # 'log_level': 'debug',
            'params_file': os.path.join(robot_nav2_share_dir, 'config', nav2_params)
        }.items()
    )
    
    action_framwork_launch = launch.actions.IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('control_svc'), 'launch', 'control_svc.launch.py')
        )
    )
    
    return [
        # Start the sequence
        action_sim_launch,
        action_nav2_launch,
        action_framwork_launch,
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2_map_display_node',
            arguments=['-d', os.path.join(bringup_official_dir, 'rviz', 'nav2_default_view.rviz')],
            parameters=[{'use_sim_time': True}],
            output='screen'
        ),
    ]


def generate_launch_description() -> launch.LaunchDescription:
    
    return launch.LaunchDescription([
        DeclareLaunchArgument(
            'robot_name',
            default_value=DEFAULT_ROBOT_NAME,
            description='The name of the robot'),
        DeclareLaunchArgument(
            'nav2_params',
            default_value=DEFAULT_ROBOT_NAV2_CONFIG,
            description="The custom navigation2 configurations (robot related)"),
        DeclareLaunchArgument(
            'map',
            default_value=DEFAULT_ASSET_SLAM2D_MAP,
            description="The custom SLAM 2D map for navigation2 & simulation env (like gazebo)"),
        OpaqueFunction(function=launch_setup)
    ])

