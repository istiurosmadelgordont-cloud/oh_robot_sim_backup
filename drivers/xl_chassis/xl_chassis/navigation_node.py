import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped, Point, Quaternion
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import threading
import time
import math
from typing import Optional

from datetime import datetime
import os
import json

# 导入底盘控制类
from .chassis import Chassis
from .objects import NavStatusResponse

class NavigateToPoseActionServer(Node):
    def __init__(self):
        super().__init__('navigate_to_pose_action_server')
        
        self.callback_group = ReentrantCallbackGroup()
        
        self.chassis = Chassis()
        
        self._action_server = ActionServer(
            self,
            NavigateToPose,
            'navigate_to_pose',
            execute_callback=self.execute_callback,
            # goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self.callback_group
        )
        
        self.is_navigating: bool = False
        self.navigation_goal_handle: ServerGoalHandle | None = None
        self.navigation_thread: threading.Thread | None = None
        self.navigation_cancel_requested: bool = False
        
        self.get_logger().info('NavigateToPose Action Server is ready')
    
    # def goal_callback(self, goal_request: NavigateToPose.Goal) -> GoalResponse:
    #     """
    #     Called when a new goal is requested.
        
    #     Args:
    #         goal_request (NavigateToPose.Goal): The goal request containing:
    #             - pose (geometry_msgs/PoseStamped): Target pose to navigate to
    #             - behavior_tree (string): Optional behavior tree to use
        
    #     Returns:
    #         GoalResponse: Either GoalResponse.ACCEPT or GoalResponse.REJECT
    #     """
    #     self.get_logger().info('Received goal request')
        
    #     # TODO: Add goal validation logic here
    #     # Example: Check if pose is valid, within bounds, etc.
        
    #     return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle: ServerGoalHandle) -> CancelResponse:
        """
        Called when a goal cancellation is requested.
        
        Args:
            goal_handle (ServerGoalHandle): The goal handle for the goal to be canceled
                Properties:
                - goal_id (unique_identifier_msgs/UUID): Unique identifier for the goal
                - request (NavigateToPose.Goal): The original goal request
                - status: Current status of the goal
        
        Returns:
            CancelResponse: Either CancelResponse.ACCEPT or CancelResponse.REJECT
        """
        self.get_logger().info('Received cancel request')
        self.navigation_cancel_requested = True
        return CancelResponse.ACCEPT

    def execute_callback(self, goal_handle: ServerGoalHandle) -> NavigateToPose.Result:
        """
        Main execution callback for the action server.
        
        Args:
            goal_handle (ServerGoalHandle): The goal handle containing:
                - request (NavigateToPose.Goal): The goal request with:
                    * pose (geometry_msgs/PoseStamped): Target pose
                    * behavior_tree (string): Optional BT
                - goal_id (unique_identifier_msgs/UUID): Unique goal identifier
                
                Methods:
                - publish_feedback(feedback_msg): Publish feedback
                - succeed(): Mark goal as succeeded
                - abort(): Mark goal as aborted
                - canceled(): Mark goal as canceled
                - is_active: Check if goal is still active
                - is_cancel_requested: Check if cancellation was requested
        
        Returns:
            NavigateToPose.Result: The result containing:
                - (Empty for NavigateToPose, but structure is available)
        """
        try:
            # 获取当前时间戳
            timestamp = datetime.now().isoformat()

            # 提取目标位姿数据
            target_pose = goal_handle.request.pose.pose
            target_x = target_pose.position.x
            target_y = target_pose.position.y
            target_z = target_pose.position.z

            # 从四元数获取偏航角
            q = target_pose.orientation
            target_yaw = self.quaternion_to_yaw(q)

            # 构建记录数据
            log_data = {
                "timestamp": timestamp,
                "goal": {
                    "x": target_x,
                    "y": target_y,
                    "z": target_z,
                    "yaw": target_yaw,
                    "quaternion": {
                        "x": q.x,
                        "y": q.y,
                        "z": q.z,
                        "w": q.w
                    }
                }
            }

            # 确保日志目录存在
            log_dir = os.path.expanduser("~/navigation_logs")
            os.makedirs(log_dir, exist_ok=True)

            # 写入日志文件（追加模式）
            log_file = os.path.join(log_dir, "navigate_to_pose_calls.jsonl")
            with open(log_file, "a") as f:
                f.write(json.dumps(log_data) + "\n")

            self.get_logger().info(f'Navigation call logged to {log_file}')

        except Exception as e:
            self.get_logger().warning(f'Failed to log navigation call: {str(e)}')

        self.get_logger().info('Received navigation goal')
        
        # 保存当前 goal handle
        self.navigation_goal_handle = goal_handle
        self.navigation_cancel_requested = False
        self.is_navigating = True
        
        # 获取目标位姿
        target_pose = goal_handle.request.pose.pose
        target_x = target_pose.position.x
        target_y = target_pose.position.y
        
        # 从四元数获取偏航角
        q = target_pose.orientation
        target_theta = self.quaternion_to_yaw(q)
        
        self.get_logger().info(f'Navigating to: x={target_x}, y={target_y}, theta={target_theta}')
        
        try:
            # 发送导航命令到底盘
            success = self.chassis.navigate_to_pose(target_x, target_y, target_theta)
            
            if not success:
                goal_handle.abort()
                result = NavigateToPose.Result()
                return result
            
            # 创建并启动导航状态监控线程
            self.navigation_thread = threading.Thread(
                target=self.monitor_navigation_status,
                args=(goal_handle, target_x, target_y, target_theta)
            )
            self.navigation_thread.start()
            
            # 等待导航完成
            while self.is_navigating and rclpy.ok():
                time.sleep(0.1)
                
            # 等待监控线程完成
            if self.navigation_thread and self.navigation_thread.is_alive():
                self.navigation_thread.join()
                
            # 准备结果
            result = NavigateToPose.Result()
            
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('Navigation canceled')
            elif hasattr(self, 'navigation_succeeded') and self.navigation_succeeded:
                goal_handle.succeed()
                self.get_logger().info('Navigation succeeded')
            else:
                goal_handle.abort()
                self.get_logger().info('Navigation failed')
                
            return result
            
        except Exception as e:
            self.get_logger().error(f'Navigation error: {str(e)}')
            goal_handle.abort()
            result = NavigateToPose.Result()
            return result
        finally:
            self.is_navigating = False
            self.navigation_goal_handle = None

    # def monitor_navigation_status(self, goal_handle, target_x, target_y):
    #     """监控导航状态并在需要时提供反馈"""
    #     last_update_time = time.time()
    #     last_distance = float('inf')
        
    #     try:
    #         while self.is_navigating and not self.navigation_cancel_requested and rclpy.ok():
    #             # 获取导航状态
    #             nav_status = self.chassis.get_navigation_status()
    #             current_time = time.time()
                
    #             # 检查导航状态
    #             res = nav_status.get('res', -1)
    #             reason = nav_status.get('reason', -1)
    #             dist = nav_status.get('dist', -1)
                
    #             # 创建反馈
    #             feedback = NavigateToPose.Feedback()
                
    #             # 设置当前位姿（可选，如果底盘API提供）
    #             try:
    #                 current_pose = self.chassis.get_pos()
    #                 feedback.current_pose = PoseStamped()
    #                 feedback.current_pose.header.stamp = self.get_clock().now().to_msg()
    #                 feedback.current_pose.header.frame_id = 'map'
    #                 feedback.current_pose.pose.position = Point(x=current_pose[0], y=current_pose[1], z=0.0)
    #                 feedback.current_pose.pose.orientation = self.yaw_to_quaternion(current_pose[2])
    #             except:
    #                 pass
                
    #             # 设置距离目标的距离
    #             feedback.distance_remaining = dist
                
    #             # 发布反馈（每秒最多10次）
    #             if current_time - last_update_time > 0.1:
    #                 goal_handle.publish_feedback(feedback)
    #                 last_update_time = current_time
                
    #             # 检查导航是否完成
    #             if res == 3:  # 导航阶段
    #                 if reason == 0:  # 导航成功
    #                     self.navigation_succeeded = True
    #                     self.is_navigating = False
    #                     break
    #                 elif reason == 1:  # 导航失败
    #                     self.navigation_succeeded = False
    #                     self.is_navigating = False
    #                     break
    #             elif res == 6:
    #                 # 检查特殊失败原因
    #                 if reason in [2, 4, 5, 6, 7, 8, 9]:  # 各种失败情况
    #                     self.navigation_succeeded = False
    #                     self.is_navigating = False
    #                     break
                
    #             # 检查是否需要取消
    #             if self.navigation_cancel_requested:
    #                 self.chassis.cancel_navigation()
    #                 self.navigation_succeeded = False
    #                 self.is_navigating = False
    #                 break
                
    #             # 超时检查（如果长时间没有进展）
    #             if dist > 0 and abs(dist - last_distance) < 0.01 and current_time - last_update_time > 30.0:
    #                 self.get_logger().warning('Navigation appears to be stuck, canceling')
    #                 self.chassis.cancel_navigation()
    #                 self.navigation_succeeded = False
    #                 self.is_navigating = False
    #                 break
                
    #             last_distance = dist
    #             time.sleep(0.2)  # 降低轮询频率以减少负载
                
    #     except Exception as e:
    #         self.get_logger().error(f'Error monitoring navigation: {str(e)}')
    #         self.navigation_succeeded = False
    #         self.is_navigating = False
    def monitor_navigation_status(self, goal_handle, target_x, target_y, target_theta):
        """监控导航状态，通过检查当前位姿与目标位姿的差异以及移动进度"""
        
        last_update_time = time.time()
        last_position = None
        last_moved_distance = 0.0
        stagnant_start_time = None
        last_progress_time = time.time()
        
        # 配置参数
        DISTANCE_THRESHOLD = 0.5    # 位置误差阈值 (米)
        ANGLE_THRESHOLD = 0.1       # 角度误差阈值 (弧度)
        STAGNANT_TIME_THRESHOLD = 60.0  # 停滞判定时间 (秒)
        STAGNANT_DISTANCE_THRESHOLD = 1.0  # 停滞判定移动距离 (米)
        MAX_NAVIGATION_TIME = 1200.0  # 最大导航时间 (秒)
        
        navigation_start_time = time.time()
        self.navigation_succeeded = False  # 初始化结果状态
        
        try:
            while self.is_navigating and not self.navigation_cancel_requested and rclpy.ok():
                current_time = time.time()
                
                # 检查总超时
                if current_time - navigation_start_time > MAX_NAVIGATION_TIME:
                    self.get_logger().warning(f'Navigation timed out after {MAX_NAVIGATION_TIME} seconds')
                    self.navigation_succeeded = False
                    self.is_navigating = False
                    break
                
                # 获取当前位置
                try:
                    current_pose = self.chassis.get_pos()
                    current_x, current_y, current_theta = current_pose
                except Exception as e:
                    self.get_logger().warning(f'Failed to get current position: {str(e)}')
                    time.sleep(0.2)
                    continue
                    
                # 计算到目标的距离
                dx = target_x - current_x
                dy = target_y - current_y
                distance_to_goal = math.sqrt(dx*dx + dy*dy)
                
                # 计算角度差（考虑圆周性）
                angle_diff = self.normalize_angle(target_theta - current_theta)
                
                # 创建并发布反馈
                self.publish_navigation_feedback(goal_handle, current_x, current_y, current_theta, distance_to_goal)
                
                # 检查是否到达目标
                if distance_to_goal < DISTANCE_THRESHOLD and abs(angle_diff) < ANGLE_THRESHOLD:
                    self.get_logger().info(f'Navigation succeeded: distance={distance_to_goal:.2f}m, angle_diff={angle_diff:.2f}rad')
                    self.navigation_succeeded = True
                    self.is_navigating = False
                    break
                
                # 检查停滞情况
                if last_position is not None:
                    last_x, last_y, _ = last_position
                    moved_distance = math.sqrt((current_x - last_x)**2 + (current_y - last_y)**2)
                    last_moved_distance += moved_distance
                    
                    # 检查是否在停滞时间内移动足够距离
                    if current_time - last_progress_time > STAGNANT_TIME_THRESHOLD:
                        if last_moved_distance < STAGNANT_DISTANCE_THRESHOLD:
                            self.get_logger().warning(
                                f'Navigation stagnant: only moved {last_moved_distance:.2f}m '
                                f'in last {STAGNANT_TIME_THRESHOLD} seconds'
                            )
                            self.navigation_succeeded = False
                            self.is_navigating = False
                            break
                        else:
                            # 有足够进展，重置计时器和距离
                            last_progress_time = current_time
                            last_moved_distance = 0.0
                
                # 更新上次位置
                last_position = (current_x, current_y, current_theta)
                
                # 检查是否需要取消
                if self.navigation_cancel_requested:
                    try:
                        self.chassis.cancel_navigation()
                        self.get_logger().info('Navigation canceled by request')
                    except Exception as e:
                        self.get_logger().warning(f'Failed to cancel navigation: {str(e)}')
                    self.navigation_succeeded = False
                    self.is_navigating = False
                    break
                    
                time.sleep(0.2)  # 降低轮询频率以减少负载
                
        except Exception as e:
            self.get_logger().error(f'Error monitoring navigation: {str(e)}')
            self.navigation_succeeded = False
            self.is_navigating = False
        
        # 确保在退出时设置状态
        if self.navigation_succeeded is None:
            self.navigation_succeeded = False

    def normalize_angle(self, angle):
        """将角度规范化到[-pi, pi]范围内"""
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def publish_navigation_feedback(self, goal_handle, x, y, theta, distance_to_goal):
        """发布导航反馈信息"""
        feedback = NavigateToPose.Feedback()
        
        # 设置当前位姿
        feedback.current_pose = PoseStamped()
        feedback.current_pose.header.stamp = self.get_clock().now().to_msg()
        feedback.current_pose.header.frame_id = 'map'
        feedback.current_pose.pose.position = Point(x=x, y=y, z=0.0)
        feedback.current_pose.pose.orientation = self.yaw_to_quaternion(theta)
        
        # 设置距离目标的距离
        feedback.distance_remaining = distance_to_goal
        
        # 发布反馈
        goal_handle.publish_feedback(feedback)

    def quaternion_to_yaw(self, q: Quaternion) -> float:
        """将四元数转换为偏航角（弧度）"""
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def yaw_to_quaternion(self, yaw: float) -> Quaternion:
        """将偏航角（弧度）转换为四元数"""
        q = Quaternion()
        q.w = math.cos(yaw / 2)
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw / 2)
        return q

def main(args=None):
    rclpy.init(args=args)
    
    # 创建节点
    node = NavigateToPoseActionServer()
    
    # 使用多线程执行器
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        # 保持节点运行
        executor.spin()
    finally:
        # 清理
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()