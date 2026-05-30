#!/usr/bin/env python3
# launch: gazebo classic with robot desc

import launch
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

import os

from robot_sim_common import config

# current package
PKG_NAME = "demos"

DEFAULT_ROBOT_NAME = "diffdrive_car"
# DEFAULT_ROBOT_NAME = "xl_ipads_fixed"
DEFAULT_ROBOT_SIM_LAUNCH_SCRIPT = "gzsim.classic.launch.py"

DEFAULT_ASSET_GZ_WORLD = "huawei_room.world"


def launch_setup(context: launch.LaunchContext, *args, **kwargs):
    # get the actual string of substitutions
    robot_name = context.perform_substitution(LaunchConfiguration('robot_name'))
    robot_sim_launch_script = context.perform_substitution(LaunchConfiguration('robot_sim_launch_script'))
    world = context.perform_substitution(LaunchConfiguration('world'))
    
    if not config.is_robot_navigable(robot_name):
        raise RuntimeError(
            f"robot '{robot_name}' is not navigable:"
            f" please create package '{config.get_robot_nav2_pkgname(robot_name)}'"
            f" and configure your robot with '{config.get_robot_nav2_params_file_pattern()}'")

    robot_desc_share_dir = config.get_robot_description_share_dir(robot_name)

    action_sim_launch = launch.actions.IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(robot_desc_share_dir, 'launch', robot_sim_launch_script)
        ),
        launch_arguments={
            'world': os.path.join(config.ASSET_GZ_WORLDS_DIR, world)
        }.items()
    )
    
    return [
        # Start the sequence
        action_sim_launch,
    ]


def generate_launch_description() -> launch.LaunchDescription:
    
    return launch.LaunchDescription([
        DeclareLaunchArgument(
            'robot_name',
            default_value=DEFAULT_ROBOT_NAME,
            description='The name of the robot'),
        DeclareLaunchArgument(
            'robot_sim_launch_script',
            default_value=DEFAULT_ROBOT_SIM_LAUNCH_SCRIPT,
            description='The custom simulation env (like gazebo) launch script for your robot'),
        DeclareLaunchArgument(
            'world',
            default_value=DEFAULT_ASSET_GZ_WORLD,
            description="The custom world for simulation env (like gazebo)"),
        OpaqueFunction(function=launch_setup)
    ])
