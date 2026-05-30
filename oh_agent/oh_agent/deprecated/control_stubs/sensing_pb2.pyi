from control_stubs import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SensorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[SensorType]
    CAMERA: _ClassVar[SensorType]
    LIDAR: _ClassVar[SensorType]
    IMU: _ClassVar[SensorType]
UNKNOWN: SensorType
CAMERA: SensorType
LIDAR: SensorType
IMU: SensorType

class SensorMetaList(_message.Message):
    __slots__ = ("entries",)
    class SensorMeta(_message.Message):
        __slots__ = ("name", "type")
        NAME_FIELD_NUMBER: _ClassVar[int]
        TYPE_FIELD_NUMBER: _ClassVar[int]
        name: str
        type: SensorType
        def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[SensorType, str]] = ...) -> None: ...
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[SensorMetaList.SensorMeta]
    def __init__(self, entries: _Optional[_Iterable[_Union[SensorMetaList.SensorMeta, _Mapping]]] = ...) -> None: ...

class SensorRequest(_message.Message):
    __slots__ = ("sensor_names",)
    SENSOR_NAMES_FIELD_NUMBER: _ClassVar[int]
    sensor_names: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, sensor_names: _Optional[_Iterable[str]] = ...) -> None: ...

class SensorData(_message.Message):
    __slots__ = ("images", "lidars", "imus")
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    LIDARS_FIELD_NUMBER: _ClassVar[int]
    IMUS_FIELD_NUMBER: _ClassVar[int]
    images: _containers.RepeatedCompositeFieldContainer[CameraImage]
    lidars: _containers.RepeatedCompositeFieldContainer[LidarScan]
    imus: _containers.RepeatedCompositeFieldContainer[ImuData]
    def __init__(self, images: _Optional[_Iterable[_Union[CameraImage, _Mapping]]] = ..., lidars: _Optional[_Iterable[_Union[LidarScan, _Mapping]]] = ..., imus: _Optional[_Iterable[_Union[ImuData, _Mapping]]] = ...) -> None: ...

class CameraImage(_message.Message):
    __slots__ = ("header", "name", "height", "width", "encoding", "is_bigendian", "step", "data")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    IS_BIGENDIAN_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    header: _common_pb2.Header
    name: str
    height: int
    width: int
    encoding: str
    is_bigendian: bool
    step: int
    data: bytes
    def __init__(self, header: _Optional[_Union[_common_pb2.Header, _Mapping]] = ..., name: _Optional[str] = ..., height: _Optional[int] = ..., width: _Optional[int] = ..., encoding: _Optional[str] = ..., is_bigendian: bool = ..., step: _Optional[int] = ..., data: _Optional[bytes] = ...) -> None: ...

class LidarScan(_message.Message):
    __slots__ = ("header", "name", "angle_min", "angle_max", "angle_increment", "ranges", "intensities")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ANGLE_MIN_FIELD_NUMBER: _ClassVar[int]
    ANGLE_MAX_FIELD_NUMBER: _ClassVar[int]
    ANGLE_INCREMENT_FIELD_NUMBER: _ClassVar[int]
    RANGES_FIELD_NUMBER: _ClassVar[int]
    INTENSITIES_FIELD_NUMBER: _ClassVar[int]
    header: _common_pb2.Header
    name: str
    angle_min: float
    angle_max: float
    angle_increment: float
    ranges: _containers.RepeatedScalarFieldContainer[float]
    intensities: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, header: _Optional[_Union[_common_pb2.Header, _Mapping]] = ..., name: _Optional[str] = ..., angle_min: _Optional[float] = ..., angle_max: _Optional[float] = ..., angle_increment: _Optional[float] = ..., ranges: _Optional[_Iterable[float]] = ..., intensities: _Optional[_Iterable[float]] = ...) -> None: ...

class ImuData(_message.Message):
    __slots__ = ("header", "name", "orientation", "angular_velocity", "linear_acceleration")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    ANGULAR_VELOCITY_FIELD_NUMBER: _ClassVar[int]
    LINEAR_ACCELERATION_FIELD_NUMBER: _ClassVar[int]
    header: _common_pb2.Header
    name: str
    orientation: _common_pb2.Quaternion
    angular_velocity: _common_pb2.Point
    linear_acceleration: _common_pb2.Point
    def __init__(self, header: _Optional[_Union[_common_pb2.Header, _Mapping]] = ..., name: _Optional[str] = ..., orientation: _Optional[_Union[_common_pb2.Quaternion, _Mapping]] = ..., angular_velocity: _Optional[_Union[_common_pb2.Point, _Mapping]] = ..., linear_acceleration: _Optional[_Union[_common_pb2.Point, _Mapping]] = ...) -> None: ...
