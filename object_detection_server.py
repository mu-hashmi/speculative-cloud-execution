import grpc
import logging
from protos import object_detection_pb2
from protos import object_detection_pb2_grpc
import io
import base64
import numpy as np
import time
from transformers import pipeline
import requests
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from random import choice
from string import ascii_uppercase
from threading import Thread
from PIL import Image
from concurrent import futures

PORT = "12345"
ENCODING = "ISO-8859-1"
# response_str = ''.join(choice(ascii_uppercase) for i in range(1000))
RESPONSE = "".join("A" for i in range(1000))

def process_image(image_data: bytes, obj_detector):
    # response = requests.get(image_data)
    im = Image.open(io.BytesIO(image_data))
    logger.info("running object detector...")
    start_time = time.time()
    objs = obj_detector(im)
    elapsed_time = time.time() - start_time
    logger.info(f"elapsed time: {elapsed_time}")
    return objs

def process_dummy_image(image_data):
    return np.frombuffer(image_data.encode(encoding=ENCODING), dtype=np.uint8)


class ImageServer(object_detection_pb2_grpc.GRPCImageServicer):
    def __init__(self):
        self.obj_detector = pipeline("object-detection", model="facebook/detr-resnet-50")

    def ProcessImageSync(self, request, context):
        logger.info("ProcessImageSync called by client with the message len: %d", len(request.image_data))
        # image_received = process_image(request.image_data)
        recv_time = time.time()
        detected_objects = process_image(request.image_data, self.obj_detector)
        # print(detected_objects)
        response = object_detection_pb2.Response(
            detected_objects=detected_objects, req_id=request.req_id, recv_time=recv_time
        )
        return response

    def ProcessImageStreaming(self, request_iterator, context):
        for request in request_iterator:
            print('iterating')
            recv_time = time.time()
            time.sleep(1.0)
            logger.info(
                "recv from client message size %d id %d",
                len(request.image_data),
                request.req_id
            )
            # image_received = process_image(request.image_data)
            detected_objects = process_image(request.image_data, self.obj_detector)
            # print(image_received)
            yield object_detection_pb2.Response(
                detected_objects=detected_objects, req_id=request.req_id, recv_time=recv_time
            )


def serve():
    options = [
        ("grpc.max_message_length", 1024 * 1024 * 1024),
        ("grpc.max_send_message_length", 1024 * 1024 * 1024),
        ("grpc.max_receive_message_length", 1024 * 1024 * 1024),
        ("grpc.http2.write_buffer_size", 1),
    ]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=3), options=options)
    object_detection_pb2_grpc.add_GRPCImageServicer_to_server(ImageServer(), server)
    server.add_insecure_port("[::]:" + PORT)
    print("------------------start Python GRPC server")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
