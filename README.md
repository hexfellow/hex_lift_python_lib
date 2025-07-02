# Hex Lift Python Library

A Python library for controlling hex lift through a WebSocket-based API.

## Overview

This library provides a simple interface for communicating with and controlling hex lifts. It uses Protocol Buffers for message serialization and WebSocket for real-time communication.

## Prerequisites

- Python 3.10 or higher
- Anaconda Distribution (recommended for beginners) - includes Python, NumPy, and commonly used scientific computing packages

## Installation

### Option 1: Direct Usage (No Installation)

If you prefer to run the library without installing it in your Python environment:

1. **Compile Protocol Buffer messages:**
   ```bash
   mkdir ./hex_lift/generated
   protoc --proto_path=proto-public-api --python_out=hex_lift/generated proto-public-api/*.proto
   ```

2. **Add the library path to your script:**
   ```python
   import sys
   sys.path.insert(1, '<your project path>/hex_lift_python_lib')
   sys.path.insert(1, '<your project path>/hex_lift_python_lib/hex_lift/generated')
   ```

3. **Run your test script:**
   ```bash
   python3 tests/<your_script>.py
   ```

### Option 2: Package Installation

To install the library in your Python environment:

1. **Build the package:**
   ```bash
   python3 -m build
   ```

2. **Install the package:**
   ```bash
   pip3 install dist/hex_lift-0.0.1-py3-none-any.whl
   ```

3. **Run your test script:**
   ```bash
   python3 tests/<your_script>.py
   ```

## Usage

All lift control interfaces are provided through the `LiftAPI` class:

```python
from hex_lift import PublicAPI as LiftAPI

# Initialize the API
api = LiftAPI(ws_url = "ws://172.18.20.80:8439", control_hz = 100)

# Get lift interface
lift = api.lift

# Control the lift
lift.set_target_pos(pos)
```

## Architecture

The library consists of three main modules:

### 1. public_api
- **Network Manager**: Handles Protocol Buffer message construction and WebSocket communication
- Manages data transmission to and from the lift

### 2. lift  
- **Lift Data Manager**: Continuously updates lift data in a loop
- Provides interfaces for:
  - Obtaining lift status
  - Controlling lift movement
  - Reading motor data

### 3. utils
- **General Tools**: Parameter management and common utility functions
- Provides helper functions for various operations

## Examples

See the `tests/` directory for example usage:
- `main.py` - Basic lift control example

## Requirements

- numpy>=1.17.4,<=1.26.4
- protobuf
- websockets