from control_stubs import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ResetRequest(_message.Message):
    __slots__ = ("seed", "randomization_params")
    class RandomizationParamsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    SEED_FIELD_NUMBER: _ClassVar[int]
    RANDOMIZATION_PARAMS_FIELD_NUMBER: _ClassVar[int]
    seed: int
    randomization_params: _containers.ScalarMap[str, float]
    def __init__(self, seed: _Optional[int] = ..., randomization_params: _Optional[_Mapping[str, float]] = ...) -> None: ...

class StepRequest(_message.Message):
    __slots__ = ("block",)
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    block: bool
    def __init__(self, block: bool = ...) -> None: ...

class StepResponse(_message.Message):
    __slots__ = ("header", "reward", "done")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    REWARD_FIELD_NUMBER: _ClassVar[int]
    DONE_FIELD_NUMBER: _ClassVar[int]
    header: _common_pb2.Header
    reward: float
    done: bool
    def __init__(self, header: _Optional[_Union[_common_pb2.Header, _Mapping]] = ..., reward: _Optional[float] = ..., done: bool = ...) -> None: ...

class ObjectState(_message.Message):
    __slots__ = ("object_name", "pose")
    OBJECT_NAME_FIELD_NUMBER: _ClassVar[int]
    POSE_FIELD_NUMBER: _ClassVar[int]
    object_name: str
    pose: _common_pb2.Pose
    def __init__(self, object_name: _Optional[str] = ..., pose: _Optional[_Union[_common_pb2.Pose, _Mapping]] = ...) -> None: ...
