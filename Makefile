ARTIFACTS=

ARTIFACTS += object_detection_pb2.py
ARTIFACTS += object_detection_pb2_grpc.py 
ARTIFACTS += object_detection_pb2.pyi 

all: ${ARTIFACTS}

object_detection_pb2.py object_detection_pb2_grpc.py object_detection_pb2.pyi object_detection.proto:
	python -m grpc_tools.protoc --python_out=./protos --grpc_python_out=./protos --pyi_out=./protos -I protos/ protos/object_detection.proto
	sed -i "" "s/import object_detection_pb2/import protos.object_detection_pb2/g" "protos/object_detection_pb2_grpc.py"

clean:
	rm -f protos/*.py protos/*.pyi