import argparse
import io
import logging
import os
import time
import warnings
from statistics import median

# Suppress PyTorch warnings
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"
warnings.filterwarnings("ignore", category=UserWarning)

import coordinator
import cv2
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
        super().__init__()
        self.obj_detector = pipeline(
            "object-detection", model="facebook/detr-resnet-50"
        )
        self.local_ex_times = []

    def execute_local(self, input_message):
        im = Image.open(io.BytesIO(input_message))
        objs = self.obj_detector(im)
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


def test_speculative_operator(video_path=None, server_ports=None):
    operator = MyOperator()
    # register cloud implementations.
    for i, port in enumerate(server_ports):
        rpc_handle = ImageRpcHandle(port=port)
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    start_time = time.time()
    vidcap = (
        video_path if video_path is not None else 1
    )  # use filepath if provided, else load from webcam (1)

    logger.info(f"vidcap = {vidcap}")
    cap = cv2.VideoCapture(vidcap)
    fps = cap.get(cv2.CAP_PROP_FPS)  # needed to send to server at same frequency
    frame_id = 0

    specop_times = []

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret or frame_id == 30:
            logger.warning(f"Can't receive frame or video ended on frame {frame_id}")
            break

        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_byte_arr = io.BytesIO()
        frame_pil.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()
        # logger.info(f"{type(img_byte_arr)} {len(img_byte_arr)}")
        message = img_byte_arr

        specop_start_time = time.time()
        result = operator.process_message(frame_id, message)
        specop_elapsed_time = time.time() - specop_start_time
        specop_times.append(specop_elapsed_time)
        logger.info(
            f"speculative execution time on frame {frame_id}: {specop_elapsed_time:.3f}"
        )

        time.sleep(1.0 / fps)  # wait for duration of a frame before proceeding

        if not result:
            logger.info("result empty")
        # else:
        #     logger.info(f"result = {result}")

        frame_id += 1

    median_local_time = median(operator.local_ex_times)
    mean_local_time = sum(operator.local_ex_times) / len(operator.local_ex_times)
    mean_cloud_times = {}
    median_cloud_times = {}
    for imp in operator.cloud_ex_times:
        mean_cloud_times[imp] = sum(operator.cloud_ex_times[imp]) / len(
            operator.cloud_ex_times[imp]
        )
        median_cloud_times[imp] = median(operator.cloud_ex_times[imp])
    mean_spec_time = sum(specop_times) / len(specop_times)
    median_spec_time = median(specop_times)

    logger.info(f"median local time: {median_local_time:.3f}")
    for imp in median_cloud_times:
        logger.info(f"median {imp} cloud time: {mean_cloud_times[imp]:.3f}")

    logger.info(f"median speculative op time: {median_spec_time:.3f}")

    elapsed_time = time.time() - start_time
    logger.info(f"sync took {elapsed_time} seconds to process all images")


def msg_handler(timestamp, input_message) -> tuple[RpcRequest, Deadline]:
    return object_detection_pb2.Request(
        image_data=input_message, req_id=timestamp
    ), Deadline(seconds=3.0, is_absolute=False)


def response_handler(input: object_detection_pb2.Response):
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=str, help="Path to the input video file")
    parser.add_argument(
        "--ports", nargs="+", type=int, help="List of server ports", required=True
    )
    args = parser.parse_args()

    test_speculative_operator(video_path=args.video, server_ports=args.ports)
