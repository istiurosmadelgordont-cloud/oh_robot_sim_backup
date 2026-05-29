import os
import yaml
import launch
from launch import LaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from robot_sim_common import config

from launch_ros.actions import Node
from launch.actions import RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessStart, OnProcessExit
from ament_index_python.packages import get_package_share_directory
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode
from launch.actions import ExecuteProcess
import xacro
from moveit_configs_utils import MoveItConfigsBuilder


def load_file(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, "r") as file:
            return file.read()
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None


def load_yaml(package_name, file_path):
    package_path = get_package_share_directory(package_name)
    absolute_file_path = os.path.join(package_path, file_path)

    try:
        with open(absolute_file_path, "r") as file:
            return yaml.safe_load(file)
    except EnvironmentError:  # parent of IOError, OSError *and* WindowsError where available
        return None


PKG_NAME = "demos"
PKG_SHARED_DIR = get_package_share_directory(PKG_NAME)
ROBOT_NAME = "franka_panda"
ROBOT_DESC_PKG_NAME = config.get_robot_description_pkgname(ROBOT_NAME)
ROBOT_DESC_PKG_SHARED_DIR = config.get_robot_description_share_dir(ROBOT_NAME)
ROBOT_MOVEIT_CONFIG_PKG_NAME = config.get_robot_moveit2_pkgname(ROBOT_NAME)
ROBOT_MOVEIT_CONFIG_SHARED_DIR = config.get_robot_moveit2_share_dir(ROBOT_NAME)
ROBOT_MUJOCO_DESC_PKG_NAME = config.get_robot_mujoco_resource_pkgname(ROBOT_NAME)
ROBOT_MUJOCO_DESC_SHARED_DIR = config.get_robot_mujoco_resource_share_dir(ROBOT_NAME)


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("panda", package_name=ROBOT_MOVEIT_CONFIG_PKG_NAME)
        .robot_description(
            file_path="config/panda.urdf.xacro",
            mappings={
                "ros2_control_hardware_type": "mujoco"
            },
        )
        .robot_description_semantic(file_path="config/panda.srdf")
        .pilz_cartesian_limits(file_path="config/pilz_cartesian_limits.yaml")
        .trajectory_execution(file_path="config/gripper_moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl", "pilz_industrial_motion_planner"])
        # # We must set this to publish robot_description_sematic
        # .planning_scene_monitor(
        #     publish_robot_description=True,
        #     publish_robot_description_semantic=True
        # )
        .to_moveit_configs()
    )
    # Start the actual move_group node/action server
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            # moveit_config.to_dict(),
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.trajectory_execution,
            moveit_config.joint_limits,
            {"use_sim_time": True}]
    )

    # Get parameters for the Servo node
    servo_yaml = load_yaml(ROBOT_DESC_PKG_NAME, "config/servo_sim_config.yaml")
    servo_params = {"moveit_servo": servo_yaml}

    # RViz
    rviz_config_file = os.path.join(
        ROBOT_DESC_PKG_SHARED_DIR, "config", "mtc.rviz"
    )
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            {"use_sim_time": True}
        ],
    )

    # ros2_control using FakeSystem as hardware
    ros2_controllers_path = os.path.join(
        ROBOT_MOVEIT_CONFIG_SHARED_DIR,
        "config",
        "ros2_controllers.yaml",
    )

    node_mujoco_ros2_control = Node(
        package='mujoco_ros2_control',
        executable='mujoco_ros2_control',
        output='screen',
        parameters=[
            moveit_config.robot_description,
            ros2_controllers_path,
            {'mujoco_model_path':os.path.join(ROBOT_MUJOCO_DESC_SHARED_DIR, ROBOT_NAME, 'scene.xml')},
            {"use_sim_time": True}
        ],
        # emulate_tty=True,
        # Redirect stdout/stderr to a file
        # Important: 'prefix' runs the node wrapped in a shell command
        # prefix=['bash -c "exec $0 $@ > ', os.path.join('/root', 'mujoco_ros2_control.log'), ' 2>&1"']
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            # "--controller-manager-timeout",
            # "300",
            "--controller-manager",
            "/controller_manager",
        ],
    )

    panda_arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["panda_arm_controller", "-c", "/controller_manager"],
    )
    panda_hand_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["panda_hand_controller", "-c", "/controller_manager"],
    )
    # Without spawning admittance controller, panda arm controller is not working.
    # Admittance controller is disabled in default, so it shouldn't apply until enabled.
    admittance_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["admittance_controller", "-c", "/controller_manager"],
    )

    # Launch as much as possible in components
    container = ComposableNodeContainer(
        name="moveit_servo_demo_container",
        namespace="/",
        package="rclcpp_components",
        executable="component_container_mt",
        composable_node_descriptions=[
            # Example of launching Servo as a node component
            # Assuming ROS2 intraprocess communications works well, this is a more efficient way.
            # ComposableNode(
            #     package="moveit_servo",
            #     plugin="moveit_servo::ServoServer",
            #     name="servo_server",
            #     parameters=[
            #         servo_params,
            #         moveit_config.robot_description,
            #         moveit_config.robot_description_semantic,
            #     ],
            # ),
            ComposableNode(
                package="robot_state_publisher",
                plugin="robot_state_publisher::RobotStatePublisher",
                name="robot_state_publisher",
                parameters=[moveit_config.robot_description, {"use_sim_time": True}],
            ),
            ComposableNode(
                package="tf2_ros",
                plugin="tf2_ros::StaticTransformBroadcasterNode",
                name="static_tf2_broadcaster",
                parameters=[
                    {
                        "frame_id": "world",
                        "child_frame_id": "panda_link0",
                        "translation": [0.0, 0.0, 0.0],
                        "rotation": [0.0, 0.0, 0.0, 1.0],
                    },
                    {"use_sim_time": True}
                ]
            ),
            # ComposableNode(
            #     package="moveit_servo",
            #     plugin="moveit_servo::JoyToServoPub",
            #     name="controller_to_servo_node",
            # ),
            ComposableNode(
                package=PKG_NAME,
                plugin="servo2c_plugins::Joy2ServoController",
                name="joy_to_servo_node",
            ),
            ComposableNode(
                package="joy",
                plugin="joy::Joy",
                name="joy_node",
            ),
        ],
        output="screen",
    )
    # Launch a standalone Servo node.
    # As opposed to a node component, this may be necessary (for example) if Servo is running on a different PC
    servo_node = Node(
        package="moveit_servo",
        executable="servo_node_main",
        parameters=[
            servo_params,
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": True}
        ],
        output="screen",
    )

    # action_framwork_launch = launch.actions.IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource(
    #         os.path.join(get_package_share_directory('control_svc'), 'launch', 'control_svc.launch.py')
    #     )
    # )
    # framework control services
    action_sim_nav_controller_node = Node(
        package='control_svc',
        executable='svc_mgr',
        name='control_svc_node',
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            {"use_sim_time": True}
        ],
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


    return LaunchDescription(
        [
            RegisterEventHandler(
                event_handler=OnProcessStart(
                    target_action=node_mujoco_ros2_control,
                    on_start=[joint_state_broadcaster_spawner],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=joint_state_broadcaster_spawner,
                    on_exit=[admittance_controller_spawner,panda_hand_controller_spawner],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=admittance_controller_spawner,
                    on_exit=[panda_arm_controller_spawner],
                )
            ),
            rviz_node,
            servo_node,
            container,
            move_group_node,
            node_mujoco_ros2_control,
            # action_framwork_launch
            pose_manager_timer,
            sim_nav_controller_timer
        ]
    )
