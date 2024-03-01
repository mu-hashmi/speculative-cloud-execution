import time
from typing import Union
from collections.abc import Iterator
import queue

import grpc

import coordinator
from coordinator import Deadline
from paper_impl import image_pb2, image_pb2_grpc

RESPONSE = "".join("A" for i in range(1000))


class MyOperator(coordinator.SpeculativeOperator[int, int]):
    def execute_local(self, input_message: int) -> int:
        pass

class RpcRequest:
    def __init__(self, input_message: str):
        self.input = input_message

# TODO:
# - implement this
# - test that you're sending requests and receiving responses from the example server.
class ImageRpcHandle(coordinator.RpcHandle[image_pb2.Request, image_pb2.Response, image_pb2_grpc.GRPCImageStub]):
    
    def stub(self) -> image_pb2_grpc.GRPCImageStub:
        return image_pb2_grpc.GRPCImageStub(self.channel)

    def __call__(self, rpc_request: Union[image_pb2.Request, Iterator[image_pb2.Request]]) -> image_pb2.Response:
        if hasattr(rpc_request, "__iter__"):
            print('calling process image streaming')
            return self.stub().ProcessImageStreaming(rpc_request)
        else:
            return self.stub().ProcessImageSync(rpc_request)


class StreamingIterator:
    def __init__(self):
        self.queue = queue.Queue()
        self.active = True
    
    def add_request(self, request):
        self.queue.put(request)

    def __iter__(self):
        while self.active:
            yield self.queue.get(block=True)

class StreamingImageRpcHandle(coordinator.RpcHandle[image_pb2.Request, image_pb2.Response, image_pb2_grpc.GRPCImageStub]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_iterator = StreamingIterator()
        stub = self.stub()
        self.response_iterator = stub.ProcessImageStreaming(self.request_iterator)

    def stub(self) -> image_pb2_grpc.GRPCImageStub:
        return image_pb2_grpc.GRPCImageStub(self.channel)
    
    def __call__(self, rpc_request):
        # Potential bug: this function might hang. May need to update some gRPC settings,
        # e.g. set ("grpc.http2.write_buffer_size", 1) in the gRPC client options.
        # Potential bug: the response might not correspond to the request. Check this!
        self.streaming_iterator.add_request(rpc_request)
        response = next(self.response_iterator)
        return response

def test_speculative_operator():
    # Create operator.
    operator = MyOperator()
    rpc_handle = ImageRpcHandle()
    images = ['https://i.imgur.com/2lnWoly.jpg', 
              'https://media-cldnry.s-nbcnews.com/image/upload/t_fit-1240w,f_auto,q_auto:best/rockcms/2023-08/230802-Waymo-driverless-taxi-ew-233p-e47145.jpg',
              'https://farm8.staticflickr.com/7117/7624759864_f1940fbfd3_z.jpg',
              'https://farm8.staticflickr.com/7419/10039650654_5d5a8b6706_z.jpg',
              'https://farm8.staticflickr.com/7135/8156447421_191b777e05_z.jpg']
    
    def request_iterator():
        for msg in images:
            yield image_pb2.Request(image_data=msg, req_id=int(time.time()))

    # Register cloud implementations.
    for i in range(3):
        # rpc_handle = coordinator.RpcHandle(client.process_image_streaming)
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    result = operator.process_message(1, request_iterator())
    # print(result)

    # for i, msg in enumerate(images):
    #     timestamp = i
    #     message = msg
    #     result = operator.process_message(timestamp, message)
    #     time.sleep(2.0) # to wait for each to get processed
    #     # maybe block until results is non-empty? 
    #     if not result:
    #         print('result empty')
    #     else:
    #         print(result)

    #     print(f"url: {msg}")

def msg_handler(timestamp, input_message) -> Iterator[tuple[RpcRequest, Deadline]]:
    for img in input_message:
        yield image_pb2.Request(image_data=img.image_data, req_id=timestamp), Deadline(seconds=1.5, is_absolute=False)

def response_handler(input: image_pb2.Response):
    pass

if __name__ == "__main__":
    test_speculative_operator()