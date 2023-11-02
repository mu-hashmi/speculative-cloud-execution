ARTIFACTS=

ARTIFACTS += image_pb2.py
ARTIFACTS += image_pb2_grpc.py 
ARTIFACTS += image_pb2.pyi 

all: ${ARTIFACTS}

image_pb2.py image_pb2_grpc.py image_pb2.pyi: image.proto
	python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --pyi_out=. -I . image.proto

clean:
	rm -f ${ARTIFACTS}