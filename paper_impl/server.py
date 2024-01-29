import grpc
import logging
import image_pb2
import image_pb2_grpc
import io
import base64
import numpy as np
import time
from transformers import pipeline
import requests

from random import choice
from string import ascii_uppercase
from threading import Thread
from PIL import Image
from concurrent import futures

PORT = "12345"
ENCODING = "ISO-8859-1"
# response_str = ''.join(choice(ascii_uppercase) for i in range(1000))
RESPONSE = "".join("A" for i in range(1000))
obj_detector = pipeline("object-detection", model="devonho/detr-resnet-50_finetuned_cppe5")


def process_image(image_data):
    im = io.BytesIO(base64.b64decode(image_data))
    pilimage = Image.open(requests.get(im, stream=True).raw)
    # pilimage = pilimage.save("received.png")
    return obj_detector(pilimage)


def process_dummy_image(image_data):
    return np.frombuffer(image_data.encode(encoding=ENCODING), dtype=np.uint8)


class ImageServer(image_pb2_grpc.GRPCImageServicer):
    def ProcessImageSync(self, request, context):
        print("ProcessImageSync called by client with the message len: %d" % (len(request.image_data)))
        # image_received = process_image(request.image_data)
        recv_time = time.time()
        image_received = process_dummy_image(request.image_data)
        # print(image_received)
        response = image_pb2.Response(
            detected_objects=[1,2,3,4], req_id=request.req_id, recv_time=recv_time
        )
        return response

    def ProcessImageStreaming(self, request_iterator, context):
        for request in request_iterator:
            recv_time = time.time()
            time.sleep(1.0)
            print(
                "recv from client message size %d id %d"
                % (len(request.image_data), request.req_id)
            )
            # image_received = process_image(request.image_data)
            image_received = process_dummy_image(request.image_data)
            # print(image_received)
            yield image_pb2.Response(
                ack_data=RESPONSE, req_id=request.req_id, recv_time=recv_time
            )


def serve():
    options = [
        ("grpc.max_message_length", 128 * 1024 * 1024),
        ("grpc.max_send_message_length", 128 * 1024 * 1024),
        ("grpc.max_receive_message_length", 128 * 1024 * 1024),
    ]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1), options=options)
    image_pb2_grpc.add_GRPCImageServicer_to_server(ImageServer(), server)
    server.add_insecure_port("[::]:" + PORT)
    print("------------------start Python GRPC server")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
