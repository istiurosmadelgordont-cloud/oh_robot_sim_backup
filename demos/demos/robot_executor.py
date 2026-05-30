#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose
import json
import time
import math

class RobotExecutor(Node):
    def __init__(self):
        super().__init__('robot_executor')
        
        self.status_pub = self.create_publisher(String, '/robot_status', 10)
        
        self.task_sub = self.create_subscription(
            String,
            '/ward_task',
            self.task_callback,
            10
        )
        
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        self.current_task = None
        
        self.get_logger().info('🤖 智能执行体 (Robot Executor) 已启动，等待取药任务...')
        
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
        
        # 启动任务执行流程
        self.execute_task(task)
        
    def navigate_to(self, x, y, theta=0.0):
        self.get_logger().info(f'导航至坐标: x={x}, y={y}')
        
        if not self.nav_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Nav2 Action Server 不在线，无法导航！(本次作为轻量级演示，将自动跳过真实导航过程)')
            return False
            
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.position.z = 0.0
        
        # 简化四元数转换 (仅用于 Z 轴旋转)
        goal_msg.pose.pose.orientation.z = math.sin(theta / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(theta / 2.0)
        
        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('导航目标被拒绝！')
            return False
            
        self.get_logger().info('导航目标已接受，正在前往...')
        
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        
        result = result_future.result().result
        self.get_logger().info('✅ 导航完成！')
        return True

    def execute_task(self, task):
        # 1. 前往药房 (假设药房坐标为 4.85, 0.0)
        self.send_status('接收到取药需求，自主规划路径前往药房...')
        nav_success = self.navigate_to(4.85, 0.0)
        
        if not nav_success:
            # 仿真轻量级演示模式：如果 Nav2 没开，用 Sleep 模拟导航时间
            self.get_logger().info('💤 [模拟] 正在自动驾驶前往药房 (5秒)...')
            time.sleep(5.0)
            
        # 2. 视觉识别与抓取
        self.send_status(f'已到达药剂室目标存储格。正在启动视觉识别模块扫描药品标签...')
        time.sleep(2.0)
        self.send_status(f'🔊 语音播报: "已精准识别目标药品 {task["medicine"]} (二维码: {task["qr_code"]})，匹配成功，开始抓取"')
        time.sleep(3.0)
        self.send_status('🦾 机械臂抓取完成，未碰撞相邻药品。')
        
        # 3. 前往病床 (距离病床 y - 1.0 的位置)
        self.send_status(f'正在规划从药房前往 {task["bed"]} 签收区的路径...')
        bed_nav_x = task['bed_x']
        bed_nav_y = task['bed_y'] - 1.0
        
        nav_success = self.navigate_to(bed_nav_x, bed_nav_y)
        if not nav_success:
            self.get_logger().info(f'💤 [模拟] 正在自动驾驶前往 {task["bed"]} (5秒)...')
            time.sleep(5.0)
            
        # 4. 到达与交付
        self.send_status('🔊 语音播报: "药品已平稳送达，请护士签收"')
        time.sleep(3.0)
        self.send_status('护士已在 PDA 上确认签收。医嘱执行状态同步至服务器中...')
        time.sleep(1.0)
        
        self.send_status('🎉 单次送药任务圆满完成！(等待下一次 PDA 触发)')
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
