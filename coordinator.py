import abc
from dataclasses import dataclass
from typing import Callable, Generic, Optional, Self, Tuple, TypeVar, List
from threading import Thread
from concurrent import futures
import time

import grpc

from paper_impl import image_pb2_grpc

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
RpcRequest = TypeVar("RpcRequest")
RpcResponse = TypeVar("RpcResponse")


class Timestamp:
    pass

@dataclass
class Deadline:
    seconds: float
    is_absolute: bool

    @classmethod
    def absolute(cls, unix_time_seconds: float) -> Self:
        cls(seconds=unix_time_seconds, is_absolute=True)

    @classmethod
    def relative(cls, seconds: float) -> Self:
        cls(seconds=seconds, is_absolute=False)

    def to_absolute(self, start_time: float) -> Self:
        if self.is_absolute:
            return self
        return Deadline(start_time + self.seconds, is_absolute=True)


class RpcHandle(Generic[RpcRequest, RpcResponse]):
    def __init__(self, rpc_call: Callable[[RpcRequest], RpcResponse]):
        self.channel = grpc.insecure_channel("localhost:12345")
        # self.stub = image_pb2_grpc.GRPCImageStub(self.channel)
        self.rpc_call = rpc_call

    def __call__(self, rpc_request: RpcRequest) -> RpcResponse:
        response = self.rpc_call(rpc_request)
        return response

@dataclass
class Implementation:
    rpc_handle: RpcHandle[RpcRequest, RpcResponse]
    message_handler: Callable[
            [Timestamp, InputT], Optional[Tuple[RpcRequest, Deadline]]
        ]
    response_handler: Callable[[RpcResponse], OutputT]
    priority: int

class SpeculativeOperator(abc.ABC, Generic[InputT, OutputT]):
    """Speculatively executes in the cloud and locally as a fallback."""

    def __init__(self):
        self.implementations = []
        self.thread = None
        self.local_result = None
        pass

    @abc.abstractmethod
    def execute_local(self, input_message: InputT) -> OutputT:
        pass

    def execute_local_separate_thread(self, input_message: InputT) -> OutputT:
        self.local_result = self.execute_local(input_message)
        return self.local_result

    def execute_cloud_separate_thread(self, imp: Implementation, timestamp: Timestamp, input_message: InputT, deadlines: List[Optional[float]]):
        # get rpc request and deadline from message handler
        time.sleep(0.1)
        rpc_request, deadline = imp.message_handler(timestamp, input_message)

        print("deadline returned by message handler:", deadline)
        deadlines.append(deadline)

        # get rpc response and convert it to the output type
        response = imp.rpc_handle(rpc_request)
        result = imp.response_handler(response)

        return result

    def process_message(self, timestamp: Timestamp, input_message: InputT) -> OutputT:
        # needs to call execute_local after calling all the message handlers
        print("executing process_message")

        # Run execute_local in a separate thread
        self.thread = Thread(target=self.execute_local_separate_thread, args=(input_message,))
        self.thread.start()
        deadlines = []

        # create a thread for each cloud implementation
        cloud_threads = [
            Thread(target=self.execute_cloud_separate_thread, args=(imp, timestamp, input_message, deadlines))
            for imp in sorted(self.implementations, key=lambda x: x.priority)
        ]

        # start all cloud threads
        for thread in cloud_threads:
            thread.start()

        threads = [self.thread] + cloud_threads
        
        start_time = time.time()

        while len(deadlines) != len(threads) - 1:
            time.sleep(0.0001)

        # find min deadline
        min_deadline = min(deadlines, key=lambda deadline: deadline.seconds)
        print('calculated min deadline')
        print(deadlines)

        thread_completed = False
        # get the first completed thread
        while not thread_completed:
            for thread in threads:
                if not thread.is_alive():
                    print("finished execution")
                    thread_completed = True
                    break
            time.sleep(0.001)

        print(start_time)
        print(min_deadline.seconds)
        elapsed_time = time.time() - start_time
        print(elapsed_time)

        if elapsed_time > min_deadline.seconds:
            print("Missed the deadline!")
        else:
            print("finished before deadline!")

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
        self.implementations.append(
            Implementation(
                rpc_handle=rpc_handle,
                message_handler=message_handler,
                response_handler=response_handler,
                priority=priority,
            )
        )
