#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from control_msgs.msg import JointJog

import grpc
from concurrent import futures
import threading
import time
import sys
import signal

import control_stubs.servo_control_pb2 as pb2
import control_stubs.servo_control_pb2_grpc as pb2_grpc

# Constants from original code
TWIST_TOPIC = "/servo_node/delta_twist_cmds"
JOINT_TOPIC = "/servo_node/delta_joint_cmds"
ROS_QUEUE_SIZE = 10
EEF_FRAME_ID = "panda_hand"
BASE_FRAME_ID = "panda_link0"


class ServoControlService(pb2_grpc.ServoControlServicer):
    def __init__(self):
        # Initialize ROS2 node
        rclpy.init()
        self.node = Node('servo_grpc_server')
        
        # Create publishers
        self.twist_pub = self.node.create_publisher(
            TwistStamped, TWIST_TOPIC, ROS_QUEUE_SIZE)
        self.joint_pub = self.node.create_publisher(
            JointJog, JOINT_TOPIC, ROS_QUEUE_SIZE)
        
        # State variables
        self.frame_to_publish = BASE_FRAME_ID
        self.joint_vel_cmd = 1.0
        self.active = True
        
        # Start ROS spinning in separate thread
        self.ros_thread = threading.Thread(target=self._ros_spin, daemon=True)
        self.ros_thread.start()
        
        self.node.get_logger().info('ServoControlService initialized')
    
    def _ros_spin(self):
        """ROS2 spinning thread"""
        while rclpy.ok() and self.active:
            rclpy.spin_once(self.node, timeout_sec=0.001)
            time.sleep(0.001)
    
    def shutdown(self):
        """Clean shutdown"""
        self.active = False
        if self.ros_thread.is_alive():
            self.ros_thread.join(timeout=1.0)
        self.node.destroy_node()
        rclpy.shutdown()
    
    def SendTwistCommand(self, request, context):
        """Send twist command for Cartesian movement"""
        try:
            # Create twist message
            twist_msg = TwistStamped()
            
            # Set twist values from request
            twist_msg.twist.linear.x = request.linear_x
            twist_msg.twist.linear.y = request.linear_y
            twist_msg.twist.linear.z = request.linear_z
            twist_msg.twist.angular.x = request.angular_x
            twist_msg.twist.angular.y = request.angular_y
            twist_msg.twist.angular.z = request.angular_z
            
            # Set header
            twist_msg.header.stamp = self.node.get_clock().now().to_msg()
            twist_msg.header.frame_id = self.frame_to_publish
            
            # Publish
            self.twist_pub.publish(twist_msg)
            
            # self.node.get_logger().debug(
            #     f'Published twist command: [{request.linear_x:.2f}, {request.linear_y:.2f}, {request.linear_z:.2f}] '
            #     f'[{request.angular_x:.2f}, {request.angular_y:.2f}, {request.angular_z:.2f}]'
            # )
            self.node.get_logger().info(
                f'Published twist command: [{request.linear_x:.2f}, {request.linear_y:.2f}, {request.linear_z:.2f}] '
                f'[{request.angular_x:.2f}, {request.angular_y:.2f}, {request.angular_z:.2f}]'
            )
            
            return pb2.CommandResponse(
                success=True,
                message="Twist command sent successfully"
            )
            
        except Exception as e:
            self.node.get_logger().error(f'Error sending twist command: {e}')
            return pb2.CommandResponse(
                success=False,
                message=f"Error sending twist command: {str(e)}"
            )
    
    def SendJointCommand(self, request, context):
        """Send joint command for individual joint movement"""
        try:
            # Validate joint name
            joint_name = request.joint_name
            if not joint_name.startswith('panda_joint'):
                return pb2.CommandResponse(
                    success=False,
                    message=f"Invalid joint name: {joint_name}"
                )
            
            # Create joint message
            joint_msg = JointJog()
            joint_msg.joint_names = [joint_name]
            joint_msg.velocities = [request.velocity * self.joint_vel_cmd]
            
            # Set header
            joint_msg.header.stamp = self.node.get_clock().now().to_msg()
            joint_msg.header.frame_id = BASE_FRAME_ID
            
            # Publish
            self.joint_pub.publish(joint_msg)
            
            # self.node.get_logger().debug(
            #     f'Published joint command: {joint_name} with velocity {request.velocity * self.joint_vel_cmd:.2f}'
            # )
            self.node.get_logger().info(
                f'Published joint command: {joint_name} with velocity {request.velocity * self.joint_vel_cmd:.2f}'
            )
            
            return pb2.CommandResponse(
                success=True,
                message="Joint command sent successfully"
            )
            
        except Exception as e:
            self.node.get_logger().error(f'Error sending joint command: {e}')
            return pb2.CommandResponse(
                success=False,
                message=f"Error sending joint command: {str(e)}"
            )
    
    def SetReferenceFrame(self, request, context):
        """Set reference frame for twist commands"""
        try:
            if request.frame == pb2.FrameCommand.BASE_FRAME:
                self.frame_to_publish = BASE_FRAME_ID
                self.node.get_logger().info('Reference frame set to base frame')
            elif request.frame == pb2.FrameCommand.END_EFFECTOR_FRAME:
                self.frame_to_publish = EEF_FRAME_ID
                self.node.get_logger().info('Reference frame set to end-effector frame')
            else:
                return pb2.CommandResponse(
                    success=False,
                    message="Unknown frame type"
                )
            
            return pb2.CommandResponse(
                success=True,
                message=f"Reference frame updated to: {self.frame_to_publish}"
            )
            
        except Exception as e:
            self.node.get_logger().error(f'Error setting frame: {e}')
            return pb2.CommandResponse(
                success=False,
                message=f"Error setting frame: {str(e)}"
            )
    
    def ReverseJointDirection(self, request, context):
        """Reverse joint movement direction"""
        try:
            self.joint_vel_cmd *= -1.0
            
            self.node.get_logger().info(
                f'Joint direction reversed. New multiplier: {self.joint_vel_cmd:.1f}'
            )
            
            return pb2.CommandResponse(
                success=True,
                message="Joint direction reversed"
            )
            
        except Exception as e:
            self.node.get_logger().error(f'Error reversing direction: {e}')
            return pb2.CommandResponse(
                success=False,
                message=f"Error reversing direction: {str(e)}"
            )
    
    def GetStatus(self, request, context):
        """Get current servo status"""
        return pb2.StatusResponse(
            active=self.active,
            current_frame=self.frame_to_publish,
            joint_velocity_multiplier=self.joint_vel_cmd
        )


def serve(server_address):
    """Run the gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service = ServoControlService()
    
    pb2_grpc.add_ServoControlServicer_to_server(service, server)
    server.add_insecure_port(server_address)
    
    print(f"gRPC server listening on {server_address}")
    server.start()
    
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        service.shutdown()
        server.stop(grace=5.0)
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    finally:
        service.shutdown()


def main(args=None):
    # Default server address
    server_address = '0.0.0.0:50051'
    
    # Override with command line argument if provided
    if len(sys.argv) > 1:
        server_address = sys.argv[1]
    
    print("Starting Servo gRPC Server (Python)...")
    
    try:
        serve(server_address)
    except Exception as e:
        print(f"Server error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())