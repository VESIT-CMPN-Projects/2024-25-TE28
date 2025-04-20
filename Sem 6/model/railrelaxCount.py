from flask import Flask, Response, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import cvlib as cv
from tensorflow.keras.preprocessing.image import img_to_array
from tensorflow.keras.models import load_model
import threading

# Load the gender detection model
gender_model = load_model('C:/Users/tejas/Downloads/final gender/final gender/gender_detection.h5')
gender_classes = ['man', 'woman']

# Load pre-trained YOLO model
weights_path = "final gender/yolov3.weights"
config_path = "final gender/yolov3.cfg"
names_path = "final gender/coco.names"

net = cv2.dnn.readNet(weights_path, config_path)
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# Load COCO class labels
with open(names_path, "r") as f:
    classes = [line.strip() for line in f.readlines()]

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

people_count = 0

def capture_and_process_video():
    global people_count

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture image")
            break

        height, width, channels = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(output_layers)

        # Arrays for detected objects
        class_ids = []
        confidences = []
        boxes = []

        # Analyze each detection
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5 and classes[class_id] == "person":
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # Apply Non-Maximum Suppression
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

        # Reset people count
        people_count = 0

        if len(indexes) > 0:
            for i in indexes:
                people_count += 1

        # To stream the video, yield the frame
        ret, jpeg = cv2.imencode('.jpg', frame)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    cap.release()

@app.route('/video_feed')
def video_feed():
    return Response(capture_and_process_video(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_count', methods=['GET'])
def get_count():
    global people_count
    return jsonify({"people_count": people_count})

if __name__ == '__main__':
    # Start the Flask server
    app.run(host='0.0.0.0', port=5000, threaded=True)
