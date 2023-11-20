import coordinator


class MyOperator(coordinator.SpeculativeOperator[int, int]):
    def execute_local(self, input_message: int) -> int:
        print("execute local")
        return 2 * input_message


def test_speculative_operator():
    # Create operator.
    operator = MyOperator()

    # Register cloud implementations.
    for i in range(3):
        rpc_handle = coordinator.RpcHandle()  # TODO: implement
        operator.use_cloud(
            rpc_handle,
            message_handler=lambda t, inp: print(f"message_handler {i}"),
            response_handler=lambda _: int(print(f"response_handler {i}")),
            priority=i,
        )

    for i in range(5):
        timestamp = i
        message = i
        operator.process_message(timestamp, message)
