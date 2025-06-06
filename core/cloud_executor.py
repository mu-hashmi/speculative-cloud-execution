import abc
import functools
import heapq
import io
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Semaphore, Thread
from typing import Callable, Generic, List, Optional, Self, Tuple, TypeVar

import grpc
import requests
from PIL import Image

logger = logging.getLogger(__name__)


def configure_logging(verbose=False):
    """Configure logging level based on verbosity.

    Args:
        verbose: If True, set logging level to INFO, otherwise to WARNING
    """
    if verbose:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARNING)


configure_logging(False)

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
RpcRequest = TypeVar("RpcRequest")
RpcResponse = TypeVar("RpcResponse")
RpcStub = TypeVar("RpcStub")


class Timestamp:
    pass


@dataclass
class Deadline:
    seconds: float
    is_absolute: bool

    @classmethod
    def absolute(cls, unix_time_seconds: float) -> Self:
        return cls(seconds=unix_time_seconds, is_absolute=True)

    @classmethod
    def relative(cls, seconds: float) -> Self:
        return cls(seconds=seconds, is_absolute=False)

    def to_absolute(self, start_time: float) -> Self:
        if self.is_absolute:
            return self
        return Deadline(start_time + self.seconds, is_absolute=True)


class RpcHandle(Generic[RpcRequest, RpcResponse, RpcStub], abc.ABC):
    def __init__(self, host: str = "localhost", port: int = 12345):
        self.channel = grpc.insecure_channel(f"{host}:{port}")

    @property
    @functools.cache
    @abc.abstractmethod
    def stub(self) -> RpcStub:
        raise NotImplementedError

    @abc.abstractmethod
    def __call__(self, rpc_request: RpcRequest) -> RpcResponse:
        raise NotImplementedError


@dataclass
class Implementation:
    rpc_handle: RpcHandle[RpcRequest, RpcResponse, RpcStub]
    message_handler: Callable[
        [Timestamp, InputT], Optional[Tuple[RpcRequest, Deadline]]
    ]
    response_handler: Callable[[RpcResponse], OutputT]
    priority: int


def register_implementation(
    implementations_list: List[Implementation],
    rpc_handle: RpcHandle[RpcRequest, RpcResponse, RpcStub],
    message_handler: Callable[
        [Timestamp, InputT], Optional[Tuple[RpcRequest, Deadline]]
    ],
    response_handler: Callable[[RpcResponse], OutputT],
    priority: int,
) -> List[Implementation]:
    """Register a cloud implementation.

    Args:
        implementations_list: List to store the implementation
        rpc_handle: Remote procedure call handle
        message_handler: Converts input to RPC request
        response_handler: Converts RPC response to output
        priority: Priority of the implementation

    Returns:
        Updated implementations list
    """
    implementations_list.append(
        Implementation(
            rpc_handle=rpc_handle,
            message_handler=message_handler,
            response_handler=response_handler,
            priority=priority,
        )
    )
    return implementations_list


def execute_cloud_separate_thread(
    imp: Implementation,
    timestamp: Timestamp,
    input_message: InputT,
    deadlines: List[Optional[float]],
    sem: Semaphore,
    result_heap: List,
    cloud_ex_times: defaultdict,
):
    """Execute cloud implementation in a separate thread.

    Args:
        imp: The cloud implementation to execute
        timestamp: Timestamp or identifier for the request
        input_message: The input message to process
        deadlines: List to store deadlines
        sem: Semaphore for synchronization
        result_heap: Heap to store results
        cloud_ex_times: Dictionary to track execution times
    """
    # get rpc request and deadline from message handler
    start_time = time.time()
    rpc_request, deadline = imp.message_handler(timestamp, input_message)

    deadlines.append(deadline)
    sem.release()

    # get rpc response and convert it to the output type
    response = imp.rpc_handle(rpc_request)
    elapsed_time = time.time() - start_time
    cloud_ex_times[imp.priority].append(elapsed_time)
    logger.info(f"Cloud implementation #{imp.priority} took {elapsed_time:.3f} s total")
    logger.info("response from server id=%d" % response.req_id)

    heapq.heappush(result_heap, (imp.priority, time.time(), response))
