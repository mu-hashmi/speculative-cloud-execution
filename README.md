# Speculative Cloud Execution for Autonomous Vehicles

This project is a speculative execution system for object detection tasks that can be executed both locally and in the cloud. The implementation demonstrates the system designed in the research paper "Leveraging Cloud Computing to make Autonomous Vehicles Safer" [1](https://pschafhalter.com/papers/2023-iros-cloud-av-safety.pdf) and was developed in collaboration with Peter Schafhalter at Berkeley RISELab.

## About

This project implements a speculative operator system that:

1. Performs object detection on images/video frames using both local and cloud resources
2. Uses deadlines and priorities to determine which result to use
3. Provides a flexible, extensible framework for speculative computation
4. Demonstrates how to effectively manage latency-sensitive ML tasks across different execution environments

The system processes video frames by sending them simultaneously to local and cloud object detection services, then uses whichever result returns first or has the highest priority.

## How It Works

1. The `SpeculativeOperator` class defines the core functionality
2. When processing a message (e.g., a video frame):
   - The system sends the frame to both local and cloud object detection services
   - Each service processes the frame and returns detected objects
   - Based on deadlines and priorities, the system selects the best result
3. Performance statistics are collected to analyze the effectiveness of the approach

## Technologies and Frameworks

- **gRPC**: Powers the communication layer between local and cloud components, enabling efficient remote procedure calls with deadline support for the speculative execution system
- **Protocol Buffers**: Defines the message format (`Request` and `Response` in [`object_detection.proto`](protos/object_detection.proto)) for serializing image data and detection results between client and servers
- **Transformers (Hugging Face)**: Provides the object detection pipeline and models (DETR) used in both local execution and server implementations
- **OpenCV**: Handles video frame extraction, processing, and format conversion in the example applications
- **PyTorch**: Serves as the underlying deep learning framework that powers the DETR object detection models
- **Python Threading**: Implements the concurrent execution of local and cloud detection tasks with deadline management

## Project Structure

- **core/**: Core implementation of the speculative execution system
  - `coordinator.py`: Implementation of the speculative execution framework
  - `cloud_executor.py`: Handles cloud execution and RPC communication

- **examples/**: Example applications demonstrating the use of the system
  - `example_sync.py`: Example usage with synchronous processing
  - `example_stream.py`: Example usage with streaming processing (WIP)

- **servers/**: Server implementations for processing requests
  - `object_detection_server.py`: Implements the object detection service

- **protos/**: Protocol buffer definitions for communication
  - `object_detection.proto`: Defines the message format for the object detection service

## Getting Started

### Prerequisites

- Python 3.11 is recommended (other versions may work but are not tested)
- A virtual environment is strongly recommended for managing dependencies

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/speculative-cloud-execution.git
   cd speculative-cloud-execution
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

4. Compile the protocol buffers:
   ```bash
   # Note: You may need to modify the Makefile's PYTHON variable to point to your virtual environment's Python interpreter
   # By default it looks for ../venv_py311/bin/python
   make
   ```

### Running the Object Detection Server

Start an object detection server on a specific port:

```bash
python servers/object_detection_server.py --port 12345 --model facebook/detr-resnet-50
```

You can start multiple servers on different ports with different models for redundancy or comparison.

### Running the Example

Process a video file using the speculative execution system:

```bash
python examples/example_sync.py --video "path/to/your/video.mp4" --ports 12345 [12346 ...]
```

Optional flags:
- `--verbose`: Enable detailed logging of internal operations

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This project is based on the research paper "Leveraging Cloud Computing to Make Autonomous Vehicles Safer" [1](https://pschafhalter.com/papers/2023-iros-cloud-av-safety.pdf)
- Developed in collaboration with Peter Schafhalter at Berkeley RISELab