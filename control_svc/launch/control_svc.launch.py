from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node



def generate_launch_description() -> LaunchDescription:
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

    return LaunchDescription([
        pose_manager_timer,
        sim_nav_controller_timer
    ])