#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped, Quaternion
import json
import time
import math
import subprocess
import os
from datetime import datetime
from typing import List, Dict

POST_SCRIPT_PATH = "/home/user/post_replay.sh"  # 写死的脚本路径

class NavigationReplayNode(Node):
    def __init__(self, log_file: str, initial_delay: float = 0.0, loop: bool = False):
        super().__init__('navigation_replay_node')
        self.log_file = log_file
        self.initial_delay = initial_delay
        self.loop = loop
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goals = self.load_navigation_log(log_file)
        
        if not self.goals:
            self.get_logger().error(f'No goals in {log_file}')
            rclpy.shutdown()
            return
            
        self.get_logger().info(f'Loaded {len(self.goals)} goals. Starting in {initial_delay}s...')
        time.sleep(initial_delay)
        self.replay_goals()

    def load_navigation_log(self, path: str) -> List[Dict]:
        if not os.path.exists(path):
            self.get_logger().error(f'Log not found: {path}')
            return []
        goals = []
        with open(path) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        goals.append({
                            'timestamp': datetime.fromisoformat(entry['timestamp']),
                            'goal': entry['goal']
                        })
                    except Exception as e:
                        self.get_logger().warning(f'Skip invalid line: {e}')
        return sorted(goals, key=lambda g: g['timestamp'])

    def replay_goals(self):
        if not self.goals:
            return
            
        time_origin = self.goals[0]['timestamp']
        total = len(self.goals)
        
        for i, entry in enumerate(self.goals):
            goal = entry['goal']
            delay = 0.0 if i == 0 else (entry['timestamp'] - self.goals[i-1]['timestamp']).total_seconds()
            
            if delay > 0:
                time.sleep(delay)
                
            self.get_logger().info(f'Executing goal {i+1}/{total}: ({goal["x"]:.2f}, {goal["y"]:.2f})')
            if not self.send_goal(goal):
                self.get_logger().warn(f'Goal {i+1} failed')
        
        # 仅在非循环模式下执行后处理脚本
        if not self.loop:
            self.execute_post_script()
        
        rclpy.shutdown()

    def send_goal(self, goal: Dict) -> bool:
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('Action server not ready')
            return False
            
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.pose.position.x = goal['x']
        goal_msg.pose.pose.position.y = goal['y']
        goal_msg.pose.pose.position.z = goal.get('z', 0.0)
        
        if 'quaternion' in goal:
            q = goal['quaternion']
            goal_msg.pose.pose.orientation = Quaternion(x=q['x'], y=q['y'], z=q['z'], w=q['w'])
        else:
            yaw = goal.get('yaw', 0.0)
            q = Quaternion()
            q.w = math.cos(yaw/2)
            q.z = math.sin(yaw/2)
            goal_msg.pose.pose.orientation = q
            
        future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if not future.result() or not future.result().accepted:
            return False
            
        result_future = future.result().get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=300.0)
        return result_future.result().status == 4  # SUCCEEDED

    def execute_post_script(self):
        if not os.path.exists(POST_SCRIPT_PATH):
            self.get_logger().warn(f'Post script not found: {POST_SCRIPT_PATH}')
            return
            
        self.get_logger().info(f'Executing post-replay script: {POST_SCRIPT_PATH}')
        try:
            result = subprocess.run(
                [POST_SCRIPT_PATH],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            if result.returncode == 0:
                self.get_logger().info('Post script succeeded')
            else:
                self.get_logger().error(f'Post script failed (code {result.returncode}):\n{result.stderr}')
        except subprocess.TimeoutExpired:
            self.get_logger().error('Post script timed out after 300 seconds')
        except Exception as e:
            self.get_logger().error(f'Error executing post script: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    
    # 简单参数解析（仅支持基本用法）
    import sys
    log_file = os.path.expanduser('~/navigation_logs/navigate_to_pose_calls.jsonl')
    delay = 0.0
    loop = False
    
    for i, arg in enumerate(sys.argv):
        if arg == '--log-file' and i + 1 < len(sys.argv):
            log_file = sys.argv[i + 1]
        elif arg == '--delay' and i + 1 < len(sys.argv):
            delay = float(sys.argv[i + 1])
        elif arg == '--loop':
            loop = True
    
    node = NavigationReplayNode(log_file, delay, loop)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Replay interrupted')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()