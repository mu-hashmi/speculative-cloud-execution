import abc
from typing import TypeVar, Generic, Callable, Optional, Tuple

class Timestamp:
    pass

class Deadline:
    pass

class RpcHandle:
    pass

InputT = TypeVar("InputT")

OutputT = TypeVar("OutputT")

class SpeculativeOperator(abc.ABC, Generic[InputT, OutputT]):
    """Uses speculative execution to run models in the cloud and locally as a fallback."""
    def __init__(self):
        pass

    @abc.abstractmethod
    def execute_local(self, input_message: InputT) -> OutputT:
        pass

    def process_message(self, input_message: InputT) -> OutputT:
        # needs to call execute_local after calling all the message handlers
        pass

    # commit comment
    def use_cloud(self, rpc_handle,  msg_handler: Callable[[InputT, Timestamp], Optional[Tuple[OutputT, Deadline]]], priority: int):
        # store rpc_handle, msg_handler, priority inside a data structure
        raise NotImplementedError()
    