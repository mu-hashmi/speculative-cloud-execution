import grpc
import image_pb2
import image_pb2_grpc
import sys
import random
import io
import time
import datetime
import logging
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


def simple_method(stub, images, num_requests, width, height, sleep, logger, csv_logger):
    print("--------------Call SimpleMethod Begin--------------")
    image_str = get_dummy_image_str(width, height)
    for i in range(num_requests):
        start_time = time.time()
        request = image_pb2.Request(image_data=image_str, req_id = i)
        response = stub.SimpleMethod(request)
        ack_string = response.ack_data
        cur = time.time()
        latency = cur - start_time
        upload = response.recv_time - start_time
        download = cur - response.recv_time
        print("resp from server id=%d latency=%f upload=%f download=%f" % (response.req_id, 1e3 * latency, 1e3 * upload, 1e3 * download))
        logger.info("id %d latency %f upload %f download %f\n" % (response.req_id, latency, upload, download))
        logger.info(f"{id},{latency},{upload},{download}")
        if latency <= sleep:
            time.sleep(sleep - latency)
        else:
            print("fall behind by %f" % (latency - sleep))
            log.write("fall behind %f\n"% (latency - sleep))
    print("--------------Call SimpleMethod Over---------------")


def bidirectional_streaming_method(stub, byte_size, frequency, logger, csv_logger):
    logger.info("--------------Call BidirectionalStreamingMethod Begin---------------")
    # duration = [0 for i in range(num_requests)]
    # start_time = [0 for i in range(num_requests)]
    # Used for sending at a fixed frequency.
    start_times = dict()
    send_times = dict()
    sleep = 1.0 / frequency

    def request_messages():
        i = 0
        true_start = time.time()
        start_times[i] = time.time()
        max_concurrent_requests = 1.0 * frequency # 1 seconds worth
        while True:
            if len(send_times) > max_concurrent_requests:
                k = 0
                while len(send_times) > 0:
                    if k % 10 == 0:
                        logger.warning(f"Queued {len(send_times)} concurrent requests...recovering")
                    time.sleep(0.1)
                    k += 1

            start_times[i + 1] = start_times[i] + 1.0 / frequency
            # image_str = get_image_str(images)
            # request = image_pb2.Request(image_data=get_image_str(images), req_id = i)
            # image_str = get_dummy_image_str(width, height)
            image_str = get_random_bytes(byte_size)
            request = image_pb2.Request(image_data=image_str, req_id=i)
            logger.info(f"Sending request id={i}, active_requests={len(start_times)}")
            send_times[i] = time.time()
            yield request
            cur_time = time.time()
            sleep_time = start_times[i + 1] - cur_time
            total_dur = cur_time - true_start
            # logger.info(f"{i + 1} requests in {total_dur} sec {(i + 1) / total_dur} req/s")
            if sleep_time >= 0:
                # logging.info(f"sleep {sleep_time}")
                time.sleep(sleep_time)
            else:
                logger.warning(f"Fell behind by {abs(sleep_time)} s")
                start_times[i + 1] = time.time()
            i += 1

    response_iterator = stub.BidirectionalStreamingMethod(request_messages())
    for response in response_iterator:
        recv_time = time.time()
        upload_ms = 1e3 * (response.recv_time - send_times[response.req_id])
        download_ms = 1e3 * (recv_time - response.recv_time)
        duration_ms = 1e3 * (time.time() - send_times[response.req_id])
        logger.info(
            f"response from server id={response.req_id}, total={duration_ms:.2f} ms, upload={upload_ms:.2f} ms, download={download_ms:.2f} ms"
        )
        csv_logger.info(f"{response.req_id},{duration_ms},{upload_ms},{download_ms}")
        del start_times[response.req_id]
        del send_times[response.req_id]
        # logger.info("resp from server id=%d time=%f" %
        # (response.req_id, duration[response.req_id]))

    logger.info("--------------Call BidirectionalStreamingMethod Over---------------")


def main(host: str, pattern: str, byte_size: int, frequency: float):
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
    date_fmt = "%Y-%m-%d-%H:%M:%S"
    date_fmt = "%Y-%m-%dT%H:%M:%S"
    time_str = datetime.datetime.now().strftime(date_fmt)
    csv_filename = f"log/FR{frequency}-{time_str}.csv"
    filename = f"log/FR{frequency}-{time_str}.log"

    logging.root.setLevel(logging.NOTSET)
    csv_handler = logging.FileHandler(csv_filename)
    csv_handler.setLevel(logging.DEBUG)
    csv_fmt = "%(asctime)s.%(msecs)03d,%(message)s"
    csv_formatter = logging.Formatter(fmt=csv_fmt, datefmt=date_fmt)
    csv_handler.setFormatter(csv_formatter)
    csv_logger = logging.getLogger("csv_logger")
    csv_logger.addHandler(csv_handler)
    csv_logger.propagate = False

    handler = logging.FileHandler(filename)
    handler.setLevel(logging.DEBUG)
    fmt = "%(asctime)s.%(msecs)03d %(name)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(fmt=fmt, datefmt=date_fmt)
    handler.setFormatter(formatter)
    logger = logging.getLogger("logger")
    logger.addHandler(handler)
    # logger.propagate = False
    stream_handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    with grpc.insecure_channel(host + ":" + PORT, options=options) as channel:
        stub = image_pb2_grpc.GRPCImageStub(channel)
        if pattern == "simple":
            # Broken
            # simple_method(stub, files, 100, 1920, 1080, 0.1, logger)
            pass
        elif pattern == "multi":
            bidirectional_streaming_method(
                stub, byte_size, frequency, logger, csv_logger
            )
        else:
            raise Exception("Error")


if __name__ == "__main__":
    fire.Fire(main)
