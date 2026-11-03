# Assistive Vision YOLOv8 FastAPI Server

This directory contains the Python FastAPI backend server for offloaded real-time vision inference (Mode B) for the ESP32-CAM.

## Prerequisites & Installation

1. Install Python 3.9+ and pip.
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Server

Start the FastAPI server on port 8000:
```bash
python app.py
```
Or using Uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

The server automatically downloads the `yolov8n.pt` pre-trained weights on its first launch.

## Testing the Endpoint

With the server running, test the endpoint with the provided synthetic image script:
```bash
python test_server.py
```

## API Specification

- **Endpoint:** `POST /detect`
- **Content-Type:** `image/jpeg` (raw JPEG body) or `multipart/form-data`
- **Response Format:**
  ```json
  [
    {
      "label": "chair",
      "confidence": 0.88,
      "position": "center"
    },
    {
      "label": "person",
      "confidence": 0.92,
      "position": "left"
    }
  ]
  ```
