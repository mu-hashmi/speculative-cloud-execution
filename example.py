import time

import coordinator
from coordinator import Deadline
from paper_impl import image_pb2, image_pb2_grpc

RESPONSE = "".join("A" for i in range(1000))


class MyOperator(coordinator.SpeculativeOperator[int, int]):
    def execute_local(self, input_message: int) -> int:
        print("execute local")
        return input_message

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
        print("request received with the message len: %d" % (len(rpc_request.image_data)))
        recv_time = time.time()
        return image_pb2.Response(ack_data=RESPONSE, req_id=rpc_request.req_id, recv_time=recv_time)


def test_speculative_operator():
    # Create operator.
    operator = MyOperator()
    rpc_handle = ImageRpcHandle()

    # Register cloud implementations.
    for i in range(3):
        # rpc_handle = coordinator.RpcHandle(client.process_image_streaming)
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    for i in range(5):
        timestamp = i
        message = i
        operator.process_message(timestamp, message)

def msg_handler(timestamp, input) -> tuple[RpcRequest, Deadline]:
    return image_pb2.Request(image_data=str(input), req_id=timestamp), Deadline(seconds=0.5, is_absolute=False)

def rpc_handle1(rpc_request: RpcRequest):
    time.sleep(2)

def rpc_handle2(rpc_request: RpcRequest):
    time.sleep(1)

def response_handler(input: image_pb2.Response):
    pass

if __name__ == "__main__":
    test_speculative_operator()