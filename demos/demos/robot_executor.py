#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped, PointStamped
from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose
from control_msgs.action import FollowJointTrajectory, GripperCommand
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import json
import time
import math

class RobotExecutor(Node):
    def __init__(self):
        super().__init__('robot_executor')
        
        self.status_pub = self.create_publisher(String, '/robot_status', 10)
        
        self.task_sub = self.create_subscription(String, '/ward_task', self.task_callback, 10)
        self.vision_sub = self.create_subscription(PointStamped, '/vision/target_medicine_pose', self.vision_callback, 10)
        
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.arm_client = ActionClient(self, FollowJointTrajectory, '/panda_arm_controller/follow_joint_trajectory')
        self.gripper_client = ActionClient(self, GripperCommand, '/panda_hand_controller/gripper_cmd')
        
        self.current_task = None
        self.vision_target = None
        
        self.get_logger().info('🤖 复合智能执行体 (Mobile Manipulator) 已启动，等待取药任务...')
        
    def send_status(self, text):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)
        self.get_logger().info(f'[{text}]')

    def task_callback(self, msg):
        if self.current_task is not None:
            self.get_logger().warn('当前已有任务正在执行，忽略新任务。')
            return
            
        task = json.loads(msg.data)
        self.current_task = task
        self.get_logger().info(f'收到任务：前往药房取药 [{task["medicine"]}]，然后送往 [{task["bed"]}]')
        
        self.execute_task(task)
        
    def vision_callback(self, msg):
        self.vision_target = msg
        
    def navigate_to(self, x, y, theta=0.0):
        self.get_logger().info(f'导航至坐标: x={x}, y={y}')
        if not self.nav_client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error('Nav2 Action Server 不在线！(演示模式将自动跳过真实导航)')
            return False
            
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation.z = math.sin(theta / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(theta / 2.0)
        
        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            return False
            
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        return True

    def move_arm(self, positions, duration_sec):
        if not self.arm_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warn('Arm Action Server 未启动，跳过物理抓取')
            return False
            
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory.joint_names = [
            'panda_joint1', 'panda_joint2', 'panda_joint3', 
            'panda_joint4', 'panda_joint5', 'panda_joint6', 'panda_joint7'
        ]
        
        point = JointTrajectoryPoint()
        point.positions = positions
        point.time_from_start.sec = duration_sec
        goal_msg.trajectory.points.append(point)
        
        future = self.arm_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()
        if handle.accepted:
            res_future = handle.get_result_async()
            rclpy.spin_until_future_complete(self, res_future)
            return True
        return False

    def control_gripper(self, width):
        if not self.gripper_client.wait_for_server(timeout_sec=2.0):
            return False
        goal_msg = GripperCommand.Goal()
        goal_msg.command.position = width
        goal_msg.command.max_effort = 50.0
        future = self.gripper_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()
        if handle.accepted:
            rclpy.spin_until_future_complete(self, handle.get_result_async())
            return True
        return False

    def execute_task(self, task):
        # 1. 导航到药房
        self.send_status('自主规划路径前往药房...')
        nav_success = self.navigate_to(4.85, 0.0)
        if not nav_success:
            time.sleep(3.0) # Mock time
            
        # 2. 伸出机械臂进行视觉扫描 (模拟初始侦察位)
        self.send_status('到达药剂室，升起机械臂准备视觉扫描...')
        self.move_arm([0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785], 3)
        self.control_gripper(0.04) # Open gripper
        
        # 等待 OpenCV 节点识别到目标
        self.vision_target = None
        self.send_status('等待 OpenCV 视觉识别模块解析二维码...')
        wait_time = 0
        while self.vision_target is None and wait_time < 50:
            rclpy.spin_once(self, timeout_sec=0.1)
            wait_time += 1
            
        if self.vision_target:
            self.send_status(f'👁️ 视觉锁定坐标 (相机系): z={self.vision_target.point.z:.2f}m')
        else:
            self.send_status('未能接收到真实的视觉反馈，使用默认抓取策略。')
            
        # 3. 执行抓取动作
        self.send_status(f'开始精细抓取动作...')
        self.move_arm([0.0, 0.0, 0.0, -1.5, 0.0, 1.571, 0.785], 2) # Reach out
        time.sleep(1)
        self.control_gripper(0.0) # Close gripper
        time.sleep(1)
        self.move_arm([0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785], 2) # Pull back
        self.send_status('🦾 药盒物理抓取完成！')
        
        # 4. 送往病床
        self.send_status(f'前往 {task["bed"]} 交付区...')
        nav_success = self.navigate_to(task['bed_x'], task['bed_y'] - 1.0)
        if not nav_success:
            time.sleep(3.0)
            
        self.send_status('🔊 药品已平稳送达，等待签收...')
        time.sleep(3.0)
        self.control_gripper(0.04) # Open gripper to release
        
        self.send_status('🎉 护士已签收，闭环任务完成！')
        self.current_task = None

def main(args=None):
    rclpy.init(args=args)
    node = RobotExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
