# test_inference.py
from ultralytics import YOLO
import cv2

# 1. Load your trained model
model = YOLO("models/best.pt")

# 2. Read a sample image
img = cv2.imread("tests/car1.jpg")  # put one or two test images under tests/

# 3. Run inference
results = model(img, imgsz=640)[0]

# 4. Print raw detections
for *box, conf, cls in results.boxes.cpu().numpy():
    label = model.names[int(cls)]
    print(f"{label:12s} {conf:.2f}  box={box}")

# 5. Visualize and save
annotated = results.plot()  # returns an OpenCV BGR image
cv2.imwrite("tests/car1_annotated.jpg", annotated)
print("Saved annotated to tests/car1_annotated.jpg")