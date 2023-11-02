#!/bin/bash

## 0. dependency
# python -m pip install grpcio grpcio-tools

## 1. Make .proto
# make

## 2. make log dir
# mkdir log

## 3. run: 
## python client.py $HOST $PATTERN $NUM_ITER $WIDTH $HEIGHT $DELAY_IN_SECOND
python client.py 127.0.0.1 multi 100 1 11100 0.033