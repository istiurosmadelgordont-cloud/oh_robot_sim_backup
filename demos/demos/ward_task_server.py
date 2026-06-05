#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
from std_msgs.msg import String
import threading
import sys
import json
import time

class WardTaskServer(Node):
    def __init__(self):
        super().__init__('ward_task_server')
        
        # Publisher for virtual PDA position
        self.pda_pub = self.create_publisher(Point, '/virtual_pda_position', 10)
        
        # Publisher for task dispatch
        self.task_pub = self.create_publisher(String, '/ward_task', 10)
        
        # Subscriber for robot status
        self.status_sub = self.create_subscription(
            String,
            '/robot_status',
            self.robot_status_callback,
            10
        )
        
        # Subscriber for PDA commands (from UI)
        self.cmd_sub = self.create_subscription(
            String,
            '/pda_command',
            self.pda_command_callback,
            10
        )
        
        # Coordinates from hospital_ward.classic.world
        # bed_w1_* are at y=3.9 (north ward), bed_w2_* at y=-3.9 (south ward)
        self.screens = {
            '1': ('Bed_W1_1', -4.85, 3.9),
            '2': ('Bed_W1_2', -2.95, 3.9),
            '3': ('Bed_W1_3', -1.05, 3.9),
            '4': ('Bed_W1_4',  0.85, 3.9),
            '5': ('Bed_W2_1', -4.85, -3.9),
            '6': ('Bed_W2_2', -2.95, -3.9),
            '7': ('Bed_W2_3', -1.05, -3.9),
            '8': ('Bed_W2_4',  0.85, -3.9),
        }
        
        self.medical_orders = {
            'Bed_W1_1': {'patient': '张三', 'medicine': '阿司匹林', 'qr_code': 'QR001'},
            'Bed_W1_2': {'patient': '李四', 'medicine': '布洛芬', 'qr_code': 'QR002'},
        }
        
        # Initial PDA position (Far away)
        self.current_pda_pos = Point(x=-10.0, y=-10.0, z=0.0)
        
        # Publish PDA pos periodically
        self.timer = self.create_timer(0.5, self.publish_pda_pos)
        
        self.get_logger().info('=============================================')
        self.get_logger().info('🏥 智慧康养数字病房 - 远程服务器节点已启动')
        self.get_logger().info('=============================================')

    def publish_pda_pos(self):
        self.pda_pub.publish(self.current_pda_pos)
        
    def robot_status_callback(self, msg):
        self.get_logger().info(f'\n🤖 [智能执行体上报]: {msg.data}\n')

    def teleport_pda(self, bed_key):
        if bed_key == '0':
            self.current_pda_pos = Point(x=-10.0, y=-10.0, z=0.0)
            self.get_logger().info('\n🏃 护士已携带 PDA 离开病房区域 (距离 > 2m)')
            return
            
        if bed_key in self.screens:
            name, sx, sy = self.screens[bed_key]
            # Teleport PDA to corridor side of bed (0.4m offset toward center corridor y=0)
            pda_y = sy - 0.4 if sy > 0 else sy + 0.4
            self.current_pda_pos = Point(x=sx, y=pda_y, z=0.0)
            self.get_logger().info(f'\n🚶 护士已携带 PDA 靠近 {name} (距离 0.4m)')
            
            # Wait a bit to let softbus trigger
            time.sleep(1.0)
            
            order = self.medical_orders.get(name, {'patient': '未知', 'medicine': '常规生理盐水', 'qr_code': 'QR_DEFAULT'})
            self.get_logger().info(f'🔄 同步医嘱数据: 患者 [{order["patient"]}], 需求 [{order["medicine"]}]')
            
            # Dispatch task
            task_data = {
                'bed': name,
                'bed_x': sx + 0.75,
                'bed_y': sy,
                'medicine': order['medicine'],
                'qr_code': order['qr_code']
            }
            task_msg = String()
            task_msg.data = json.dumps(task_data)
            self.task_pub.publish(task_msg)
            self.get_logger().info(f'🚀 已将取药任务下发至智能执行体: 前往药房抓取 {order["medicine"]}')
        else:
            self.get_logger().info('无效的输入。')

    def pda_command_callback(self, msg):
        cmd = msg.data.strip()
        self.get_logger().info(f'📱 收到 UI 终端指令: {cmd}')
        if cmd in ['0', '1', '2', '3', '4', '5', '6', '7', '8']:
            self.teleport_pda(cmd)
        else:
            self.get_logger().warn(f'⚠️ 未知指令: {cmd}')

def input_thread(node):
    print("\n--- 虚拟 PDA 传送台 ---")
    print("按 1~8 传送 PDA 至对应病床 (1-4为病房1，5-8为病房2)")
    print("按 0 将 PDA 撤出病房 (触发断开连接)")
    print("输入 'q' 退出\n")
    
    while True:
        try:
            cmd = input("请输入操作指令: ").strip()
            if cmd == 'q':
                print("正在退出...")
                break
            if cmd in ['0', '1', '2', '3', '4', '5', '6', '7', '8']:
                node.teleport_pda(cmd)
            else:
                print("无效指令。")
        except EOFError:
            break

def main(args=None):
    rclpy.init(args=args)
    node = WardTaskServer()
    
    thread = threading.Thread(target=input_thread, args=(node,), daemon=True)
    thread.start()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
