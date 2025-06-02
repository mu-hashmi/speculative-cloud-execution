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

import cloud_executor
import coordinator
import cv2
from cloud_executor import Deadline
from PIL import Image
from protos import object_detection_pb2, object_detection_pb2_grpc
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FRAME_LIMIT = 30


class ObjectDetectionOperator(coordinator.SpeculativeOperator[int, int]):
    """Operator that performs object detection locally and in the cloud,
    then using whichever result arrives first.
    """

    def __init__(self):
        super().__init__()
        self.obj_detector = pipeline(
            "object-detection", model="facebook/detr-resnet-50"
        )

    def execute_local(self, input_message):
        """Execute object detection locally on the input image data."""
        im = Image.open(io.BytesIO(input_message))
        objs = self.obj_detector(im)
        return objs


class ImageRpcHandle(
    cloud_executor.RpcHandle[
        object_detection_pb2.Request,
        object_detection_pb2.Response,
        object_detection_pb2_grpc.GRPCImageStub,
    ]
):
    """RPC handle for communicating with the object detection server."""

    def stub(self) -> object_detection_pb2_grpc.GRPCImageStub:
        """Create a gRPC stub for the object detection service."""
        return object_detection_pb2_grpc.GRPCImageStub(self.channel)

    def __call__(
        self, rpc_request: object_detection_pb2.Request
    ) -> object_detection_pb2.Response:
        """Send a synchronous request to the object detection server."""
        return self.stub().ProcessImageSync(rpc_request)


def report_performance_statistics(operator, specop_times, total_time, frame_count):
    """Report performance statistics for video processing.

    Args:
        operator: The SpeculativeOperator instance used for processing
        specop_times: List of execution times for each speculative operation
        total_time: Total processing time
        frame_count: Number of frames processed
    """
    if operator.local_ex_times:
        median_local_time = median(operator.local_ex_times)
        logger.info(f"Median local execution time: {median_local_time:.3f}s")

    for imp in operator.cloud_ex_times:
        if operator.cloud_ex_times[imp]:
            median_cloud_time = median(operator.cloud_ex_times[imp])
            logger.info(
                f"Median cloud execution time (impl {imp}): {median_cloud_time:.3f}s"
            )

    if specop_times:
        median_spec_time = median(specop_times)
        logger.info(f"Median speculative execution time: {median_spec_time:.3f}s")

    logger.info(f"Total processing time: {total_time:.3f}s")
    logger.info(
        f"Successfully processed {frame_count} frames using speculative execution"
    )


def process_video(video_path, server_ports):
    """Process a video using speculative execution with local and cloud detection.

    Args:
        video_path: Path to the video file to process
        server_ports: List of ports where object detection servers are running
    """
    operator = ObjectDetectionOperator()

    # Register cloud implementations for each provided server port
    for i, port in enumerate(server_ports):
        rpc_handle = ImageRpcHandle(port=port)
        operator.use_cloud(
            rpc_handle,
            msg_handler,
            response_handler,
            priority=i,
        )

    logger.info(f"Processing video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(f"Video has {total_frames} frames at {fps} FPS")

    start_time = time.time()
    frame_id = 0
    specop_times = []

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret or frame_id == FRAME_LIMIT:
            logger.info(f"Finished processing video after {frame_id} frames")
            break

        # Convert frame to format suitable for processing
        frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img_byte_arr = io.BytesIO()
        frame_pil.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        # Process frame using speculative execution
        specop_start_time = time.time()
        result = operator.process_message(frame_id, img_byte_arr)
        specop_elapsed_time = time.time() - specop_start_time
        specop_times.append(specop_elapsed_time)

        logger.info(
            f"Frame {frame_id}/{total_frames}: processed in {specop_elapsed_time:.3f}s"
        )

        # Respect original video timing
        time.sleep(1.0 / fps)
        frame_id += 1

    cap.release()

    total_time = time.time() - start_time
    report_performance_statistics(operator, specop_times, total_time, frame_id)


def msg_handler(
    timestamp, input_message
) -> tuple[object_detection_pb2.Request, Deadline]:
    """Prepare a request to send to the object detection server.

    Args:
        timestamp: Frame ID or other identifier
        input_message: Raw image data to process

    Returns:
        A tuple of (request object, deadline)
    """
    return object_detection_pb2.Request(
        image_data=input_message, req_id=timestamp
    ), Deadline(seconds=3.0, is_absolute=False)


def response_handler(response: object_detection_pb2.Response):
    """Process the response from the object detection server.

    This function can be expanded to handle the detected objects.

    Args:
        response: Response from the object detection server
    """
    return response.detected_objects


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Speculative execution example for object detection"
    )
    parser.add_argument(
        "--video", type=str, required=True, help="Path to the input video file"
    )
    parser.add_argument(
        "--ports",
        nargs="+",
        type=int,
        required=True,
        help="List of server ports where object detection servers are running",
    )
    args = parser.parse_args()

    process_video(video_path=args.video, server_ports=args.ports)
