#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped
import cv2
from cv_bridge import CvBridge

class VisionRecognitionNode(Node):
    def __init__(self):
        super().__init__('vision_recognition_node')
        
        self.bridge = CvBridge()
        self.qr_detector = cv2.QRCodeDetector()
        
        # Subscribe to Eye-in-Hand camera
        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            10
        )
        
        # Publish detected medicine coordinates (in camera frame)
        self.target_pub = self.create_publisher(PointStamped, '/vision/target_medicine_pose', 10)
        
        # Expected target QR code from the server
        self.target_qr = None
        self.get_logger().info('👁️ 视觉识别模块 (OpenCV) 已启动，等待摄像头画面...')

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            self.get_logger().error(f"CV Bridge Error: {e}")
            return
            
        data, bbox, straight_qrcode = self.qr_detector.detectAndDecode(cv_image)
        
        if bbox is not None and len(data) > 0:
            # We found a QR Code
            self.get_logger().info(f'📷 扫描到二维码: {data}')
            
            # Simple assumption: QR code is in the center of the bounding box
            # To get 3D pose, we would need camera intrinsics + depth.
            # Here we just mock the 3D position based on pixel coordinates for demonstration
            # In a real physical sim, you'd use a Depth Camera (RGB-D) or PnP.
            
            target_msg = PointStamped()
            target_msg.header.stamp = self.get_clock().now().to_msg()
            target_msg.header.frame_id = 'eye_camera_optical_frame'
            
            # Mock depth = 0.3 meters ahead of camera
            target_msg.point.x = 0.0
            target_msg.point.y = 0.0
            target_msg.point.z = 0.30 
            
            self.target_pub.publish(target_msg)
            
            # Draw bounding box for debug
            n = len(bbox[0])
            for i in range(n):
                cv2.line(cv_image, tuple(bbox[0][i].astype(int)), tuple(bbox[0][(i+1) % n].astype(int)), color=(0, 255, 0), thickness=3)
        
        # If we wanted to visualize the camera feed:
        # cv2.imshow("Eye-in-Hand View", cv_image)
        # cv2.waitKey(1)

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
