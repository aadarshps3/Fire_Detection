import cv2
import RPi.GPIO as GPIO
import time
from flask import Flask, Response

# Flask app initialization
app = Flask(__name__)

# GPIO setup
SERVO_PIN = 17  # Servo motor GPIO pin
VALVE_PIN = 23  # Solenoid valve (Relay) GPIO pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(VALVE_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz PWM frequency
servo.start(0)  # Start with duty cycle 0

# Fire detection setup
fire_cascade = cv2.CascadeClassifier('fire_detection_cascade_model.xml')  # Adjust filename as needed
cap = cv2.VideoCapture(0)  # Use 0 for built-in camera, 1 for USB camera


# Function to rotate servo based on direction
def rotate_servo(direction):
    if direction == "left":
        duty_cycle = 7  # Left position
    elif direction == "right":
        duty_cycle = 12  # Right position
    else:
        duty_cycle = 10  # Center position
    servo.ChangeDutyCycle(duty_cycle)
    time.sleep(1)  # Wait for servo to move
    servo.ChangeDutyCycle(0)  # Stop servo


# Function to control solenoid valve
def control_solenoid(valve_state):
    if valve_state == "open":
        GPIO.output(VALVE_PIN, GPIO.HIGH)
        print("Solenoid Valve Opened")
    else:
        GPIO.output(VALVE_PIN, GPIO.LOW)
        print("Solenoid Valve Closed")


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

        fire_detected = len(fires) > 0
        for (x, y, w, h) in fires:
            # Draw rectangle around detected fire
            cv2.rectangle(frame, (x - 20, y - 20), (x + w + 20, y + h + 20), (255, 0, 0), 2)
            print("Fire detected")

            # Rotate servo based on fire position (assuming 640x480 resolution)
            if x < 320:  # Fire on left
                rotate_servo("left")
            elif x > 320:  # Fire on right
                rotate_servo("right")
            else:
                rotate_servo("center")

            # Open solenoid valve
            control_solenoid("open")

        # If no fire detected, close solenoid valve
        if not fire_detected:
            control_solenoid("close")
            rotate_servo("center")  # Reset servo to center

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
        servo.stop()
        GPIO.cleanup()
        print("System shutdown")