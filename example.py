import coordinator
from paper_impl import client
import time
from coordinator import Deadline

class MyOperator(coordinator.SpeculativeOperator[int, int]):
    def execute_local(self, input_message: int) -> int:
        print("execute local")
        return input_message

class RpcRequest:
    def __init__(self, input_message: str):
        self.input = input_message

def test_speculative_operator():
    # Create operator.
    operator = MyOperator()

    # Register cloud implementations.
    for i in range(3):
        # rpc_handle = coordinator.RpcHandle(client.process_image_streaming)
        operator.use_cloud(
            rpc_handle1,
            msg_handler,
            response_handler=lambda _: print(f"response_handler {i}"),
            priority=i,
        )

    for i in range(5):
        timestamp = i
        message = i
        operator.process_message(timestamp, message)

def msg_handler(timestamp, input) -> tuple[RpcRequest, Deadline]:
    return RpcRequest(input), Deadline(seconds=0.5, is_absolute=False)

def rpc_handle1(rpc_request: RpcRequest):
    time.sleep(2)

def rpc_handle2(rpc_request: RpcRequest):
    time.sleep(1)

if __name__ == "__main__":
    test_speculative_operator()