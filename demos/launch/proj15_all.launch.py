#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    pkg_demos = get_package_share_directory('demos')

    # 1. Include the main Gazebo and Nav2 launch file
    gazebo_nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_demos, 'launch', 'gzsim.nav2.launch.py')
        )
    )

    # 2. Vision Recognition Node
    vision_node = Node(
        package='demos',
        executable='vision_recognition_node',
        name='vision_recognition_node',
        output='screen'
    )

    # 3. PDA SoftBus Monitor Node
    softbus_node = Node(
        package='demos',
        executable='pda_softbus_monitor',
        name='pda_softbus_monitor',
        output='screen'
    )

    # 4. Robot Executor Node
    executor_node = Node(
        package='demos',
        executable='robot_executor',
        name='robot_executor',
        output='screen'
    )

    # 5. Ward Task Server Node
    task_server_node = Node(
        package='demos',
        executable='ward_task_server',
        name='ward_task_server',
        output='screen'
    )

    # Delay starting the python nodes slightly to allow Gazebo and Nav2 to initialize
    delayed_nodes = TimerAction(
        period=5.0,
        actions=[vision_node, softbus_node, executor_node, task_server_node]
    )

    return LaunchDescription([
        gazebo_nav2_launch,
        delayed_nodes
    ])
