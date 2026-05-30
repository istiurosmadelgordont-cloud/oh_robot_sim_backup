import rclpy, sys
from rclpy.node import Node
from sensor_msgs.msg import Image
import numpy as np
from cv_bridge import CvBridge

rclpy.init()
node = Node('tmp_depth_stat')
bridge = CvBridge()
msg = None
fg = 0

def proc(m):
    global msg, fg
    print(f"proc here: {msg}")
    fg += 1
    msg = m

sub = node.create_subscription(Image, '/camera/depth_image', proc, 10)
while fg == 0:
    rclpy.spin_once(node, timeout_sec=0.1)
assert msg is not None
m = msg
try:
    cv = bridge.imgmsg_to_cv2(m, desired_encoding='passthrough')
except Exception as e:
    cv = bridge.imgmsg_to_cv2(m, desired_encoding='32FC1')

arr = np.array(cv).astype(np.float32)
total = arr.size
n_nan = np.isnan(arr).sum()
n_posinf = np.isposinf(arr).sum()
n_neginf = np.isneginf(arr).sum()
n_zero = (arr == 0.0).sum()
valid_mask = ~ (np.isnan(arr) | np.isinf(arr))
valid_count = valid_mask.sum()
mn = float(np.nanmin(np.where(valid_mask, arr, np.nan)))
mx = float(np.nanmax(np.where(valid_mask, arr, np.nan)))
print(f'encoding: {m.encoding}, shape: {arr.shape}')
print(f'total pixels: {total}')
print(f'valid pixels: {valid_count} ({100.0*valid_count/total:.1f}%)')
print(f'n_nan: {n_nan} ({100.0*n_nan/total:.1f}%)')
print(f'n_posinf: {n_posinf} ({100.0*n_posinf/total:.1f}%)')
print(f'n_neginf: {n_neginf} ({100.0*n_neginf/total:.1f}%)')
print(f'n_zero: {n_zero} ({100.0*n_zero/total:.1f}%)')
print(f'valid min: {mn:.6f}, valid max: {mx:.6f}')
