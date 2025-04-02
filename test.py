import cv2
from flask import Flask, Response

# Flask app initialization
app = Flask(__name__)

# Fire detection setup
fire_cascade = cv2.CascadeClassifier('fire_detection_cascade_model.xml')  # Adjust filename as needed
cap = cv2.VideoCapture(0)  # Use 0 for built-in camera, 1 for USB camera


# Function to generate video frames for streaming
def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            print("Failed to capture frame")
            break

        # Convert frame to grayscale for fire detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fires = fire_cascade.detectMultiScale(gray, 1.2, 5)  # Detect fire

        # Draw rectangles around detected fire
        for (x, y, w, h) in fires:
            cv2.rectangle(frame, (x - 20, y - 20), (x + w + 20, y + h + 20), (255, 0, 0), 2)
            print("Fire detected")

        # Encode frame as JPEG for streaming
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            print("Failed to encode frame")
            continue
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# Flask route for video streaming
@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# Main execution
if __name__ == '__main__':
    try:
        print("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000)  # Run Flask server
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        print("System shutdown")