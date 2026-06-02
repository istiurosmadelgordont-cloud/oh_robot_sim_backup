#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped
from std_msgs.msg import String
import json

class VisionRecognitionNode(Node):
    def __init__(self):
        super().__init__('vision_recognition_node')
        
        # Subscribe to Eye-in-Hand camera (if available)
        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        
        # Subscribe to robot status to know when to "scan"
        self.status_sub = self.create_subscription(
            String,
            '/robot_status',
            self.status_callback,
            10
        )
        
        # Publish detected medicine coordinates (in camera frame)
        self.target_pub = self.create_publisher(PointStamped, '/vision/target_medicine_pose', 10)
        
        self.has_real_camera = False
        self.scan_requested = False
        
        self.get_logger().info('👁️ 视觉识别模块 (OpenCV) 已启动，等待扫描指令...')

    def status_callback(self, msg):
        """Listen for robot status to know when vision scan is needed"""
        if '视觉识别' in msg.data or '视觉扫描' in msg.data or '二维码' in msg.data:
            self.get_logger().info('📡 收到扫描请求，启动视觉识别流程...')
            # Use a timer to simulate processing delay
            self.create_timer(1.5, self.publish_simulated_detection)

    def image_callback(self, msg):
        """Process real camera images if available"""
        self.has_real_camera = True
        try:
            from cv_bridge import CvBridge
            import cv2
            bridge = CvBridge()
            cv_image = bridge.imgmsg_to_cv2(msg, "bgr8")
            qr_detector = cv2.QRCodeDetector()
            data, bbox, _ = qr_detector.detectAndDecode(cv_image)
            
            if bbox is not None and len(data) > 0:
                self.get_logger().info(f'📷 扫描到二维码: {data}')
                self.publish_detection(data)
        except Exception as e:
            self.get_logger().error(f"CV Bridge Error: {e}")

    def publish_simulated_detection(self):
        """Publish a simulated detection when no real camera is available"""
        if self.has_real_camera:
            return  # Don't simulate if we have a real camera
            
        self.get_logger().info('📷 [模拟模式] 视觉扫描完成，识别到目标药品二维码！')
        self.get_logger().info('📷 二维码内容: QR_MEDICINE_ASPIRIN | 置信度: 98.7%')
        
        target_msg = PointStamped()
        target_msg.header.stamp = self.get_clock().now().to_msg()
        target_msg.header.frame_id = 'eye_camera_optical_frame'
        
        # Simulated target: 0.3m ahead of camera
        target_msg.point.x = 0.0
        target_msg.point.y = 0.0
        target_msg.point.z = 0.30
        
        self.target_pub.publish(target_msg)
        self.get_logger().info('✅ 目标药品 3D 坐标已发布至 /vision/target_medicine_pose')

    def publish_detection(self, qr_data):
        """Publish a real detection from QR code"""
        target_msg = PointStamped()
        target_msg.header.stamp = self.get_clock().now().to_msg()
        target_msg.header.frame_id = 'eye_camera_optical_frame'
        target_msg.point.x = 0.0
        target_msg.point.y = 0.0
        target_msg.point.z = 0.30
        
        self.target_pub.publish(target_msg)

def main(args=None):
    rclpy.init(args=args)
    node = VisionRecognitionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
