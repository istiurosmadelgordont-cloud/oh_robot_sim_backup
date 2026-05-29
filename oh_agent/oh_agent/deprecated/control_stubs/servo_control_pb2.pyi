from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TwistCommand(_message.Message):
    __slots__ = ("linear_x", "linear_y", "linear_z", "angular_x", "angular_y", "angular_z")
    LINEAR_X_FIELD_NUMBER: _ClassVar[int]
    LINEAR_Y_FIELD_NUMBER: _ClassVar[int]
    LINEAR_Z_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_X_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_Y_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_Z_FIELD_NUMBER: _ClassVar[int]
    linear_x: float
    linear_y: float
    linear_z: float
    angular_x: float
    angular_y: float
    angular_z: float
    def __init__(self, linear_x: _Optional[float] = ..., linear_y: _Optional[float] = ..., linear_z: _Optional[float] = ..., angular_x: _Optional[float] = ..., angular_y: _Optional[float] = ..., angular_z: _Optional[float] = ...) -> None: ...

class JointCommand(_message.Message):
    __slots__ = ("joint_name", "velocity")
    JOINT_NAME_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    joint_name: str
    velocity: float
    def __init__(self, joint_name: _Optional[str] = ..., velocity: _Optional[float] = ...) -> None: ...

class FrameCommand(_message.Message):
    __slots__ = ("frame",)
    class FrameType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        BASE_FRAME: _ClassVar[FrameCommand.FrameType]
        END_EFFECTOR_FRAME: _ClassVar[FrameCommand.FrameType]
    BASE_FRAME: FrameCommand.FrameType
    END_EFFECTOR_FRAME: FrameCommand.FrameType
    FRAME_FIELD_NUMBER: _ClassVar[int]
    frame: FrameCommand.FrameType
    def __init__(self, frame: _Optional[_Union[FrameCommand.FrameType, str]] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CommandResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class StatusResponse(_message.Message):
    __slots__ = ("active", "current_frame", "joint_velocity_multiplier")
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CURRENT_FRAME_FIELD_NUMBER: _ClassVar[int]
    JOINT_VELOCITY_MULTIPLIER_FIELD_NUMBER: _ClassVar[int]
    active: bool
    current_frame: str
    joint_velocity_multiplier: float
    def __init__(self, active: bool = ..., current_frame: _Optional[str] = ..., joint_velocity_multiplier: _Optional[float] = ...) -> None: ...
