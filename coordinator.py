import abc
import functools
import time
from dataclasses import dataclass
from threading import Semaphore, Thread
from typing import Callable, Generic, List, Optional, Self, Tuple, TypeVar
import heapq
import requests
from transformers import pipeline
from PIL import Image
import io
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import grpc

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
        cls(seconds=unix_time_seconds, is_absolute=True)

    @classmethod
    def relative(cls, seconds: float) -> Self:
        cls(seconds=seconds, is_absolute=False)

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


class SpeculativeOperator(abc.ABC, Generic[InputT, OutputT]):
    """Speculatively executes in the cloud and locally as a fallback."""

    def __init__(self):
        self.implementations = []
        self.thread = None
        self.local_result = None
        # self.obj_detector = pipeline("object-detection", model="facebook/detr-resnet-50")
        

    @abc.abstractmethod
    def execute_local(self, input_message: InputT) -> OutputT:
        response = requests.get(input_message)
        im = Image.open(io.BytesIO(response.content))
        logger.info("running object detector locally...")
        start_time = time.time()
        objs = self.obj_detector(im)
        elapsed_time = time.time() - start_time
        logger.info(f"elapsed time: {elapsed_time}")
        return objs

    def execute_local_separate_thread(self, input_message: InputT, result_heap: List):
        # self.local_result = self.execute_local(input_message)
        # time.sleep(1.2)
        # heapq.heappush(self.results, (-1, time.time(), self.local_result))
        pass

    def execute_cloud_separate_thread(
        self,
        imp: Implementation,
        timestamp: Timestamp,
        input_message: InputT,
        deadlines: List[Optional[float]],
        sem: Semaphore,
        result_heap: List
    ):
        # get rpc request and deadline from message handler
        rpc_handler = imp.msg_handler(timestamp, input_message)
        requests = []
        for rpc_request, deadline in rpc_handler:
            deadlines.append(deadline)
            sem.release()
            requests.append(rpc_request)

        # get rpc response and convert it to the output type
        for request in requests:
            response = imp.rpc_handle(rpc_request)
            logger.info("response from server id=%d", response.req_id)
        # result = imp.response_handler(response)

        heapq.heappush(result_heap, (imp.priority, time.time(), response))
        # print(result_heap)

    def process_message(self, timestamp: Timestamp, input_message: InputT) -> OutputT:
        # needs to call execute_local after calling all the message handlers
        logger.info("executing process_message")
        local_result_heap = []
        cloud_result_heap = []

        # Run execute_local in a separate thread
        self.local_thread = Thread(
            target=self.execute_local_separate_thread, args=(input_message, local_result_heap)
        )
        self.local_thread.start()
        deadlines = []
        sem = Semaphore(0)

        # create a thread for each cloud implementation
        cloud_threads = [
            Thread(
                target=self.execute_cloud_separate_thread,
                args=(imp, timestamp, input_message, deadlines, sem, cloud_result_heap),
            )
            for imp in sorted(self.implementations, key=lambda x: x.priority)
        ]

        # start all cloud threads
        start_time = time.time()
        for thread in cloud_threads:
            thread.start()

        for thread in cloud_threads:
            sem.acquire()

        # find min deadline
        min_deadline = min(deadlines, key=lambda deadline: deadline.seconds)

        threads = [self.local_thread] + cloud_threads
        thread_completed = False

        # get the first completed thread
        while not thread_completed:
            elapsed_time = time.time() - start_time
            if elapsed_time > min_deadline.seconds:
                break
    
            for thread in threads:
                if not thread.is_alive():
                    logger.info("finished execution before deadline")
                    thread_completed = True
                    break
            time.sleep(0.001)
        
        if not thread_completed:
            raise Exception("No threads finished before deadline!")
        
        while not local_result_heap and not cloud_result_heap:
            time.sleep(0.00001)
        
        if local_result_heap:
            result = heapq.heappop(local_result_heap)
        else:
            result = heapq.heappop(cloud_result_heap)

        while local_result_heap:
            heapq.heappop(local_result_heap)

        while cloud_result_heap:
            heapq.heappop(cloud_result_heap)

        return result
    
    def process_message_stream(self, timestamp: Timestamp, input_iterator: InputT) -> OutputT:
        # needs to call execute_local after calling all the message handlers
        logger.info("executing process_message_stream")
        local_result_heap = []
        cloud_result_heap = []

        for request in input_iterator:

            # Run execute_local in a separate thread
            self.local_thread = Thread(
                target=self.execute_local_separate_thread, args=(request.image_data, local_result_heap)
            )
            self.local_thread.start()
            deadlines = []
            sem = Semaphore(0)

            # create a thread for each cloud implementation
            cloud_threads = [
                Thread(
                    target=self.execute_cloud_separate_thread,
                    args=(imp, timestamp, request.image_data, deadlines, sem, cloud_result_heap),
                )
                for imp in sorted(self.implementations, key=lambda x: x.priority)
            ]

            # start all cloud threads
            start_time = time.time()
            for thread in cloud_threads:
                thread.start()

            for thread in cloud_threads:
                sem.acquire()

            # find min deadline
            min_deadline = min(deadlines, key=lambda deadline: deadline.seconds)

            threads = [self.local_thread] + cloud_threads
            thread_completed = False

            # get the first completed thread
            while not thread_completed:
                elapsed_time = time.time() - start_time
                if elapsed_time > min_deadline.seconds:
                    break
        
                for thread in threads:
                    if not thread.is_alive():
                        logger.info("finished execution before deadline")
                        thread_completed = True
                        break
                time.sleep(0.001)
            
            if not thread_completed:
                raise Exception("No threads finished before deadline!")
            
            while not local_result_heap and not cloud_result_heap:
                time.sleep(0.00001)
            
            if local_result_heap:
                result = heapq.heappop(local_result_heap)
            else:
                result = heapq.heappop(cloud_result_heap)

            local_result_heap = []
            cloud_result_heap = []

            print(result)

    def use_cloud(
        self,
        rpc_handle: RpcHandle[RpcRequest, RpcResponse, RpcStub],
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
