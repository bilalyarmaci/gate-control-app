from flask import Flask, request, render_template, jsonify
from ultralytics import YOLO
import cv2, numpy as np, base64, serial

app = Flask(__name__, template_folder="static")

# 1) Load your trained model
# model = YOLO("models/best.pt")

# 2) (Optional) Set up your Arduino serial port
# ser = serial.Serial("/dev/ttyACM0", 9600, timeout=1)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/detect", methods=["POST"])
def detect():
    # Expecting JSON: { "image": "<base64-encoded JPEG>" }
    data = request.get_json()
    img_data = base64.b64decode(data["image"].split(",")[1])
    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # 3) Run YOLO inference
    results = model(frame, imgsz=640)[0]
    dets = []
    for *box, conf, cls in results.boxes.cpu().numpy():
        dets.append({
            "class": model.names[int(cls)],
            "conf": float(conf),
            "box": [int(b) for b in box]
        })

    # 4) Gate logic (example)
    # trucks = [d for d in dets if d["class"]=="truck"]
    # plates = [d for d in dets if d["class"]=="licence_plate"]
    # if trucks and plates:
    #     plate_crop = crop_plate(frame, plates[0]["box"])
    #     text = ocr_plate(plate_crop)
    #     if text in ALLOWED_PLATES:
    #         ser.write(b"OPEN\n")
    #     else:
    #         ser.write(b"BUZZ\n")

    return jsonify(detections=dets)

def crop_plate(img, box):
    x1,y1,x2,y2 = box
    return img[y1:y2, x1:x2]

def ocr_plate(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    from pytesseract import image_to_string
    txt = image_to_string(th, config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return txt.strip()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)