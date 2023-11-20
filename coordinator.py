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
    def use_cloud(self, rpc_handle,  msg_handler: Callable[[InputT, Timestamp], Optional[Tuple[OutputT, int]]]):
        raise NotImplementedError()
    