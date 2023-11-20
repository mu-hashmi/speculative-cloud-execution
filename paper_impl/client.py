import grpc
import image_pb2
import image_pb2_grpc
import random
import time
from os import listdir
from os.path import isfile, join
import base64
import numpy as np
import fire

PORT = "12345"
ENCODING = "ISO-8859-1"


def get_image_str(images):
    select_image = images[random.randint(0, len(images) - 1)]
    im = open(select_image, "rb")
    return base64.b64encode(im.read())


def get_dummy_image_str(width, height):
    np_img = np.random.randint(0, 256, size=(width, height, 3), dtype=np.uint8)
    return np_img.tobytes().decode(encoding=ENCODING)


def get_random_bytes(size):
    array = np.random.randint(0, 256, size=size, dtype=np.uint8)
    return array.tobytes().decode(encoding=ENCODING)


def process_image_sync(stub, images, num_requests, width, height, sleep):
    print('calling client process_image_sync')
    image_str = get_dummy_image_str(width, height)
    for i in range(num_requests):
        start_time = time.time()
        request = image_pb2.Request(image_data=image_str, req_id=i)
        response = stub.ProcessImageSync(request)
        ack_string = response.ack_data
        cur = time.time()
        latency = cur - start_time
        upload = response.recv_time - start_time
        download = cur - response.recv_time
        print(
            "resp from server id=%d latency=%f upload=%f download=%f"
            % (response.req_id, 1e3 * latency, 1e3 * upload, 1e3 * download)
        )
        if latency <= sleep:
            time.sleep(sleep - latency)
        else:
            print("fall behind by %f" % (latency - sleep))


def process_image_streaming(stub, byte_size, frequency):
    start_times = dict()
    send_times = dict()
    sleep = 1.0 / frequency

    def request_messages():
        i = 0
        true_start = time.time()
        start_times[i] = time.time()
        max_concurrent_requests = 1.0 * frequency  # 1 seconds worth
        while True:
            if len(send_times) > max_concurrent_requests:
                k = 0
                while len(send_times) > 0:
                    time.sleep(0.1)
                    k += 1

            start_times[i + 1] = start_times[i] + 1.0 / frequency
            # image_str = get_image_str(images)
            # request = image_pb2.Request(image_data=get_image_str(images), req_id = i)
            # image_str = get_dummy_image_str(width, height)
            image_str = get_random_bytes(byte_size)
            request = image_pb2.Request(image_data=image_str, req_id=i)
            send_times[i] = time.time()
            yield request
            cur_time = time.time()
            sleep_time = start_times[i + 1] - cur_time
            total_dur = cur_time - true_start
            if sleep_time >= 0:
                time.sleep(sleep_time)
            else:
                start_times[i + 1] = time.time()
            i += 1

    response_iterator = stub.ProcessImageStreaming(request_messages())
    for response in response_iterator:
        recv_time = time.time()
        upload_ms = 1e3 * (response.recv_time - send_times[response.req_id])
        download_ms = 1e3 * (recv_time - response.recv_time)
        duration_ms = 1e3 * (time.time() - send_times[response.req_id])
        print('response time:', recv_time - send_times[response.req_id])
        del start_times[response.req_id]
        del send_times[response.req_id]
        print('received response with id', response.req_id)
        # (response.req_id, duration[response.req_id]))

def process_image_streaming_muhammad(stub, byte_size, frequency):
    start_times = dict()
    send_times = dict()
    sleep = 1.0 / frequency

    def request_messages():
        i = 0
        true_start = time.time()
        start_times[i] = time.time()
        max_concurrent_requests = 1.0 * frequency  # 1 seconds worth
        while True:

            start_times[i + 1] = start_times[i] + 1.0 / frequency
            # image_str = get_image_str(images)
            # request = image_pb2.Request(image_data=get_image_str(images), req_id = i)
            # image_str = get_dummy_image_str(width, height)
            image_str = get_random_bytes(byte_size)
            request = image_pb2.Request(image_data=image_str, req_id=i)
            send_times[i] = time.time()
            yield request
            cur_time = time.time()
            sleep_time = start_times[i + 1] - cur_time
            total_dur = cur_time - true_start
            if sleep_time >= 0:
                time.sleep(sleep_time)
            else:
                start_times[i + 1] = time.time()
            i += 1

    response_iterator = stub.ProcessImageStreaming(request_messages())
    for response in response_iterator:
        recv_time = time.time()
        upload_ms = 1e3 * (response.recv_time - send_times[response.req_id])
        download_ms = 1e3 * (recv_time - response.recv_time)
        duration_ms = 1e3 * (time.time() - send_times[response.req_id])
        print('response time:', recv_time - send_times[response.req_id])
        del start_times[response.req_id]
        del send_times[response.req_id]
        print('received response with id', response.req_id)
        # (response.req_id, duration[response.req_id]))


def main(host: str, pattern: str, byte_size: int, frequency: float, height: int, delay: float):
    files = []  # Not using real images
    # image_folder = "images"
    # filenames = [f for f in listdir(image_folder) if isfile(join(image_folder, f))]
    # files = [image_folder+'/'+ filename for filename in filenames]
    # print("List of images " + str(files))
    options = [
        ("grpc.max_message_length", 128 * 1024 * 1024),
        ("grpc.max_send_message_length", 128 * 1024 * 1024),
        ("grpc.max_receive_message_length", 128 * 1024 * 1024),
        ("grpc.http2.write_buffer_size", 1),
        # ("grpc.writeFlags.BUFFER_HINT", 1),
    ]
    # time_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

    with grpc.insecure_channel(host + ":" + PORT, options=options) as channel:
        stub = image_pb2_grpc.GRPCImageStub(channel)
        if pattern == "simple":
            process_image_sync(stub, files, byte_size, frequency, height, delay)
        elif pattern == "multi":
            process_image_streaming_muhammad(stub, byte_size, frequency)
        else:
            raise Exception("Error")


if __name__ == "__main__":
    fire.Fire(main)
