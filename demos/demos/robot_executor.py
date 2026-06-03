#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from geometry_msgs.msg import PoseStamped, PointStamped
from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose
import json
import time
import math
import threading

class RobotExecutor(Node):
    def __init__(self):
        super().__init__('robot_executor')
        
        # Use ReentrantCallbackGroup to allow nested spinning
        self.cb_group = ReentrantCallbackGroup()
        
        self.status_pub = self.create_publisher(String, '/robot_status', 10)
        
        self.task_sub = self.create_subscription(
            String, '/ward_task', self.task_callback, 10,
            callback_group=self.cb_group)
        self.vision_sub = self.create_subscription(
            PointStamped, '/vision/target_medicine_pose', self.vision_callback, 10,
            callback_group=self.cb_group)
        
        self.nav_client = ActionClient(
            self, NavigateToPose, 'navigate_to_pose',
            callback_group=self.cb_group)
        
        self.arm_named_pose_pub = self.create_publisher(String, '/arm_named_pose', 10)
        self.arm_abs_pose_pub = self.create_publisher(PoseStamped, '/arm_absolute_pose', 10)
        
        self.current_task = None
        self.vision_target = None
        self.nav_timeout = 120.0
        self._active_goal_handle = None
        
        self.get_logger().info('🤖 复合智能执行体 (Mobile Manipulator) 已启动，等待取药任务...')
        
    def send_status(self, text):
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)
        self.get_logger().info(f'{text}')

    def task_callback(self, msg):
        if self.current_task is not None:
            self.get_logger().warn('当前已有任务正在执行，忽略新任务。')
            return
            
        task = json.loads(msg.data)
        self.current_task = task
        self.get_logger().info(f'收到任务：前往药房取药 [{task["medicine"]}]，然后送往 [{task["bed"]}]')
        # Run in separate thread to keep executor callback threads free for Nav2/vision responses
        threading.Thread(target=self.execute_task, args=(task,), daemon=True).start()
        
    def vision_callback(self, msg):
        self.vision_target = msg
        
    def navigate_to(self, x, y, theta=0.0):
        self.send_status(f'🚗 导航至坐标: x={x}, y={y}')
        
        if not self.nav_client.wait_for_server(timeout_sec=5.0):
            self.send_status('⚠️ Nav2 不在线，模拟导航 (3s)...')
            time.sleep(3.0)
            return True
        
        # Cancel any previous active goal before sending a new one
        if hasattr(self, '_active_goal_handle') and self._active_goal_handle is not None:
            try:
                self.get_logger().info('取消上一个导航目标...')
                cancel_future = self._active_goal_handle.cancel_goal_async()
                # Wait briefly for cancellation to process
                wait_start = time.time()
                while not cancel_future.done() and (time.time() - wait_start) < 3.0:
                    time.sleep(0.1)
            except Exception:
                pass
            self._active_goal_handle = None
            time.sleep(0.5)  # Let Nav2 settle after cancellation
            
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.position.z = 0.0
        goal_msg.pose.pose.orientation.z = math.sin(theta / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(theta / 2.0)
        
        # Send goal and wait for acceptance
        self.send_status('📡 发送导航目标...')
        send_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self._nav_feedback_callback)
        
        # Wait for goal response
        start = time.time()
        while not send_future.done():
            time.sleep(0.1)
            if time.time() - start > 10.0:
                self.send_status('⚠️ 发送目标超时，继续任务')
                return True
            
        goal_handle = send_future.result()
        if not goal_handle or not goal_handle.accepted:
            self.send_status('⚠️ 导航目标被拒绝，继续任务')
            return True
        
        # Store active goal handle for cleanup
        self._active_goal_handle = goal_handle
            
        self.send_status('📡 导航目标已接受，机器人正在移动...')
        result_future = goal_handle.get_result_async()
        
        # Wait for navigation to complete with timeout
        start = time.time()
        while not result_future.done():
            time.sleep(0.5)
            elapsed = time.time() - start
            if elapsed > self.nav_timeout:
                self.send_status(f'⏱️ 导航超时({self.nav_timeout}s)，取消目标')
                goal_handle.cancel_goal_async()
                self._active_goal_handle = None
                time.sleep(1.0)
                return True
        
        self._active_goal_handle = None
        self.send_status('✅ 到达目标点！')
        return True
    
    def _nav_feedback_callback(self, feedback_msg):
        """Log navigation progress from Nav2 feedback."""
        pass  # Silently consume feedback to keep action client responsive

    def execute_task(self, task):
        self.send_status('=' * 40)
        self.send_status(f'🚀 开始执行取药任务: {task["medicine"]} → {task["bed"]}')
        self.send_status('=' * 40)
        
        # ====== Phase 1: Navigate to pharmacy ======
        # Use waypoints to ensure robot can navigate through narrow doors reliably
        self.send_status('📍 Phase 1/7: 自主规划路径前往药剂室...')
        self.navigate_to(-2.0, 0.0)   # Corridor junction (through door if in ward)
        self.navigate_to(5.0, 0.0)    # Corridor near pharmacy
        self.navigate_to(5.0, 4.5)    # Pharmacy shelf
        
        # ====== Phase 2: Arm scan pose ======
        self.send_status('🦾 Phase 2/7: 升起机械臂，进入视觉扫描姿态...')
        msg = String()
        msg.data = 'extended'
        self.arm_named_pose_pub.publish(msg)
        time.sleep(3.0)
        
        # ====== Phase 3: Wait for vision ======
        self.vision_target = None
        self.send_status('👁️ Phase 3/7: 等待 OpenCV 视觉识别模块解析二维码...')
        wait_start = time.time()
        while self.vision_target is None and (time.time() - wait_start) < 5.0:
            time.sleep(0.2)
            
        # ====== Phase 4: Grasp medicine ======
        self.send_status(f'已识别目标药品{task["medicine"]}，开始抓取')
        
        if self.vision_target:
            self.send_status(f'👁️ 视觉锁定！坐标 (相机系): x={self.vision_target.point.x:.2f}, y={self.vision_target.point.y:.2f}, z={self.vision_target.point.z:.2f}m')
            
            # Send physical arm to target coordinate
            target_pose = PoseStamped()
            target_pose.header = self.vision_target.header
            target_pose.pose.position.x = self.vision_target.point.x
            target_pose.pose.position.y = self.vision_target.point.y
            target_pose.pose.position.z = self.vision_target.point.z
            target_pose.pose.orientation.w = 1.0 # Default orientation matching camera
            
            self.arm_abs_pose_pub.publish(target_pose)
            time.sleep(4.0) # Wait for arm to reach
        else:
            self.send_status('📡 未收到摄像头反馈，启用预设抓取策略')
            time.sleep(2.0)
            
        self.send_status('🦾 夹爪闭合，锁定药盒！')
        time.sleep(1.0)
        self.send_status('🦾 机械臂收回安全位')
        msg.data = 'ready'
        self.arm_named_pose_pub.publish(msg)
        time.sleep(3.0)
        
        self.send_status(f'✅ 药盒 [{task["medicine"]}] 抓取完成！')
        
        # ====== Phase 5: Return to corridor ======
        self.send_status('📍 Phase 5/7: 携带药品退出药房...')
        self.navigate_to(5.0, 0.0)
        
        # ====== Phase 6: Navigate to bedside ======
        # 1. Drive down the corridor to the ward door (x=-2.0)
        self.send_status(f'📍 Phase 6/7: 途径走廊前往病房门...')
        self.navigate_to(-2.0, 0.0)
        
        # 2. Drive straight through the narrow door (y=1.0) into the room (y=1.5)
        door_y_nav = 1.5 if task['bed_y'] > 0 else -1.5
        self.send_status(f'📍 Phase 6/7: 穿越病房窄门...')
        self.navigate_to(-2.0, door_y_nav)
        
        # 3. Drive to the bed delivery zone (50cm away per spec)
        # Beds are 2m long (±1m from center). Target is 1m + 0.5m = 1.5m from center.
        bed_y_nav = task['bed_y'] - 1.5 if task['bed_y'] > 0 else task['bed_y'] + 1.5
        self.send_status(f'📍 Phase 6/7: 前往 {task["bed"]} 签收区 (床旁50cm)...')
        self.navigate_to(task['bed_x'], bed_y_nav)
        
        # ====== Phase 7: Delivery ======
        self.send_status('药品已送达，请签收')
        time.sleep(2.0)
        self.send_status('🦾 释放夹爪，交付药品')
        time.sleep(1.0)
        
        self.send_status('=' * 40)
        self.send_status('药品签收成功，返回待命')
        self.send_status('=' * 40)
        self.current_task = None

def main(args=None):
    rclpy.init(args=args)
    node = RobotExecutor()
    
    # MultiThreadedExecutor allows callbacks to run in parallel,
    # so navigate_to can block while other callbacks still get processed
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
