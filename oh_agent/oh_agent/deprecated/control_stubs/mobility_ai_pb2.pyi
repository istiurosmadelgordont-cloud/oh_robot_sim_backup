from control_stubs import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class NavGoal(_message.Message):
    __slots__ = ("target_pose", "target_frame", "max_velocity")
    TARGET_POSE_FIELD_NUMBER: _ClassVar[int]
    TARGET_FRAME_FIELD_NUMBER: _ClassVar[int]
    MAX_VELOCITY_FIELD_NUMBER: _ClassVar[int]
    target_pose: _common_pb2.Pose
    target_frame: str
    max_velocity: float
    def __init__(self, target_pose: _Optional[_Union[_common_pb2.Pose, _Mapping]] = ..., target_frame: _Optional[str] = ..., max_velocity: _Optional[float] = ...) -> None: ...

class NaturalLanguageRequest(_message.Message):
    __slots__ = ("prompt", "context", "model_selector")
    class ModelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        AUTO: _ClassVar[NaturalLanguageRequest.ModelType]
        VLA_MANIPULATION: _ClassVar[NaturalLanguageRequest.ModelType]
        VLN_NAVIGATION: _ClassVar[NaturalLanguageRequest.ModelType]
    AUTO: NaturalLanguageRequest.ModelType
    VLA_MANIPULATION: NaturalLanguageRequest.ModelType
    VLN_NAVIGATION: NaturalLanguageRequest.ModelType
    class ContextEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    MODEL_SELECTOR_FIELD_NUMBER: _ClassVar[int]
    prompt: str
    context: _containers.ScalarMap[str, str]
    model_selector: NaturalLanguageRequest.ModelType
    def __init__(self, prompt: _Optional[str] = ..., context: _Optional[_Mapping[str, str]] = ..., model_selector: _Optional[_Union[NaturalLanguageRequest.ModelType, str]] = ...) -> None: ...

class TaskFeedback(_message.Message):
    __slots__ = ("task_id", "status", "eta", "feedback_text", "debug_image")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ETA_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_TEXT_FIELD_NUMBER: _ClassVar[int]
    DEBUG_IMAGE_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    status: _common_pb2.Status
    eta: int
    feedback_text: str
    debug_image: bytes
    def __init__(self, task_id: _Optional[str] = ..., status: _Optional[_Union[_common_pb2.Status, _Mapping]] = ..., eta: _Optional[int] = ..., feedback_text: _Optional[str] = ..., debug_image: _Optional[bytes] = ...) -> None: ...
