import abc
from typing import Callable, Generic, Optional, Tuple, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
RpcRequest = TypeVar("RpcRequest")
RpcResponse = TypeVar("RpcResponse")


class Timestamp:
    pass


class Deadline:
    pass


class RpcHandle(Generic[RpcRequest, RpcResponse]):
    def __call__(self, rpc_request: RpcRequest) -> RpcResponse:
        pass


class SpeculativeOperator(abc.ABC, Generic[InputT, OutputT]):
    """Speculatively executes in the cloud and locally as a fallback."""

    def __init__(self):
        pass

    @abc.abstractmethod
    def execute_local(self, input_message: InputT) -> OutputT:
        pass

    def process_message(self, timestamp: Timestamp, input_message: InputT) -> OutputT:
        # needs to call execute_local after calling all the message handlers
        pass

    # commit comment
    def use_cloud(
        self,
        rpc_handle: RpcHandle[RpcRequest, RpcResponse],
        message_handler: Callable[
            [Timestamp, InputT], Optional[Tuple[RpcRequest, Deadline]]
        ],
        response_handler: Callable[[RpcResponse], OutputT],
        priority: int,
    ):
        """Registers a cloud implementation for the operator.

        Args:
            rpc_handle: Remote procedure call (RPC) handle used to invoke the cloud
                implementation.
            message_handler: Converts the timestamp and the input message to an
                `RpcRequest`. The `RpcRequest` is provided to the `rpc_handle` in order
                to run the cloud implementation.
            response_handler: Converts the `RpcResponse` returned by the `rpc_handle` to
                the output type.
            priority: Priority of the cloud implementations. If multiple cloud
                implementations are registered, they will execute in parallel. If both
                return responses within their deadlines, the result from the the
                implementation with the highest priority is selected.
        """
        # store rpc_handle, msg_handler, priority inside a data structure
        raise NotImplementedError()
