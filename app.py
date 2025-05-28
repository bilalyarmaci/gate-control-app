from flask import Flask, request, render_template, jsonify
from ultralytics import YOLO
import cv2, numpy as np, base64, serial, logging
from logging.handlers import RotatingFileHandler
import json

# or pytesseract
import easyocr

app = Flask(__name__, template_folder="static")

# Configure logging
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
)
handler.setFormatter(formatter)

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)  # Use GPU if available

# 1) Load trained model
model = YOLO("models/best.pt")

# 2) Set up Arduino serial port
ser = serial.Serial("/dev/cu.usbserial-120", 9600, timeout=1)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/detect", methods=["POST"])
def detect():
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image data received"}), 400

        # Decode image
        try:
            img_data = base64.b64decode(data["image"].split(",")[1])
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            return jsonify({"error": f"Invalid image data: {str(e)}"}), 400

        # Run YOLO inference
        results = model(frame, imgsz=640)[0]
        detections = []

        # Process detections
        if results.boxes is not None:
            boxes = results.boxes.cpu().numpy()
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                class_name = model.names[cls]
                app.logger.info(f"Detected {class_name} with confidence {conf:.2f}")
                detections.append({
                    "class": class_name,
                    "conf": conf,
                    "box": [x1, y1, x2, y2] 
                })

        # Process license plates and add OCR results
        plates = [d for d in detections if d["class"] == "license_plate"]
        for plate in plates:
            if plate["conf"] > 0.5:  # Lower threshold for processing more plates
                plate_img = crop_plate(frame, plate["box"])
                if plate_img is not None:
                    plate_text = ocr_plate(plate_img)
                    plate["ocr_text"] = plate_text if plate_text else "No text detected"
                else:
                    plate["ocr_text"] = "Failed to crop"
            else:
                plate["ocr_text"] = "Low confidence"

        if not detections:
            status = "No objects detected"
        else:
            status_parts = []
            
            # Group detections by class
            vehicles = [d for d in detections if d["class"] in ["truck", "car"]]
            plates = [d for d in detections if d["class"] == "license_plate"]
            other_objects = [d for d in detections if d["class"] not in ["truck", "car", "license_plate"]]
            
            # Add vehicle information
            if vehicles:
                for i, vehicle in enumerate(vehicles):
                    status_parts.append(f"{vehicle['class'].capitalize()} #{i+1} (conf: {vehicle['conf']:.2f})")
            
            # Add license plate information
            if plates:
                for i, plate in enumerate(plates):
                    plate_info = f"License Plate #{i+1} (conf: {plate['conf']:.2f})"
                    if "ocr_text" in plate and plate["ocr_text"]:
                        plate_info += f" - Text: '{plate['ocr_text']}'"
                    status_parts.append(plate_info)
            
            # Add other objects
            if other_objects:
                for i, obj in enumerate(other_objects):
                    status_parts.append(f"{obj['class'].capitalize()} #{i+1} (conf: {obj['conf']:.2f})")
            
            status = " | ".join(status_parts) if status_parts else "Objects detected but not classified"

        app.logger.info(f"Status: {status}")
        app.logger.info(f"Total detections: {len(detections)}")

        # Load allowed plates
        try:
            with open("allowed_plates.json") as f:
                allowed = json.load(f)
        except:
            allowed = []

        # --- Send command to Arduino based on detections ---
        action = None
        plate_text = None
        try:
            if not detections:
                ser.write(b"ERROR\n")
                action = "error"
                plate_text = None
                app.logger.info("Sent ERROR command to Arduino (no objects detected)")
            else:
                detected_classes = [d["class"] for d in detections]
                # If there's a truck detection, check its plate
                if "truck" in detected_classes:
                    plates_text = [d.get("ocr_text", "") for d in detections if d["class"] == "license_plate"]
                    # If any detected plate matches allowed list, open gate
                    match = next((text for text in plates_text if text in allowed), None)
                    if match:
                        ser.write(b"OPEN\n")
                        action = "allowed"
                        plate_text = match
                        app.logger.info("Sent OPEN command to Arduino (authorized truck)")
                    else:
                        ser.write(b"DENIED\n")
                        action = "denied"
                        plate_text = plates_text[0] if plates_text else None
                        app.logger.info("Sent DENIED command to Arduino (unauthorized truck)")
                # Car or other objects: single buzz
                elif "car" in detected_classes:
                    ser.write(b"BUZZ\n")
                    action = "buzz"
                    app.logger.info("Sent BUZZ command to Arduino (car detected)")
                else:
                    ser.write(b"BUZZ\n")
                    action = "buzz"
                    app.logger.info("Sent BUZZ command to Arduino (objects detected but none are car/truck)")
        except Exception as e:
            app.logger.error(f"Failed to send serial command: {e}")
        # --- End Arduino command block ---

        return jsonify({
            "detections": detections,
            "status": status,
            "action": action,
            "plate_text": plate_text
        })

    except Exception as e:
        app.logger.error(f"Detection error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def crop_plate(img, box):
    try:
        x1, y1, x2, y2 = box
        
        # coordinates within image bounds
        h, w = img.shape[:2]
        x1, x2 = max(0, int(x1)), min(w, int(x2))
        y1, y2 = max(0, int(y1)), min(h, int(y2))
        
        # check crop area is valid
        if x2 <= x1 or y2 <= y1:
            app.logger.warning("Invalid crop dimensions")
            return None
        
        padding_x = max(5, int((x2 - x1) * 0.1))
        padding_y = max(3, int((y2 - y1) * 0.1))
        
        x1_padded = max(0, x1 - padding_x)
        y1_padded = max(0, y1 - padding_y)
        x2_padded = min(w, x2 + padding_x)
        y2_padded = min(h, y2 + padding_y)
        
        crop = img[y1_padded:y2_padded, x1_padded:x2_padded]
        
        app.logger.info(f"Cropped plate: original box=({x1},{y1},{x2},{y2}), padded=({x1_padded},{y1_padded},{x2_padded},{y2_padded}), crop_shape={crop.shape}")
        
        return crop
        
    except Exception as e:
        app.logger.error(f"Error cropping plate: {str(e)}")
        return None

def ocr_plate(crop):
    try:
        if crop is None or crop.size == 0:
            app.logger.warning("Empty crop received for OCR")
            return ""
            
        app.logger.info(f"Original crop shape: {crop.shape}")
        
        # Save original crop for debugging
        cv2.imwrite('debug_original_crop.jpg', crop)
        
        # Initialize variables for best result
        best_text = ""
        best_confidence = 0
        
        # Try multiple preprocessing approaches
        variants = []
        
        # 1. Original resized image (color)
        scale_factor = 2
        resized = cv2.resize(crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        variants.append(('original', resized))
        
        # 2. Enhanced grayscale
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_gray = clahe.apply(gray)
        variants.append(('enhanced_gray', enhanced_gray))
        
        # 3. Thresholded version
        _, thresh1 = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(('threshold', thresh1))
        
        # 4. Denoised version
        denoised = cv2.fastNlMeansDenoisingColored(resized, None, 10, 10, 7, 21)
        variants.append(('denoised', denoised))
        
        # OCR on all variants
        for variant_name, img in variants:
            # Save debug image
            cv2.imwrite(f'debug_{variant_name}.jpg', img)
            
            # Run EasyOCR
            results = reader.readtext(img)
            
            for (bbox, text, prob) in results:
                app.logger.info(f"EasyOCR ({variant_name}) result: '{text}' with confidence {prob:.2f}")
                
                # Clean the detected text
                cleaned_text = ''.join(c for c in text if c.isalnum() or c.isspace())
                
                # Update best result if this has higher confidence
                if prob > best_confidence and cleaned_text:
                    best_confidence = prob
                    best_text = cleaned_text
        
        if best_text:
            app.logger.info(f"Best OCR Result: {best_text} (confidence: {best_confidence:.2f})")
            return best_text
        
        app.logger.warning("No text detected by any OCR attempt")
        return ""

    except Exception as e:
        app.logger.error(f"OCR error: {str(e)}")
        return ""

@app.route("/plates", methods=["GET", "POST"])
def manage_plates():
    if request.method == "POST":
        data = request.get_json()
        with get_db() as db:
            db.execute(
                "INSERT INTO authorized_plates (plate_number, vehicle_type) VALUES (?, ?)",
                (data["plate"], data["type"])
            )
            db.commit()
        return jsonify({"status": "success"})
    
    with get_db() as db:
        plates = db.execute("SELECT * FROM authorized_plates").fetchall()
    return render_template("plates.html", plates=plates)

@app.route("/update_allowed", methods=["POST"])
def update_allowed():
    data = request.get_json() or {}
    plates = data.get("plates", [])
    try:
        with open("allowed_plates.json", "w") as f:
            json.dump(plates, f)
        return jsonify({"status": "success"})
    except Exception as e:
        app.logger.error(f"Failed to update allowed plates: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)