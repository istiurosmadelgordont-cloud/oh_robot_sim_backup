

import launch
import launch.launch_description_sources
import launch_ros
from launch.actions import RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit, OnProcessStart
from ament_index_python.packages import get_package_share_directory

import os


PKG_NAME = "agent2c"
NAV_CONTROL_PKG_NAME = 'diffdrive_car_nav2'
NAV_CONTROLLER_PKG_NAME = 'nav2c'


def generate_launch_description() -> launch.LaunchDescription:
    pkg_shared_dir = get_package_share_directory(PKG_NAME)
    sim_nav_pkg_shared_dir = get_package_share_directory(NAV_CONTROL_PKG_NAME)
    
    use_sim_time = launch.substitutions.LaunchConfiguration(
        'use_sim_time', default='true')

    # set env for simulator
    os.environ["MACHINE_TYPE"] = "JetRover_Acker"
    os.environ["LIDAR_TYPE"] = "A1"
    os.environ["CAMERA_TYPE"] = "HP60C"

    action_sim_and_nav2_launch = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            os.path.join(sim_nav_pkg_shared_dir, 'launch', 'nav2sim.jazzy.launch.py')
        )
    )

    action_sim_nav_controller_node = launch_ros.actions.Node(
        package=NAV_CONTROLLER_PKG_NAME,
        executable='nav2c',
        name='nav2controller_node',
        output='screen'
    )

    action_pose_manager_node = launch_ros.actions.Node(
        package=NAV_CONTROLLER_PKG_NAME,
        executable='pose_manager',
        name='pose_manager_node',
        output='screen'
    )

    action_agent_control_node = launch_ros.actions.Node(
        package=PKG_NAME,
        executable='agent_control_sim',
        name='agent_control_sim_node',
        output='screen'
    )

    # Create timed launch sequence using cascading TimerActions

    # nav_base_timer = TimerAction(
    #     period=5.0,
    #     actions=[action_sim_and_nav2_launch]
    # )
    pose_manager_timer = TimerAction(
        period=8.0,
        actions=[action_pose_manager_node]
    )
    sim_nav_controller_timer = TimerAction(
        period=16.0,
        actions=[action_sim_nav_controller_node]
    )
    
    # Start action_agent_control_node after 18 seconds (same as pose_manager, but use event handler)
    agent_control_timer = RegisterEventHandler(
        OnProcessStart(
            target_action=action_pose_manager_node,
            on_start=[action_agent_control_node]
        )
    )
    
    return launch.LaunchDescription([
        launch.actions.DeclareLaunchArgument('use_sim_time', default_value=use_sim_time,
                                             description='Use simulation (Gazebo) clock if true'),
        # TODO
        # action_sim_launch -(间隔 3 秒)-> action_nav_base_launch -(间隔 10 秒)-> action_sim_nav_node -(间隔 5 秒)-> action_pose_manager_node -> action_agent_control_node -> action_map_display_node
        
        # Start the sequence
        action_sim_and_nav2_launch,
        # action_sim_launch,  # Starts immediately
        # nav_base_timer,     # Starts after 5 seconds
        # map_display_timer,  # Starts after 10 seconds

        pose_manager_timer, # Starts after 15 seconds (3 + 10 + 5)

        sim_nav_controller_timer,      # Starts after 25 seconds (3 + 10)
        
        # Register event handlers for the last node
        agent_control_timer,
    ])
