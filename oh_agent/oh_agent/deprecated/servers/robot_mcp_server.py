#!/usr/bin/env python3

import asyncio
import base64
import io
import os
import sys
from typing import Dict, Any

import grpc
from google.protobuf.json_format import MessageToDict
from fastmcp import FastMCP

# Import generated proto modules
try:
    from control_stubs import common_pb2 as common_pb
    from control_stubs import robot_core_pb2 as core_pb
    from control_stubs import robot_core_pb2_grpc as core_grpc
    from control_stubs import sensing_pb2 as sensing_pb
    from control_stubs import sensing_pb2_grpc as sensing_grpc
    from control_stubs import mobility_ai_pb2 as ai_pb
    from control_stubs import mobility_ai_pb2_grpc as ai_grpc
except ImportError:
    print("Error: Could not import proto modules. Ensure they are generated and in PYTHONPATH.\n"
          " Tips: You can regenerate them using `scripts/build_oh_agent_proto.sh`")
    sys.exit(1)

# Configuration
GRPC_HOST = os.getenv("ROBOT_GRPC_HOST", "localhost")
GRPC_PORT = int(os.getenv("ROBOT_GRPC_PORT", "50051"))
GRPC_CHANNEL: grpc.aio.Channel | None = None


def get_channel() -> grpc.aio.Channel:
    global GRPC_CHANNEL
    if GRPC_CHANNEL is None:
        target = f"{GRPC_HOST}:{GRPC_PORT}"
        GRPC_CHANNEL = grpc.aio.insecure_channel(target)
    return GRPC_CHANNEL


def pb_to_dict(msg) -> Dict[str, Any]:
    return MessageToDict(
        msg,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=True,
        use_integers_for_enums=True,
    )


# Initialize MCP server
mcp = FastMCP(
    name="robot-simulator-mcp",
    instructions="MCP server for controlling and sensing a robot simulator via gRPC"
)


# ============================================================================
# Robot Core Service Tools
# ============================================================================

@mcp.tool()
async def get_robot_state() -> dict:
    """Get the current state of the robot including joint positions, velocities, and efforts.
    Returns a dictionary with joint names and their corresponding values."""
    try:
        stub = core_grpc.RobotCoreServiceStub(get_channel())
        response: core_pb.RobotState = await stub.GetRobotState(common_pb.Empty())
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def get_robot_description() -> dict:
    """Get robot description including joint names, limits, and types.
    Useful for checking if the robot is servo-capable and understanding joint constraints."""
    try:
        stub = core_grpc.RobotCoreServiceStub(get_channel())
        response: core_pb.RobotDescription = await stub.GetRobotDescription(common_pb.Empty())
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def set_joint_target(
    joint_names: list[str],
    joint_values: list[float],
    mode: str = "POSITION",
    move_group: str = ""
) -> dict:
    """Set joint targets for the robot. Mode can be 'POSITION', 'VELOCITY', or 'TORQUE'.
    
    Args:
        joint_names: List of joint names to control
        joint_values: Corresponding values for each joint
        mode: Control mode (POSITION, VELOCITY, or TORQUE)
        move_group: Optional move group name for grouped control
    """
    try:
        mode_map = {
            "POSITION": core_pb.JointCommand.POSITION,
            "VELOCITY": core_pb.JointCommand.VELOCITY,
            "TORQUE": core_pb.JointCommand.TORQUE,
        }
        
        if mode not in mode_map:
            return {"error": f"Invalid mode: {mode}. Must be POSITION, VELOCITY, or TORQUE"}
        
        if len(joint_names) != len(joint_values):
            return {"error": "joint_names and joint_values must have the same length"}
        
        cmd = core_pb.JointCommand(
            name=joint_names,
            data=joint_values,
            mode=mode_map[mode]
        )
        
        if move_group:
            cmd.group.move_group = move_group
        
        stub = core_grpc.RobotCoreServiceStub(get_channel())
        response: common_pb.Status = await stub.SetJointTarget(cmd)
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def get_end_effector_state(move_group: str = "manipulator") -> dict:
    """Get the current pose of the end effector for a specific move group.
    Returns the position (x, y, z) and orientation (quaternion) of the end effector.
    
    Args:
        move_group: Name of the move group (default: 'manipulator')
    """
    try:
        stub = core_grpc.RobotCoreServiceStub(get_channel())
        request = core_pb.MoveGroupRequest(move_group=move_group)
        response: core_pb.EndEffectorState = await stub.GetEndEffectorState(request)
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def emergency_stop() -> dict:
    """Immediately stop all robot motion. Use in emergency situations."""
    try:
        stub = core_grpc.RobotCoreServiceStub(get_channel())
        response: common_pb.Status = await stub.EmergencyStop(common_pb.Empty())
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


# ============================================================================
# Sensing Service Tools
# ============================================================================

@mcp.tool()
async def list_sensors() -> dict:
    """List all available sensors on the robot including cameras, lidars, and IMUs.
    Returns sensor names and types."""
    try:
        stub = sensing_grpc.SensingServiceStub(get_channel())
        response: sensing_pb.SensorMetaList = await stub.ListSensors(common_pb.Empty())
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def get_camera_image(camera_name: str) -> dict:
    """Get a snapshot from a specific camera sensor.
    Returns image data in base64 format along with metadata.
    
    Args:
        camera_name: Name of the camera sensor
    """
    try:
        stub = sensing_grpc.SensingServiceStub(get_channel())
        request = sensing_pb.SensorRequest(sensor_names=[camera_name])
        response: sensing_pb.SensorData = await stub.GetSensors(request)
        
        if not response.images:
            return {"error": f"No image data received from camera '{camera_name}'"}
        
        image = response.images[0]
        base64_data = base64.b64encode(image.data).decode('utf-8')
        
        return {
            "camera_name": image.name,
            "width": image.width,
            "height": image.height,
            "encoding": image.encoding,
            "timestamp": image.header.timestamp,
            "frame_id": image.header.frame_id,
            "image_base64": base64_data
        }
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def get_lidar_scan(lidar_name: str) -> dict:
    """Get a scan from a specific lidar sensor.
    Returns range data and metadata.
    
    Args:
        lidar_name: Name of the lidar sensor
    """
    try:
        stub = sensing_grpc.SensingServiceStub(get_channel())
        request = sensing_pb.SensorRequest(sensor_names=[lidar_name])
        response: sensing_pb.SensorData = await stub.GetSensors(request)
        
        if not response.lidars:
            return {"error": f"No lidar data received from '{lidar_name}'"}
        
        lidar = response.lidars[0]
        return {
            "lidar_name": lidar.name,
            "angle_min": lidar.angle_min,
            "angle_max": lidar.angle_max,
            "angle_increment": lidar.angle_increment,
            "ranges": list(lidar.ranges),
            "intensities": list(lidar.intensities),
            "timestamp": lidar.header.timestamp,
            "frame_id": lidar.header.frame_id
        }
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def get_imu_data(imu_name: str) -> dict:
    """Get data from a specific IMU sensor.
    Returns orientation, angular velocity, and linear acceleration.
    
    Args:
        imu_name: Name of the IMU sensor
    """
    try:
        stub = sensing_grpc.SensingServiceStub(get_channel())
        request = sensing_pb.SensorRequest(sensor_names=[imu_name])
        response: sensing_pb.SensorData = await stub.GetSensors(request)
        
        if not response.imus:
            return {"error": f"No IMU data received from '{imu_name}'"}
        
        imu = response.imus[0]
        return pb_to_dict(imu)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


# ============================================================================
# AI/Navigation Service Tools
# ============================================================================

@mcp.tool()
async def get_robot_pose_in_map() -> dict:
    """Get the current pose of the robot in the map.
    Returns robot pose on the map including position and orientation."""
    try:
        stub = ai_grpc.MobilityServiceStub(get_channel())
        response: sensing_pb.SensorMetaList = await stub.GetRobotPoseInMap(common_pb.Empty())
        return pb_to_dict(response)
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def navigate_to(
    x: float,
    y: float,
    z: float = 0.0,
    qx: float = 0.0,
    qy: float = 0.0,
    qz: float = 0.0,
    qw: float = 1.0,
    target_frame: str = "map",
    max_velocity: float = 0.0
) -> dict:
    """Navigate the robot to a target pose using SLAM 2D navigation.
    Returns feedback on navigation progress.
    
    Args:
        x, y, z: Target position coordinates
        qx, qy, qz, qw: Target orientation as quaternion
        target_frame: Coordinate frame (default: 'map')
        max_velocity: Maximum velocity override (0 = use default)
    """
    try:
        stub = ai_grpc.MobilityServiceStub(get_channel())
        
        goal = ai_pb.NavGoal(
            target_pose=common_pb.Pose(
                position=common_pb.Point(x=x, y=y, z=z),
                orientation=common_pb.Quaternion(x=qx, y=qy, z=qz, w=qw)
            ),
            target_frame=target_frame,
            max_velocity=max_velocity
        )
        
        feedback_list = []
        async for feedback in stub.NavigateTo(goal):
            fb_dict = pb_to_dict(feedback)
            feedback_list.append(fb_dict)
            
            # Break if task completed or failed
            if feedback.status.code in [common_pb.STATUS_SUCCESS, common_pb.STATUS_FAILURE]:
                break
        
        return {
            "final_status": feedback_list[-1] if feedback_list else None,
            "all_feedback": feedback_list
        }
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


@mcp.tool()
async def execute_natural_command(
    prompt: str,
    context: dict | None = None,
    model_type: str = "AUTO"
) -> dict:
    """Execute a natural language command using VLA/VLN models.
    
    Args:
        prompt: Natural language instruction (e.g., 'Pick up the red apple')
        context: Optional context dictionary with additional information
        model_type: Model selector - 'AUTO', 'VLA_MANIPULATION', or 'VLN_NAVIGATION'
    """
    try:
        model_map = {
            "AUTO": ai_pb.NaturalLanguageRequest.AUTO,
            "VLA_MANIPULATION": ai_pb.NaturalLanguageRequest.VLA_MANIPULATION,
            "VLN_NAVIGATION": ai_pb.NaturalLanguageRequest.VLN_NAVIGATION,
        }
        
        if model_type not in model_map:
            return {"error": f"Invalid model_type: {model_type}"}
        
        stub = ai_grpc.MobilityServiceStub(get_channel())
        
        request = ai_pb.NaturalLanguageRequest(
            prompt=prompt,
            model_selector=model_map[model_type]
        )
        
        if context:
            request.context.update(context)
        
        feedback_list = []
        async for feedback in stub.ExecuteNaturalCommand(request):
            fb_dict = pb_to_dict(feedback)
            feedback_list.append(fb_dict)
            
            # Break if task completed or failed
            if feedback.status.code in [common_pb.STATUS_SUCCESS, common_pb.STATUS_FAILURE]:
                break
        
        return {
            "final_status": feedback_list[-1] if feedback_list else None,
            "all_feedback": feedback_list
        }
    except grpc.aio.AioRpcError as e:
        return {"error": f"gRPC error: {e.code()}", "message": e.details()}


# ============================================================================
# Main entry point
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robot Simulator MCP Server")
    parser.add_argument("--grpc-host", default=GRPC_HOST, help="gRPC server host")
    parser.add_argument("--grpc-port", type=int, default=GRPC_PORT, help="gRPC server port")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], 
                        help="Transport method")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP server host (for SSE)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP server port (for SSE)")
    
    args = parser.parse_args()
    
    # Set environment variables
    os.environ["ROBOT_GRPC_HOST"] = args.grpc_host
    os.environ["ROBOT_GRPC_PORT"] = str(args.grpc_port)
    GRPC_HOST = args.grpc_host
    GRPC_PORT = args.grpc_port
    
    try:
        if args.transport == "stdio":
            mcp.run(transport="stdio")
        else:
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
        sys.exit(0)