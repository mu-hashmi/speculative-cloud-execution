from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BoundingBox(_message.Message):
    __slots__ = ["xmin", "xmax", "ymin", "ymax"]
    XMIN_FIELD_NUMBER: _ClassVar[int]
    XMAX_FIELD_NUMBER: _ClassVar[int]
    YMIN_FIELD_NUMBER: _ClassVar[int]
    YMAX_FIELD_NUMBER: _ClassVar[int]
    xmin: float
    xmax: float
    ymin: float
    ymax: float
    def __init__(self, xmin: _Optional[float] = ..., xmax: _Optional[float] = ..., ymin: _Optional[float] = ..., ymax: _Optional[float] = ...) -> None: ...

class DetectedObject(_message.Message):
    __slots__ = ["score", "label", "box"]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    BOX_FIELD_NUMBER: _ClassVar[int]
    score: float
    label: str
    box: BoundingBox
    def __init__(self, score: _Optional[float] = ..., label: _Optional[str] = ..., box: _Optional[_Union[BoundingBox, _Mapping]] = ...) -> None: ...

class Request(_message.Message):
    __slots__ = ["image_data", "req_id"]
    IMAGE_DATA_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    image_data: bytes
    req_id: int
    def __init__(self, image_data: _Optional[bytes] = ..., req_id: _Optional[int] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["detected_objects", "req_id", "recv_time"]
    DETECTED_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    RECV_TIME_FIELD_NUMBER: _ClassVar[int]
    detected_objects: _containers.RepeatedCompositeFieldContainer[DetectedObject]
    req_id: int
    recv_time: float
    def __init__(self, detected_objects: _Optional[_Iterable[_Union[DetectedObject, _Mapping]]] = ..., req_id: _Optional[int] = ..., recv_time: _Optional[float] = ...) -> None: ...
