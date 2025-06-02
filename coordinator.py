import abc
import heapq
import logging
import time
from collections import defaultdict
from threading import Semaphore, Thread
from typing import Generic, List

from cloud_executor import (
    Deadline,
    Implementation,
    InputT,
    OutputT,
    RpcHandle,
    RpcRequest,
    RpcResponse,
    RpcStub,
    Timestamp,
    execute_cloud_separate_thread,
    logger,
    register_implementation,
)


class SpeculativeOperator(abc.ABC, Generic[InputT, OutputT]):
    """Speculatively executes in the cloud and locally as a fallback."""

    def __init__(self):
        self.implementations = []
        self.thread = None
        self.local_result = None
        self.cloud_ex_times = defaultdict(list)
        self.local_ex_times = []

    @abc.abstractmethod
    def execute_local(self, input_message: InputT) -> OutputT:
        raise NotImplementedError()

    def execute_local_separate_thread(self, input_message: InputT, result_heap: List):
        start_time = time.time()
        self.local_result = self.execute_local(input_message)
        elapsed_time = time.time() - start_time
        self.local_ex_times.append(elapsed_time)
        logger.info(f"Local ex took {elapsed_time:.3f} s")
        # time.sleep(1.2)
        heapq.heappush(result_heap, (-1, time.time(), self.local_result))

    def process_message(self, timestamp: Timestamp, input_message: InputT) -> OutputT:
        # needs to call execute_local after calling all the message handlers
        logger.info("executing process_message")
        local_result_heap = []
        cloud_result_heap = []

        # Run execute_local in a separate thread
        self.local_thread = Thread(
            target=self.execute_local_separate_thread,
            args=(input_message, local_result_heap),
        )
        self.local_thread.start()
        deadlines = []
        sem = Semaphore(0)

        # create a thread for each cloud implementation
        cloud_threads = [
            Thread(
                target=execute_cloud_separate_thread,
                args=(
                    imp,
                    timestamp,
                    input_message,
                    deadlines,
                    sem,
                    cloud_result_heap,
                    self.cloud_ex_times,
                ),
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

    def use_cloud(
        self,
        rpc_handle: RpcHandle[RpcRequest, RpcResponse, RpcStub],
        message_handler: callable,
        response_handler: callable,
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
        self.implementations = register_implementation(
            self.implementations,
            rpc_handle=rpc_handle,
            message_handler=message_handler,
            response_handler=response_handler,
            priority=priority,
        )
