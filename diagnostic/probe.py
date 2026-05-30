#!/usr/bin/env python3
# depth_diagnostic_save.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np
import cv2

class DepthDiagSave(Node):
    def __init__(self):
        super().__init__('depth_diag_save')
        self.bridge = CvBridge()
        self.sub = self.create_subscription(
            Image, '/camera/depth_image', self.cb, 10
        )
        self.once = False
        self.get_logger().info("Waiting for one depth image...")

    def cb(self, msg):
        if self.once:
            return
        self.once = True
        self.get_logger().info("Received depth image. Processing...")

        # ---------------------------
        # Convert ROS Image → numpy
        # ---------------------------
        depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        depth = np.array(depth, dtype=np.float32)

        # Save raw
        np.save("depth_raw.npy", depth)
        self.get_logger().info("Saved raw depth to depth_raw.npy")

        # ---------------------------
        # Identify invalid pixels
        # ---------------------------
        mask_nan = np.isnan(depth)
        mask_posinf = np.isposinf(depth)
        mask_neginf = np.isneginf(depth)
        invalid_mask = mask_nan | mask_posinf | mask_neginf

        n_invalid = np.count_nonzero(invalid_mask)
        self.get_logger().info(f"Invalid pixel count: {n_invalid}")

        # ---------------------------
        # Determine fill value
        # ---------------------------
        valid_mask = ~invalid_mask
        if valid_mask.any():
            max_valid = float(np.nanmax(depth[valid_mask]))
            fill_val = max_valid
        else:
            fill_val = 10.0  # fallback

        self.get_logger().info(f"Using fill_val = {fill_val}")

        # ---------------------------
        # Make cleaned depth image
        # ---------------------------
        depth_clean = depth.copy()
        depth_clean[invalid_mask] = fill_val
        np.save("depth_clean.npy", depth_clean)
        self.get_logger().info("Saved cleaned depth to depth_clean.npy")

        # ---------------------------
        # Make visualization image
        # ---------------------------
        # Normalize depth to 0..255
        max_vis = max_valid if valid_mask.any() else 10.0
        depth_clip = np.clip(depth_clean, 0.0, max_vis)
        vis_gray = (255.0 * (1.0 - depth_clip / max_vis)).astype(np.uint8)

        # Convert grayscale → color
        vis_color = cv2.cvtColor(vis_gray, cv2.COLOR_GRAY2BGR)

        # Mark invalid pixels red
        vis_color[invalid_mask] = (0, 0, 255)

        cv2.imwrite("depth_vis.png", vis_color)
        self.get_logger().info("Saved depth visualization to depth_vis.png")

        # All done — shutdown
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = DepthDiagSave()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

