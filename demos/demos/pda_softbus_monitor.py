#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

class PDASoftBusMonitor(Node):
    def __init__(self):
        super().__init__('pda_softbus_monitor')

        # 硬编码 8 个床头屏的绝对坐标 (x, y)
        self.screens = {
            'Bed_W1_1': (-4.85, 4.85),
            'Bed_W1_2': (-2.95, 4.85),
            'Bed_W1_3': (-1.05, 4.85),
            'Bed_W1_4': ( 0.85, 4.85),
            'Bed_W2_1': (-4.85, -4.85),
            'Bed_W2_2': (-2.95, -4.85),
            'Bed_W2_3': (-1.05, -4.85),
            'Bed_W2_4': ( 0.85, -4.85),
        }

        # 滞回算法阈值
        self.CONNECT_DIST = 0.5    # 小于此距离触发无感鉴权
        self.DISCONNECT_DIST = 2.0 # 大于此距离触发界面跳回

        # 当前连接的设备状态
        self.connected_screen = None

        # PDA 的当前虚拟坐标
        self.pda_x = None
        self.pda_y = None

        # 订阅虚拟 PDA 坐标
        from geometry_msgs.msg import Point
        self.pda_sub = self.create_subscription(
            Point,
            '/virtual_pda_position',
            self.pda_position_callback,
            10
        )

        # 500ms 检查一次距离 (2Hz)
        self.timer = self.create_timer(0.5, self.check_distance_callback)
        self.get_logger().info('🟢 PDA 软总线模拟监控节点已启动，正在监听虚拟 PDA 坐标 (/virtual_pda_position) ...')

    def pda_position_callback(self, msg):
        self.pda_x = msg.x
        self.pda_y = msg.y

    def check_distance_callback(self):
        if self.pda_x is None or self.pda_y is None:
            # 如果尚未获取到PDA坐标，则静默等待
            return

        # 遍历所有屏幕，找到距离最近的一个
        closest_screen = None
        min_dist = float('inf')

        for name, (sx, sy) in self.screens.items():
            dist = math.hypot(self.pda_x - sx, self.pda_y - sy)
            if dist < min_dist:
                min_dist = dist
                closest_screen = name

        # ===== 核心：状态机与滞回判定 =====
        if self.connected_screen is None:
            # 当前无连接，若最近的屏幕在触发距离内，则建立连接
            if min_dist < self.CONNECT_DIST:
                self.connected_screen = closest_screen
                self.get_logger().info(
                    f'\n========================================\n'
                    f'🔗 [SoftBus] 自动发现设备！\n'
                    f'📱 PDA 靠近 {self.connected_screen} 床头屏 (距离: {min_dist:.2f}m)\n'
                    f'✅ 软总线无感身份鉴权完成！\n'
                    f'🔊 [语音播报]: "身份验证通过，可执行医嘱，并同步药品需求至智能执行体"\n'
                    f'========================================\n'
                )
        else:
            # 当前已有连接，计算当前机器人与【已连接屏幕】的距离
            sx, sy = self.screens[self.connected_screen]
            current_conn_dist = math.hypot(self.pda_x - sx, self.pda_y - sy)

            # 若距离大于断开阈值，则断开连接
            if current_conn_dist > self.DISCONNECT_DIST:
                self.get_logger().info(
                    f'\n----------------------------------------\n'
                    f'❌ [SoftBus] 离开通信范围！\n'
                    f'📱 PDA 已远离 {self.connected_screen} 床头屏 (距离: {current_conn_dist:.2f}m)\n'
                    f'🚫 软总线连接已断开，界面自动跳回床头卡界面。\n'
                    f'----------------------------------------\n'
                )
                self.connected_screen = None

def main(args=None):
    rclpy.init(args=args)
    node = PDASoftBusMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
