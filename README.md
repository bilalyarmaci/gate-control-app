# Gate Control App

A Flask-based application for automatic gate control using:

- YOLO object detection for vehicle type recognition
- License plate detection and OCR
- Arduino integration for physical gate control

## Setup

1. Install requirements:

```bash
pip install -r requirements.txt
```

2. Place your trained YOLO model at `models/best.pt`

3. Run the application:

```bash
python app.py
```

## Project Structure

- `app.py`: Main Flask application
- `test_inference.py`: Test script for YOLO model
- `static/`: Frontend files
- `models/`: YOLO model directory
