ARTIFACTS=

ARTIFACTS += object_detection_pb2.py
ARTIFACTS += object_detection_pb2_grpc.py 
ARTIFACTS += object_detection_pb2.pyi

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S), Linux)
	REPLACE_CMD = sed -i "s/import object_detection_pb2/import protos.object_detection_pb2/g" "protos/object_detection_pb2_grpc.py"
else ifeq ($(UNAME_S), Darwin)
	REPLACE_CMD = sed -i "" "s/import object_detection_pb2/import protos.object_detection_pb2/g" "protos/object_detection_pb2_grpc.py"
endif

# Use Python from parent directory's virtual environment
# Python 3.11 is used for package compatibility. Other versions may work, but are not tested.
PYTHON := ../venv_py311/bin/python

all: ${ARTIFACTS}

object_detection_pb2.py object_detection_pb2_grpc.py object_detection_pb2.pyi object_detection.proto:
	$(PYTHON) -m grpc_tools.protoc --python_out=./protos --grpc_python_out=./protos --pyi_out=./protos -I protos/ protos/object_detection.proto
	$(REPLACE_CMD)
	

clean:
	rm -f protos/*.py protos/*.pyi
