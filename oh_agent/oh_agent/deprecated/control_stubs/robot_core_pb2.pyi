from control_stubs import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TwistCmdType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CMD_VEL: _ClassVar[TwistCmdType]
    MOVEIT: _ClassVar[TwistCmdType]
CMD_VEL: TwistCmdType
MOVEIT: TwistCmdType

class RobotDescription(_message.Message):
    __slots__ = ("robot_name", "joints")
    ROBOT_NAME_FIELD_NUMBER: _ClassVar[int]
    JOINTS_FIELD_NUMBER: _ClassVar[int]
    robot_name: str
    joints: _containers.RepeatedCompositeFieldContainer[JointLimit]
    def __init__(self, robot_name: _Optional[str] = ..., joints: _Optional[_Iterable[_Union[JointLimit, _Mapping]]] = ...) -> None: ...

class JointLimit(_message.Message):
    __slots__ = ("name", "lower_limit", "upper_limit", "velocity_limit", "effort_limit")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOWER_LIMIT_FIELD_NUMBER: _ClassVar[int]
    UPPER_LIMIT_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_LIMIT_FIELD_NUMBER: _ClassVar[int]
    EFFORT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    name: str
    lower_limit: float
    upper_limit: float
    velocity_limit: float
    effort_limit: float
    def __init__(self, name: _Optional[str] = ..., lower_limit: _Optional[float] = ..., upper_limit: _Optional[float] = ..., velocity_limit: _Optional[float] = ..., effort_limit: _Optional[float] = ...) -> None: ...

class RobotState(_message.Message):
    __slots__ = ("header", "name", "position", "velocity", "effort")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    EFFORT_FIELD_NUMBER: _ClassVar[int]
    header: _common_pb2.Header
    name: _containers.RepeatedScalarFieldContainer[str]
    position: _containers.RepeatedScalarFieldContainer[float]
    velocity: _containers.RepeatedScalarFieldContainer[float]
    effort: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, header: _Optional[_Union[_common_pb2.Header, _Mapping]] = ..., name: _Optional[_Iterable[str]] = ..., position: _Optional[_Iterable[float]] = ..., velocity: _Optional[_Iterable[float]] = ..., effort: _Optional[_Iterable[float]] = ...) -> None: ...

class MoveGroupRequest(_message.Message):
    __slots__ = ("move_group",)
    MOVE_GROUP_FIELD_NUMBER: _ClassVar[int]
    move_group: str
    def __init__(self, move_group: _Optional[str] = ...) -> None: ...

class EndEffectorState(_message.Message):
    __slots__ = ("pose_stamped",)
    POSE_STAMPED_FIELD_NUMBER: _ClassVar[int]
    pose_stamped: _common_pb2.PoseStamped
    def __init__(self, pose_stamped: _Optional[_Union[_common_pb2.PoseStamped, _Mapping]] = ...) -> None: ...

class TwistCommand(_message.Message):
    __slots__ = ("twist", "cmd_type", "group")
    TWIST_FIELD_NUMBER: _ClassVar[int]
    CMD_TYPE_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    twist: _common_pb2.TwistStamped
    cmd_type: TwistCmdType
    group: MoveGroupRequest
    def __init__(self, twist: _Optional[_Union[_common_pb2.TwistStamped, _Mapping]] = ..., cmd_type: _Optional[_Union[TwistCmdType, str]] = ..., group: _Optional[_Union[MoveGroupRequest, _Mapping]] = ...) -> None: ...

class JointCommand(_message.Message):
    __slots__ = ("name", "data", "mode", "group")
    class ControlMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        POSITION: _ClassVar[JointCommand.ControlMode]
        VELOCITY: _ClassVar[JointCommand.ControlMode]
        TORQUE: _ClassVar[JointCommand.ControlMode]
    POSITION: JointCommand.ControlMode
    VELOCITY: JointCommand.ControlMode
    TORQUE: JointCommand.ControlMode
    NAME_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    GROUP_FIELD_NUMBER: _ClassVar[int]
    name: _containers.RepeatedScalarFieldContainer[str]
    data: _containers.RepeatedScalarFieldContainer[float]
    mode: JointCommand.ControlMode
    group: MoveGroupRequest
    def __init__(self, name: _Optional[_Iterable[str]] = ..., data: _Optional[_Iterable[float]] = ..., mode: _Optional[_Union[JointCommand.ControlMode, str]] = ..., group: _Optional[_Union[MoveGroupRequest, _Mapping]] = ...) -> None: ...

class ServoCommand(_message.Message):
    __slots__ = ("joint_cmd", "twist_cmd", "pose_cmd")
    JOINT_CMD_FIELD_NUMBER: _ClassVar[int]
    TWIST_CMD_FIELD_NUMBER: _ClassVar[int]
    POSE_CMD_FIELD_NUMBER: _ClassVar[int]
    joint_cmd: JointCommand
    twist_cmd: TwistCommand
    pose_cmd: _common_pb2.PoseStamped
    def __init__(self, joint_cmd: _Optional[_Union[JointCommand, _Mapping]] = ..., twist_cmd: _Optional[_Union[TwistCommand, _Mapping]] = ..., pose_cmd: _Optional[_Union[_common_pb2.PoseStamped, _Mapping]] = ...) -> None: ...
