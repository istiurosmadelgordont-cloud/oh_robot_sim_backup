import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Time as RosTime
from google.protobuf.timestamp_pb2 import Timestamp
from nav_msgs.msg import Odometry
from scipy.spatial.transform import Rotation as R
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped, PoseStamped
import math
import os
import cv2
import numpy as np
# from kinematics.kinematics_control import set_pose_target
# from servo_controller.bus_servo_control import set_servo_position
# from servo_controller_msgs.msg import ServosPosition
# from kinematics_msgs.srv import SetRobotPose
from sensor_msgs.msg import CameraInfo

import time

from concurrent import futures
import grpc
from robot_sim_dto.srv import SetPose2D, GetPose2D
from std_srvs.srv import Trigger
from std_msgs.msg import String, Bool
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge

import numpy as np
import math
from typing import Tuple


from tf_transformations import euler_from_quaternion

from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup

from control_stubs import robot_control_pb2
from control_stubs import robot_control_pb2_grpc

color_topic = "camera/rgbd/image"
depth_topic = "camera/rgbd/depth_image"
cam_i_topic = "camera/rgbd/camera_info"


class CameraServiceImpl(robot_control_pb2_grpc.CameraServiceServicer):
    def __init__(self, ros_node: Node):
        self.ros_node = ros_node
        self.bridge = CvBridge()

        # 最新图像缓存
        self.color_image = None
        self.depth_image = None

        # 共享可重入回调组
        self.shared_cbg = ReentrantCallbackGroup()

        # 订阅彩色图像
        self.ros_node.create_subscription(
            Image,
            color_topic,
            self.color_callback,
            10,
            callback_group=self.shared_cbg
        )

        # 订阅深度图像
        self.ros_node.create_subscription(
            Image,
            depth_topic,
            self.depth_callback,
            10,
            callback_group=self.shared_cbg
        )

        # 默认配置（可动态修改）
        self.config = robot_control_pb2.CameraConfig(
            format=robot_control_pb2.CameraConfig.RAW,
            resolution=robot_control_pb2.CameraConfig.RES_640x480,
            frame_rate=30.0,
            auto_exposure=True,
            exposure_time=10.0,
            gain=1.0,
            color=True,
            quality=1.0,
            enable_depth=True,
            enable_pointcloud=False,
        )

    def color_callback(self, msg: Image):
        try:
            if msg.encoding != 'bgr8':
                # 转换成OpenCV格式
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                
                # 如果是bgr8，转换为rgb8
                if msg.encoding == 'rgb8':
                    self.color_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
                else:
                    # 其他编码格式，需要根据具体格式进行转换
                    # 比如mono8灰度图，可以转成3通道
                    if msg.encoding == 'mono8':
                        self.color_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
                    else:
                        # 如果是别的格式，根据情况处理，或者报错
                        pass
            else:
                self.color_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            
        except Exception as e:
            self.ros_node.get_logger().warn(f"[CameraService] Failed to convert color image: {e}")

    def depth_callback(self, msg: Image):
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.ros_node.get_logger().warn(f"[CameraService] Failed to convert depth image: {e}")

    def GetCameraConfig(self, request, context):
        return self.config

    def GetImage(self, request, context):
        # 检查图像是否准备好
        if self.color_image is None or self.depth_image is None:
            context.set_details("Image not ready")
            context.set_code(1)
            return robot_control_pb2.ImageResponse()

        # 构造时间戳
        now = time.time()
        timestamp = Timestamp(seconds=int(now), nanos=int((now % 1) * 1e9))

        # 获取图像尺寸
        height, width, channels = self.color_image.shape

        # 构造图像元数据
        metadata = robot_control_pb2.ImageMetadata(
            capture_time=timestamp,
            width=width,
            height=height,
            channels=channels,
            camera_position=robot_control_pb2.Position(x=0.0, y=0.0, z=0.0),
            camera_orientation=robot_control_pb2.Orientation(roll=0.0, pitch=0.0, yaw=0.0),
            custom_metadata={}
        )
        success, encoded_image = cv2.imencode('.jpeg', self.color_image)
        with open("./saved_image.jpeg", "wb") as f:
                f.write(encoded_image)
        # 图像转换为 RAW 字节流
        full_image_raw_bytes = encoded_image.tobytes()

        # 处理深度图数据
        flat_depth = self.depth_image.astype(np.float32).flatten()
        depth_data = flat_depth.tolist()

        min_depth = float(np.nanmin(flat_depth))
        max_depth = float(np.nanmax(flat_depth))

        depth_image_msg = robot_control_pb2.DepthImage(
            depth_data=depth_data,
            min_depth=min_depth,
            max_depth=max_depth
        )

        # 构造响应
        response = robot_control_pb2.ImageResponse(
            metadata=metadata,
            config=self.config,
            full_image=full_image_raw_bytes,
            depth_image=depth_image_msg
        )

        return response

class RobotControlServiceImpl(robot_control_pb2_grpc.RobotControlServiceServicer):

    @staticmethod
    def quaternion_to_euler(q):
        r = R.from_quat([q.x, q.y, q.z, q.w])
        roll, pitch, yaw = r.as_euler('xyz', degrees=False)
        return roll, pitch, yaw

    def __init__(self, ros_node: Node):
        self.ros_node = ros_node
        self.ros_node.get_logger().info("initializing RobotControlService...")

        # 共享可重入回调组
        # self.shared_cbg = ReentrantCallbackGroup()
        self.shared_cbg = None
        
        self.set_pose_client = self.ros_node.create_client(
            SetPose2D, 'navigation_controller/set_pose', callback_group=self.shared_cbg)
        self.set_pose_client.wait_for_service()
        self.stop_client = self.ros_node.create_client(
            Trigger, 'navigation_controller/stop', callback_group=self.shared_cbg)
        self.stop_client.wait_for_service()

        self.ros_node.get_logger().info("nav2 controller services (set_pose, stop) available!")

        # self.place_control_pub = self.ros_node.create_publisher(Bool, '/agent_place_control', 10)
        # self.joints_pub = self.ros_node.create_publisher(ServosPosition, '/servo_controller', 1)
        self.ros_node.create_subscription(
            Bool, '/is_using_gripper', self.is_using_gripper_callback, 1, callback_group=self.shared_cbg)
        self.ros_node.create_subscription(
            Bool, '/is_moving_arm', self.is_moving_arm_callback, 1, callback_group=self.shared_cbg)
        # self.is_using_local_pub =self.ros_node.create_publisher(Bool, '/is_using_local', 1)
       
        self.intrinsic_matrix: np.ndarray | None = None
        self.ros_node.create_subscription(
            Bool, 'navigation_controller/reach_goal', self.reach_goal_callback, 1, callback_group=self.shared_cbg)
        self.reach_goal = False
        self.unreach_goal = False
        self.is_moving = robot_control_pb2.RobotState.IDLE

        self.cmd_vel_pub = self.ros_node.create_publisher(
            Twist, '/cmd_vel', 10, callback_group=self.shared_cbg)

        # self.set_pose_target_client = self.ros_node.create_client(SetRobotPose, '/kinematics/set_pose_target')
        # self.set_pose_target_client.wait_for_service()

        self.start_x: float | None = None
        self.start_y: float | None = None
        self.distance_traveled = 0.0
        self.target_distance = 0.05  # 目标前进距离，单位米
        self.image_width = 640
        self.image_height = 480
        
        self.bridge = CvBridge()
        self.depth_image: np.ndarray | None = None

        # 订阅深度图像
        self.ros_node.create_subscription(
            Image,
            depth_topic,
            self.depth_callback,
            1,
            callback_group=self.shared_cbg
        )
        # 订阅相机信息以校准相机内参
        self.ros_node.create_subscription(
            CameraInfo,
            cam_i_topic,
            self.depth_info_callback,
            1,
            callback_group=self.shared_cbg
        )
        
        self.is_using_gripper = False
        self.is_moving_arm = False
        self.is_moving_target_distance = False
        
        # 订阅 nav2 给出的位置信息
        self.ros_node.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self.pose_callback,
            10,
            callback_group=self.shared_cbg
        )
        # 位置管理
        self.pose_manager_get_client = self.ros_node.create_client(
            GetPose2D, "pose_manager/get_pose", callback_group=self.shared_cbg)
        self.pose_manager_get_client.wait_for_service()
        self.pose_manager_persist_client = self.ros_node.create_client(
            SetPose2D, 'pose_manager/set_pose', callback_group=self.shared_cbg)
        self.pose_manager_persist_client.wait_for_service()
        self.ros_node.get_logger().info("pose manager services (get_pose, set_pose) available!")
        # 使用 PoseManager 获取初始位置
        self.ros_node.get_logger().info("querying pose manager for initial pose...")
        get_pose2d_resp: GetPose2D.Response | None = self.send_request(self.pose_manager_get_client, GetPose2D.Request())
        assert get_pose2d_resp is not None
        self.ros_node.get_logger().info(f"get_pose2d_resp: {get_pose2d_resp}, {get_pose2d_resp.success}")
        
        # regarded as cache
        self.current_pose: PoseWithCovarianceStamped = RobotControlServiceImpl.pose_stamped_add_cov(get_pose2d_resp.pose)
        self.ros_node.get_logger().info(f"current_pose initialized from pose manager: {self.current_pose}")
        
        # 订阅里程计信息，方便主动位置微调
        self.ros_node.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10,
            callback_group=self.shared_cbg
        )
        self.current_status = robot_control_pb2.RobotState()

    def status_update(self):
        pos = self.current_pose.pose.pose.position
        ori = self.current_pose.pose.pose.orientation

        roll0, pitch0, yaw0 = euler_from_quaternion([ori.x, ori.y, ori.z, ori.w])
        roll, pitch, yaw = self.quaternion_to_euler(ori)
        # moving = self.is_robot_moving()

        assert (math.fabs(roll0 - roll) < 0.05 and math.fabs(pitch0 - pitch) < 0.05
            and math.fabs(yaw0 - yaw) < 0.05), "euler_from_quaternion error overflow"
        
        stamp = Timestamp()
        stamp.GetCurrentTime()
        
        self.current_status = robot_control_pb2.RobotState(
            position=robot_control_pb2.Position(
                x=pos.x,
                y=pos.y,
                z=pos.z
            ),
            orientation=robot_control_pb2.Orientation(
                roll=roll,
                pitch=pitch,
                yaw=yaw
            ),
            battery_level=1.0,
            warnings=[],
            state_code=self.is_moving,
            is_using_gripper=self.is_using_gripper,
            is_moving_arm=self.is_moving_arm,
            timestamp=stamp
        )
        self.ros_node.get_logger().info("robot status updated")

    def pose_callback(self, msg):
        self.current_pose = msg
        self.status_update()

    @staticmethod
    def pose_stamped_add_cov(pose: PoseStamped):
        result = PoseWithCovarianceStamped()
        result.header = pose.header
        result.pose.pose.position = pose.pose.position
        result.pose.pose.orientation = pose.pose.orientation
        return result

    def MoveToPosition(self, request, context):
        self.ros_node.get_logger().info(
            f"gRPC MoveToPosition received: x={request.position.x}, y={request.position.y}, roll={request.orientation.roll}, pitch={request.orientation.pitch}, yaw={request.orientation.yaw}"
        )

        msg = SetPose2D.Request()
        msg.data.x = request.position.x
        msg.data.y = request.position.y
        msg.data.roll = request.orientation.roll
        msg.data.pitch = request.orientation.pitch
        msg.data.yaw = request.orientation.yaw

        result = self.send_request(self.set_pose_client, msg)

        if result:  # 成功调用服务
            return robot_control_pb2.ControlResponse(
                code=robot_control_pb2.ControlResponse.SUCCESS,
                message="Move command sent successfully.",
                current_state=self.current_status,
                suggested_actions=[]
            )
        else:  # 服务调用失败
            return robot_control_pb2.ControlResponse(
                code=robot_control_pb2.ControlResponse.TIMEOUT,
                message="Failed to send move command.",
                current_state=self.current_status,
                suggested_actions=["Check navigation service", "Ensure robot is localized"]
            )

    def StreamMoveToPosition(self, request, context):
        self.ros_node.get_logger().info(
            f"gRPC StreamMoveToPosition received: x={request.position.x}, y={request.position.y}, roll={request.orientation.roll}, pitch={request.orientation.pitch}, yaw={request.orientation.yaw}"
        )
        self.reach_goal = False
        
        self.is_moving = robot_control_pb2.RobotState.MOVING
        self.ros_node.get_logger().info("before status_update")
        self.status_update()
        self.ros_node.get_logger().info("after status_update")
        
        # 取目标
        target_x = request.position.x
        target_y = request.position.y
        target_z = request.position.z if hasattr(request.position, 'z') else 0.0
        tgt_ori = request.orientation
        tol_pos = request.tolerance if hasattr(request, 'tolerance') else 0.01
        tol_ori = request.orientation_tolerance if hasattr(request, 'orientation_tolerance') else 0.01

        # 1) 发送一次移动指令
        msg = SetPose2D.Request()
        msg.data.x = target_x
        msg.data.y = target_y
        msg.data.roll = tgt_ori.roll
        msg.data.pitch = tgt_ori.pitch
        msg.data.yaw = tgt_ori.yaw
        self.ros_node.get_logger().info("StreamMoveToPosition is sending sync request to set_pose client")
        result = self.send_request(self.set_pose_client, msg)
        self.ros_node.get_logger().info(f"received result from set_pose client: {result}")
        # if not result:
        #     context.set_code(grpc.StatusCode.DEADLINE_EXCEEDED)
        #     context.set_details("Failed to call SetPose2D service")
        #     return
        
        # 2) 持续流状态
        while not self.reach_goal:
            if not context.is_active() or self.unreach_goal:
                break
            self.status_update()
            yield self.current_status
            self.ros_node.get_logger().info("yielding current status...")
            
            time.sleep(0.1)
        
        # self.position_calculation()
        # if self.current_pose.pose.pose.position.x != target_x and self.current_pose.pose.pose.position.y != target_y :
        #     self.reach_goal = False
        #     self.send_request(self.set_pose_client, msg)
        #     while not self.reach_goal:
        #         if not context.is_active():
        #             break
        #         self.position_calculation()
        #         yield self.current_status
                
        #         time.sleep(0.1)
        
        self.is_moving = robot_control_pb2.RobotState.IDLE
        self.status_update()
        
        if self.unreach_goal:
            self.unreach_goal = False
            self.is_moving = robot_control_pb2.RobotState.EMERGE_STOP
            self.status_update()
            self.current_status.warnings.append("Failed to reach the target position.")
        yield self.current_status
        return
    
    def StreamMove(self, request, context): 
        self.ros_node.get_logger().info(
            f"gRPC Stream Move Direction received: {request.direction},{request.distance}"
        )
        self.is_moving = robot_control_pb2.RobotState.MOVING
        self.status_update()
        self.is_moving_target_distance = True
        self.target_distance = request.distance/100

        machine_type = os.environ['MACHINE_TYPE']
        twist = Twist()
        if request.direction == robot_control_pb2.RobotDirection.FORWARD:
            self.ros_node.get_logger().info("forward")
            twist.linear.x = 0.1
        elif request.direction == robot_control_pb2.RobotDirection.BACKWARD:
            self.ros_node.get_logger().info("backward")
            twist.linear.x = -0.1
        elif request.direction == robot_control_pb2.RobotDirection.FORWARD_LEFT:
            self.ros_node.get_logger().info("forward left")
            twist.angular.z = 0.1
            twist.linear.x = 0.1
        elif request.direction == robot_control_pb2.RobotDirection.FORWARD_RIGHT:
            self.ros_node.get_logger().info("forward right")
            twist.angular.z = -0.1
            twist.linear.x = 0.1
        elif request.direction == robot_control_pb2.RobotDirection.BACKWARD_LEFT:
            self.ros_node.get_logger().info("backward left")
            if machine_type == 'JetRover_Mecanum':
                twist.angular.z = -0.1
            else:
                twist.angular.z = 0.1
            twist.linear.x = -0.1
        elif request.direction == robot_control_pb2.RobotDirection.BACKWARD_RIGHT:
            self.ros_node.get_logger().info("backward right")
            if machine_type == 'JetRover_Mecanum':
                twist.angular.z = 0.1
            else:
                twist.angular.z = -0.1
            twist.linear.x = -0.1
        self.cmd_vel_pub.publish(twist)
        while self.is_moving_target_distance:
            self.status_update()
            yield self.current_status

            time.sleep(0.1)
        self.is_moving = robot_control_pb2.RobotState.IDLE
        self.status_update()
        yield self.current_status
        return


    def GetCurrentPosition(self, request, context):
        if self.current_pose is None:
            self.ros_node.get_logger().warn("No current pose available yet.")
            return robot_control_pb2.ControlResponse(
                code=robot_control_pb2.ControlResponse.TIMEOUT,
                message="Robot position not available yet.",
                current_state=robot_control_pb2.RobotState(),  # 空状态
                suggested_actions=[
                    "Check if localization system (AMCL) is active",
                    "Ensure robot has moved or received sensor data"
                ]
            )

        return robot_control_pb2.ControlResponse(
            code=robot_control_pb2.ControlResponse.SUCCESS,
            message="Get current position successfully.",
            current_state=self.current_status,
            suggested_actions=[]
        )

    def EmergencyStop(self, request, context):
        self.ros_node.get_logger().info("[gRPC] EmergencyStop request received.")

        stop_req = Trigger.Request()

        result = self.send_request(self.stop_client, stop_req)

        if result is not None:
            # 注意，紧急停止操作下，无论 result 是否成功，nav controller 都应该确保机器停止
            if result.success:
                self.ros_node.get_logger().info("Navigation stopped successfully.")
                return robot_control_pb2.ControlResponse(
                    code=robot_control_pb2.ControlResponse.EMERGENCY_STOP,
                    message="Emergency stop executed successfully.",
                    current_state=self.current_status,
                    suggested_actions=[]
                )
            else:
                self.ros_node.get_logger().warn(f"Force stop: {result.message}")
                return robot_control_pb2.ControlResponse(
                    code=robot_control_pb2.ControlResponse.EMERGENCY_STOP,
                    message=f"Force stop with message: {result.message}",
                    current_state=self.current_status,
                    suggested_actions=[]
                )
        else:
            self.ros_node.get_logger().error("Failed to call stop service.")
            return robot_control_pb2.ControlResponse(
                code=robot_control_pb2.ControlResponse.TIMEOUT,
                message="Failed to call stop service.",
                current_state=self.current_status,
                suggested_actions=["Ensure ROS node is running", "Check if stop service is available"]
            )

    def pixel_to_camera(self, u: float, v: float, depth: float,
                        fx: float, fy: float, cx: float, cy: float) -> Tuple[float, float, float]:
        Z = depth/1000 #转换为米
        X = (u - cx) * Z / fx
        Y = (v - cy) * Z / fy
        return X, Y, Z

    def distance_to_center(self, u: int, v: int,
                        depth_image: np.ndarray,
                        intrinsic_matrix: np.ndarray) -> float:
        """
        计算像素 (u, v) 对应的三维点 P_A 与同深度下图像中心点 P_C 的欧氏距离
        depth_image: 深度图，单位米（或者你自己转换成米）
        intrinsic_matrix: 3×3 相机内参矩阵
        """
        # 从深度图里直接读取深度
        self.ros_node.get_logger().info("#############test1")
        Z = depth_image[v, u]      # 注意：depth_image 行对应 v，列对应 u
        self.ros_node.get_logger().info("#############test2")
        fx, fy = intrinsic_matrix[0,0], intrinsic_matrix[1,1]
        self.ros_node.get_logger().info("#############test3")
        cx, cy = intrinsic_matrix[0,2], intrinsic_matrix[1,2]
        self.ros_node.get_logger().info("#############test4")

        # 反投影得到物体 A 的相机坐标
        XA, YA, ZA = self.pixel_to_camera(u, v, Z, fx, fy, cx, cy)
        self.ros_node.get_logger().info("#############test5")
        P_A = np.array([XA, YA, ZA])
        self.ros_node.get_logger().info("#############test6")

        # 反投影图像中心 (cx, cy)
        Z = depth_image[int(self.image_height / 2), int(self.image_width / 2)]
        self.ros_node.get_logger().info("#############test7")
        Xc, Yc, Zc = self.pixel_to_camera(int(self.image_height / 2), int(self.image_width / 2), Z, fx, fy, cx, cy)
        self.ros_node.get_logger().info("#############test8")
        P_C = np.array([Xc, Yc, Zc])
        self.ros_node.get_logger().info("#############test9")

        # 计算两点距离
        return np.linalg.norm(P_A - P_C)

    
    def StreamPickUpObject(self, request, context):
        # self.is_moving_arm = True
        # is_using_local_msg = Bool()
        # is_using_local_msg.data = False
        # if request.x_min == 0 and request.y_min == 0 and request.x_max == 0 or request.y_max == 0:
        #     is_using_local_msg.data = True
        # else:
        #     object_center_x = int((request.x_min + request.x_max) / 2)
        #     object_center_y = int((request.y_min + request.y_max) / 2)
        #     self.ros_node.get_logger().info(f"start Pick up,x:{object_center_x}, y:{object_center_y}")
        #     self.target_distance = self.distance_to_center(object_center_x, object_center_y, self.depth_image, self.intrinsic_matrix)
        #     self.ros_node.get_logger().info(f"###################Pick up################### target distance: {self.target_distance} m")
        #     if self.target_distance > 0.03:
        #         self.target_distance = self.target_distance + 0.03 #移动补偿 
        #         self.is_moving = robot_control_pb2.RobotState.MOVING
        #         self.status_update()
        #         self.is_moving_target_distance = True
        #         machine_type = os.environ['MACHINE_TYPE']
        #         twist = Twist()
        #         if object_center_y>self.image_height/2:
        #             if object_center_x>self.image_width/2:
        #                 self.ros_node.get_logger().info("backward left")
        #                 if machine_type == 'JetRover_Mecanum':
        #                     twist.angular.z = -0.1
        #                 else:
        #                     twist.angular.z = 0.1
        #                 twist.linear.x = -0.1
        #             elif object_center_x<self.image_width/2:
        #                 self.ros_node.get_logger().info("backward right")
        #                 if machine_type == 'JetRover_Mecanum':
        #                     twist.angular.z = 0.1
        #                 else:
        #                     twist.angular.z = -0.1
        #                 twist.linear.x = -0.1
        #         else:
        #             if object_center_x>self.image_width/2:
        #                 self.ros_node.get_logger().info("forward left")
        #                 if machine_type == 'JetRover_Mecanum':
        #                     twist.angular.z = -0.1
        #                 else:
        #                     twist.angular.z = 0.1
        #                 twist.linear.x = 0.1
        #             elif object_center_x<self.image_width/2:
        #                 self.ros_node.get_logger().info("forward right")
        #                 if machine_type == 'JetRover_Mecanum':
        #                     twist.angular.z = 0.1
        #                 else:
        #                     twist.angular.z = -0.1
        #                 twist.linear.x = 0.1
        #         self.cmd_vel_pub.publish(twist)
        #         while self.is_moving_target_distance:
        #             if not context.is_active():
        #                 break
        #             yield self.current_status
        #             time.sleep(0.1)
                
        #         self.is_moving = robot_control_pb2.RobotState.IDLE
        
        # self.is_using_local_pub.publish(is_using_local_msg)
        
        # self.status_update()
        # msg = String()
        # msg.data = request.cmd
        # self.asr_result_pub.publish(msg)
        
        # while self.is_moving_arm:
        #     if not context.is_active():
        #         break
            
        #     yield self.current_status
        #     time.sleep(0.1)
        # self.status_update() 
        # yield self.current_status
        pass

    def StreamPlaceObject(self, request, context):
        # self.is_moving_arm = True
        # self.status_update()
        # msg = Bool()
        # msg.data = True
        # self.place_control_pub.publish(msg)
        
        # while self.is_moving_arm:
        #     if not context.is_active():
        #         break
           
        #     self.status_update()
        #     yield self.current_status
        #     time.sleep(0.1)
        
        # self.status_update()
        # yield self.current_status
        pass

    def StreamPickWithPosition(self, request, context):
        # self.is_moving_arm = True
        # self.status_update()
        # position = [request.x, request.y, request.z]
        # self.pick_with_position(position)
        
        # while self.is_moving_arm:
        #     if not context.is_active():
        #         break
            
        #     self.status_update()
        #     yield self.current_status
        #     time.sleep(0.1)
        # self.status_update() 
        # yield self.current_status
        pass

    def send_request(self, client, msg):
        self.ros_node.get_logger().info(f"send_request using client {client} with msg {msg}")
        future = client.call_async(msg)
        rclpy.spin_until_future_complete(self.ros_node, future)
        self.ros_node.get_logger().info(f"request future is done with {future.result()}")
        if not rclpy.ok():
            self.ros_node.get_logger().warn("ros eventloop is shutting down")
            return None
        return future.result()
    
    def odom_callback(self, msg: Odometry):
        self.current_velocity = msg.twist.twist
        
        if self.is_moving_target_distance:
            pos = msg.pose.pose.position
            if self.start_x is None or self.start_y is None:
                # 初始位置
                self.start_x = pos.x
                self.start_y = pos.y
                return

            # 计算与起始点的直线距离
            dx = pos.x - self.start_x
            dy = pos.y - self.start_y
            self.distance_traveled = math.sqrt(dx ** 2 + dy ** 2)

            self.ros_node.get_logger().info(f"Distance traveled: {self.distance_traveled:.3f} m")

            if self.is_moving and self.distance_traveled >= self.target_distance:
                self.stop_move()
                self.ros_node.get_logger().info("Target distance reached. Stopping robot.")
    
    def is_robot_moving(self):
        count = 0
        threshold = 0.01
        is_moving = False
        while count < 10:
            count = count + 1
            if self.current_velocity is None:
                time.sleep(0.1)
                continue
            linear = self.current_velocity.linear
            angular = self.current_velocity.angular
            linear_speed = (linear.x**2 + linear.y**2 + linear.z**2)**0.5
            angular_speed = (angular.x**2 + angular.y**2 + angular.z**2)**0.5
            is_moving = linear_speed > threshold or angular_speed > threshold

            if is_moving:
                break
            time.sleep(0.1)
        return is_moving
    
    def is_using_gripper_callback(self, msg):
        self.is_using_gripper = msg.data
        self.status_update()

    def is_moving_arm_callback(self, msg):
        self.is_moving_arm = msg.data
        self.status_update()
    
    def reach_goal_callback(self, msg):
        self.reach_goal = msg.data
        self.ros_node.get_logger().info(f"self reach goal :{self.reach_goal}")
        if not self.reach_goal:
            self.unreach_goal = True     
    def stop_move(self):
        twist = Twist()  
        self.cmd_vel_pub.publish(twist)
        self.is_moving_target_distance = False
        self.start_x = None
        self.start_y = None
    def pick_with_position(self, position):
        # # position[0] += 0.015
        # # position[2] += 0.02
        # position[1] += 0.004
        # if position[2] < 0.2:
        #     yaw = 80
        # else:
        #     yaw = 30
        # self.get_logger().info(f'position: {position}, yaw: {yaw}')
        # msg = set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
        # res = self.send_request(self.set_pose_target_client, msg)
        # if res.pulse:
        #     servo_data = res.pulse
        #     set_servo_position(self.joints_pub, 1, ((1, servo_data[0]), ))
        #     time.sleep(1)
        #     set_servo_position(self.joints_pub, 1.5, ((1, servo_data[0]),(2, servo_data[1]), (3, servo_data[2]),(4, servo_data[3]), (5, servo_data[4])))
        #     time.sleep(1.5)
        # set_servo_position(self.joints_pub, 0.5, ((10, 800),))
        # time.sleep(1)
        # position[2] += 0.01

        # msg = set_pose_target(position, yaw, [-180.0, 180.0], 1.0)
        # res = self.send_request(self.set_pose_target_client, msg)
        # if res.pulse:
        #     servo_data = res.pulse
        #     set_servo_position(self.joints_pub, 1, ((1, servo_data[0]),(2, servo_data[1]), (3, servo_data[2]),(4, servo_data[3]), (5, servo_data[4])))
        #     time.sleep(1)
        # set_servo_position(self.joints_pub, 1, ((1, 500), (2, 720), (3, 100), (4, 120), (5, 500), (10, 800)))
        # time.sleep(1)
        # self.is_moving_arm = False
        # self.is_using_gripper = True
        pass

    def depth_callback(self, msg: Image):
        try:
            self.depth_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as e:
            self.ros_node.get_logger().warn(f"[CameraService] Failed to convert depth image: {e}")
    
    def depth_info_callback(self, msg):
        self.intrinsic_matrix = np.array(msg.k).reshape(3, 3)

class RobotControlNode(Node):
    def __init__(self):
        super().__init__('agent_control_node')

        self.get_logger().info("Initializing RobotControlNode...")
        self.get_logger().info("Creating gRPC servers...")

        # 启动gRPC服务
        self.grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        robot_control_pb2_grpc.add_RobotControlServiceServicer_to_server(
            RobotControlServiceImpl(self),
            self.grpc_server
        )
        
        robot_control_pb2_grpc.add_CameraServiceServicer_to_server(
            CameraServiceImpl(self),
            self.grpc_server
        )

        self.get_logger().info("Adding gRPC insecure port...")
        self.grpc_server.add_insecure_port('[::]:50051')
        self.grpc_server.start()
        self.get_logger().info("\n############## gRPC server started on [::]:50051 ##############\n")

    def destroy_node(self):
        self.get_logger().info("Stopping gRPC server")
        self.grpc_server.stop(0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RobotControlNode()

    # executor = MultiThreadedExecutor()
    # executor.add_node(node)

    try:
        # executor.spin()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
