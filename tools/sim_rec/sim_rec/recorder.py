#!/usr/bin/env python3

import os
import signal
import sys
import shutil
import numpy as np
from threading import Lock, RLock
import cv2
from cv_bridge import CvBridge

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import qos_profile_sensor_data

import tf2_ros
from tf2_ros import TransformException
from tf_transformations import euler_from_quaternion

from sensor_msgs.msg import JointState, Image
from std_srvs.srv import Trigger

from lerobot.datasets.lerobot_dataset import LeRobotDataset
import torch


class LeRobotRecorderNode(Node):

    REPO_NAME_DEFAULT = 'robot_data_recording'
    ROOT_PATH_DEFAULT = './data'

    def __init__(self):
        super().__init__('lerobot_recorder_node')
        
        # Parameters
        self.declare_parameter('repo_name', LeRobotRecorderNode.REPO_NAME_DEFAULT)
        self.declare_parameter('root_path', LeRobotRecorderNode.ROOT_PATH_DEFAULT)
        self.declare_parameter('fps', 20)
        self.declare_parameter('joint_names', ['panda_joint1', 'panda_joint2', 'panda_joint3', 
                                             'panda_joint4', 'panda_joint5', 'panda_joint6', 
                                             'panda_joint7', 'panda_finger_joint1'])
        self.declare_parameter('end_effector_frame', 'panda_hand')
        self.declare_parameter('base_frame', 'panda_link0')

        # dynamic parameter: read from parameter server every time /record/start_episode is called
        self.declare_parameter('task', 'grasp the red box and put it in the green container')
        
        # Get parameters
        self.repo_name = self.get_parameter('repo_name').get_parameter_value().string_value
        self.root_path = self.get_parameter('root_path').get_parameter_value().string_value
        self.fps = self.get_parameter('fps').get_parameter_value().integer_value
        self.joint_names = self.get_parameter('joint_names').get_parameter_value().string_array_value
        self.end_effector_frame = self.get_parameter('end_effector_frame').get_parameter_value().string_value
        self.base_frame = self.get_parameter('base_frame').get_parameter_value().string_value
        
        # Initialize CV bridge for image conversion
        self.cv_bridge = CvBridge()
        
        # TF2 buffer and listener for pose tracking
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        
        # Data storage
        self.data_lock = Lock()
        self.joint_data = None
        self.image_data = None
        self.wrist_image_data = None
        self.end_effector_pose = None
        self.obj_init = np.zeros(6, dtype=np.float32)  # Initialize with zeros
        
        # Recording state
        self.recording = False
        self.current_episode_data = []
        # NOTE: Use dynamic property with only getter
        # self.current_task = ""
        self._current_task = ""
        self.episode_count = self.get_prev_episode_count()
        self.dataset = None

        # Node state
        self.shutdown_flag_relock = RLock()
        self.shutdown_flag = False
        
        # Create callback group for concurrent callbacks
        self.callback_group = ReentrantCallbackGroup()
        
        # Create subscribers
        self.joint_sub = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            10,
            callback_group=self.callback_group
        )
        
        self.image_sub = self.create_subscription(
            Image,
            '/cam/world_camera/image_raw',
            self.image_callback,
            qos_profile_sensor_data,
            callback_group=self.callback_group
        )
        
        self.wrist_image_sub = self.create_subscription(
            Image,
            '/cam/wrist_camera/image_raw',
            self.wrist_image_callback,
            qos_profile_sensor_data,
            callback_group=self.callback_group
        )
        
        self.start_episode_srv = self.create_service(
            Trigger,
            '/record/start_episode',
            self.start_episode_callback,
            callback_group=self.callback_group
        )
        
        self.end_episode_srv = self.create_service(
            Trigger,
            '/record/end_episode',
            self.end_episode_callback,
            callback_group=self.callback_group
        )

        self.abort_episode_srv = self.create_service(
            Trigger,
            '/record/abort_episode',
            self.abort_episode_callback,
            callback_group=self.callback_group
        )
        
        # Initialize LeRobotDataset (but don't start recording yet)
        self.initialize_dataset()
        
        # Timer for data recording at specified FPS (only when recording is active)
        self.timer = self.create_timer(
            1.0 / self.fps, 
            self.record_data_callback,
            callback_group=self.callback_group
        )
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.get_logger().info(f'LeRobot Recorder Node initialized (not recording yet)')
        self.get_logger().info(f'Monitoring joints: {self.joint_names}')
        self.get_logger().info(f'Recording FPS: {self.fps}')
        self.get_logger().info(f'Set parameters like "task" using parameter server.')
        self.get_logger().info('Services available:')
        self.get_logger().info('  - /record/start_episode: Start recording a new episode')
        self.get_logger().info('  - /record/end_episode: End current episode and save data')
        self.get_logger().info('  - /record/abort_episode: End current episode and discard it')
        self.get_logger().info('Press Ctrl+C to stop and save current dataset')

    @property
    def current_task(self) -> str:
        # TODO: move the refresh operation to a working thread
        self._current_task = self.get_parameter('task').get_parameter_value().string_value
        return self._current_task

    def get_prev_episode_count(self) -> int:
        chunk_dir = os.path.join(self.root_path, "data", "chunk-000")
        if not os.path.exists(chunk_dir):
            return 0
        assert os.path.isdir(chunk_dir), "invalid LeRobot Dataset (v2.1)"
        return len(os.listdir(chunk_dir))

    def initialize_dataset(self):
        """Initialize the LeRobotDataset (create if doesn't exist)"""
        try:
            if not os.path.exists(self.root_path):
                self.dataset = LeRobotDataset.create(
                    repo_id=self.repo_name,
                    root=self.root_path,
                    robot_type="panda",
                    fps=self.fps,
                    features={
                        "observation.image": {
                            "dtype": "image",
                            "shape": (480, 640, 3),
                            "names": ["height", "width", "channel"],
                        },
                        "observation.wrist_image": {
                            "dtype": "image",
                            "shape": (480, 640, 3),
                            "names": ["height", "width", "channel"],
                        },
                        "observation.state": {
                            "dtype": "float32",
                            "shape": (6,),
                            "names": ["state"],
                        },
                        "action": {
                            "dtype": "float32",
                            "shape": (8,),
                            "names": ["action"],
                        },
                        "obj_init": {
                            "dtype": "float32",
                            "shape": (6,),
                            "names": ["obj_init"],
                        },
                    },
                    image_writer_threads=10,
                    image_writer_processes=5,
                )
                self.get_logger().info(f'Dataset initialized at: {self.root_path}')
            else:
                self.dataset = LeRobotDataset(repo_id=self.repo_name, root=self.root_path)
                self.get_logger().info(f'Dataset loaded from {self.root_path}')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize dataset: {str(e)}')
            raise

    def start_episode_callback(self, request, response):
        """Service callback to start recording a new episode with task description"""
        try:
            with self.data_lock:
                # If already recording, automatically end current episode first
                if self.recording:
                    self.get_logger().info(f"Auto-ending current episode {self.episode_count} before starting new episode")
                    self.recording = False
                    frames_saved = self.save_current_episode()
                    self.get_logger().info(f"Auto-saved {frames_saved} frames from previous episode")
                
                # Validate task parameter
                cur_task = self.current_task
                if not cur_task or cur_task.strip() == "":
                    response.success = False
                    response.message = "Task description cannot be empty"
                    self.get_logger().warn(response.message)
                    return response
                
                # Start new episode
                self.recording = True
                self.current_episode_data = []
                self.episode_count += 1
                
                response.success = True
                response.message = f"Started recording episode {self.episode_count} with task: '{cur_task}'"
                self.get_logger().info(response.message)
                
        except Exception as e:
            response.success = False
            response.message = f"Error starting episode: {str(e)}"
            self.get_logger().error(response.message)
        
        return response

    def end_episode_callback(self, request, response):
        """Service callback to end current episode and save data"""
        try:
            with self.data_lock:
                if not self.recording:
                    response.success = False
                    response.message = "No episode is currently being recorded"
                    self.get_logger().warn(response.message)
                    return response
                
                # Stop recording
                self.recording = False
                
                # Save current episode data
                frames_saved = self.save_current_episode()
                
                response.success = True
                response.message = f"Episode {self.episode_count} ended. Saved {frames_saved} frames. Ready for next episode."
                self.get_logger().info(response.message)
                
        except Exception as e:
            response.success = False
            response.message = f"Error ending episode: {str(e)}"
            self.get_logger().error(response.message)
        
        return response

    def abort_episode_callback(self, request, response):
        """Service callback to end current episode and discard it"""
        try:
            with self.data_lock:
                if not self.recording:
                    response.success = False
                    response.message = "No episode is currently being recorded"
                    self.get_logger().warn(response.message)
                    return response
                
                # Stop recording and reset episode data
                self.recording = False
                self.current_episode_data = []
                self.episode_count -= 1
                
                response.success = True
                response.message = f"Episode {self.episode_count+1} discarded. Ready for next episode."
                self.get_logger().info(response.message)
                
        except Exception as e:
            response.success = False
            response.message = f"Error aborting episode: {str(e)}"
            self.get_logger().error(response.message)
        
        return response

    def save_current_episode(self) -> int:
        """Save the current episode data to the dataset"""
        if not self.current_episode_data:
            self.get_logger().warn(f"Episode {self.episode_count} has no data to save")
            return 0
        
        with self.shutdown_flag_relock:
            if self.shutdown_flag:
                self.get_logger().error("node is shutting down")
                return 0
        
        try:
            frames_added = 0
            # Retrieve current_task property from parameter server
            cur_task = self.current_task
            for data_frame in self.current_episode_data:
                self.dataset.add_frame(data_frame, task=cur_task)
                frames_added += 1
            
            # Consolidate dataset to ensure data is written to disk
            if hasattr(self.dataset, 'consolidate'):
                self.dataset.consolidate()
            
            self.dataset.save_episode()

            self.get_logger().info(f"Episode {self.episode_count} (task: '{cur_task}'): Saved {frames_added} frames to dataset")
            self.current_episode_data = []  # Clear episode data
            return frames_added
            
        except Exception as e:
            self.get_logger().error(f"Error saving episode {self.episode_count}: {str(e)}")
            return 0

    def joint_callback(self, msg):
        """Callback for joint state data"""
        with self.data_lock:
            try:
                # Extract joint positions for specified joints
                joint_positions = []
                for joint_name in self.joint_names:
                    if joint_name in msg.name:
                        idx = msg.name.index(joint_name)
                        joint_positions.append(msg.position[idx])
                    else:
                        self.get_logger().warn(f'Joint {joint_name} not found in joint_states')
                        joint_positions.append(0.0)
                
                if len(joint_positions) == 8:  # 7 joints + 1 gripper
                    self.joint_data = np.array(joint_positions, dtype=np.float32)
            except Exception as e:
                self.get_logger().error(f'Error processing joint data: {str(e)}')

    def image_callback(self, msg):
        """Callback for main camera image"""
        try:
            cv_image = self.cv_bridge.imgmsg_to_cv2(msg, "bgr8")
            # Resize to expected dimensions if necessary
            cv_image = cv2.resize(cv_image, (640, 480))
            with self.data_lock:
                self.image_data = cv_image
        except Exception as e:
            self.get_logger().error(f'Error processing main camera image: {str(e)}')

    def wrist_image_callback(self, msg):
        """Callback for wrist camera image"""
        try:
            cv_image = self.cv_bridge.imgmsg_to_cv2(msg, "bgr8")
            # Resize to expected dimensions if necessary
            cv_image = cv2.resize(cv_image, (640, 480))
            with self.data_lock:
                self.wrist_image_data = cv_image
        except Exception as e:
            self.get_logger().error(f'Error processing wrist camera image: {str(e)}')

    def get_end_effector_pose(self):
        """Get end effector pose using TF2"""
        try:
            # Get transform from base to end effector
            transform = self.tf_buffer.lookup_transform(
                self.base_frame,
                self.end_effector_frame,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=0.1)
            )
            
            # Extract position and orientation
            pos = transform.transform.translation
            rot = transform.transform.rotation
            
            # Convert quaternion to euler angles (roll, pitch, yaw)
            euler = euler_from_quaternion([rot.x, rot.y, rot.z, rot.w])
            
            # Return as [x, y, z, roll, pitch, yaw]
            pose = np.array([pos.x, pos.y, pos.z, euler[0], euler[1], euler[2]], dtype=np.float32)
            return pose
            
        except TransformException as e:
            self.get_logger().debug(f'Could not get end effector pose: {str(e)}')
            return np.zeros(6, dtype=np.float32)

    def record_data_callback(self):
        """Timer callback to record data at specified FPS (only when recording is active)"""
        if not self.recording:
            return
            
        with self.data_lock:
            # Check if we have all required data
            if (self.joint_data is None or 
                self.image_data is None or 
                self.wrist_image_data is None):
                self.get_logger().debug('Waiting for all data sources...')
                return
            
            # Get current end effector pose
            current_pose = self.get_end_effector_pose()
            
            try:
                # Convert images to RGB (LeRobot expects RGB)
                image_rgb = cv2.cvtColor(self.image_data, cv2.COLOR_BGR2RGB)
                wrist_image_rgb = cv2.cvtColor(self.wrist_image_data, cv2.COLOR_BGR2RGB)
                
                # Prepare data dictionary
                data = {
                    "observation.image": torch.from_numpy(image_rgb),
                    "observation.wrist_image": torch.from_numpy(wrist_image_rgb),
                    "observation.state": torch.from_numpy(current_pose),
                    "action": torch.from_numpy(self.joint_data),
                    "obj_init": torch.from_numpy(self.obj_init),
                }
                
                # Add data to current episode buffer
                self.current_episode_data.append(data)
                
                # Log progress occasionally
                if len(self.current_episode_data) % 50 == 0:
                    self.get_logger().info(f'Episode {self.episode_count}: Recorded {len(self.current_episode_data)} frames')
                    
            except Exception as e:
                self.get_logger().error(f'Error recording data: {str(e)}')

    def signal_handler(self, signum, frame):
        """Handle SIGINT and SIGTERM signals"""
        with self.shutdown_flag_relock:
            if self.shutdown_flag:
                # wait for other thread to shutdown
                return
            self.shutdown_flag = True
        
        self.get_logger().info(f'Received signal {signum}. Stopping recording...')
        self.save_and_exit()

    def save_and_exit(self):
        """Save current episode (if recording) and dataset, then cancel the timer (prepared to exit)"""
        try:
            with self.data_lock:
                # If currently recording, save the current episode first
                if self.recording:
                    self.get_logger().info(f'Auto-ending episode {self.episode_count} before shutdown...')
                    self.recording = False
                    frames_saved = self.save_current_episode()
                    self.get_logger().info(f'Auto-saved {frames_saved} frames from episode {self.episode_count}')
                
                if not os.path.exists(os.path.join(self.root_path, "meta", "tasks.jsonl")):
                    shutil.rmtree(self.root_path)
                    self.get_logger().warn("No episode/data generated!")

                # Cancel the timer
                self.timer.cancel()
                # Print dataset information
                total_frames = len(self.dataset) if self.dataset else 0
                self.get_logger().info('=== Recording Summary ===')
                self.get_logger().info(f'Total episodes recorded: {self.episode_count}')
                self.get_logger().info(f'Total frames in dataset: {total_frames}')
                self.get_logger().info(f'Dataset saved to: {self.root_path}')
                self.get_logger().info(f'Repository ID: {self.repo_name}')
            
        except Exception as e:
            self.get_logger().error(f'Error during shutdown: {str(e)}')
        
        # Shutdown ROS2 node
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    
    try:
        # Create node
        node = LeRobotRecorderNode()
        
        # Use MultiThreadedExecutor for concurrent callbacks
        executor = MultiThreadedExecutor()
        executor.add_node(node)
        
        try:
            executor.spin()
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        print(f"Error starting node: {e}")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()