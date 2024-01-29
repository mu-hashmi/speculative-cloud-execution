from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BoundingBox(_message.Message):
    __slots__ = ["x_min", "x_max", "y_min", "y_max"]
    X_MIN_FIELD_NUMBER: _ClassVar[int]
    X_MAX_FIELD_NUMBER: _ClassVar[int]
    Y_MIN_FIELD_NUMBER: _ClassVar[int]
    Y_MAX_FIELD_NUMBER: _ClassVar[int]
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    def __init__(self, x_min: _Optional[float] = ..., x_max: _Optional[float] = ..., y_min: _Optional[float] = ..., y_max: _Optional[float] = ...) -> None: ...

class DetectedObject(_message.Message):
    __slots__ = ["box", "object_type_str"]
    BOX_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_STR_FIELD_NUMBER: _ClassVar[int]
    box: BoundingBox
    object_type_str: str
    def __init__(self, box: _Optional[_Union[BoundingBox, _Mapping]] = ..., object_type_str: _Optional[str] = ...) -> None: ...

class Request(_message.Message):
    __slots__ = ["image_data", "req_id"]
    IMAGE_DATA_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    image_data: str
    req_id: int
    def __init__(self, image_data: _Optional[str] = ..., req_id: _Optional[int] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["detected_objects", "req_id", "recv_time"]
    DETECTED_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    RECV_TIME_FIELD_NUMBER: _ClassVar[int]
    detected_objects: _containers.RepeatedCompositeFieldContainer[DetectedObject]
    req_id: int
    recv_time: float
    def __init__(self, detected_objects: _Optional[_Iterable[_Union[DetectedObject, _Mapping]]] = ..., req_id: _Optional[int] = ..., recv_time: _Optional[float] = ...) -> None: ...
