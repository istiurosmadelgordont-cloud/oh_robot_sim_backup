#!/usr/bin/env python3
"""
Simple Python test client for the gRPC servo control server
"""

import grpc
import time
import sys

import control_stubs.servo_control_pb2 as servo_control_pb2
import control_stubs.servo_control_pb2_grpc as servo_control_pb2_grpc


class ServoTestClient:
    def __init__(self, server_address="localhost:50051"):
        self.channel = grpc.insecure_channel(server_address)
        self.stub = servo_control_pb2_grpc.ServoControlStub(self.channel)
        self.server_address = server_address
    
    def test_connection(self):
        """Test connection to the server"""
        try:
            # Try to get status to test connection
            request = servo_control_pb2.Empty()
            response = self.stub.GetStatus(request, timeout=5.0)
            print(f"✓ Connected to server at {self.server_address}")
            print(f"  Status: Active={response.active}, Frame={response.current_frame}, "
                  f"Joint Multiplier={response.joint_velocity_multiplier}")
            return True
        except grpc.RpcError as e:
            print(f"✗ Failed to connect to server: {e}")
            return False
    
    def test_twist_commands(self):
        """Test twist commands (Cartesian movement)"""
        print("\nTesting twist commands...")
        
        test_cases = [
            ("Forward", 1.0, 0.0, 0.0),
            ("Backward", -1.0, 0.0, 0.0),
            ("Left", 0.0, -1.0, 0.0),
            ("Right", 0.0, 1.0, 0.0),
            ("Up", 0.0, 0.0, 1.0),
            ("Down", 0.0, 0.0, -1.0),
        ]
        
        for name, x, y, z in test_cases:
            try:
                request = servo_control_pb2.TwistCommand(
                    linear_x=x, linear_y=y, linear_z=z
                )
                response = self.stub.SendTwistCommand(request)
                status = "✓" if response.success else "✗"
                print(f"  {status} {name}: {response.message}")
                time.sleep(0.5)
            except grpc.RpcError as e:
                print(f"  ✗ {name}: gRPC error - {e}")
    
    def test_joint_commands(self):
        """Test joint commands"""
        print("\nTesting joint commands...")
        
        joints = ["panda_joint1", "panda_joint2", "panda_joint3", "panda_joint4",
                 "panda_joint5", "panda_joint6", "panda_joint7"]
        
        for joint in joints:
            try:
                request = servo_control_pb2.JointCommand(
                    joint_name=joint, velocity=1.0
                )
                response = self.stub.SendJointCommand(request)
                status = "✓" if response.success else "✗"
                print(f"  {status} {joint}: {response.message}")
                time.sleep(0.3)
            except grpc.RpcError as e:
                print(f"  ✗ {joint}: gRPC error - {e}")
    
    def test_frame_switching(self):
        """Test reference frame switching"""
        print("\nTesting reference frame switching...")
        
        frames = [
            ("Base Frame", servo_control_pb2.FrameCommand.BASE_FRAME),
            ("End-Effector Frame", servo_control_pb2.FrameCommand.END_EFFECTOR_FRAME),
        ]
        
        for name, frame_type in frames:
            try:
                request = servo_control_pb2.FrameCommand(frame=frame_type)
                response = self.stub.SetReferenceFrame(request)
                status = "✓" if response.success else "✗"
                print(f"  {status} {name}: {response.message}")
                time.sleep(0.5)
            except grpc.RpcError as e:
                print(f"  ✗ {name}: gRPC error - {e}")
    
    def test_reverse_direction(self):
        """Test reversing joint direction"""
        print("\nTesting reverse direction...")
        
        try:
            request = servo_control_pb2.Empty()
            response = self.stub.ReverseJointDirection(request)
            status = "✓" if response.success else "✗"
            print(f"  {status} Reverse direction: {response.message}")
        except grpc.RpcError as e:
            print(f"  ✗ Reverse direction: gRPC error - {e}")
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"Testing gRPC Servo Server at {self.server_address}")
        print("=" * 50)
        
        if not self.test_connection():
            return False
        
        self.test_twist_commands()
        self.test_joint_commands()
        self.test_frame_switching()
        self.test_reverse_direction()
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        return True
    
    def interactive_mode(self):
        """Interactive mode for manual testing"""
        print(f"\nInteractive mode - Connected to {self.server_address}")
        print("Commands:")
        print("  w/a/s/d - Move forward/left/backward/right")
        print("  q/e - Move up/down")
        print("  1-7 - Move joints 1-7")
        print("  f - Switch frame")
        print("  r - Reverse direction")
        print("  x - Exit")
        
        try:
            while True:
                cmd = input("Enter command: ").strip().lower()
                
                if cmd == 'x':
                    break
                elif cmd == 'w':
                    self.stub.SendTwistCommand(servo_control_pb2.TwistCommand(linear_x=1.0))
                elif cmd == 's':
                    self.stub.SendTwistCommand(servo_control_pb2.TwistCommand(linear_x=-1.0))
                elif cmd == 'a':
                    self.stub.SendTwistCommand(servo_control_pb2.TwistCommand(linear_y=-1.0))
                elif cmd == 'd':
                    self.stub.SendTwistCommand(servo_control_pb2.TwistCommand(linear_y=1.0))
                elif cmd == 'q':
                    self.stub.SendTwistCommand(servo_control_pb2.TwistCommand(linear_z=1.0))
                elif cmd == 'e':
                    self.stub.SendTwistCommand(servo_control_pb2.TwistCommand(linear_z=-1.0))
                elif cmd in '1234567':
                    joint_name = f"panda_joint{cmd}"
                    self.stub.SendJointCommand(servo_control_pb2.JointCommand(
                        joint_name=joint_name, velocity=1.0))
                elif cmd == 'f':
                    # Get current status to determine frame
                    status = self.stub.GetStatus(servo_control_pb2.Empty())
                    new_frame = servo_control_pb2.FrameCommand.END_EFFECTOR_FRAME \
                        if status.current_frame == "panda_link0" \
                        else servo_control_pb2.FrameCommand.BASE_FRAME
                    self.stub.SetReferenceFrame(servo_control_pb2.FrameCommand(frame=new_frame))
                elif cmd == 'r':
                    self.stub.ReverseJointDirection(servo_control_pb2.Empty())
                else:
                    print("Unknown command")
                
                print("Command sent!")
                
        except KeyboardInterrupt:
            print("\nExiting interactive mode...")


def main():
    server_address = "localhost:50051"
    if len(sys.argv) > 1:
        server_address = sys.argv[1]
    
    client = ServoTestClient(server_address)
    
    # Run tests
    if client.run_all_tests():
        # Ask if user wants interactive mode
        try:
            response = input("\nEnter interactive mode? (y/N): ").strip().lower()
            if response in ['y', 'yes']:
                client.interactive_mode()
        except KeyboardInterrupt:
            print("\nGoodbye!")


if __name__ == "__main__":
    main()