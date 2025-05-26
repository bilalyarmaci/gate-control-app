from ultralytics import YOLO
import cv2
import os
import numpy as np
from glob import glob
from pathlib import Path

def load_yolo_label(label_path):
    """Load YOLO format labels"""
    if not os.path.exists(label_path):
        return []
    
    labels = []
    with open(label_path, 'r') as f:
        for line in f:
            class_id, x, y, w, h = map(float, line.strip().split())
            labels.append({
                'class_id': int(class_id),
                'bbox': [x, y, w, h]  # normalized coordinates
            })
    return labels

def test_detection():
    # Load model
    model = YOLO("models/best.pt")
    
    # Get all test images
    test_dir = Path("data/test/images")
    label_dir = Path("data/test/labels")
    test_images = list(test_dir.glob("*.jpg"))
    
    print(f"Found {len(test_images)} test images")
    
    # Create output directory
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Test statistics
    total_detections = 0
    correct_detections = 0
    
    # Test on each image
    for img_path in test_images[:5]:  # Start with first 5 images
        print(f"\nTesting: {img_path.name}")
        
        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"Failed to load image: {img_path}")
            continue
        
        # Load corresponding label
        label_path = label_dir / f"{img_path.stem}.txt"
        ground_truth = load_yolo_label(str(label_path))
        
        # Run inference
        results = model(img)
        
        # Process results
        for r in results:
            print(f"Found {len(r.boxes)} objects")
            total_detections += len(r.boxes)
            
            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                print(f"Class: {model.names[cls]} | Confidence: {conf:.2f}")
                
                # Compare with ground truth
                if any(gt['class_id'] == cls for gt in ground_truth):
                    correct_detections += 1
        
        # Save annotated image
        output_path = output_dir / img_path.name
        results[0].save(str(output_path))
        print(f"Saved annotated image to: {output_path}")
    
    # Print summary
    print("\nTest Summary:")
    print(f"Total detections: {total_detections}")
    print(f"Correct detections: {correct_detections}")
    if total_detections > 0:
        accuracy = correct_detections / total_detections * 100
        print(f"Detection accuracy: {accuracy:.2f}%")

if __name__ == "__main__":
    test_detection()