import time
from typing import Union
from collections.abc import Iterator
import queue
from PIL import Image
import io
import requests

import grpc

import coordinator
from coordinator import Deadline
from protos import object_detection_pb2, object_detection_pb2_grpc

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
class ImageRpcHandle(coordinator.RpcHandle[object_detection_pb2.Request, object_detection_pb2.Response, object_detection_pb2_grpc.GRPCImageStub]):
    
    def stub(self) -> object_detection_pb2_grpc.GRPCImageStub:
        return object_detection_pb2_grpc.GRPCImageStub(self.channel)

    def __call__(self, rpc_request: Union[object_detection_pb2.Request, Iterator[object_detection_pb2.Request]]) -> object_detection_pb2.Response:
            return self.stub().ProcessImageSync(rpc_request)


class StreamingIterator:
    def __init__(self):
        self.queue = queue.Queue()
        self.active = True
    
    def add_request(self, request):
        print('adding request')
        self.queue.put(request)

    def __iter__(self):
        return self
    
    def __next__(self):
        while self.active:
            return self.queue.get(block=True)

class StreamingImageRpcHandle(coordinator.RpcHandle[object_detection_pb2.Request, object_detection_pb2.Response, object_detection_pb2_grpc.GRPCImageStub]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_iterator = StreamingIterator()
        stub = self.stub()
        self.response_iterator = stub.ProcessImageStreaming(self.request_iterator)

    def stub(self) -> object_detection_pb2_grpc.GRPCImageStub:
        return object_detection_pb2_grpc.GRPCImageStub(self.channel)
    
    def __call__(self, rpc_request):
        # Potential bug: this function might hang. May need to update some gRPC settings,
        # e.g. set ("grpc.http2.write_buffer_size", 1) in the gRPC client options.
        # Potential bug: the response might not correspond to the request. Check this!
        self.request_iterator.add_request(rpc_request)
        response = next(self.response_iterator)
        return response

def test_speculative_operator():
    # Create operator.
    operator = MyOperator()
    # rpc_handle = StreamingImageRpcHandle()
    images = [# 'https://i.imgur.com/2lnWoly.jpg', 
              'https://media-cldnry.s-nbcnews.com/image/upload/t_fit-1240w,f_auto,q_auto:best/rockcms/2023-08/230802-Waymo-driverless-taxi-ew-233p-e47145.jpg',
              'https://farm8.staticflickr.com/7117/7624759864_f1940fbfd3_z.jpg',
              'https://farm8.staticflickr.com/7419/10039650654_5d5a8b6706_z.jpg',
              'https://farm8.staticflickr.com/7135/8156447421_191b777e05_z.jpg']

    # Register cloud implementations.
    for i in range(3): # TODO: this doesn't work for streaming when the range is > 1
        # rpc_handle = coordinator.RpcHandle(client.process_image_streaming)
        rpc_handle = StreamingImageRpcHandle()
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    for i, img_url in enumerate(images):
        img = Image.open(requests.get(img_url, stream=True).raw)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        print(type(img_byte_arr), len(img_byte_arr))

        timestamp = i
        message = img_byte_arr
        result = operator.process_message(timestamp, message)
        #time.sleep(2.0) # to wait for each to get processed
        # maybe block until results is non-empty? 
        if not result:
            print('result empty')
        else:
            print(result)

        # print(f"url: {msg}")

def msg_handler(timestamp, input_message) -> tuple[RpcRequest, Deadline]:
    return object_detection_pb2.Request(image_data=input_message, req_id=timestamp), Deadline(seconds=1.5, is_absolute=False)

def response_handler(input: object_detection_pb2.Response):
    pass

if __name__ == "__main__":
    test_speculative_operator()