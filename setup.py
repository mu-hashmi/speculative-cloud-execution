from setuptools import find_packages, setup

setup(
    name="speculative-cloud-execution",
    version="0.1.0",
    description="Speculative execution system for object detection in autonomous vehicles",
    author="Muhammad Hashmi",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "grpcio>=1.59.2",
        "grpcio-tools>=1.59.2",
        "numpy>=2.0.0",
        "Pillow>=10.2.0",
        "protobuf>=4.25.0",
        "transformers>=4.52.3",
        "torch>=2.7.0",
        "opencv-python>=4.11.0.86",
        "requests>=2.32.3",
        "timm>=1.0.15",
        "torchvision>=0.22.0",
    ],
)
