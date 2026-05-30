from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node


PKG_NAME = 'xl_chassis'
SAVE_MAP_DELAY = 60.0   # seconds

def generate_launch_description():
    cur_pkg_share_dir = FindPackageShare(PKG_NAME)
    # nav2_bringup_dir = FindPackageShare('nav2_bringup')
    explore_lite_launch = PathJoinSubstitution(
        [FindPackageShare('explore_lite'), 'launch', 'explore.launch.py']
    )

    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value=PathJoinSubstitution([cur_pkg_share_dir, 'config', 'ipads_params.classic.yaml']),
        description='Full path to the ROS2 parameters file to use for all launched nodes',
    )

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time', default_value='True', description='Use simulation (Gazebo) clock if true'
    )

    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([cur_pkg_share_dir, 'launch', 'slam.launch.py'])
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )
    # nav2_bringup_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         PathJoinSubstitution([nav2_bringup_dir, 'launch', 'navigation_launch.py'])
    #     ),
    #     launch_arguments={
    #         'use_sim_time': use_sim_time,
    #         'params_file': params_file,
    #     }.items(),
    # )
    nav2_mock_node = Node(
        package=PKG_NAME,
        executable="nav2_node",
        name="nav2_mock_node",
        output="screen"
    )
    planner = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[params_file],
    )

    nav2_csvr_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file],
    )
    
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_costmap',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'autostart': True},
            {'node_names': ['planner_server', 'controller_server']}
        ])

    explore_lite_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([explore_lite_launch]),
        launch_arguments={
            'use_sim_time': use_sim_time,
        }.items(),
    )

    return LaunchDescription(
        [
            declare_params_file_cmd,
            declare_use_sim_time_cmd,
            slam_launch,
            # nav2_bringup_launch,
            nav2_mock_node,
            planner,
            nav2_csvr_node,
            lifecycle_manager_node,
            explore_lite_launch
        ]
    )