import argparse
import io
import logging
import os
import time
import warnings
from concurrent import futures

# Suppress PyTorch warnings
os.environ["PYTHONWARNINGS"] = "ignore::UserWarning"
warnings.filterwarnings("ignore", category=UserWarning)

import grpc
import numpy as np
from PIL import Image
from protos import object_detection_pb2, object_detection_pb2_grpc
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = "12345"
ENCODING = "ISO-8859-1"
RESPONSE = "".join("A" for i in range(1000))


def process_image(image_data: bytes, obj_detector):
    im = Image.open(io.BytesIO(image_data))
    logger.info("running object detector on server...")
    start_time = time.time()
    objs = obj_detector(im)
    elapsed_time = time.time() - start_time
    logger.info(f"elapsed time: {elapsed_time}")
    return objs


def process_dummy_image(image_data):
    return np.frombuffer(image_data.encode(encoding=ENCODING), dtype=np.uint8)


class ImageServer(object_detection_pb2_grpc.GRPCImageServicer):
    def __init__(self, model_name: str):
        self.obj_detector = pipeline("object-detection", model=model_name)

    def ProcessImageSync(self, request, context):
        logger.info(
            "ProcessImageSync called by client with the message len: %d",
            len(request.image_data),
        )
        recv_time = time.time()
        detected_objects = process_image(request.image_data, self.obj_detector)
        response = object_detection_pb2.Response(
            detected_objects=detected_objects,
            req_id=request.req_id,
            recv_time=recv_time,
        )
        return response

    def ProcessImageStreaming(self, request_iterator, context):
        for request in request_iterator:
            recv_time = time.time()
            time.sleep(1.0)
            logger.info(
                "recv from client message size %d id %d",
                len(request.image_data),
                request.req_id,
            )
            detected_objects = process_image(request.image_data, self.obj_detector)
            yield object_detection_pb2.Response(
                detected_objects=detected_objects,
                req_id=request.req_id,
                recv_time=recv_time,
            )


def serve(port: str, model_name: str):
    options = [
        ("grpc.max_message_length", 1024 * 1024 * 1024),
        ("grpc.max_send_message_length", 1024 * 1024 * 1024),
        ("grpc.max_receive_message_length", 1024 * 1024 * 1024),
        ("grpc.http2.write_buffer_size", 1),
    ]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3), options=options)
    object_detection_pb2_grpc.add_GRPCImageServicer_to_server(
        ImageServer(model_name), server
    )
    server.add_insecure_port("[::]:" + port)
    print(
        f"------------------start Python GRPC server on port {port} with model {model_name}"
    )
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    parser = argparse.ArgumentParser(description="GRPC Object Detection Server")
    parser.add_argument(
        "--port", type=str, default="12345", help="Port to run the server on"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="facebook/detr-resnet-50",
        help="Object detection model to use (facebook/detr-resnet-50 or facebook/detr-resnet-101)",
    )
    args = parser.parse_args()
    serve(args.port, args.model)
