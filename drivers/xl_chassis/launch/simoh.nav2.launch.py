#!/usr/bin/env python3
# launch: navigation2 & framework
# NOTE: robot simulator/ real robot need to be setup before launching this script

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

DEFAULT_ROBOT_NAME = "diffdrive_car"
DEFAULT_ROBOT_SIM_LAUNCH_SCRIPT = "gzsim.classic.launch.py"
DEFAULT_ROBOT_NAV2_CONFIG = "nav2_params.classic.yaml"

DEFAULT_ASSET_GZ_WORLD = "standard_room.classic.world"
DEFAULT_ASSET_SLAM2D_MAP = "standard_map.yaml"


def launch_setup(context: launch.LaunchContext, *args, **kwargs):
    
    # framework control services
    action_sim_nav_controller_node = Node(
        package='control_svc',
        executable='svc_mgr',
        name='control_svc_node',
        output='screen'
    )
    
    # navigation2 initial pose manager
    action_pose_manager_node = Node(
        package='control_svc',
        executable='pose_mgr',
        name='pose_manager_node',
        output='screen'
    )

    # Create timed launch sequence using cascading TimerActions
    pose_manager_timer = TimerAction(
        period=8.0,
        actions=[action_pose_manager_node]
    )
    sim_nav_controller_timer = TimerAction(
        period=15.0,
        actions=[action_sim_nav_controller_node]
    )
    
    return [
        pose_manager_timer,
        sim_nav_controller_timer,
    ]


def generate_launch_description() -> launch.LaunchDescription:
    
    return launch.LaunchDescription([
        OpaqueFunction(function=launch_setup)
    ])

