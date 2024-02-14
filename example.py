import time

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

    def __call__(self, rpc_request: image_pb2.Request) -> image_pb2.Response:
        return self.stub().ProcessImageSync(rpc_request)


def test_speculative_operator():
    # Create operator.
    operator = MyOperator()
    rpc_handle = ImageRpcHandle()
    images = ['https://i.imgur.com/2lnWoly.jpg', 'https://media-cldnry.s-nbcnews.com/image/upload/t_fit-1240w,f_auto,q_auto:best/rockcms/2023-08/230802-Waymo-driverless-taxi-ew-233p-e47145.jpg',
              'https://farm8.staticflickr.com/7117/7624759864_f1940fbfd3_z.jpg',
              'https://farm8.staticflickr.com/7419/10039650654_5d5a8b6706_z.jpg',
              'https://farm8.staticflickr.com/7135/8156447421_191b777e05_z.jpg']

    # Register cloud implementations.
    for i in range(1):
        # rpc_handle = coordinator.RpcHandle(client.process_image_streaming)
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    for i, msg in enumerate(images):
        timestamp = i
        message = msg
        operator.process_message(timestamp, message)
        time.sleep(1.2) # to wait for each to get processed
        # maybe block until results is non-empty? 
        print(operator.results)
        operator.results.pop()
        print(f"url: {msg}")

def msg_handler(timestamp, input_message) -> tuple[RpcRequest, Deadline]:
    return image_pb2.Request(image_data=input_message, req_id=timestamp), Deadline(seconds=1.5, is_absolute=False)

def response_handler(input: image_pb2.Response):
    pass

if __name__ == "__main__":
    test_speculative_operator()