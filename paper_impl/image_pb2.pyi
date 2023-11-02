from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Request(_message.Message):
    __slots__ = ["image_data", "req_id"]
    IMAGE_DATA_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    image_data: str
    req_id: int
    def __init__(self, image_data: _Optional[str] = ..., req_id: _Optional[int] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["ack_data", "req_id", "recv_time"]
    ACK_DATA_FIELD_NUMBER: _ClassVar[int]
    REQ_ID_FIELD_NUMBER: _ClassVar[int]
    RECV_TIME_FIELD_NUMBER: _ClassVar[int]
    ack_data: str
    req_id: int
    recv_time: float
    def __init__(self, ack_data: _Optional[str] = ..., req_id: _Optional[int] = ..., recv_time: _Optional[float] = ...) -> None: ...
