import io
import logging
import time

import coordinator
import requests
from coordinator import Deadline
from PIL import Image
from protos import object_detection_pb2, object_detection_pb2_grpc
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RESPONSE = "".join("A" for i in range(1000))


class MyOperator(coordinator.SpeculativeOperator[int, int]):
    def __init__(self):
        self.obj_detector = pipeline(
            "object-detection", model="facebook/detr-resnet-50"
        )

    def execute_local(self, input_message: int) -> int:
        response = requests.get(input_message)
        im = Image.open(io.BytesIO(response.content))
        logger.info("running object detector locally...")
        start_time = time.time()
        objs = self.obj_detector(im)
        elapsed_time = time.time() - start_time
        logger.info(f"elapsed time: {elapsed_time}")
        return objs


class RpcRequest:
    def __init__(self, input_message: str):
        self.input = input_message


class ImageRpcHandle(
    coordinator.RpcHandle[
        object_detection_pb2.Request,
        object_detection_pb2.Response,
        object_detection_pb2_grpc.GRPCImageStub,
    ]
):
    def stub(self) -> object_detection_pb2_grpc.GRPCImageStub:
        return object_detection_pb2_grpc.GRPCImageStub(self.channel)

    def __call__(
        self, rpc_request: object_detection_pb2.Request
    ) -> object_detection_pb2.Response:
        return self.stub().ProcessImageSync(rpc_request)


def test_speculative_operator():
    operator = MyOperator()
    ports = [54321, 12345]
    # register cloud implementations.
    for i, port in enumerate(ports):
        rpc_handle = ImageRpcHandle(port=port)
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    images = [  #'https://i.imgur.com/2lnWoly.jpg',
        "https://media-cldnry.s-nbcnews.com/image/upload/t_fit-1240w,f_auto,q_auto:best/rockcms/2023-08/230802-Waymo-driverless-taxi-ew-233p-e47145.jpg",
        "https://farm8.staticflickr.com/7117/7624759864_f1940fbfd3_z.jpg",
        "https://farm8.staticflickr.com/7419/10039650654_5d5a8b6706_z.jpg",
        "https://farm8.staticflickr.com/7135/8156447421_191b777e05_z.jpg",
    ]

    start_time = time.time()
    for i, img_url in enumerate(images):
        img = Image.open(requests.get(img_url, stream=True).raw)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()
        logger.info(f"{type(img_byte_arr)} {len(img_byte_arr)}")

        timestamp = i
        message = img_byte_arr
        result = operator.process_message(timestamp, message)
        if not result:
            logger.info("result empty")
        else:
            logger.info(result)

    elapsed_time = time.time() - start_time
    logger.info(f"sync took {elapsed_time} seconds to process all images")


def msg_handler(timestamp, input_message) -> tuple[RpcRequest, Deadline]:
    return object_detection_pb2.Request(
        image_data=input_message, req_id=timestamp
    ), Deadline(seconds=1.5, is_absolute=False)


def response_handler(input: object_detection_pb2.Response):
    pass


if __name__ == "__main__":
    test_speculative_operator()
