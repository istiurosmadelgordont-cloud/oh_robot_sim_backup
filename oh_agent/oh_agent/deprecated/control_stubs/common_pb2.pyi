from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StatusCode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STATUS_UNKNOWN: _ClassVar[StatusCode]
    STATUS_SUCCESS: _ClassVar[StatusCode]
    STATUS_RUNNING: _ClassVar[StatusCode]
    STATUS_FAILURE: _ClassVar[StatusCode]
    STATUS_PREEMPTED: _ClassVar[StatusCode]
STATUS_UNKNOWN: StatusCode
STATUS_SUCCESS: StatusCode
STATUS_RUNNING: StatusCode
STATUS_FAILURE: StatusCode
STATUS_PREEMPTED: StatusCode

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Header(_message.Message):
    __slots__ = ("seq", "timestamp", "frame_id")
    SEQ_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    seq: int
    timestamp: float
    frame_id: str
    def __init__(self, seq: _Optional[int] = ..., timestamp: _Optional[float] = ..., frame_id: _Optional[str] = ...) -> None: ...

class Point(_message.Message):
    __slots__ = ("x", "y", "z")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ...) -> None: ...

class Quaternion(_message.Message):
    __slots__ = ("x", "y", "z", "w")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    Z_FIELD_NUMBER: _ClassVar[int]
    W_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    z: float
    w: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ..., z: _Optional[float] = ..., w: _Optional[float] = ...) -> None: ...

class Pose(_message.Message):
    __slots__ = ("position", "orientation")
    POSITION_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    position: Point
    orientation: Quaternion
    def __init__(self, position: _Optional[_Union[Point, _Mapping]] = ..., orientation: _Optional[_Union[Quaternion, _Mapping]] = ...) -> None: ...

class PoseStamped(_message.Message):
    __slots__ = ("header", "pose")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    POSE_FIELD_NUMBER: _ClassVar[int]
    header: Header
    pose: Pose
    def __init__(self, header: _Optional[_Union[Header, _Mapping]] = ..., pose: _Optional[_Union[Pose, _Mapping]] = ...) -> None: ...

class Twist(_message.Message):
    __slots__ = ("linear", "angular")
    LINEAR_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_FIELD_NUMBER: _ClassVar[int]
    linear: Point
    angular: Point
    def __init__(self, linear: _Optional[_Union[Point, _Mapping]] = ..., angular: _Optional[_Union[Point, _Mapping]] = ...) -> None: ...

class TwistStamped(_message.Message):
    __slots__ = ("header", "twist")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    TWIST_FIELD_NUMBER: _ClassVar[int]
    header: Header
    twist: Twist
    def __init__(self, header: _Optional[_Union[Header, _Mapping]] = ..., twist: _Optional[_Union[Twist, _Mapping]] = ...) -> None: ...

class Tensor(_message.Message):
    __slots__ = ("shape", "dtype", "data")
    SHAPE_FIELD_NUMBER: _ClassVar[int]
    DTYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    shape: _containers.RepeatedScalarFieldContainer[int]
    dtype: str
    data: bytes
    def __init__(self, shape: _Optional[_Iterable[int]] = ..., dtype: _Optional[str] = ..., data: _Optional[bytes] = ...) -> None: ...

class Status(_message.Message):
    __slots__ = ("code", "message")
    CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    code: StatusCode
    message: str
    def __init__(self, code: _Optional[_Union[StatusCode, str]] = ..., message: _Optional[str] = ...) -> None: ...
